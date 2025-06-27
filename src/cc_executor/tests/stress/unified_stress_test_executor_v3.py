#!/usr/bin/env python3
"""
Unified Stress Test Executor V3 - With Full Response Capture and Reporting
This version captures the ACTUAL responses from Claude, not just pattern matching.
"""

import asyncio
import json
import time
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import websockets
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class UnifiedStressTestExecutorV3:
    def __init__(self, task_file: str):
        """Initialize with comprehensive response capture"""
        self.task_file = task_file
        self.tasks = self.load_tasks()
        self.results = defaultdict(list)
        self.captured_responses = {}  # Store full responses
        self.execution_start = None
        self.execution_end = None
        
        # Create output directory for captured responses
        self.output_dir = Path("stress_test_outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Response capture settings
        self.max_response_display = 500  # Characters to show in summary
        self.save_full_responses = True
        
    def load_tasks(self) -> Dict[str, Any]:
        """Load task definitions from JSON file"""
        with open(self.task_file, 'r') as f:
            return json.load(f)
    
    async def execute_single_task(self, category: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task and capture FULL response"""
        task_id = task['id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        marker = f"MARKER_{timestamp}_{task_id}"
        
        # Prepare request with marker
        payload = task['json_payload'].copy()
        payload['question'] = f"{marker}\n\n{payload['question']}"
        
        print(f"\n{'='*80}")
        print(f"Executing Task: {task['name']} (ID: {task_id}) from category: {category}")
        print(f"Marker: {marker}")
        print(f"Request: {task['natural_language_request'][:80]}...")
        
        result = {
            'task_id': task_id,
            'task_name': task['name'],
            'category': category,
            'marker': marker,
            'start_time': time.time(),
            'request': task['natural_language_request'],
            'response_chunks': [],
            'full_response': "",
            'pattern_matches': {},
            'success': False,
            'error': None,
            'duration': 0
        }
        
        try:
            # Calculate timeout
            timeout = self.calculate_timeout(category, task_id, task)
            
            # Connect to WebSocket
            ws_url = "ws://localhost:8003/ws/mcp"
            
            async with websockets.connect(ws_url) as websocket:
                # Wait for connection message
                connect_msg = await websocket.recv()
                connect_data = json.loads(connect_msg)
                
                if connect_data.get('method') == 'connected':
                    session_id = connect_data['params']['session_id']
                    print(f"✓ Connected to WebSocket. Session: {session_id}")
                
                # Send execute command - invoke Claude Code CLI directly
                # Create a prompt that includes the marker and question
                full_prompt = f"{marker}\\n\\n{payload['question']}"
                # Escape for shell - double quotes to preserve newlines
                prompt_escaped = full_prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                
                # Build command to invoke Claude Code
                # Use stream-json for better progress visibility (shows when Claude starts responding)
                command = f'bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH claude -p --output-format stream-json --verbose \\"{prompt_escaped}\\""'
                
                execute_msg = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "execute",
                    "params": {
                        "command": command
                    }
                }
                
                await websocket.send(json.dumps(execute_msg))
                print(f"→ Sent task command")
                
                # Collect all responses with timeout
                start_time = time.time()
                while True:
                    try:
                        if time.time() - start_time > timeout:
                            raise asyncio.TimeoutError(f"Timeout after {timeout}s")
                            
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        result['response_chunks'].append(response_data)
                        
                        # Process different message types
                        if response_data.get('method') == 'process.output':
                            data = response_data['params'].get('data', '')
                            if data:
                                result['full_response'] += data
                                
                                # Handle stream-json format - parse JSON events
                                if '--output-format stream-json' in command:
                                    try:
                                        for line in data.strip().split('\n'):
                                            if line.strip():
                                                event = json.loads(line)
                                                event_type = event.get('type', '')
                                                
                                                # Show progress based on event type
                                                if event_type == 'system':
                                                    print("\n🔄 Claude initializing...", flush=True)
                                                elif event_type == 'assistant':
                                                    # Extract actual content
                                                    msg = event.get('message', {})
                                                    content = msg.get('content', [])
                                                    for item in content:
                                                        if item.get('type') == 'text':
                                                            text = item.get('text', '')
                                                            if text and marker not in text:  # Don't show marker echo
                                                                print(f"\n✍️  Claude: {text}", flush=True)
                                                        elif item.get('type') == 'tool_use':
                                                            print(f"\n🔧 Claude using tool: {item.get('name')}", flush=True)
                                                elif event_type == 'result':
                                                    # Final result
                                                    result_text = event.get('result', '')
                                                    if result_text and marker not in result_text:
                                                        print(f"\n✅ Final output received ({len(result_text)} chars)", flush=True)
                                    except json.JSONDecodeError:
                                        # Not JSON, just print as-is
                                        print(data, end="", flush=True)
                                else:
                                    # Regular text output
                                    print(data, end="", flush=True)
                                    
                        elif response_data.get('method') == 'process.completed':
                            exit_code = response_data['params'].get('exit_code')
                            print(f"\n✓ Process completed with exit code: {exit_code}")
                            break
                            
                        elif response_data.get('error'):
                            result['error'] = response_data['error']
                            print(f"\n❌ Error: {response_data['error']}")
                            break
                            
                    except asyncio.TimeoutError:
                        if time.time() - start_time > timeout:
                            raise
                        continue
            
            print(f"\n✅ Response captured: {len(result['full_response'])} characters")
            
            # Verify patterns in full response
            for pattern in task['verification']['expected_patterns']:
                found = pattern.lower() in result['full_response'].lower()
                result['pattern_matches'][pattern] = found
                status = "✓" if found else "✗"
                print(f"  {status} Pattern '{pattern}': {'Found' if found else 'Not found'}")
            
            # Check if response was captured in transcript
            result['transcript_verified'] = await self.verify_in_transcript(marker)
            
            # Only mark as successful if response captured
            result['success'] = len(result['full_response']) > 0
            
        except asyncio.TimeoutError:
            result['error'] = f"Timeout after {timeout}s"
            print(f"\n❌ Task timed out after {timeout}s")
        except Exception as e:
            result['error'] = str(e)
            print(f"\n❌ Task failed: {e}")
        
        result['end_time'] = time.time()
        result['duration'] = result['end_time'] - result['start_time']
        
        # Save full response to file
        if self.save_full_responses and result['full_response']:
            response_file = self.output_dir / f"{category}_{task_id}_{timestamp}.txt"
            with open(response_file, 'w') as f:
                f.write(f"Task: {task['name']}\n")
                f.write(f"Category: {category}\n")
                f.write(f"Request: {task['natural_language_request']}\n")
                f.write(f"Marker: {marker}\n")
                f.write(f"Duration: {result['duration']:.2f}s\n")
                f.write("="*80 + "\n\n")
                f.write(result['full_response'])
            print(f"  📄 Full response saved to: {response_file}")
        
        return result
    
    def calculate_timeout(self, category: str, task_id: str, task: Dict[str, Any]) -> float:
        """Calculate timeout with Redis lookup"""
        base_timeout = 300  # 5 minutes minimum for MCP
        
        # Try Redis for historical data
        try:
            result = subprocess.run(
                ['/home/graham/.claude/commands/check-task-timeout', category, task_id, str(base_timeout)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                redis_timeout = float(result.stdout.strip())
                print(f"Using Redis historical timeout: {redis_timeout}s")
                return redis_timeout
        except:
            pass
        
        # Fallback to complexity-based calculation
        complexity = self.calculate_complexity(task['natural_language_request'])
        calculated_timeout = base_timeout + (complexity * 10)
        print(f"Calculated timeout: {calculated_timeout}s (complexity: {complexity})")
        return calculated_timeout
    
    def calculate_complexity(self, request: str) -> int:
        """Calculate task complexity score"""
        score = 0
        
        # Length factor
        words = len(request.split())
        score += words // 50
        
        # Keywords that indicate complexity
        complex_keywords = ['simultaneous', 'multiple', 'comprehensive', 'detailed', 
                          'analyze', 'compare', 'create', 'guide', 'explain',
                          '100', '1000', '10000', 'all', 'every', 'complete']
        
        for keyword in complex_keywords:
            if keyword in request.lower():
                score += 3
        
        return min(score, 50)  # Cap at 50
    
    async def verify_in_transcript(self, marker: str) -> bool:
        """Verify execution in transcript"""
        try:
            cmd = f'rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and marker in result.stdout
        except:
            return False
    
    async def run_category(self, category: str, tasks: List[Dict[str, Any]]) -> None:
        """Run all tasks in a category"""
        print(f"\n{'#'*80}")
        print(f"# Running Category: {category}")
        print(f"# Description: {self.tasks['categories'][category]['description']}")
        print(f"# Tasks: {len(tasks)}")
        print(f"{'#'*80}")
        
        # Run tasks with limited concurrency
        exec_cfg = self.tasks.get('execution_config', {})
        max_concurrent = min(3, exec_cfg.get('max_concurrent', 5))
        
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            results = await asyncio.gather(
                *[self.execute_single_task(category, task) for task in batch],
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"Task failed with exception: {result}")
                else:
                    self.results[category].append(result)
                    # Record to Redis if successful
                    if result['success']:
                        await self.record_to_redis(category, result['task_id'], 
                                                 result.get('timeout', 300), 
                                                 result['duration'])
    
    async def record_to_redis(self, category: str, task_id: str, expected: float, actual: float) -> None:
        """Record execution time to Redis"""
        try:
            subprocess.run([
                '/home/graham/.claude/commands/record-task-time',
                category, task_id, str(expected), str(actual), 'true'
            ], timeout=5)
        except:
            pass
    
    def generate_detailed_report(self) -> str:
        """Generate comprehensive report with actual responses"""
        report = []
        report.append("="*80)
        report.append("UNIFIED STRESS TEST DETAILED REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Task File: {self.task_file}")
        report.append(f"Total Duration: {(self.execution_end - self.execution_start):.2f}s")
        report.append("")
        
        # Summary statistics
        total_tasks = sum(len(tasks) for tasks in self.results.values())
        successful_tasks = sum(1 for tasks in self.results.values() for t in tasks if t['success'])
        
        report.append(f"Total Tasks: {total_tasks}")
        report.append(f"Successful: {successful_tasks}")
        report.append(f"Failed: {total_tasks - successful_tasks}")
        report.append(f"Success Rate: {(successful_tasks/total_tasks*100):.1f}%")
        report.append("")
        
        # Category breakdown with actual responses
        for category, tasks in self.results.items():
            report.append(f"\n{'='*80}")
            report.append(f"CATEGORY: {category}")
            report.append(f"{'='*80}")
            
            for task in tasks:
                report.append(f"\n{'─'*60}")
                report.append(f"Task: {task['task_name']} (ID: {task['task_id']})")
                report.append(f"Duration: {task['duration']:.2f}s")
                report.append(f"Success: {'✅ Yes' if task['success'] else '❌ No'}")
                
                if task['error']:
                    report.append(f"Error: {task['error']}")
                
                report.append(f"\nRequest: {task['request'][:200]}...")
                
                # Pattern matching results
                report.append("\nPattern Verification:")
                for pattern, found in task['pattern_matches'].items():
                    status = "✓" if found else "✗"
                    report.append(f"  {status} '{pattern}'")
                
                # Show response preview
                if task['full_response']:
                    report.append(f"\nResponse Preview ({len(task['full_response'])} chars total):")
                    preview = task['full_response'][:self.max_response_display]
                    if len(task['full_response']) > self.max_response_display:
                        preview += "...\n[Response truncated - see full file in stress_test_outputs/]"
                    report.append("-" * 60)
                    report.append(preview)
                    report.append("-" * 60)
                
                report.append(f"\nTranscript Verified: {'✓ Yes' if task.get('transcript_verified') else '✗ No'}")
        
        # Summary table
        report.append(f"\n{'='*80}")
        report.append("SUMMARY BY CATEGORY")
        report.append("="*80)
        report.append(f"{'Category':<25} {'Total':<10} {'Success':<10} {'Failed':<10} {'Avg Time':<10}")
        report.append("-"*65)
        
        for category, tasks in self.results.items():
            total = len(tasks)
            success = sum(1 for t in tasks if t['success'])
            failed = total - success
            avg_time = sum(t['duration'] for t in tasks) / total if total > 0 else 0
            report.append(f"{category:<25} {total:<10} {success:<10} {failed:<10} {avg_time:<10.2f}s")
        
        return "\n".join(report)
    
    async def run_all_tests(self, categories: Optional[List[str]] = None) -> None:
        """Run all stress tests with full response capture"""
        self.execution_start = time.time()
        
        # Determine which categories to run
        if categories:
            categories_to_run = {k: v for k, v in self.tasks['categories'].items() if k in categories}
        else:
            categories_to_run = self.tasks['categories']
        
        # Run each category
        for category, config in categories_to_run.items():
            await self.run_category(category, config['tasks'])
        
        self.execution_end = time.time()
        
        # Generate and save report
        report = self.generate_detailed_report()
        
        # Save report
        report_file = f"stress_test_detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n{'='*80}")
        print(f"📊 Detailed report saved to: {report_file}")
        print(f"📁 Full responses saved to: {self.output_dir}/")
        
        # Also save JSON summary
        json_report = {
            'execution_time': self.execution_end - self.execution_start,
            'categories': {}
        }
        
        for category, tasks in self.results.items():
            json_report['categories'][category] = {
                'total': len(tasks),
                'successful': sum(1 for t in tasks if t['success']),
                'tasks': [
                    {
                        'id': t['task_id'],
                        'name': t['task_name'],
                        'success': t['success'],
                        'duration': t['duration'],
                        'response_length': len(t['full_response']),
                        'patterns_found': sum(1 for found in t['pattern_matches'].values() if found),
                        'patterns_total': len(t['pattern_matches']),
                        'error': t.get('error')
                    }
                    for t in tasks
                ]
            }
        
        json_file = f"stress_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        print(f"📄 JSON summary saved to: {json_file}")


async def main():
    """Main entry point"""
    task_file = sys.argv[1] if len(sys.argv) > 1 else "unified_stress_test_tasks.json"
    categories = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    
    if not os.path.exists(task_file):
        # Try relative paths
        possible_paths = [
            task_file,
            f"../../tasks/{task_file}",
            f"src/cc_executor/tasks/{task_file}",
            f"/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/{task_file}"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                task_file = path
                break
        else:
            print(f"Error: Task file not found: {task_file}")
            sys.exit(1)
    
    print(f"Loading tasks from: {task_file}")
    executor = UnifiedStressTestExecutorV3(task_file)
    
    print(f"Loaded task list: {executor.tasks['task_list_id']}")
    print(f"Description: {executor.tasks['description']}")
    
    await executor.run_all_tests(categories)


if __name__ == "__main__":
    asyncio.run(main())