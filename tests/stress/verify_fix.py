#!/usr/bin/env python3
"""
Verify that the WebSocket handler fix works
Run the handler standalone and test it
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
import uuid

# Get project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

async def test_fix():
    """Test the fixed WebSocket handler"""
    
    # Kill any existing handlers
    os.system('pkill -9 -f websocket_handler')
    await asyncio.sleep(2)
    
    logger.info("Starting fixed WebSocket handler...")
    
    # Create a simple startup script
    startup_script = f"""
import sys
sys.path.insert(0, '{project_root}/src')
import os
os.chdir('{project_root}')

# Set environment
os.environ['PYTHONPATH'] = '{project_root}/src'
if 'ANTHROPIC_API_KEY' in os.environ:
    del os.environ['ANTHROPIC_API_KEY']

# Now import and run the handler
try:
    # Import as script
    with open('{project_root}/src/cc_executor/core/websocket_handler.py') as f:
        code = f.read()
    exec(code)
except Exception as e:
    print(f"Error starting handler: {{e}}")
    import traceback
    traceback.print_exc()
"""
    
    # Write startup script
    startup_path = "/tmp/start_handler.py"
    with open(startup_path, 'w') as f:
        f.write(startup_script)
    
    # Start handler with the startup script
    handler = subprocess.Popen(
        [sys.executable, startup_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for startup
    await asyncio.sleep(5)
    
    if handler.poll() is not None:
        output, _ = handler.communicate()
        logger.error(f"Handler died during startup:\n{output}")
        return
    
    logger.info("Handler started, running tests...")
    
    # Test sequence
    ws_url = "ws://localhost:8004/ws"
    test_results = []
    
    tests = [
        ("Echo", 'echo "test"'),
        ("Claude Simple", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Claude Essay", 'claude -p "Write a 1000 word essay about testing" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
        ("Claude After Essay", 'claude -p "What is 5+5?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
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
                
                start = time.time()
                completed = False
                output_lines = 0
                
                while time.time() - start < 90:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        
                        if data.get("method") == "process.output":
                            output_lines += 1
                        elif data.get("method") == "process.completed":
                            exit_code = data.get("params", {}).get("exit_code")
                            logger.info(f"✅ Completed with exit code: {exit_code} (received {output_lines} output lines)")
                            completed = True
                            test_results.append((test_name, True, time.time() - start))
                            break
                    except asyncio.TimeoutError:
                        continue
                
                if not completed:
                    logger.error(f"❌ Test timed out after {time.time() - start:.1f}s")
                    test_results.append((test_name, False, time.time() - start))
                    
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            test_results.append((test_name, False, 0))
        
        await asyncio.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success, _ in test_results if success)
    total = len(test_results)
    
    logger.info(f"Total: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    
    for name, success, duration in test_results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name:<20} {duration:.1f}s")
    
    if passed == total:
        logger.success("\n🎉 FIX VERIFIED! WebSocket handler can handle sequential Claude commands!")
    else:
        logger.warning("\n⚠️ Some tests failed - fix may need adjustment")
    
    # Cleanup
    handler.terminate()
    os.remove(startup_path)

if __name__ == "__main__":
    asyncio.run(test_fix())