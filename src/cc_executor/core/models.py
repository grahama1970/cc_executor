"""
Pydantic models for CC Executor MCP WebSocket Service.

This module defines all request/response models used by the service,
providing type safety and automatic validation for WebSocket messages.

Third-party Documentation:
- Pydantic Models: https://docs.pydantic.dev/latest/usage/models/
- Pydantic Validation: https://docs.pydantic.dev/latest/usage/validators/
- JSON-RPC 2.0 Spec: https://www.jsonrpc.org/specification
- FastAPI Request/Response Models: https://fastapi.tiangolo.com/tutorial/body/

Example Input:
    JSON-RPC Execute Request:
    {
        "jsonrpc": "2.0",
        "method": "execute",
        "params": {"command": "echo 'Hello World'"},
        "id": 1
    }

Expected Output:
    Parsed into ExecuteRequest model with:
    - command: "echo 'Hello World'"
    - id: 1
    Validation ensures command is non-empty string.
"""

from typing import Optional, Any, Dict, Literal, Union, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fastapi import WebSocket
    import asyncio


# Error Types

class TimeoutError(Exception):
    """Raised when an operation times out."""
    def __init__(self, message: str, duration: Optional[float] = None):
        super().__init__(message)
        self.duration = duration


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProcessNotFoundError(Exception):
    """Raised when a process cannot be found."""
    def __init__(self, message: str, pid: Optional[int] = None, pgid: Optional[int] = None):
        super().__init__(message)
        self.pid = pid
        self.pgid = pgid


class CommandNotAllowedError(Exception):
    """Raised when a command is not allowed by security policy."""
    def __init__(self, message: str, command: Optional[str] = None):
        super().__init__(message)
        self.command = command


class SessionLimitError(Exception):
    """Raised when session limit is exceeded."""
    def __init__(self, message: str, current_sessions: Optional[int] = None, max_sessions: Optional[int] = None):
        super().__init__(message)
        self.current_sessions = current_sessions
        self.max_sessions = max_sessions


# Request Models

class JSONRPCRequest(BaseModel):
    """Base JSON-RPC 2.0 request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class ExecuteRequest(BaseModel):
    """Request to execute a command."""
    command: str = Field(..., description="Command to execute")
    timeout: Optional[int] = Field(None, description="Stream timeout in seconds (overrides STREAM_TIMEOUT)")
    id: Optional[Any] = Field(None, description="Optional request ID for correlation")


class ControlRequest(BaseModel):
    """Request to control a running process."""
    type: Literal["PAUSE", "RESUME", "CANCEL"] = Field(..., description="Control action type")
    id: Optional[Any] = Field(None, description="Optional request ID for correlation")


# Response Models

class JSONRPCResponse(BaseModel):
    """Base JSON-RPC 2.0 response model."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""
    code: int
    message: str
    data: Optional[Any] = None


class StatusUpdate(BaseModel):
    """Process status update notification."""
    status: Literal["started", "completed", "failed", "paused", "resumed", "canceled"]
    pid: Optional[int] = Field(None, description="Process ID")
    pgid: Optional[int] = Field(None, description="Process group ID")
    exit_code: Optional[int] = Field(None, description="Exit code (for completed/failed)")
    error: Optional[str] = Field(None, description="Error message (for failed)")


class StreamOutput(BaseModel):
    """Stream output notification."""
    type: Literal["stdout", "stderr"]
    data: str
    truncated: bool = Field(False, description="Whether the line was truncated")
    chunk_index: Optional[int] = Field(None, description="Index of this chunk (0-based) if message was chunked")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks if message was chunked")


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    session_id: str
    version: str = "1.0.0"
    capabilities: list[str] = ["execute", "control", "stream"]


# Session Models (internal use)

class SessionInfo(BaseModel):
    """Internal session information."""
    session_id: str
    websocket: "WebSocket" if TYPE_CHECKING else Any  # FastAPI WebSocket instance
    process: Optional["asyncio.subprocess.Process"] if TYPE_CHECKING else Optional[Any] = None
    pgid: Optional[int] = None
    task: Optional["asyncio.Task"] if TYPE_CHECKING else Optional[Any] = None
    created_at: float
    last_activity: float
    
    class Config:
        arbitrary_types_allowed = True


# Health Check Models

