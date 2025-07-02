#!/usr/bin/env python3
"""
CC_Execute - WebSocket Task Executor (Graduated from cc_execute.md)

This module executes tasks by spawning Claude instances through WebSocket,
providing bidirectional communication, token/rate limit detection, and
timeout control via Redis.

Graduation achieved: 10:1 success ratio on 2025-07-01
"""

import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from cc_executor.client.websocket_client_standalone import WebSocketClient


class CCExecute:
    """Execute tasks through Claude instances via WebSocket."""
    
    def __init__(self, host: str = "localhost", port: int = 8004):
        self.client = WebSocketClient(host=host, port=port)
    
    async def execute_task(self, task_description: str) -> Dict:
        """
        Execute a task following the cc_execute pattern.
        
        Args:
            task_description: Full task description including:
                - Task: The question to execute
                - Timeout: Seconds or "Redis estimate"
                - Success Criteria: List of checks
                - Retry Strategy: How to improve if failed
        
        Returns:
            Dict with execution results including success status and output
        """
        # Parse the task description
        parsed = self._parse_task(task_description)
        
        # Build Claude command
        cmd = self._build_command(parsed['task'])
        
        # Execute via WebSocket
        result = await self._execute_via_websocket(cmd, parsed.get('timeout'))
        
        if not result.get('success'):
            # Handle specific errors
            if result.get('retry_hint') == 'shorter_response':
                # Retry with concise request
                refined_task = parsed['task'] + " Keep the response concise."
                cmd = self._build_command(refined_task)
                result = await self._execute_via_websocket(cmd, parsed.get('timeout'))
        
        # Parse response if successful
        if result.get('success'):
            output_data = result.get('output_data', [])
            parsed_response = self._parse_claude_response(output_data)
            
            # Evaluate against criteria
            if parsed.get('criteria'):
                success, failed = self._evaluate_criteria(
                    parsed_response['text'], 
                    parsed['criteria']
                )
                result['criteria_met'] = success
                result['failed_criteria'] = failed
                result['parsed_output'] = parsed_response['text']
                
                # Apply retry strategy if needed
                if not success and parsed.get('retry_strategy'):
                    result['retry_suggestion'] = self._build_retry_suggestion(
                        parsed['task'],
                        failed,
                        parsed['retry_strategy']
                    )
        
        return result
    
    def _parse_task(self, task_description: str) -> Dict:
        """Parse task description into components."""
        result = {}
        
        # Extract task
        task_match = re.search(r'Task:\s*(.+?)(?=\n|$)', task_description)
        if task_match:
            result['task'] = task_match.group(1).strip()
        
        # Extract timeout
        timeout_match = re.search(r'Timeout:\s*(.+?)(?=\n|$)', task_description)
        if timeout_match:
            timeout_str = timeout_match.group(1).strip()
            if timeout_str.lower() in ['redis estimate', 'redis estimation']:
                result['timeout'] = None  # Let WebSocket handler use Redis
            else:
                try:
                    result['timeout'] = int(re.search(r'\d+', timeout_str).group())
                except:
                    result['timeout'] = None
        
        # Extract criteria
        criteria_match = re.search(r'Success Criteria:(.*?)(?=Retry Strategy:|$)', 
                                  task_description, re.DOTALL)
        if criteria_match:
            criteria_text = criteria_match.group(1)
            criteria = []
            for line in criteria_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+[\.\)]', line):
                    criteria.append(re.sub(r'^\d+[\.\)]\s*', '', line))
            result['criteria'] = criteria
        
        # Extract retry strategy
        retry_match = re.search(r'Retry Strategy:\s*(.+?)(?=\n|$)', task_description)
        if retry_match:
            result['retry_strategy'] = retry_match.group(1).strip()
        
        return result
    
    def _build_command(self, task: str) -> str:
        """Build Claude command with appropriate tools."""
        # Select tools based on task content
        tools = []
        task_lower = task.lower()
        
        if any(word in task_lower for word in ['create', 'file', 'write']):
            tools.append("Write")
        if any(word in task_lower for word in ['run', 'execute', 'command']):
            tools.append("Bash")
        if any(word in task_lower for word in ['check', 'verify', 'read']):
            tools.extend(["Bash", "Read"])
        
        # Always include Read for verification
        if "Read" not in tools:
            tools.append("Read")
        
        tools_str = ",".join(tools)
        return f'claude -p "{task}" --output-format stream-json --verbose --allowedTools {tools_str} --dangerously-skip-permissions'
    
    async def _execute_via_websocket(self, cmd: str, timeout: Optional[int] = None) -> Dict:
        """Execute command via WebSocket with error handling."""
        try:
            # Send command - WebSocket handler manages subprocess
            result = await self.client.execute_command(cmd, timeout=timeout)
            
            # Check for common issues
            if not result.get('success', False):
                error = result.get('error', 'Unknown error')
                
                # Specific error handling
                if 'token limit' in error or "Claude's response exceeded" in error:
                    return {'success': False, 'retry_hint': 'shorter_response', 'error': error}
                elif 'rate limit' in error:
                    return {'success': False, 'retry_hint': 'wait_and_retry', 'error': error}
                elif 'timeout' in error.lower():
                    return {'success': False, 'retry_hint': 'increase_timeout', 'error': error}
                
                return {'success': False, 'error': error}
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'WebSocket error: {str(e)}'}
    
    def _parse_claude_response(self, output_data: List[str]) -> Dict:
        """Extract content from Claude's JSON stream output."""
        content = []
        tool_uses = []
        
        for line in output_data:
            try:
                data = json.loads(line)
                
                # Get text content
                if data.get('type') == 'assistant' and 'content' in data.get('message', {}):
                    for item in data['message']['content']:
                        if item.get('type') == 'text':
                            content.append(item['text'])
                        elif item.get('type') == 'tool_use':
                            tool_uses.append(item)
                            
            except json.JSONDecodeError:
                continue
        
        return {
            'text': '\n'.join(content),
            'tools': tool_uses
        }
    
    def _evaluate_criteria(self, output: str, criteria: List[str]) -> Tuple[bool, List[str]]:
        """Evaluate output against success criteria."""
        failed = []
        output_lower = output.lower()
        
        for criterion in criteria:
            criterion_lower = criterion.lower()
            met = False
            
            # File existence checks
            if "exists" in criterion_lower and "file" in criterion_lower:
                # Extract filename
                words = criterion.split()
                for i, word in enumerate(words):
                    if word.lower() == "file" and i + 1 < len(words):
                        filename = words[i + 1]
                        met = filename in output or f"created {filename}" in output_lower
                        break
            
            # Contains checks
            elif "contains" in criterion_lower or "output" in criterion_lower:
                # Extract what should be contained
                if ":" in criterion:
                    target = criterion.split(":", 1)[1].strip()
                    met = target.lower() in output_lower
                else:
                    # Generic contains - check for key words
                    key_words = [w for w in criterion.split() if len(w) > 3]
                    met = any(word.lower() in output_lower for word in key_words)
            
            # Error checks
            elif "no" in criterion_lower and "error" in criterion_lower:
                error_words = ["error", "failed", "exception", "traceback", "refused"]
                met = not any(word in output_lower for word in error_words)
            
            # Exit code checks
            elif "exit" in criterion_lower and "code" in criterion_lower:
                met = "exit code: 0" in output_lower or "successfully" in output_lower
            
            else:
                # Generic keyword matching
                key_words = [w for w in criterion.split() if len(w) > 3]
                met = any(word.lower() in output_lower for word in key_words)
            
            if not met:
                failed.append(criterion)
        
        return len(failed) == 0, failed
    
    def _build_retry_suggestion(self, task: str, failed_criteria: List[str], 
                               retry_strategy: str) -> str:
        """Build a refined task based on what failed."""
        refinements = []
        
        for criterion in failed_criteria:
            if "exists" in criterion:
                refinements.append("Make sure to actually create the file")
            elif "contains" in criterion:
                # Extract what should be contained
                if ":" in criterion:
                    what = criterion.split(":", 1)[1].strip()
                    refinements.append(f"Include '{what}' in your response")
            elif "error" in criterion:
                refinements.append("Ensure the code/command runs without errors")
        
        refined_task = task
        if refinements:
            refined_task += "\n\nIMPORTANT: " + ". ".join(refinements)
        
        if retry_strategy:
            refined_task += f"\n\nRetry Strategy: {retry_strategy}"
        
        return refined_task


