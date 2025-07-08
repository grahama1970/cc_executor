"""
FastAPI wrapper for CC Executor - provides REST API for safe task execution.

This API layer allows remote task execution in a containerized environment,
providing isolation and security for code execution.
"""

import asyncio
import uuid
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from ..client.client import WebSocketClient
from ..simple import ensure_server_running


# Request/Response models
class TaskListRequest(BaseModel):
    """Request to execute a list of tasks."""
    tasks: List[str] = Field(..., description="List of tasks to execute sequentially")
    timeout_per_task: Optional[int] = Field(None, description="Timeout in seconds per task")
    execution_id: Optional[str] = Field(None, description="Optional execution ID for tracking")


class TaskResult(BaseModel):
    """Result of a single task execution."""
    task_number: int
    task_description: str
    exit_code: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: float
    completed_at: datetime


class TaskListResponse(BaseModel):
    """Response for task list execution."""
    execution_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    results: List[TaskResult]
    started_at: datetime
    completed_at: datetime
    total_execution_time: float


class ExecutionStatus(BaseModel):
    """Status of an execution."""
    execution_id: str
    status: str  # "running", "completed", "failed"
    progress: str  # "3/5 tasks completed"
    current_task: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="CC Executor API",
    description="REST API for safe sequential task execution with Claude Code",
    version="1.0.0"
)

