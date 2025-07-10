#!/usr/bin/env python3
"""
Simple server starter that properly daemonizes the uvicorn process.
"""

import sys
import os
import subprocess
from pathlib import Path


def start_server(host="127.0.0.1", port=8003):
    """Start the server in the background using nohup."""
    log_dir = Path.home() / ".cc_executor"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "server.log"
    pid_file = Path("/tmp/cc_executor.pid")
    
    # Build the command
    cmd = [
        "nohup",
        sys.executable,
        "-m", "uvicorn",
        "cc_executor.core.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    # Start the server with nohup
    with open(log_file, 'a') as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    
    # Save the PID
    pid_file.write_text(str(process.pid))
    
    print(f"Server started with PID: {process.pid}")
    print(f"Log file: {log_file}")
    print(f"WebSocket URL: ws://{host}:{port}/ws/mcp")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()
    
    start_server(args.host, args.port)