#!/usr/bin/env python3
"""
Simple test to verify the WebSocket timeout fix works
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

async def execute_command(ws_url, command, timeout=120):
    """Execute a command via WebSocket"""
    try:
        async with websockets.connect(ws_url, ping_timeout=None) as ws:
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": str(uuid.uuid4())
            }
            
            await ws.send(json.dumps(request))
            
            start = time.time()
            completed = False
            outputs = 0
            
            while time.time() - start < timeout:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    
                    if data.get("method") == "process.output":
                        outputs += 1
                    elif data.get("method") == "process.completed":
                        completed = True
                        exit_code = data.get("params", {}).get("exit_code", -1)
                        duration = time.time() - start
                        return True, exit_code, outputs, duration
                        
                except asyncio.TimeoutError:
                    continue
            
            return False, None, outputs, time.time() - start
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False, None, 0, 0

async def main():
    # Kill any existing handlers
    os.system('pkill -9 -f websocket_handler')
    await asyncio.sleep(2)
    
    logger.info("Starting WebSocket handler...")
    
    # Start handler
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    handler = subprocess.Popen(
        [sys.executable, "-m", "cc_executor.core.websocket_handler"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=project_root
    )
    
    # Wait for startup
    await asyncio.sleep(5)
    
    if handler.poll() is not None:
        output, _ = handler.communicate()
        logger.error(f"Handler died: {output}")
        return
    
    ws_url = "ws://localhost:8004/ws"
    
    # Test sequence designed to reproduce the issue
    tests = [
        ("Test 1: Echo", 'echo "test"', 10),
        ("Test 2: Claude simple", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
        ("Test 3: Claude essay (triggers fix)", 'claude -p "Write a 2000 word essay about artificial intelligence" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 120),
        ("Test 4: Claude after timeout", 'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 30),
        ("Test 5: Final echo", 'echo "still working"', 10),
    ]
    
    results = []
    
    for name, command, timeout in tests:
        logger.info(f"\n=== {name} ===")
        success, exit_code, outputs, duration = await execute_command(ws_url, command, timeout)
        
        if success:
            logger.success(f"✅ PASSED in {duration:.1f}s (exit: {exit_code}, outputs: {outputs})")
        else:
            logger.error(f"❌ FAILED after {duration:.1f}s")
        
        results.append((name, success, duration))
        await asyncio.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FIX VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, duration in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name:<35} {duration:6.1f}s")
    
    logger.info(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")
    
    if passed == total:
        logger.success("\n🎉 FIX VERIFIED! All tests passed!")
        logger.info("The 60s timeout prevents the handler from hanging on short Claude responses.")
    else:
        logger.warning(f"\n⚠️ Fix partially working: {passed}/{total} tests passed")
    
    # Check handler still alive
    if handler.poll() is None:
        logger.info("\nHandler process still running - good!")
        handler.terminate()
    else:
        logger.error("\nHandler process died during tests!")

if __name__ == "__main__":
    asyncio.run(main())