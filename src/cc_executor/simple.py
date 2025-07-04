"""
Simple high-level API for CC Executor.

⚠️ IMPORTANT: CC Executor is ONLY for sequential task lists!
Do NOT use it for single Claude queries - that's what 'claude -p' is for.

CC Executor's value proposition:
- Maintains workflow coherence across multiple related tasks
- Gives each task fresh 200K context to avoid confusion
- Ensures sequential execution with dependency management
- Provides anti-hallucination hooks across the entire workflow

If you're not executing multiple related tasks in sequence,
you're using the wrong tool.
"""

import asyncio
import subprocess
import time
from typing import Dict, Any, Optional
from .client.client import WebSocketClient
from loguru import logger


def ensure_server_running() -> bool:
    """Ensure the CC Executor server is running."""
    try:
        # Check if server is already running
        result = subprocess.run(
            ["cc-executor", "server", "status"],
            capture_output=True,
            text=True
        )
        
        if "running" in result.stdout.lower():
            return True
            
        # Start the server
        logger.info("Starting CC Executor server...")
        subprocess.run(
            ["cc-executor", "server", "start"],
            capture_output=True,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure server is running: {e}")
        return False


async def _execute_async(command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Execute a command asynchronously via WebSocket."""
    client = WebSocketClient()
    
    try:
        await client.connect()
        
        # Execute the command
        if timeout:
            result = await client.execute_command(command, timeout=timeout)
        else:
            result = await client.execute_command(command)
            
        return result
        
    finally:
        await client.disconnect()


def cc_execute_task_list(tasks: list[str], timeout: Optional[int] = None) -> list[Dict[str, Any]]:
    """
    Execute a list of related tasks sequentially using Claude Code via CC Executor.
    
    ⚠️ IMPORTANT: This is for SEQUENTIAL TASK LISTS, not individual calls.
    For single Claude queries, use the Claude CLI directly.
    
    CC Executor's value is in maintaining workflow coherence across multiple
    tasks while giving each task fresh context to avoid confusion.
    
    Args:
        tasks: List of task descriptions for Claude to execute in sequence
        timeout: Optional timeout in seconds per task
        
    Returns:
        List of dicts, one per task, each with keys:
        - exit_code: Process exit code
        - stdout: Standard output (if any)
        - stderr: Standard error (if any)
        - task: The original task description
        
    Example:
        >>> from cc_executor import cc_execute_task_list
        >>> tasks = [
        ...     "Task 1: Create Django project structure",
        ...     "Task 2: Add user authentication models",
        ...     "Task 3: Create authentication views",
        ...     "Task 4: Add tests for auth flow"
        ... ]
        >>> results = cc_execute_task_list(tasks)
        >>> for i, result in enumerate(results):
        ...     print(f"Task {i+1}: {'✅' if result['exit_code'] == 0 else '❌'}")
    """
    # Ensure server is running
    if not ensure_server_running():
        return [{
            "exit_code": 1,
            "stderr": "Failed to start CC Executor server",
            "task": task
        } for task in tasks]
    
    results = []
    
    # Execute each task in sequence
    for i, task in enumerate(tasks, 1):
        logger.info(f"Executing task {i}/{len(tasks)}: {task[:50]}...")
        
        # Wrap task in Claude command
        # Using -p flag for print mode
        command = f'claude -p "{task}"'
        
        # Execute via WebSocket
        try:
            result = asyncio.run(_execute_async(command, timeout))
            result["task"] = task
            results.append(result)
            
            # Stop on failure unless explicitly told to continue
            if result.get("exit_code", 1) != 0:
                logger.warning(f"Task {i} failed, stopping execution")
                break
                
        except Exception as e:
            logger.error(f"Task {i} execution failed: {e}")
            results.append({
                "exit_code": 1,
                "stderr": str(e),
                "task": task
            })
            break
    
    return results


# Make cc_execute_task_list available at package level
__all__ = ["cc_execute_task_list"]