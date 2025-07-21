#!/usr/bin/env python3
"""
Simple server runner that bypasses the usage function.
"""
import sys
import os
import uvicorn


from main import app
from config import DEFAULT_PORT, SERVICE_NAME, SERVICE_VERSION
from loguru import logger

def run_server(port=DEFAULT_PORT, host="0.0.0.0"):
    """Run the server directly."""
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION} on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,  # Use loguru instead of uvicorn logging
        # WebSocket keepalive settings
        ws_ping_interval=float(os.environ.get("WS_PING_INTERVAL", "20.0")),
        ws_ping_timeout=float(os.environ.get("WS_PING_TIMEOUT", "30.0")),
        ws_max_size=int(os.environ.get("WS_MAX_SIZE", str(10 * 1024 * 1024)))
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CC Executor Server Runner")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    
    args = parser.parse_args()
    run_server(port=args.port, host=args.host)