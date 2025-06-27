"""
Main entry point for CC Executor MCP WebSocket Service.

This module sets up the FastAPI application, initializes all components,
and provides the WebSocket endpoint and health checks. It serves as the
orchestrator for the modular service architecture.

Third-party Documentation:
- FastAPI: https://fastapi.tiangolo.com/
- Uvicorn: https://www.uvicorn.org/
- WebSocket API: https://fastapi.tiangolo.com/advanced/websockets/
- Kubernetes Health Checks: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Example Input:
    Health check: GET /health
    WebSocket: ws://localhost:8003/ws/mcp
    Command line: python main.py --port 8003 --host 0.0.0.0

Expected Output:
    Health response: {"status":"healthy","service":"CC Executor MCP","version":"1.0.0","active_sessions":0,"max_sessions":10}
    WebSocket: Bidirectional JSON-RPC communication
    Server logs: Structured logs with session tracking
    Graceful shutdown: All sessions cleaned up properly
"""

import argparse
import sys
import uuid
from typing import Dict, Any
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from loguru import logger

try:
    from .config import (
        SERVICE_NAME, SERVICE_VERSION, DEFAULT_PORT,
        LOG_LEVEL, LOG_FORMAT, DEBUG_MODE
    )
    from .session_manager import SessionManager
    from .process_manager import ProcessManager
    from .stream_handler import StreamHandler
    from .websocket_handler import WebSocketHandler
except ImportError:
    # For standalone execution
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import (
        SERVICE_NAME, SERVICE_VERSION, DEFAULT_PORT,
        LOG_LEVEL, LOG_FORMAT, DEBUG_MODE
    )
    from session_manager import SessionManager
    from process_manager import ProcessManager
    from stream_handler import StreamHandler
    from websocket_handler import WebSocketHandler


# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=LOG_LEVEL,
    colorize=True
)

# Initialize FastAPI app
app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="MCP WebSocket Service for remote command execution"
)

# Initialize components
session_manager = SessionManager()
process_manager = ProcessManager()
stream_handler = StreamHandler()
websocket_handler = WebSocketHandler(
    session_manager,
    process_manager,
    stream_handler
)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns service status and session statistics.
    """
    stats = session_manager.get_stats()
    
    return JSONResponse({
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "active_sessions": stats["active_sessions"],
        "max_sessions": stats["max_sessions"],
        "uptime_seconds": stats["uptime_seconds"]
    })


@app.get("/healthz")
async def health_check_k8s() -> Dict[str, str]:
    """
    Kubernetes-style health check endpoint.
    
    Returns minimal response for liveness/readiness probes.
    """
    return {"status": "ok"}


@app.websocket("/ws/mcp")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for MCP protocol.
    
    Handles bidirectional communication for command execution
    and process control.
    """
    session_id = str(uuid.uuid4())
    
    logger.info(f"New WebSocket connection: {session_id}")
    
    try:
        await websocket_handler.handle_connection(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
        # Connection already closed by handler
    finally:
        logger.info(f"WebSocket connection closed: {session_id}")


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Performs initialization tasks.
    """
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION}")
    logger.info(f"Debug mode: {DEBUG_MODE}")
    logger.info(f"Session limit: {session_manager.max_sessions}")
    
    # Could add periodic cleanup task here if needed
    # e.g., for expired session cleanup


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    
    Performs cleanup tasks.
    """
    logger.info("Shutting down service...")
    
    # Clean up all active sessions
    all_sessions = await session_manager.get_all_sessions()
    for session_id in all_sessions:
        logger.info(f"Cleaning up session: {session_id}")
        await websocket_handler._cleanup_session(session_id)
        
    logger.info("Shutdown complete")


def main():
    """
    Main entry point for running the service directly.
    """
    parser = argparse.ArgumentParser(
        description="CC Executor MCP WebSocket Service"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    import uvicorn
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_config=None,  # Use loguru instead of uvicorn logging
        # WebSocket keepalive settings (configurable via environment)
        ws_ping_interval=float(os.environ.get("WS_PING_INTERVAL", "20.0")),  # Send ping interval
        ws_ping_timeout=float(os.environ.get("WS_PING_TIMEOUT", "30.0")),   # Wait for pong timeout
        ws_max_size=int(os.environ.get("WS_MAX_SIZE", str(10 * 1024 * 1024)))  # Max message size
    )


if __name__ == "__main__":
    """
    Direct debug entry point for VSCode.
    
    VSCode Debug:
        1. Set breakpoints in websocket_endpoint() or startup_event()
        2. Press F5 to start the full server
        3. Connect with any WebSocket client to ws://localhost:8003/ws/mcp
    """
    """
    Usage example demonstrating service startup and testing.
    
    Start the service:
        python main.py --port 8003
        
    Test with curl:
        # Health check
        curl http://localhost:8003/health | jq
        
        # WebSocket test with wscat
        npm install -g wscat
        wscat -c ws://localhost:8003/ws/mcp
        
        # Send execute command
        {"jsonrpc":"2.0","method":"execute","params":{"command":"echo hello"},"id":1}
        
    Test with Python client:
        See examples/test_websocket_handler.py for comprehensive tests
    """
    
    import os
    import subprocess
    import time
    import requests
    
    # Check if running as test
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("=== Main Service Test ===\n")
        
        # Test 1: Health check endpoint
        print("--- Test 1: Testing health endpoints ---")
        
        # Start server in background
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        server_process = subprocess.Popen(
            [sys.executable, __file__, "--port", "8004"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        print("Starting server on port 8004...")
        time.sleep(2)
        
        try:
            # Test health endpoint
            response = requests.get("http://localhost:8004/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✓ Health check passed: {health_data['status']}")
                print(f"  Service: {health_data['service']} v{health_data['version']}")
                print(f"  Sessions: {health_data['active_sessions']}/{health_data['max_sessions']}")
            else:
                print(f"✗ Health check failed: {response.status_code}")
            
            # Test K8s health endpoint
            response = requests.get("http://localhost:8004/healthz")
            if response.status_code == 200:
                print(f"✓ K8s health check passed: {response.json()['status']}")
            else:
                print(f"✗ K8s health check failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("✗ Could not connect to server")
        finally:
            # Stop server
            server_process.terminate()
            server_process.wait()
            print("\n✓ Server stopped cleanly")
        
        print("\n✅ Main service tests completed!")
        print("\nFor WebSocket tests, run:")
        print("  python examples/test_websocket_handler.py")
        
    else:
        # Normal startup
        main()