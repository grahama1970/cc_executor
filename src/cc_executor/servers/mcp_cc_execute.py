#!/usr/bin/env python3
"""
MCP Server for CC Executor - provides cc_execute tools via Model Context Protocol.

This server exposes CC Executor functionality as MCP tools that can be used
by Claude Code and other MCP-compatible clients.
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastmcp import FastMCP
from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig
from cc_executor.reporting import check_hallucination, generate_hallucination_report

# Initialize FastMCP server
mcp = FastMCP("cc-executor", dependencies=["cc_executor"])


@mcp.tool(
    description="""Execute a task using Claude Code. This tool runs Claude in a subprocess
    and returns the output. Use this for complex tasks that require AI assistance.
    
    Examples:
    - "Write a Python script that calculates fibonacci numbers"
    - "Analyze this code and suggest improvements"
    - "Create unit tests for the Calculator class"
    """
)
async def execute_task(
    task: str,
    json_mode: bool = False,
    timeout: Optional[int] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Execute a task using Claude Code.
    
    Args:
        task: The task description for Claude to execute
        json_mode: If True, expect structured JSON output
        timeout: Optional timeout in seconds (default: 120)
        verbose: If True, include detailed execution info
        
    Returns:
        Dictionary with execution results
    """
    try:
        # Create config if needed
        config = CCExecutorConfig(
            timeout=timeout or 120
        )
        
        # Execute the task with json_mode
        if json_mode:
            result = await cc_execute(task, config=config, json_mode=True)
        else:
            result = await cc_execute(task, config=config)
        
        # Format response based on mode
        if json_mode and isinstance(result, dict):
            return {
                "success": True,
                "output": result,
                "mode": "json"
            }
        else:
            return {
                "success": True,
                "output": result,
                "mode": "text"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp.tool(
    description="""Get the current status of the CC Executor service, including
    health checks, version info, and configuration."""
)
async def get_executor_status() -> Dict[str, Any]:
    """
    Get the current status of CC Executor.
    
    Returns:
        Status information including health, version, and config
    """
    try:
        # Check if WebSocket server is running
        ws_healthy = False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8003/health")
                if response.status_code == 200:
                    ws_healthy = True
        except:
            pass
            
        return {
            "service": "cc-executor",
            "version": "1.0.0",
            "websocket_healthy": ws_healthy,
            "websocket_url": "ws://localhost:8003/ws",
            "features": [
                "task_execution",
                "json_mode",
                "streaming_output",
                "timeout_control"
            ],
            "config": {
                "default_timeout": 120,
                "max_timeout": 600,
                "json_mode_available": True
            }
        }
    except Exception as e:
        return {
            "service": "cc-executor",
            "error": str(e),
            "status": "error"
        }


@mcp.tool(
    description="""Execute multiple tasks sequentially, useful for multi-step workflows.
    Each task is executed in order, and execution stops on first failure unless
    continue_on_error is True.
    
    Example tasks:
    - Create a new Python file called math_utils.py
    - Add a function to calculate factorial
    - Add unit tests for the factorial function"""
)
async def execute_task_list(
    tasks: List[str],
    continue_on_error: bool = False,
    timeout_per_task: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute a list of tasks sequentially.
    
    Args:
        tasks: List of task descriptions
        continue_on_error: If True, continue even if a task fails
        timeout_per_task: Timeout for each task in seconds
        
    Returns:
        Results for all executed tasks
    """
    results = []
    
    for i, task in enumerate(tasks):
        try:
            result = await execute_task(
                task=task,
                json_mode=False,
                timeout=timeout_per_task
            )
            
            results.append({
                "task_number": i + 1,
                "task": task,
                "result": result
            })
            
            # Stop on error unless told to continue
            if not result.get("success") and not continue_on_error:
                break
                
        except Exception as e:
            error_result = {
                "task_number": i + 1,
                "task": task,
                "result": {
                    "success": False,
                    "error": str(e)
                }
            }
            results.append(error_result)
            
            if not continue_on_error:
                break
                
    return {
        "total_tasks": len(tasks),
        "executed_tasks": len(results),
        "successful_tasks": sum(1 for r in results if r["result"].get("success")),
        "results": results
    }


@mcp.tool(
    description="""Analyze the complexity of a task and estimate execution time.
    Useful for understanding resource requirements before execution."""
)
async def analyze_task_complexity(task: str) -> Dict[str, Any]:
    """
    Analyze task complexity and estimate execution time.
    
    Args:
        task: Task description to analyze
        
    Returns:
        Complexity analysis with time estimates
    """
    # Simple heuristic-based analysis
    task_lower = task.lower()
    
    # Keywords that indicate complexity
    complex_keywords = ["analyze", "refactor", "design", "architect", "optimize", "review"]
    simple_keywords = ["echo", "print", "hello", "test", "check"]
    file_keywords = ["create", "write", "read", "file", "directory"]
    
    complexity = "medium"
    estimated_time = 60
    
    if any(kw in task_lower for kw in complex_keywords):
        complexity = "high"
        estimated_time = 180
    elif any(kw in task_lower for kw in simple_keywords):
        complexity = "low"
        estimated_time = 30
    elif any(kw in task_lower for kw in file_keywords):
        complexity = "medium"
        estimated_time = 60
        
    # Adjust for task length
    if len(task) > 500:
        estimated_time = int(estimated_time * 1.5)
        if complexity == "low":
            complexity = "medium"
        elif complexity == "medium":
            complexity = "high"
            
    return {
        "task": task,
        "complexity": complexity,
        "estimated_seconds": estimated_time,
        "estimated_minutes": round(estimated_time / 60, 1),
        "factors": {
            "task_length": len(task),
            "has_complex_keywords": any(kw in task_lower for kw in complex_keywords),
            "has_file_operations": any(kw in task_lower for kw in file_keywords)
        },
        "recommendation": f"Allow at least {estimated_time} seconds for this task"
    }


@mcp.tool(
    description="""Verify that recent cc_execute calls are not hallucinated.
    This tool checks for physical JSON response files on disk to prove executions happened.
    Use this to generate anti-hallucination reports and verify execution results.
    
    Examples:
    - Verify the last execution
    - Check a specific execution UUID
    - Generate a verification report for the last 5 executions
    """
)
async def verify_execution(
    execution_uuid: Optional[str] = None,
    last_n: int = 1,
    generate_report: bool = True
) -> Dict[str, Any]:
    """
    Verify cc_execute results are real by checking JSON response files.
    
    Args:
        execution_uuid: Specific UUID to verify (optional)
        last_n: Number of recent executions to check (default: 1)
        generate_report: Whether to generate a markdown report (default: True)
        
    Returns:
        Verification results with hallucination check
    """
    try:
        # Check for hallucinations
        result = check_hallucination(execution_uuid=execution_uuid, last_n=last_n)
        
        # Generate report if requested
        if generate_report and not result.get("is_hallucination", True):
            report_path = generate_hallucination_report(
                verifications=result.get("verifications", []),
                output_file=f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )
            result["report_path"] = str(report_path)
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "is_hallucination": True,
            "message": "Failed to verify execution - likely hallucinated"
        }


@mcp.resource(
    uri="executor://logs",
    name="executor-logs",
    description="Recent execution logs from CC Executor"
)
async def get_executor_logs() -> str:
    """Get recent execution logs."""
    try:
        log_file = Path("/tmp/cc_executor_recent.log")
        if log_file.exists():
            # Return last 50 lines
            lines = log_file.read_text().splitlines()
            return "\n".join(lines[-50:])
        else:
            return "No recent logs available"
    except Exception as e:
        return f"Error reading logs: {e}"


@mcp.resource(
    uri="executor://config",
    name="executor-config",
    description="Current CC Executor configuration"
)
async def get_executor_config() -> str:
    """Get current configuration as YAML."""
    config = {
        "cc_executor": {
            "version": "1.0.0",
            "websocket": {
                "host": "localhost",
                "port": 8003,
                "timeout": 120
            },
            "execution": {
                "default_timeout": 120,
                "max_timeout": 600,
                "json_mode": True,
                "streaming": True
            },
            "security": {
                "docker_enabled": True,
                "resource_limits": True,
                "network_isolation": True
            }
        }
    }
    
    # Format as YAML-like output
    lines = []
    for section, values in config.items():
        lines.append(f"{section}:")
        for subsection, subvalues in values.items():
            if isinstance(subvalues, dict):
                lines.append(f"  {subsection}:")
                for key, value in subvalues.items():
                    lines.append(f"    {key}: {value}")
            else:
                lines.append(f"  {subsection}: {subvalues}")
                
    return "\n".join(lines)


# Run the server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CC Executor MCP Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8002, help="Port to bind to")
    
    args = parser.parse_args()
    
    print(f"Starting CC Executor MCP Server on {args.host}:{args.port}")
    print("Available tools:")
    print("  - execute_task: Run tasks with Claude Code")
    print("  - execute_task_list: Run multiple tasks sequentially")
    print("  - analyze_task_complexity: Estimate task complexity")
    print("  - get_executor_status: Check service health")
    print("  - verify_execution: Verify executions are not hallucinated")
    print("\nPress Ctrl+C to stop")
    
    # FastMCP runs as stdio by default for MCP protocol
    mcp.run()