# In-memory storage for execution tracking (use Redis in production)
executions: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize API on startup."""
    logger.info("Starting CC Executor API...")
    # In Docker, the WebSocket service is already running as a separate container
    # No need to start it here
    logger.info("CC Executor API ready")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "cc-executor-api",
        "timestamp": datetime.utcnow()
    }


@app.get("/auth/status")
async def check_auth_status():
    """
    Check Claude Code authentication status.
    
    Returns whether Claude is authenticated and provides setup instructions.
    """
    # Check if credentials file exists in the mounted volume
    import os
    creds_path = "/home/appuser/.claude/.credentials.json"
    
    if os.path.exists(creds_path):
        return {
            "status": "authenticated",
            "message": "Claude Code is authenticated and ready to use",
            "credentials_found": True
        }
    else:
        return {
            "status": "not_authenticated",
            "message": "Claude Code is not authenticated",
            "credentials_found": False,
            "instructions": {
                "title": "Authentication Required",
                "steps": [
                    "1. On your HOST machine (not in Docker), install Claude CLI:",
                    "   npm install -g @anthropic-ai/claude-code",
                    "",
                    "2. Authenticate on your HOST machine:",
                    "   claude /login",
                    "   (This will open a browser for authentication)",
                    "",
                    "3. Verify authentication files exist:",
                    "   ls -la ~/.claude/.credentials.json",
                    "",
                    "4. Restart the Docker container to mount credentials:",
                    "   docker compose down",
                    "   docker compose up -d",
                    "",
                    "5. Check this endpoint again to verify authentication"
                ],
                "why": "Claude Code uses browser-based OAuth authentication which cannot be done inside Docker containers. The container must mount credentials from an already-authenticated host system.",
                "alternative": "For CI/CD environments, consider using the Anthropic API directly with API keys instead of Claude Code CLI."
            }
        }


@app.post("/auth/claude", deprecated=True)
async def authenticate_claude():
    """
    DEPRECATED: This endpoint doesn't work because Claude requires browser authentication.
    
    Use GET /auth/status instead to check authentication and get setup instructions.
    """
    return {
        "status": "deprecated",
        "message": "This endpoint is deprecated because Claude authentication requires a browser",
        "alternative": "Use GET /auth/status to check authentication status and get setup instructions",
        "explanation": "Claude Code uses OAuth browser flow which cannot work in headless Docker containers"
    }


@app.get("/.well-known/mcp/cc-executor.json")
async def get_mcp_manifest():
    """
    Serve MCP manifest for Claude tool discovery.
    
    This allows Claude to discover and use cc-executor as a native MCP tool.
    """
    # Determine the WebSocket URL based on environment
    ws_host = os.environ.get("WEBSOCKET_HOST", "localhost")
    ws_port = os.environ.get("WEBSOCKET_PORT", "8003")
    ws_url = f"ws://{ws_host}:{ws_port}/ws"
    
    return {
        "name": "cc-executor",
        "description": "Execute commands and task lists via Claude Code with streaming output",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",  # MCP protocol version
        "server": {
            "url": ws_url,
            "type": "websocket"
        },
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False,
            "sampling": False
        },
        "tools": [
            {
                "name": "execute",
                "description": "Execute a single command via Claude Code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 600)"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "execute_task_list",
                "description": "Execute a list of tasks sequentially",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tasks to execute"
                        },
                        "timeout_per_task": {
                            "type": "integer",
                            "description": "Timeout per task in seconds (default: 600)"
                        }
                    },
                    "required": ["tasks"]
                }
            },
            {
                "name": "control",
                "description": "Control execution (pause/resume/cancel)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["pause", "resume", "cancel"],
                            "description": "Control action"
                        },
                        "execution_id": {
                            "type": "string",
                            "description": "Execution ID to control"
                        }
                    },
                    "required": ["type"]
                }
            }
        ]
    }


@app.post("/execute", response_model=TaskListResponse)
async def execute_task_list(request: TaskListRequest, background_tasks: BackgroundTasks):
    """
    Execute a list of tasks sequentially.
    
    This endpoint provides a safe way to execute Claude Code tasks in a
    containerized environment. Each task gets fresh context and runs in
    isolation.
    """
    # Generate execution ID if not provided
    execution_id = request.execution_id or str(uuid.uuid4())
    
    # Initialize execution tracking
    executions[execution_id] = {
        "status": "running",
        "started_at": datetime.utcnow(),
        "total_tasks": len(request.tasks),
        "completed_tasks": 0,
        "current_task": None,
        "results": []
    }
    
    # Execute tasks
    start_time = datetime.utcnow()
    results = []
    failed_count = 0
    
    # In Docker, connect to the websocket service by name
    ws_host = "websocket" if os.environ.get("WEBSOCKET_URL") else "localhost"
    client = WebSocketClient(host=ws_host)
    
    for i, task in enumerate(request.tasks, 1):
        task_start = datetime.utcnow()
        
        # Update execution status
        executions[execution_id]["current_task"] = f"Task {i}: {task[:50]}..."
        
        try:
            # Execute via Claude
            command = f'claude -p "{task}"'
            if request.timeout_per_task:
                result = await client.execute_command(command, timeout=request.timeout_per_task)
            else:
                result = await client.execute_command(command)
            
            # Process result from WebSocketClient format
            task_result = TaskResult(
                task_number=i,
                task_description=task,
                exit_code=result.get("exit_code", 1),
                stdout=result.get("output_data", ""),
                stderr=result.get("error", "") if result.get("error") else None,
                execution_time=(datetime.utcnow() - task_start).total_seconds(),
                completed_at=datetime.utcnow()
            )
            
            results.append(task_result)
            
            if task_result.exit_code != 0:
                failed_count += 1
                logger.warning(f"Task {i} failed with exit code {task_result.exit_code}")
                # Continue or stop based on configuration
                
            executions[execution_id]["completed_tasks"] = i
            executions[execution_id]["results"].append(task_result.dict())
            
        except Exception as e:
            logger.error(f"Task {i} execution error: {e}")
            task_result = TaskResult(
                task_number=i,
                task_description=task,
                exit_code=1,
                stderr=str(e),
                execution_time=(datetime.utcnow() - task_start).total_seconds(),
                completed_at=datetime.utcnow()
            )
            results.append(task_result)
            failed_count += 1
            break
        
    # Finalize execution
    end_time = datetime.utcnow()
    total_time = (end_time - start_time).total_seconds()
    
    executions[execution_id]["status"] = "completed" if failed_count == 0 else "failed"
    executions[execution_id]["completed_at"] = end_time
    
    response = TaskListResponse(
        execution_id=execution_id,
        total_tasks=len(request.tasks),
        completed_tasks=len(results),
        failed_tasks=failed_count,
        results=results,
        started_at=start_time,
        completed_at=end_time,
        total_execution_time=total_time
    )
    
    return response


@app.get("/executions/{execution_id}/status", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
    """Get the status of an execution."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    exec_data = executions[execution_id]
    
    return ExecutionStatus(
        execution_id=execution_id,
        status=exec_data["status"],
        progress=f"{exec_data['completed_tasks']}/{exec_data['total_tasks']} tasks completed",
        current_task=exec_data.get("current_task")
    )


@app.get("/executions/{execution_id}/results")
async def get_execution_results(execution_id: str):
    """Get the full results of an execution."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return executions[execution_id]


@app.delete("/executions/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel a running execution."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if executions[execution_id]["status"] != "running":
        raise HTTPException(status_code=400, detail="Execution is not running")
    
    # TODO: Implement actual cancellation logic
    executions[execution_id]["status"] = "cancelled"
    
    return {"message": "Execution cancelled", "execution_id": execution_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)