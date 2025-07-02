#!/usr/bin/env python3
"""Execute the improved task list following cc_execute.md pattern."""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cc_executor.client.websocket_client_standalone import WebSocketClient

class TaskExecutor:
    def __init__(self):
        self.client = WebSocketClient(host="localhost", port=8004)
        self.results = []
        
    async def execute_task(self, task_num: int, task_desc: str, timeout: int, criteria: list, retry_strategy: str):
        """Execute a single task following cc_execute.md pattern."""
        
        print(f"\n{'='*60}")
        print(f"Task {task_num} Update: Starting")
        print(f"{'='*60}")
        print(f"Description: {task_desc}")
        
        # Build Claude command based on task type
        if task_desc.startswith("Create"):
            prompt = f"What is a {task_desc[7:]}? Show the complete code/content and create the file."
        elif task_desc.startswith("Run"):
            prompt = f"What happens when I {task_desc[4:]}? Execute it and show the output."
        elif task_desc.startswith("Check"):
            prompt = f"How do I {task_desc}? Execute the command and show the result."
        else:
            prompt = f"What is {task_desc}?"
            
        cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools Bash,Read,Write --dangerously-skip-permissions'
        
        print(f"Timeout: {timeout}s")
        print("Executing via WebSocket...")
        
        start_time = datetime.now()
        
        # Attempt 1
        result = await self.client.execute_command(cmd, timeout=timeout)
        
        if not result.get('success', False):
            print(f"❌ Execution failed: {result.get('error', 'Unknown error')}")
            
            # Check for retry hints
            if 'token limit' in str(result.get('error', '')):
                print("Retrying with shorter response request...")
                prompt += " Keep the response concise."
                cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools Bash,Read,Write --dangerously-skip-permissions'
                result = await self.client.execute_command(cmd, timeout=timeout)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Parse response
        if result.get('success'):
            output_data = result.get('output_data', [])
            parsed = self.parse_response(output_data)
            
            print("\nResponse received:")
            print("-" * 40)
            print(parsed['text'][:500] + "..." if len(parsed['text']) > 500 else parsed['text'])
            print("-" * 40)
            
            # Evaluate criteria
            success, failed = self.evaluate_criteria(parsed['text'], criteria)
            
            print("\nEvaluation:")
            for i, criterion in enumerate(criteria):
                status = "✅" if criterion not in failed else "❌"
                print(f"  {status} {criterion}")
            
            if not success and retry_strategy:
                print(f"\nRetrying with strategy: {retry_strategy}")
                # Would retry here with refined prompt
            
            self.results.append({
                'task': task_num,
                'success': success,
                'duration': duration,
                'failed_criteria': failed
            })
            
            print(f"\nTask {task_num} Update: {'Completed ✅' if success else 'Failed ❌'}")
            print(f"Duration: {duration:.1f}s")
            
        else:
            self.results.append({
                'task': task_num,
                'success': False,
                'duration': duration,
                'error': result.get('error', 'Unknown error')
            })
            print(f"\nTask {task_num} Update: Failed ❌")
    
    def parse_response(self, output_data: list) -> dict:
        """Parse Claude's JSON stream output."""
        content = []
        tool_uses = []
        
        for line in output_data:
            try:
                data = json.loads(line)
                if data.get('type') == 'assistant' and 'content' in data.get('message', {}):
                    for item in data['message']['content']:
                        if item.get('type') == 'text':
                            content.append(item['text'])
                        elif item.get('type') == 'tool_use':
                            tool_uses.append(item)
            except:
                pass
                
        return {
            'text': '\n'.join(content),
            'tools': tool_uses
        }
    
    def evaluate_criteria(self, output: str, criteria: list) -> tuple[bool, list]:
        """Evaluate output against success criteria."""
        failed = []
        output_lower = output.lower()
        
        for criterion in criteria:
            criterion_lower = criterion.lower()
            met = False
            
            # File existence
            if "exists" in criterion_lower and "file" in criterion_lower:
                # Extract filename
                words = criterion.split()
                for i, word in enumerate(words):
                    if word.lower() == "file" and i + 1 < len(words):
                        filename = words[i + 1]
                        met = filename in output or f"created {filename}" in output_lower
                        break
            
            # Contains checks
            elif "contains" in criterion_lower:
                # Extract what should be contained
                if "DATABASE_URL" in criterion:
                    met = "database_url" in output_lower or "DATABASE_URL" in output
                elif "DEBUG" in criterion:
                    met = "debug" in output_lower and ("true" in output_lower or "True" in output)
                elif "PONG" in criterion:
                    met = "pong" in output_lower
                else:
                    # Generic contains
                    target = criterion.split("contains")[-1].strip()
                    met = target.lower() in output_lower
            
            # Output checks
            elif "output" in criterion_lower:
                if "shows" in criterion_lower or "displays" in criterion_lower:
                    # Extract expected output
                    if "DB:" in criterion:
                        met = "db:" in output_lower and "sqlite:///test.db" in output_lower
                    else:
                        met = True  # Generic output check
            
            # Error checks
            elif "no" in criterion_lower and "error" in criterion_lower:
                error_words = ["error", "failed", "exception", "traceback", "refused"]
                met = not any(word in output_lower for word in error_words)
            
            # Exit code checks
            elif "exit code" in criterion_lower:
                met = "exit code: 0" in output_lower or "successfully" in output_lower
            
            else:
                # Generic keyword matching
                key_words = [w for w in criterion.split() if len(w) > 3]
                met = any(word.lower() in output_lower for word in key_words)
            
            if not met:
                failed.append(criterion)
        
        return len(failed) == 0, failed
    
    async def run_all_tasks(self):
        """Execute all tasks from the improved task list."""
        
        print("Starting Improved Task List Execution")
        print("Using cc_execute.md pattern with WebSocket")
        print("="*60)
        
        # Task 1
        await self.execute_task(
            1,
            "Create a config.py file with DATABASE_URL='sqlite:///test.db' and DEBUG=True",
            45,
            ["File config.py exists", "Contains DATABASE_URL with correct value", "Contains DEBUG=True"],
            "Retry with more specific Python syntax instructions"
        )
        
        # Brief pause
        await asyncio.sleep(2)
        
        # Task 2
        await self.execute_task(
            2,
            "Run python -c \"from config import DATABASE_URL, DEBUG; print(f'DB: {DATABASE_URL}, Debug: {DEBUG}')\"",
            30,
            ["Output shows DB: sqlite:///test.db, Debug: True", "No import errors", "No syntax errors"],
            "Check if config.py is in current directory"
        )
        
        # Brief pause
        await asyncio.sleep(2)
        
        # Task 3
        await self.execute_task(
            3,
            "Check Redis connection by running redis-cli ping",
            None,  # Let Redis estimate timeout
            ["Output contains PONG", "No connection refused errors", "Exit code is 0"],
            "Check if Redis is running with ps aux | grep redis"
        )
        
        # Summary
        print(f"\n{'='*60}")
        print("Task List Summary")
        print(f"{'='*60}")
        
        successful = sum(1 for r in self.results if r['success'])
        total = len(self.results)
        
        print(f"Total tasks: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success rate: {successful/total*100:.0f}%")
        
        for r in self.results:
            status = "✅" if r['success'] else "❌"
            print(f"  Task {r['task']}: {status} ({r['duration']:.1f}s)")

async def main():
    executor = TaskExecutor()
    await executor.run_all_tasks()

if __name__ == "__main__":
    asyncio.run(main())