# Self-verification when run directly
if __name__ == "__main__":
    async def self_verify():
        """Verify cc_execute functionality."""
        print("CC_Execute Self-Verification")
        print("="*60)
        
        executor = CCExecute()
        
        # Test task parsing
        test_task = """Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is 2 + 2? Calculate and show the result.
- Timeout: 30 seconds
- Success Criteria:
  1. Output contains "4"
  2. No errors occurred
- Retry Strategy: Show the calculation step by step"""
        
        parsed = executor._parse_task(test_task)
        
        print("Task Parsing Test:")
        print(f"  Task: {parsed.get('task', 'NOT FOUND')}")
        print(f"  Timeout: {parsed.get('timeout', 'NOT FOUND')}")
        print(f"  Criteria: {len(parsed.get('criteria', []))} items")
        print(f"  Retry: {'✓' if parsed.get('retry_strategy') else '✗'}")
        
        assert parsed.get('task') == "What is 2 + 2? Calculate and show the result."
        assert parsed.get('timeout') == 30
        assert len(parsed.get('criteria', [])) == 2
        assert parsed.get('retry_strategy') is not None
        
        print("\n✅ All self-verification tests passed!")
        print("\nCC_Execute graduated from cc_execute.md with 10:1 success ratio")
    
    asyncio.run(self_verify())