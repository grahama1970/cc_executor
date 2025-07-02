#!/usr/bin/env python3
"""
Quick test to validate WebSocket handler with a simple Claude command

This is a minimal test to ensure the basic setup works before running
the full stress test suite.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


async def quick_test():
    """Run a quick test with Claude"""
    print("=" * 60)
    print("QUICK WEBSOCKET TEST")
    print("=" * 60)
    
    # Check Claude CLI
    result = subprocess.run(['which', 'claude'], capture_output=True)
    if result.returncode != 0:
        print("❌ Claude CLI not found")
        print("Install with: npm install -g @anthropic-ai/claude-cli")
        return False
    print("✓ Claude CLI found")
    
    # Kill any existing process
    os.system('lsof -ti:8004 | xargs -r kill -9 2>/dev/null')
    time.sleep(1)
    
    # Start WebSocket handler
    print("\nStarting WebSocket handler...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(project_root, 'src')
    
    handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
    proc = subprocess.Popen(
        [sys.executable, handler_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    
    # Wait for startup
    started = False
    for i in range(20):
        if proc.poll() is not None:
            output, _ = proc.communicate()
            print(f"❌ Handler died: {output[:500]}")
            return False
        
        try:
            async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as ws:
                await ws.close()
                started = True
                break
        except:
            await asyncio.sleep(0.5)
    
    if not started:
        print("❌ Handler failed to start")
        proc.terminate()
        return False
    
    print("✓ WebSocket handler started")
    
    # Run test command
    print("\nExecuting test command...")
    command = 'claude -p "What is 2+2?" --output-format stream-json --dangerously-skip-permissions --allowedTools none'
    
    try:
        async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as websocket:
            # Send command
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": "quick-test"
            }
            
            await websocket.send(json.dumps(request))
            print("✓ Command sent")
            
            # Wait for completion
            start_time = time.time()
            completed = False
            found_answer = False
            exit_code = None
            
            while time.time() - start_time < 30:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("method") == "process.output":
                        output = data.get("params", {}).get("data", "")
                        if "4" in output or "four" in output.lower():
                            found_answer = True
                            print("✓ Found answer in output")
                    
                    elif data.get("method") == "process.completed":
                        completed = True
                        exit_code = data.get("params", {}).get("exit_code")
                        print(f"✓ Process completed with exit code: {exit_code}")
                        break
                
                except asyncio.TimeoutError:
                    continue
            
            duration = time.time() - start_time
            
            if completed and exit_code == 0 and found_answer:
                print(f"\n✅ TEST PASSED in {duration:.1f}s")
                success = True
            else:
                print(f"\n❌ TEST FAILED")
                print(f"  Completed: {completed}")
                print(f"  Exit code: {exit_code}")
                print(f"  Found answer: {found_answer}")
                success = False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        success = False
    
    finally:
        # Cleanup
        print("\nStopping WebSocket handler...")
        proc.terminate()
        proc.wait(timeout=5)
    
    return success


async def main():
    """Main entry point"""
    success = await quick_test()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Quick test passed! Ready to run full stress tests.")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run basic validation:")
        print("   python stress_tests/validate_websocket_basic.py")
        print("\n2. Run comprehensive tests:")
        print("   python stress_tests/comprehensive_websocket_stress_test.py")
        print("\n3. Run unified stress tests:")
        print("   python stress_tests/run_unified_stress_tests.py")
    else:
        print("\n" + "=" * 60)
        print("❌ Quick test failed. Please fix issues before running full tests.")
        print("=" * 60)
        print("\nDebug steps:")
        print("1. Check WebSocket handler logs:")
        print("   tail -50 logs/websocket_handler_*.log | grep ERROR")
        print("\n2. Test Claude CLI directly:")
        print("   claude -p 'What is 2+2?' --output-format json")
        print("\n3. Check environment:")
        print("   echo $PYTHONPATH")
        print("   echo $ANTHROPIC_API_KEY")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)