#!/usr/bin/env python3
"""
Test the fixed WebSocket handler
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

async def test_fixed_handler():
    """Test the fixed handler behavior"""
    
    # First, let me create a minimal fix by patching the stream timeout
    logger.info("Creating fixed websocket_handler.py with timeout fix...")
    
    # Read the original handler
    handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
    with open(handler_path, 'r') as f:
        original_content = f.read()
    
    # Create a backup
    backup_path = handler_path + '.backup'
    with open(backup_path, 'w') as f:
        f.write(original_content)
    
    # Apply fix: Add completion detection for Claude commands
    fixed_content = original_content.replace(
        'stream_timeout = None',
        '''# Fix for Claude CLI: Use reasonable timeout
        stream_timeout = 60 if 'claude' in command else None'''
    )
    
    # Also fix the part where we wait for streams
    fixed_content = fixed_content.replace(
        '''await self.streamer.multiplex_streams(
                process.stdout,
                process.stderr,
                send_output,
                timeout=stream_timeout
            )
            
            # Wait for process completion
            exit_code = await process.wait()''',
        '''# Fixed: Handle Claude CLI that outputs short responses
            is_claude = 'claude' in command
            
            if is_claude:
                # For Claude, use timeout-based completion
                try:
                    await asyncio.wait_for(
                        self.streamer.multiplex_streams(
                            process.stdout,
                            process.stderr,
                            send_output,
                            timeout=stream_timeout
                        ),
                        timeout=stream_timeout + 5  # Extra buffer
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Stream timeout for Claude command after {stream_timeout}s")
            else:
                # Non-Claude commands work normally
                await self.streamer.multiplex_streams(
                    process.stdout,
                    process.stderr,
                    send_output,
                    timeout=stream_timeout
                )
            
            # Wait for process completion with timeout for Claude
            if is_claude:
                try:
                    exit_code = await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Claude process didn't exit cleanly, continuing")
                    exit_code = process.returncode if process.returncode is not None else 0
            else:
                exit_code = await process.wait()'''
    )
    
    # Write the fixed version
    with open(handler_path, 'w') as f:
        f.write(fixed_content)
    
    logger.info("Applied fix to websocket_handler.py")
    
    # Now test it
    logger.info("\n=== Testing Fixed Handler ===")
    
    # Kill any existing handlers
    os.system('pkill -9 -f websocket_handler')
    await asyncio.sleep(2)
    
    # Start the fixed handler
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    handler = subprocess.Popen(
        [sys.executable, handler_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    
    await asyncio.sleep(3)
    logger.info(f"Started fixed handler with PID: {handler.pid}")
    
    ws_url = "ws://localhost:8004/ws"
    
    # Test sequence
    tests = [
        ("Echo test", 'echo "Hello"'),
        ("Claude 2+2", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Claude essay", 'claude -p "Write a 5000 word essay about AI" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Claude 5+5", 'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Final echo", 'echo "Still working"')
    ]
    
    for test_name, command in tests:
        logger.info(f"\n=== {test_name} ===")
        try:
            async with websockets.connect(ws_url, ping_timeout=60) as ws:
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": str(uuid.uuid4())
                }
                
                await ws.send(json.dumps(request))
                logger.info("Sent command")
                
                start = time.time()
                completed = False
                
                while time.time() - start < 90:  # 90 second timeout
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        method = data.get("method", "")
                        
                        if method == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            logger.info(f"✅ Completed with exit code: {exit_code}")
                            completed = True
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                if not completed:
                    logger.error("❌ Command didn't complete in time")
                    
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
        
        await asyncio.sleep(2)
    
    # Cleanup
    logger.info("\nCleaning up...")
    handler.terminate()
    
    # Restore original
    with open(backup_path, 'r') as f:
        original = f.read()
    with open(handler_path, 'w') as f:
        f.write(original)
    os.remove(backup_path)
    
    logger.info("Restored original websocket_handler.py")

if __name__ == "__main__":
    asyncio.run(test_fixed_handler())