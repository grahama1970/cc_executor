#!/usr/bin/env python3
"""
Unified startup script for CC Executor services.
Runs both WebSocket server and FastAPI in the same process.
"""

import asyncio
import uvicorn
from multiprocessing import Process
import sys
import os
import time

# Add the source directory to Python path
sys.path.insert(0, '/app/src')

def start_websocket_server():
    """Start the WebSocket server on port 8003."""
    from cc_executor.core.websocket_handler import app as ws_app
    
    uvicorn.run(
        ws_app,
        host="0.0.0.0",
        port=8003,
        ws_ping_interval=20.0,
        ws_ping_timeout=30.0,
        ws_max_size=10 * 1024 * 1024
    )

def start_api_server():
    """Start the FastAPI server on port 8000."""
    # Set WebSocket URL to localhost since we're in the same container
    os.environ["WEBSOCKET_URL"] = "ws://localhost:8003/ws"
    
    # Set WEBSOCKET_HOST for the client connection
    os.environ["WEBSOCKET_HOST"] = "localhost"
    os.environ["WEBSOCKET_PORT"] = "8003"
    
    from cc_executor.api.main import app as api_app
    
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000
    )

def main():
    """Start both servers."""
    print("🚀 Starting CC Executor services...")
    
    # Start WebSocket server in a separate process
    ws_process = Process(target=start_websocket_server)
    ws_process.start()
    
    # Give WebSocket server time to start
    print("⏳ Waiting for WebSocket server to start...")
    time.sleep(5)
    
    # Start API server in main process
    print("🌐 Starting API server...")
    start_api_server()
    
    # Wait for WebSocket process
    ws_process.join()

if __name__ == "__main__":
    main()