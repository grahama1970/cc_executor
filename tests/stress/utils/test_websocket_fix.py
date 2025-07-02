#!/usr/bin/env python3
"""
Simple test to verify WebSocket handler fix
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

# Setup paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

async def test_handler():
    """Test the WebSocket handler with the fix"""
    
    # Kill any existing handlers
    os.system('pkill -9 -f websocket_handler')
    os.system('lsof -ti:8004 | xargs -r kill -9 2>/dev/null')
    await asyncio.sleep(2)
    
    logger.info("Starting WebSocket handler...")
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    # CRITICAL: Unset API key for Claude CLI
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
    
    # Start handler
    handler = subprocess.Popen(
        [sys.executable, "-m", "cc_executor.core.websocket_handler"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=project_root
    )
    
    # Wait for startup
    await asyncio.sleep(5)
    
    if handler.poll() is not None:
        output, _ = handler.communicate()
        logger.error(f"Handler died during startup:\n{output}")
        return
    
    logger.success("Handler started!")
    
    # Run test sequence
    ws_url = "ws://localhost:8004/ws"
    
    tests = [
        ("Test 1: Simple command", 'echo "Hello World"'),
        ("Test 2: Claude simple", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Test 3: Claude essay", 'claude -p "Write a 1000 word essay about WebSockets" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Test 4: Claude after essay", 'claude -p "What is 10+10?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
    ]
    
    results = []
    
    for test_name, command in tests:
        logger.info(f"\n=== {test_name} ===")
        
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
                output_count = 0
                timeout_warning = False
                
                while time.time() - start < 90:  # 90s overall timeout
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        
                        if data.get("method") == "process.output":
                            output_count += 1
                            # Check if we see timeout warning in logs
                            if "Stream timeout" in str(data):
                                timeout_warning = True
                                
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            duration = time.time() - start
                            logger.success(f"✅ Completed in {duration:.1f}s (exit: {exit_code}, outputs: {output_count})")
                            
                            if timeout_warning:
                                logger.warning("Had timeout warning but completed successfully!")
                            
                            completed = True
                            results.append((test_name, True, duration))
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                if not completed:
                    duration = time.time() - start
                    logger.error(f"❌ Timed out after {duration:.1f}s")
                    results.append((test_name, False, duration))
                    
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            results.append((test_name, False, 0))
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, duration in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name:<30} {duration:.1f}s")
    
    logger.info(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")
    
    if passed == total:
        logger.success("\n🎉 ALL TESTS PASSED! The fix works!")
    elif passed > total // 2:
        logger.warning(f"\n⚠️ Partial success: {passed}/{total} tests passed")
    else:
        logger.error(f"\n❌ Fix not working: only {passed}/{total} tests passed")
    
    # Cleanup
    handler.terminate()
    handler.wait()

if __name__ == "__main__":
    asyncio.run(test_handler())