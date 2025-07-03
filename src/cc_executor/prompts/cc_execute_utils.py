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
from pathlib import Path
from typing import Optional, Dict, Any, List

def execute_task_via_websocket(
    task: str,
    timeout: Optional[int] = None,
    tools: Optional[List[str]] = None
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
    
    Returns:
        Dict containing success status, exit code, output lines, and any errors
    """
    
    # Build the Claude command
    if tools is None:
        tools = ["Read", "Write", "Edit", "Bash"]  # Default tools
    
    # Build command following websocket_handler.py patterns
    base_cmd = 'claude -p --output-format stream-json --verbose'
    
    # Add tools if specified
    if tools:
        tools_str = " ".join(tools)
        base_cmd += f' --allowedTools "{tools_str}"'
    
    # Add the task/prompt
    claude_cmd = f'{base_cmd} "{task}"'
    
    # Get paths
    current_dir = Path(__file__).parent
    websocket_handler_path = current_dir.parent / "core" / "websocket_handler.py"
    
    # Build the subprocess command
    # Note: websocket_handler.py needs to support --execute flag
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
    
    # Execute via subprocess
    try:
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Parse output
        output_lines = result.stdout.strip().split('\n') if result.stdout else []
        
        # Return results to orchestrator
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'output_lines': output_lines,
            'stderr': result.stderr if result.stderr else None,
            'task': task
        }
    
    except Exception as e:
        return {
            'success': False,
            'exit_code': -1,
            'output_lines': [],
            'stderr': str(e),
            'task': task
        }


# Usage function for testing
if __name__ == "__main__":
    import asyncio
    
    def test_execution():
        """Test the execution function."""
        print("=== CC_Execute Utils Test ===")
        
        # Test task
        test_task = "What is 2+2? Write the answer to a file called answer.txt"
        
        print(f"Task: {test_task}")
        print("Executing via WebSocket handler pattern...")
        
        result = execute_task_via_websocket(
            task=test_task,
            timeout=60,
            tools=["Write"]
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