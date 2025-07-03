#!/usr/bin/env python3
"""
Web Project Task Orchestrator using cc_execute pattern.
Executes tasks sequentially using Claude Code instances with two-stage evaluation.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.core.client import WebSocketClient
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


class WebProjectOrchestrator:
    """Orchestrates web project setup tasks using cc_execute pattern."""
    
    def __init__(self, host: str = "localhost", port: int = 8004):
        self.client = WebSocketClient(host=host, port=port)
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.task_results = []
        
    async def cc_execute(self, task: dict) -> dict:
        """
        Execute a task using cc_execute pattern via WebSocket.
        Implements Stage 1 evaluation inside Claude instance.
        """
        # Build the cc_execute prompt with self-reflection
        cc_execute_prompt = f"""
{task['prompt']}

After providing your answer, evaluate it against these criteria:
{chr(10).join(f"{i+1}. {criterion}" for i, criterion in enumerate(task['success_criteria']))}

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as 'Initial Response:' and 'Improved Response:' if needed.
Maximum self-improvements: 2

IMPORTANT: Follow these guidelines from CLAUDE_CODE_PROMPT_RULES.md:
- Provide complete, working code examples
- Use proper Python syntax and imports
- Include error handling where appropriate
- Add helpful comments to explain the code
- For web-related tasks, use modern best practices
"""
        
        # Add metadata for categorization
        full_command = f'claude -p "[category:{task["category"]}][task_id:{task["id"]}] {cc_execute_prompt}" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
        
        logger.info(f"[TASK {task['id']}] Executing: {task['name']}")
        
        try:
            # Execute via WebSocket (let Redis determine timeout if not specified)
            result = await self.client.execute_command(
                command=full_command,
                timeout=task.get('timeout'),  # None means Redis decides
                restart_handler=False
            )
            
            # Stage 1 evaluation (basic success/failure)
            stage1_eval = {
                'success': result['success'],
                'has_output': bool(result.get('output_data')),
                'has_error': bool(result.get('error')),
                'duration': result.get('duration', 0)
            }
            
            # Parse output for Stage 2 evaluation
            output_text = '\n'.join(result.get('output_data', []))
            
            # Check for improved response pattern
            has_improvement = 'Improved Response:' in output_text
            
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'stage1_evaluation': stage1_eval,
                'output': output_text,
                'has_self_improvement': has_improvement,
                'raw_result': result
            }
            
        except Exception as e:
            logger.error(f"[TASK {task['id']}] Execution failed: {e}")
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'stage1_evaluation': {'success': False, 'error': str(e)},
                'output': '',
                'has_self_improvement': False,
                'raw_result': {'success': False, 'error': str(e)}
            }
    
    def stage2_evaluation(self, task: dict, cc_result: dict) -> dict:
        """
        Stage 2 evaluation by orchestrator.
        Evaluates if output meets success criteria.
        """
        output = cc_result['output'].lower()
        criteria_results = []
        
        for criterion in task['success_criteria']:
            criterion_lower = criterion.lower()
            met = False
            
            # Smart evaluation based on criterion type
            if 'must contain' in criterion_lower:
                # Extract what must be contained
                target = criterion_lower.split('must contain')[-1].strip()
                # Handle code-specific checks
                if 'import' in target:
                    imports = target.replace('and', ',').split(',')
                    met = all(imp.strip() in output for imp in imports)
                else:
                    met = target in output
                    
            elif 'should' in criterion_lower:
                # Less strict - look for key concepts
                if 'create' in criterion_lower:
                    keywords = ['mkdir', 'makedirs', 'create', 'path']
                    met = any(kw in output for kw in keywords)
                elif 'implement' in criterion_lower or 'include' in criterion_lower:
                    target = criterion_lower.split('implement')[-1].split('include')[-1].strip()
                    met = target in output
                else:
                    # Generic should check
                    key_parts = criterion_lower.split('should')[-1].strip().split()
                    met = any(part in output for part in key_parts if len(part) > 3)
                    
            elif 'must have' in criterion_lower or 'must include' in criterion_lower:
                target = criterion_lower.split('must have')[-1].split('must include')[-1].strip()
                met = target in output
                
            else:
                # Default: check if key terms from criterion appear in output
                key_terms = [term for term in criterion.split() if len(term) > 4]
                met = any(term.lower() in output for term in key_terms)
            
            criteria_results.append({
                'criterion': criterion,
                'met': met
            })
        
        # Calculate overall success
        total_criteria = len(criteria_results)
        met_criteria = sum(1 for c in criteria_results if c['met'])
        success_rate = met_criteria / total_criteria if total_criteria > 0 else 0
        
        # Determine if retry is needed
        needs_retry = success_rate < 0.8  # 80% threshold
        
        # Generate improvement suggestions
        missing_criteria = [c['criterion'] for c in criteria_results if not c['met']]
        suggestions = []
        
        for missing in missing_criteria:
            if 'import' in missing.lower():
                suggestions.append(f"Add the required imports: {missing}")
            elif 'endpoint' in missing.lower():
                suggestions.append(f"Implement the missing endpoint: {missing}")
            elif 'docker' in missing.lower():
                suggestions.append(f"Include Docker configuration: {missing}")
            else:
                suggestions.append(f"Address: {missing}")
        
        return {
            'success': success_rate >= 0.8,
            'success_rate': success_rate,
            'criteria_results': criteria_results,
            'needs_retry': needs_retry,
            'suggestions': suggestions,
            'missing_criteria': missing_criteria
        }
    
    async def execute_task_with_retry(self, task: dict, max_retries: int = 2) -> dict:
        """Execute a task with retry logic based on evaluation."""
        attempt = 0
        task_copy = task.copy()
        
        while attempt <= max_retries:
            attempt += 1
            logger.info(f"[TASK {task['id']}] Attempt {attempt}/{max_retries + 1}")
            
            # Execute with cc_execute
            cc_result = await self.cc_execute(task_copy)
            
            # Stage 2 evaluation
            stage2_eval = self.stage2_evaluation(task, cc_result)
            
            # Combine evaluations
            final_result = {
                'task': task,
                'attempt': attempt,
                'cc_execute_result': cc_result,
                'stage2_evaluation': stage2_eval,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check if successful or last attempt
            if stage2_eval['success'] or attempt > max_retries:
                if stage2_eval['success']:
                    logger.success(f"[TASK {task['id']}] Completed successfully!")
                else:
                    logger.warning(f"[TASK {task['id']}] Failed after {attempt} attempts")
                
                # Save task output to file
                output_file = self.results_dir / f"{task['id']}_{task['name'].replace(' ', '_').lower()}.md"
                with open(output_file, 'w') as f:
                    f.write(f"# {task['name']}\n\n")
                    f.write(f"**Task ID**: {task['id']}\n")
                    f.write(f"**Category**: {task['category']}\n")
                    f.write(f"**Success**: {'✅' if stage2_eval['success'] else '❌'}\n")
                    f.write(f"**Success Rate**: {stage2_eval['success_rate']:.1%}\n\n")
                    f.write("## Output\n\n")
                    f.write("```\n")
                    f.write(cc_result['output'])
                    f.write("\n```\n\n")
                    f.write("## Evaluation\n\n")
                    for cr in stage2_eval['criteria_results']:
                        f.write(f"- {'✅' if cr['met'] else '❌'} {cr['criterion']}\n")
                
                return final_result
            
            # Refine prompt for retry
            logger.info(f"[TASK {task['id']}] Refining prompt for retry...")
            missing_parts = '\n'.join(f"- {s}" for s in stage2_eval['suggestions'])
            
            task_copy['prompt'] = f"""{task['prompt']}

