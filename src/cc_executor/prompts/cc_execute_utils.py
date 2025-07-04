#!/usr/bin/env python3
"""
CC_Execute utilities - Helper functions for spawning fresh Claude instances.

This module provides the implementation for executing tasks through the
WebSocket handler, ensuring each task gets a fresh Claude instance with
full 200K context.
"""
import subprocess
import sys
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Try to import config, but use defaults if not available
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config import DEFAULT_EXECUTION_TIMEOUT
except ImportError:
    DEFAULT_EXECUTION_TIMEOUT = 600  # 10 minutes fallback

def execute_task_via_websocket(
    task: str,
    timeout: Optional[int] = None,
    tools: Optional[List[str]] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Execute a task by calling websocket_handler.py to spawn a fresh Claude instance.
    
    This is the simple approach:
    1. Build the Claude command with appropriate tools
    2. Call websocket_handler.py with the command
    3. Return the results
    
    Args:
        task: The task description for Claude to execute
        timeout: Optional timeout in seconds (default: 600)
        tools: Optional list of tools to enable (default: Read, Write, Edit, Bash)
        max_retries: Maximum number of retry attempts for transient failures (default: 3)
    
    Returns:
        Dict containing success status, exit code, output lines, and any errors
    """
    
    # Build the Claude command
    if tools is None:
        tools = ["Read", "Write", "Edit", "Bash"]  # Default tools
    
    # Use configured timeout if not specified
    if timeout is None:
        timeout = DEFAULT_EXECUTION_TIMEOUT
    
    # Build command following websocket_handler.py patterns
    # The prompt must come immediately after -p flag
    base_cmd = f'claude -p "{task}" --output-format stream-json --verbose'
    
    # Add tools if specified
    if tools:
        tools_str = " ".join(tools)
        base_cmd += f' --allowedTools {tools_str}'
    
    claude_cmd = base_cmd
    
    # Get paths
    current_dir = Path(__file__).parent
    websocket_handler_path = current_dir.parent / "core" / "websocket_handler.py"
    
    # Build the subprocess command
    cmd_args = [
        sys.executable,
        str(websocket_handler_path),
        "--execute", claude_cmd
    ]
    
    # Add timeout if specified
    if timeout:
        cmd_args.extend(["--timeout", str(timeout)])
    
    # Add no-server flag to prevent WebSocket server from starting
    cmd_args.append("--no-server")
    
    print(f"[CC_EXECUTE] Calling websocket_handler.py...")
    print(f"[CC_EXECUTE] Command: {claude_cmd[:100]}...")
    
    # Execute via subprocess with retry logic
    last_error = None
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse output
            output_lines = result.stdout.strip().split('\n') if result.stdout else []
            stderr = result.stderr if result.stderr else None
            
            # Check for transient failures and rate limits
            is_transient = False
            is_rate_limited = False
            retry_after = None
            
            if result.returncode != 0 and stderr:
                # Check for known transient errors
                transient_patterns = [
                    "Connection refused",
                    "Connection reset",
                    "Timeout expired",
                    "504 Gateway Timeout",
                    "502 Bad Gateway",
                    "ECONNRESET"
                ]
                is_transient = any(pattern in stderr for pattern in transient_patterns)
                
                # Check for rate limiting (429 Too Many Requests)
                if "429" in stderr or "Too Many Requests" in stderr or "rate limit" in stderr.lower():
                    is_rate_limited = True
                    is_transient = True
                    
                    # Try to extract Retry-After header value
                    import re
                    retry_match = re.search(r'Retry-After[:"]\s*(\d+)', stderr, re.IGNORECASE)
                    if retry_match:
                        retry_after = int(retry_match.group(1))
                    else:
                        # Default to 60 seconds if no Retry-After header
                        retry_after = 60
            
            # If successful or non-transient error, return immediately
            if result.returncode == 0 or not is_transient:
                return {
                    'success': result.returncode == 0,
                    'exit_code': result.returncode,
                    'output_lines': output_lines,
                    'stderr': stderr,
                    'task': task,
                    'attempts': attempt + 1
                }
            
            # If transient error and not last attempt, retry with appropriate backoff
            if attempt < max_retries - 1:
                if is_rate_limited and retry_after:
                    wait_time = retry_after
                    print(f"[CC_EXECUTE] Rate limit detected (429), waiting {wait_time}s as requested (attempt {attempt + 2}/{max_retries})...")
                else:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[CC_EXECUTE] Transient error detected, retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            
            last_error = stderr
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[CC_EXECUTE] Exception occurred, retrying in {wait_time}s (attempt {attempt + 2}/{max_retries}): {e}")
                time.sleep(wait_time)
            continue
    
    # All retries exhausted
    return {
        'success': False,
        'exit_code': -1,
        'output_lines': [],
        'stderr': f"Failed after {max_retries} attempts. Last error: {last_error}",
        'task': task,
        'attempts': max_retries
    }


# Usage function for testing
if __name__ == "__main__":
    import asyncio
    
    def test_execution():
        """Test the execution function."""
        print("=== CC_Execute Utils Test ===")
        
        # Test task - simple computation that returns in JSON
        test_task = "What is 2+2? Just tell me the answer."
        
        print(f"Task: {test_task}")
        print("Executing via WebSocket handler pattern...")
        
        result = execute_task_via_websocket(
            task=test_task,
            timeout=60,
            tools=[]  # No tools needed for simple answer
        )
        
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output lines: {len(result['output_lines'])}")
        
        # Save raw output to prevent hallucination
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create output directory
        output_dir = Path(__file__).parent / "tmp" / "responses"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save response
        response_file = output_dir / f"cc_execute_test_{timestamp}.json"
        with open(response_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Raw response saved to: {response_file}")
        
        return result['success']
    
    # Run the test
    success = test_execution()
    exit(0 if success else 1)