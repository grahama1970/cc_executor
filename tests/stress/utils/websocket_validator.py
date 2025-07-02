#!/usr/bin/env python3
"""
Basic WebSocket validation script to test core functionality

This script performs basic tests to ensure:
1. WebSocket handler starts correctly
2. Can execute simple commands
3. JSON streaming works
4. Process completion is detected
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import websockets
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


async def validate_basic_functionality():
    """Validate basic WebSocket functionality"""
    print("=" * 60)
    print("WEBSOCKET HANDLER BASIC VALIDATION")
    print("=" * 60)
    
    # Step 1: Check environment
    print("\n1. Checking environment...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_path = os.path.join(project_root, 'src')
    
    if not os.path.exists(src_path):
        print(f"❌ src directory not found at: {src_path}")
        return False
    print(f"✓ src directory found: {src_path}")
    
    # Check for .mcp.json
    mcp_config = os.path.join(project_root, '.mcp.json')
    if os.path.exists(mcp_config):
        print(f"✓ MCP config found: {mcp_config}")
    else:
        print("⚠️  No .mcp.json found (MCP tools won't be available)")
    
    # Step 2: Start WebSocket handler
    print("\n2. Starting WebSocket handler...")
    
    # Kill any existing process
    os.system('lsof -ti:8004 | xargs -r kill -9 2>/dev/null')
    time.sleep(1)
    
    env = os.environ.copy()
    env['PYTHONPATH'] = src_path
    
    handler_path = os.path.join(project_root, 'src/cc_executor/core/websocket_handler.py')
    proc = subprocess.Popen(
        [sys.executable, handler_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    
    # Wait for startup
    print("   Waiting for handler to start...")
    start_time = time.time()
    started = False
    
    while time.time() - start_time < 10:
        if proc.poll() is not None:
            output, _ = proc.communicate()
            print(f"❌ Handler died during startup!")
            print(f"Output:\n{output}")
            return False
        
        try:
            # Try to connect
            async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as ws:
                await ws.close()
                started = True
                break
        except:
            await asyncio.sleep(0.5)
    
    if not started:
        print("❌ Handler failed to start within 10 seconds")
        proc.terminate()
        return False
    
    print("✓ WebSocket handler started successfully")
    
    # Step 3: Test basic command execution
    print("\n3. Testing basic command execution...")
    
    try:
        async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as websocket:
            # Test simple echo command
            command = 'echo "Hello from WebSocket test"'
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": "test-1"
            }
            
            print(f"   Sending: {command}")
            await websocket.send(json.dumps(request))
            
            # Collect responses
            responses = []
            completed = False
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout and not completed:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    responses.append(data)
                    
                    if data.get("method") == "process.completed":
                        completed = True
                        exit_code = data.get("params", {}).get("exit_code")
                        print(f"   ✓ Process completed with exit code: {exit_code}")
                    elif data.get("method") == "process.output":
                        output = data.get("params", {}).get("data", "").strip()
                        if output:
                            print(f"   Output: {output}")
                except asyncio.TimeoutError:
                    continue
            
            if not completed:
                print("   ❌ Command did not complete within timeout")
                return False
    
    except Exception as e:
        print(f"   ❌ Error during command execution: {e}")
        proc.terminate()
        return False
    
    # Step 4: Test JSON streaming with Claude
    print("\n4. Testing Claude command with JSON streaming...")
    
    # Check if Claude CLI exists
    claude_check = subprocess.run(['which', 'claude'], capture_output=True)
    if claude_check.returncode != 0:
        print("   ⚠️  Claude CLI not found - skipping Claude test")
        print("   Install with: npm install -g @anthropic-ai/claude-cli")
    else:
        try:
            async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as websocket:
                command = 'claude -p "What is 2+2?" --output-format stream-json --dangerously-skip-permissions --allowedTools none'
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": command},
                    "id": "test-2"
                }
                
                print(f"   Sending Claude command...")
                await websocket.send(json.dumps(request))
                
                # Collect JSON responses
                json_messages = []
                completed = False
                timeout = 30
                start_time = time.time()
                
                while time.time() - start_time < timeout and not completed:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        json_messages.append(data)
                        
                        if data.get("method") == "process.completed":
                            completed = True
                            exit_code = data.get("params", {}).get("exit_code")
                            print(f"   ✓ Claude command completed with exit code: {exit_code}")
                        elif data.get("method") == "process.output":
                            # Don't print all output, just confirm we're receiving it
                            if len(json_messages) == 5:  # Print status after first few messages
                                print(f"   ✓ Receiving streaming JSON output...")
                    except asyncio.TimeoutError:
                        continue
                
                if completed:
                    print(f"   ✓ Received {len(json_messages)} JSON messages")
                else:
                    print("   ❌ Claude command did not complete within timeout")
        
        except Exception as e:
            print(f"   ❌ Error during Claude test: {e}")
    
    # Step 5: Cleanup
    print("\n5. Cleaning up...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
        print("✓ WebSocket handler stopped cleanly")
    except:
        proc.kill()
        print("⚠️  Had to force kill WebSocket handler")
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the comprehensive stress test:")
    print("   python stress_tests/comprehensive_websocket_stress_test.py")
    print("\n2. Check WebSocket handler logs:")
    print("   tail -f logs/websocket_handler_*.log")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(validate_basic_functionality())
    sys.exit(0 if success else 1)