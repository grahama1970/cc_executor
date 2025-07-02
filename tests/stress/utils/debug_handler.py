#!/usr/bin/env python3
"""Debug script to test WebSocket handler startup."""

import asyncio
import os
import sys
import time
import websockets
from pathlib import Path

async def test_handler_startup():
    """Test starting the WebSocket handler with proper output handling."""
    print("Testing WebSocket handler startup...")
    
    # Kill any existing processes
    os.system('lsof -ti:8004 | xargs -r kill -9 2>/dev/null')
    time.sleep(1)
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
    
    # Create log directory
    log_dir = Path("test_outputs/debug")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"handler_startup_{int(time.time())}.log"
    
    print(f"Logging to: {log_file}")
    
    # Method 1: Write to file (avoids pipe buffer)
    with open(log_file, 'w') as f:
        process = await asyncio.create_subprocess_exec(
            sys.executable, 'src/cc_executor/core/websocket_handler.py',
            stdout=f,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )
        
        # Wait a bit for startup
        await asyncio.sleep(3)
        
        if process.returncode is not None:
            print(f"Process died with code: {process.returncode}")
        else:
            print("Process is running, checking connection...")
            
            # Try to connect
            try:
                async with websockets.connect("ws://localhost:8004/ws") as ws:
                    await ws.close()
                print("✓ Successfully connected to WebSocket!")
            except Exception as e:
                print(f"✗ Failed to connect: {e}")
                
        # Terminate the process
        process.terminate()
        await process.wait()
    
    # Show the log
    print("\nLog contents:")
    print("-" * 60)
    with open(log_file, 'r') as f:
        print(f.read())

if __name__ == "__main__":
    asyncio.run(test_handler_startup())