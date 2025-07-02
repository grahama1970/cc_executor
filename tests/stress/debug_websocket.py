#!/usr/bin/env python3
"""
Debug WebSocket connection issues
"""

import asyncio
import json
import sys
import os
import subprocess
import time
import websockets
import uuid
from pathlib import Path

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="DEBUG")

async def test_websocket_connection():
    """Test WebSocket connection and command execution"""
    
    # Start WebSocket handler
    logger.info("Starting WebSocket handler...")
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    
    # CRITICAL: UNSET ANTHROPIC_API_KEY
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
    ws_process = subprocess.Popen(
        [sys.executable, handler_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    
    # Wait for startup
    await asyncio.sleep(2)
    
    try:
        # Test 1: Simple connection
        logger.info("\n=== Test 1: Simple WebSocket connection ===")
        try:
            async with websockets.connect("ws://localhost:8004/ws", ping_timeout=5) as ws:
                logger.success("Connected successfully")
                await ws.close()
        except Exception as e:
            logger.error(f"Connection failed: {e}")
        
        await asyncio.sleep(1)
        
        # Test 2: Execute simple command
        logger.info("\n=== Test 2: Execute simple command ===")
        try:
            async with websockets.connect("ws://localhost:8004/ws", ping_timeout=5) as ws:
                logger.info("Connected, sending command...")
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": "echo 'Hello World'"},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                logger.info("Command sent, waiting for response...")
                
                # Wait for responses
                timeout = 10
                start = time.time()
                while time.time() - start < timeout:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(response)
                        logger.info(f"Received: {data}")
                        
                        if data.get("method") == "process.completed":
                            logger.success("Command completed successfully")
                            break
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Test 2 failed: {e}")
        
        await asyncio.sleep(1)
        
        # Test 3: Multiple sequential connections
        logger.info("\n=== Test 3: Multiple sequential connections ===")
        for i in range(3):
            try:
                logger.info(f"Connection {i+1}/3...")
                async with websockets.connect("ws://localhost:8004/ws", ping_timeout=5) as ws:
                    request = {
                        "jsonrpc": "2.0", 
                        "method": "execute",
                        "params": {"command": f"echo 'Test {i+1}'"},
                        "id": str(uuid.uuid4())
                    }
                    await ws.send(json.dumps(request))
                    
                    # Just wait for connected message
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    logger.success(f"Connection {i+1} successful")
                    
            except Exception as e:
                logger.error(f"Connection {i+1} failed: {e}")
            
            await asyncio.sleep(0.5)
        
    finally:
        # Stop handler
        logger.info("\nStopping WebSocket handler...")
        ws_process.terminate()
        ws_process.wait(timeout=5)
        logger.info("WebSocket handler stopped")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())