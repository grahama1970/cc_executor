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
    AI-friendly usage example for main service verification.
    This demonstrates core functionality without blocking operations.
    """
    import json
    import os
    from usage_helper import OutputCapture
    
    # Check if being run with --server flag to start actual server
    if len(sys.argv) > 1 and "--server" in sys.argv:
        main()
    else:
        with OutputCapture(__file__) as capture:
            print("=== CC Executor Main Service Usage ===\n")
            
            # Test 1: Service configuration
            print("--- Test 1: Service Configuration ---")
            print(f"Service: {SERVICE_NAME} v{SERVICE_VERSION}")
            print(f"Default port: {DEFAULT_PORT}")
            print(f"Debug mode: {DEBUG_MODE}")
            print(f"Log level: {LOG_LEVEL}")
            print("✓ Configuration loaded successfully")
            
            # Test 2: Component initialization
            print("\n--- Test 2: Component Initialization ---")
            
            # Initialize components
            test_session_manager = SessionManager()
            print(f"✓ SessionManager initialized (max sessions: {test_session_manager.max_sessions})")
            
            test_process_manager = ProcessManager()
            print("✓ ProcessManager initialized")
            
            test_stream_handler = StreamHandler()
            print(f"✓ StreamHandler initialized (max buffer: {test_stream_handler.max_line_size:,} bytes)")
            
            test_websocket_handler = WebSocketHandler(
                test_session_manager,
                test_process_manager,
                test_stream_handler
            )
            print("✓ WebSocketHandler initialized")
            
            # Test 3: FastAPI application endpoints
            print("\n--- Test 3: FastAPI Application Endpoints ---")
            print("Available endpoints:")
            for route in app.routes:
                if hasattr(route, 'path'):
                    print(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")
            
            # Test 4: Health check data structure
            print("\n--- Test 4: Health Check Response Structure ---")
            stats = test_session_manager.get_stats()
            health_response = {
                "status": "healthy",
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "active_sessions": stats["active_sessions"],
                "max_sessions": stats["max_sessions"],
                "uptime_seconds": stats["uptime_seconds"]
            }
            print(f"Health response: {json.dumps(health_response, indent=2)}")
            
            # Test 5: WebSocket protocol info
            print("\n--- Test 5: WebSocket Protocol Info ---")
            print("WebSocket endpoint: /ws/mcp")
            print("Protocol: JSON-RPC 2.0 over WebSocket")
            print("Supported methods:")
            print("  - execute: Run commands with streaming output")
            print("  - control: Process control (PAUSE/RESUME/CANCEL)")
            print("Environment variables:")
            print(f"  - WS_PING_INTERVAL: {os.environ.get('WS_PING_INTERVAL', '20.0')}s")
            print(f"  - WS_PING_TIMEOUT: {os.environ.get('WS_PING_TIMEOUT', '30.0')}s")
            print(f"  - WS_MAX_SIZE: {int(os.environ.get('WS_MAX_SIZE', str(10 * 1024 * 1024))):,} bytes")
            
            # Result
            print("\n✅ All main service components verified!")
            print("\nTo start the service:")
            print("  python main.py --server --port 8003")
            print("\nFor full integration tests:")
            print("  python examples/test_websocket_handler.py")