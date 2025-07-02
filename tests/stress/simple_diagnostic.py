#!/usr/bin/env python3
"""
Simple diagnostic to understand why WebSocket handler fails after Claude commands
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

async def test_handler_behavior():
    """Test what happens to the WebSocket handler"""
    
    # Kill any existing handlers
    os.system('pkill -9 -f websocket_handler')
    await asyncio.sleep(2)
    
    # Start handler
    logger.info("Starting WebSocket handler...")
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
    handler = subprocess.Popen(
        [sys.executable, handler_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    
    await asyncio.sleep(3)
    logger.info(f"Handler started with PID: {handler.pid}")
    
    ws_url = "ws://localhost:8004/ws"
    
    # Test 1: Simple echo
    logger.info("\n=== Test 1: Echo command ===")
    try:
        async with websockets.connect(ws_url) as ws:
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": "echo 'Hello'"},
                "id": "1"
            }
            await ws.send(json.dumps(request))
            
            # Wait for completion
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("method") == "process.completed":
                    logger.info("✅ Echo completed successfully")
                    break
    except Exception as e:
        logger.error(f"❌ Echo failed: {e}")
    
    # Check handler state
    if handler.poll() is None:
        logger.info("✅ Handler still running after echo")
    else:
        logger.error("❌ Handler died after echo!")
        return
    
    await asyncio.sleep(2)
    
    # Test 2: First Claude command
    logger.info("\n=== Test 2: First Claude command ===")
    try:
        async with websockets.connect(ws_url) as ws:
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'},
                "id": "2"
            }
            await ws.send(json.dumps(request))
            
            # Collect output
            output_count = 0
            start = time.time()
            while time.time() - start < 30:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    method = data.get("method", "")
                    
                    if method == "process.output":
                        output_count += 1
                    elif method == "process.completed":
                        logger.info(f"✅ First Claude completed (received {output_count} output messages)")
                        break
                except asyncio.TimeoutError:
                    continue
    except Exception as e:
        logger.error(f"❌ First Claude failed: {e}")
    
    # Check handler state
    if handler.poll() is None:
        logger.info("✅ Handler still running after first Claude")
    else:
        logger.error("❌ Handler died after first Claude!")
        stdout, _ = handler.communicate()
        logger.error(f"Handler output: {stdout[-1000:]}")
        return
    
    await asyncio.sleep(2)
    
    # Test 3: Second Claude command
    logger.info("\n=== Test 3: Second Claude command (expect failure) ===")
    try:
        # First check if we can connect
        logger.info("Attempting to connect...")
        async with websockets.connect(ws_url, ping_timeout=5) as ws:
            logger.info("✅ Connected to WebSocket")
            
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": 'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'},
                "id": "3"
            }
            await ws.send(json.dumps(request))
            logger.info("✅ Sent command")
            
            # Wait for any response
            received_count = 0
            start = time.time()
            while time.time() - start < 20:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    method = data.get("method", "")
                    received_count += 1
                    
                    if method:
                        logger.info(f"Received: {method}")
                    
                    if method == "process.completed":
                        exit_code = data.get("params", {}).get("exit_code")
                        logger.info(f"✅ Second Claude completed! Exit code: {exit_code}")
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout after {received_count} messages...")
                    continue
                
    except Exception as e:
        logger.error(f"❌ Second Claude failed at connection: {type(e).__name__}: {e}")
    
    # Final state check
    if handler.poll() is None:
        logger.info("\n✅ Handler still running at end")
        
        # Check if it accepts new connections
        try:
            async with websockets.connect(ws_url, ping_timeout=2) as ws:
                await ws.close()
            logger.info("✅ Handler still accepts connections")
        except:
            logger.error("❌ Handler not accepting new connections")
            
        # Kill handler
        handler.terminate()
    else:
        logger.error("\n❌ Handler died!")
    
    logger.info("\n=== SUMMARY ===")
    logger.info("The WebSocket handler becomes unresponsive after processing")
    logger.info("a Claude command, even though the process is still running.")
    logger.info("New connections timeout during the handshake phase.")

if __name__ == "__main__":
    asyncio.run(test_handler_behavior())