class HealthStatus(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    version: str
    active_sessions: int
    max_sessions: int
    uptime_seconds: float
    
    
# Validation helpers

def validate_command(command: str, allowed_commands: Optional[list[str]] = None) -> tuple[bool, Optional[str]]:
    """
    Validate a command against security policies.
    
    Args:
        command: Command to validate
        allowed_commands: Optional list of allowed commands
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not command or not command.strip():
        return False, "Command cannot be empty"
        
    if allowed_commands:
        # Check if command starts with any allowed command
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False, "Invalid command format"
            
        base_command = cmd_parts[0]
        if not any(base_command == allowed or base_command.startswith(allowed + " ") 
                   for allowed in allowed_commands):
            return False, f"Command '{base_command}' is not allowed"
            
    return True, None


if __name__ == "__main__":
    """Usage example demonstrating model validation and JSON-RPC parsing."""
    from usage_helper import OutputCapture
    
    with OutputCapture(__file__) as capture:
        print("=== Testing ExecuteRequest Model ===")
        
        # Valid request
        valid_request = ExecuteRequest(command="echo 'Hello World'", id=123)
        print(f"Valid request: {valid_request}")
        print(f"Command: {valid_request.command}")
        print(f"ID: {valid_request.id}")
        
        # Test validation
        try:
            invalid_request = ExecuteRequest(command="", id=456)
        except Exception as e:
            print(f"Empty command validation: Would fail in validate_command()")
        
        print("\n=== Testing ControlRequest Model ===")
        
        control_requests = [
            ControlRequest(type="PAUSE", id=1),
            ControlRequest(type="RESUME", id=2),
            ControlRequest(type="CANCEL", id=3)
        ]
        
        for req in control_requests:
            print(f"Control: {req.type} (id={req.id})")
        
        print("\n=== Testing JSON-RPC Models ===")
        
        # Create a JSON-RPC request
        jsonrpc_req = JSONRPCRequest(
            jsonrpc="2.0",
            method="execute",
            params={"command": "ls -la"},
            id=42
        )
        
        print(f"JSON-RPC Request: {jsonrpc_req.model_dump_json(indent=2)}")
        
        # Create a success response
        success_response = JSONRPCResponse(
            jsonrpc="2.0",
            result={"status": "started", "pid": 12345},
            id=42
        )
        
        print(f"\nSuccess Response: {success_response.model_dump_json(indent=2, exclude_none=True)}")
        
        # Create an error response
        error_response = JSONRPCResponse(
            jsonrpc="2.0",
            error=JSONRPCError(
                code=-32602,
                message="Invalid params",
                data="Command cannot be empty"
            ).model_dump(),
            id=42
        )
        
        print(f"\nError Response: {error_response.model_dump_json(indent=2, exclude_none=True)}")
        
        print("\n=== Testing Command Validation ===")
        
        # Test allowed commands
        test_cases = [
            ("echo test", None, True),
            ("echo test", ["echo", "ls"], True),
            ("rm -rf /", ["echo", "ls"], False),
            ("", None, False),
            ("ls -la", ["echo", "ls"], True)
        ]
        
        for command, allowed, expected in test_cases:
            valid, msg = validate_command(command, allowed)
            status = "✓" if valid == expected else "✗"
            print(f"{status} Command: '{command}' | Allowed: {allowed} | Valid: {valid}")
            if msg:
                print(f"   Message: {msg}")
        
        print("\n=== Testing Stream Output Model ===")
        
        outputs = [
            StreamOutput(type="stdout", data="Hello World\n", truncated=False),
            StreamOutput(type="stderr", data="Error: File not found...\n", truncated=True)
        ]
        
        for output in outputs:
            truncated = " (truncated)" if output.truncated else ""
            print(f"{output.type}: {output.data.strip()}{truncated}")
        
        print("\n✅ All model tests completed!")
        
        print("\n=== Testing Structured Error Types ===")
        
        # Test TimeoutError
        try:
            raise TimeoutError("Operation timed out after 30 seconds", duration=30.0)
        except TimeoutError as e:
            print(f"TimeoutError: {e}, duration={e.duration}s")
        
        # Test RateLimitError
        try:
            raise RateLimitError("Rate limit exceeded", retry_after=60)
        except RateLimitError as e:
            print(f"RateLimitError: {e}, retry_after={e.retry_after}s")
        
        # Test ProcessNotFoundError
        try:
            raise ProcessNotFoundError("Process not found", pid=12345, pgid=67890)
        except ProcessNotFoundError as e:
            print(f"ProcessNotFoundError: {e}, pid={e.pid}, pgid={e.pgid}")
        
        # Test CommandNotAllowedError
        try:
            raise CommandNotAllowedError("Command not allowed", command="rm -rf /")
        except CommandNotAllowedError as e:
            print(f"CommandNotAllowedError: {e}, command='{e.command}'")
        
        # Test SessionLimitError
        try:
            raise SessionLimitError("Too many sessions", current_sessions=10, max_sessions=10)
        except SessionLimitError as e:
            print(f"SessionLimitError: {e}, current={e.current_sessions}, max={e.max_sessions}")
        
        print("\n✅ All error type tests completed!")