IMPORTANT: Your previous attempt was incomplete. Please ensure you address these specific requirements:
{missing_parts}

Remember to provide COMPLETE, WORKING code that satisfies ALL the criteria listed above."""
            
            # Brief pause before retry
            await asyncio.sleep(2)
        
        return final_result
    
    async def run_all_tasks(self):
        """Execute all tasks in the web project sequence."""
        # Load tasks
        tasks_file = Path(__file__).parent / "web_project_tasks.json"
        with open(tasks_file) as f:
            task_data = json.load(f)
        
        tasks = task_data['task_list']['tasks']
        
        logger.info(f"Starting {len(tasks)} web project tasks...")
        
        # Execute tasks sequentially
        for i, task in enumerate(tasks):
            logger.info(f"\n{'='*60}")
            logger.info(f"Task {i+1}/{len(tasks)}: {task['name']}")
            logger.info(f"{'='*60}")
            
            result = await self.execute_task_with_retry(task)
            self.task_results.append(result)
            
            # Brief pause between tasks
            if i < len(tasks) - 1:
                await asyncio.sleep(3)
        
        # Generate summary report
        await self.generate_summary_report()
        
    async def generate_summary_report(self):
        """Generate a comprehensive summary report."""
        report_file = self.results_dir / "web_project_summary.md"
        
        total_tasks = len(self.task_results)
        successful_tasks = sum(1 for r in self.task_results if r['stage2_evaluation']['success'])
        
        with open(report_file, 'w') as f:
            f.write("# Web Project Tasks Summary Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Tasks**: {total_tasks}\n")
            f.write(f"**Successful**: {successful_tasks} ({successful_tasks/total_tasks:.1%})\n")
            f.write(f"**Failed**: {total_tasks - successful_tasks}\n\n")
            
            f.write("## Task Results\n\n")
            
            # Group by category
            categories = {}
            for result in self.task_results:
                cat = result['task']['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(result)
            
            # Write results by category
            for category, results in categories.items():
                f.write(f"### {category.replace('_', ' ').title()}\n\n")
                
                for r in results:
                    task = r['task']
                    eval2 = r['stage2_evaluation']
                    
                    f.write(f"#### {task['name']} ({task['id']})\n")
                    f.write(f"- **Success**: {'✅' if eval2['success'] else '❌'}\n")
                    f.write(f"- **Success Rate**: {eval2['success_rate']:.1%}\n")
                    f.write(f"- **Attempts**: {r['attempt']}\n")
                    f.write(f"- **Duration**: {r['cc_execute_result']['stage1_evaluation'].get('duration', 0):.1f}s\n")
                    
                    if not eval2['success']:
                        f.write(f"- **Missing Criteria**:\n")
                        for mc in eval2['missing_criteria']:
                            f.write(f"  - {mc}\n")
                    
                    f.write("\n")
            
            # Overall statistics
            f.write("## Performance Statistics\n\n")
            total_duration = sum(r['cc_execute_result']['stage1_evaluation'].get('duration', 0) 
                               for r in self.task_results)
            avg_duration = total_duration / len(self.task_results) if self.task_results else 0
            
            f.write(f"- **Total Execution Time**: {total_duration:.1f}s\n")
            f.write(f"- **Average Task Duration**: {avg_duration:.1f}s\n")
            f.write(f"- **Tasks with Self-Improvement**: {sum(1 for r in self.task_results if r['cc_execute_result']['has_self_improvement'])}\n")
            
            # Save detailed results
            detailed_file = self.results_dir / "detailed_results.json"
            with open(detailed_file, 'w') as df:
                json.dump(self.task_results, df, indent=2)
            
            f.write(f"\n## Detailed Results\n\n")
            f.write(f"Full execution details saved to: `{detailed_file.name}`\n")
        
        logger.success(f"Summary report generated: {report_file}")


async def main():
    """Main entry point."""
    orchestrator = WebProjectOrchestrator()
    
    try:
        await orchestrator.run_all_tasks()
        logger.success("All tasks completed!")
        
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        raise
    finally:
        # Ensure client is closed
        if orchestrator.client._client:
            await orchestrator.client._client.close()


if __name__ == "__main__":
    asyncio.run(main())