"""
CC Executor Core Module.

This package contains the modular implementation of the MCP WebSocket service.
The service provides secure remote command execution with process control
capabilities over WebSocket using the JSON-RPC 2.0 protocol.

Architecture:
- config.py: Configuration constants and environment variables
- models.py: Pydantic models for JSON-RPC messages and validation
- session_manager.py: WebSocket session lifecycle management
- process_manager.py: Process execution and control (PAUSE/RESUME/CANCEL)
- stream_handler.py: Stdout/stderr streaming with back-pressure handling
- websocket_handler.py: WebSocket protocol and message routing
- main.py: FastAPI application and service endpoints

Third-party Documentation:
- Model Context Protocol: https://modelcontextprotocol.io/docs
- JSON-RPC 2.0: https://www.jsonrpc.org/specification

Example Input:
    from cc_executor.core import app, SERVICE_NAME, SERVICE_VERSION
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

Expected Output:
    Service running on http://0.0.0.0:8003
    WebSocket endpoint: ws://localhost:8003/ws/mcp
    Health check: http://localhost:8003/health
"""

try:
    from .main import app
    from .config import SERVICE_NAME, SERVICE_VERSION
except ImportError:
    # For standalone execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from main import app
    from config import SERVICE_NAME, SERVICE_VERSION

__all__ = [
    # Main FastAPI app
    "app",
    
    # Service metadata
    "SERVICE_NAME", 
    "SERVICE_VERSION",
]


if __name__ == "__main__":
    """Quick module test."""
    print(f"✓ {SERVICE_NAME} v{SERVICE_VERSION} module loaded")
    print(f"✓ FastAPI app: {app.title}")
    print(f"✓ Endpoints: {len(app.routes)} routes configured")