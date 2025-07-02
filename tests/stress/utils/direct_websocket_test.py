#!/usr/bin/env python3
"""
Direct test of WebSocket handler timeout fix
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

# Add project to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

async def test_websocket():
    """Test a single command to see what happens"""
    
    # Check if handler is running
    ws_url = "ws://localhost:8004/ws"
    
    # Test command that should trigger timeout
    command = 'claude -p "Write a 1000 word essay about testing" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
    
    logger.info(f"Testing command: {command[:50]}...")
    
    try:
        async with websockets.connect(ws_url, ping_timeout=None) as ws:
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": str(uuid.uuid4())
            }
            
            await ws.send(json.dumps(request))
            logger.info("Request sent, waiting for responses...")
            
            start = time.time()
            outputs = []
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    
                    if data.get("method") == "process.output":
                        output = data.get("params", {}).get("data", "")
                        outputs.append(output)
                        logger.info(f"[{time.time() - start:.1f}s] Output received: {len(output)} chars")
                        
                        # Try to parse Claude output
                        if output.strip().startswith("{"):
                            try:
                                claude_data = json.loads(output)
                                if claude_data.get("type") == "assistant":
                                    content = claude_data.get("message", {}).get("content", [])
                                    if content and isinstance(content, list):
                                        text = content[0].get("text", "")
                                        logger.info(f"Claude response: '{text[:100]}...' ({len(text)} chars)")
                            except:
                                pass
                    
                    elif data.get("method") == "process.completed":
                        exit_code = data.get("params", {}).get("exit_code")
                        duration = time.time() - start
                        logger.success(f"✅ Process completed in {duration:.1f}s with exit code: {exit_code}")
                        
                        # Analyze output
                        full_output = "".join(outputs)
                        word_count = len(full_output.split())
                        logger.info(f"Total output: {len(outputs)} messages, ~{word_count} words")
                        break
                    
                    elif data.get("method") == "process.error":
                        error = data.get("params", {}).get("error", "Unknown error")
                        logger.error(f"Process error: {error}")
                        break
                        
                except asyncio.TimeoutError:
                    elapsed = time.time() - start
                    if elapsed > 120:
                        logger.error(f"Timeout after {elapsed:.1f}s - handler is stuck")
                        break
                    else:
                        logger.debug(f"[{elapsed:.1f}s] Waiting for more output...")
                        
    except Exception as e:
        logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    # First check if handler is already running
    try:
        subprocess.run(["lsof", "-i", ":8004"], check=True, capture_output=True)
        logger.info("Handler is already running on port 8004")
    except:
        logger.error("No handler running! Start it first with: python -m cc_executor.core.websocket_handler")
        sys.exit(1)
    
    asyncio.run(test_websocket())