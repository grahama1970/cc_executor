#!/usr/bin/env python3
"""
JSON-RPC WebSocket test for CC Executor MCP server.
Tests the WebSocket connection using proper JSON-RPC format.
"""

import asyncio
import json
import websockets
import uuid
import sys


async def test_websocket_jsonrpc():
    """Test WebSocket connection using JSON-RPC format."""
    print("Testing WebSocket JSON-RPC connection to CC Executor MCP server...")
    
    uri = "ws://localhost:8003/ws/mcp"
    
    try:
        # Connect to the WebSocket
        async with websockets.connect(uri, ping_interval=None) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Wait for connection message
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"Connection message: {json.dumps(data, indent=2)}")
            session_id = data["params"]["session_id"]
            
            # Test 1: Simple echo test using JSON-RPC
            print("\n📝 Test 1: Echo test (JSON-RPC)...")
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "execute",
                "params": {
                    "command": "echo 'Hello from JSON-RPC test'",
                    "timeout": 10
                }
            }
            
            await websocket.send(json.dumps(request))
            print(f"Sent: {json.dumps(request, indent=2)}")
            
            # Collect responses
            full_output = ""
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=15)
                    data = json.loads(msg)
                    
                    if data.get("method") == "process.output":
                        # Stream output
                        params = data.get("params", {})
                        if params.get("type") == "stdout":
                            chunk = params.get("data", "")
                            full_output += chunk
                            print(f"Stream: {chunk.strip()}")
                    elif data.get("method") == "process.exit":
                        # Process completed
                        params = data.get("params", {})
                        exit_code = params.get("exit_code", -1)
                        print(f"Process exited with code: {exit_code}")
                    elif "result" in data:
                        # Final result
                        print(f"✅ Result: {data['result']}")
                        break
                    elif "error" in data:
                        # Error response
                        print(f"❌ Error: {data['error']}")
                        break
                    else:
                        print(f"Other message: {json.dumps(data, indent=2)}")
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
            
            # Test 2: Math calculation via Claude
            print("\n📝 Test 2: Math calculation via Claude...")
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "execute",
                "params": {
                    "command": "What is 25 + 17? Just respond with the number.",
                    "timeout": 30
                }
            }
            
            await websocket.send(json.dumps(request))
            print(f"Sent: {json.dumps(request, indent=2)}")
            
            # Collect responses
            full_output = ""
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=35)
                    data = json.loads(msg)
                    
                    if data.get("method") == "process.output":
                        # Stream output
                        params = data.get("params", {})
                        if params.get("type") == "stdout":
                            chunk = params.get("data", "")
                            full_output += chunk
                            print(f"Stream chunk received ({len(chunk)} chars)")
                    elif data.get("method") == "process.exit":
                        # Process completed
                        params = data.get("params", {})
                        exit_code = params.get("exit_code", -1)
                        print(f"Process exited with code: {exit_code}")
                        if full_output:
                            print(f"Full output: {full_output.strip()[:200]}...")
                    elif "result" in data:
                        # Final result
                        result = data.get("result", {})
                        output = result.get("output", full_output).strip()
                        print(f"✅ Result: {output}")
                        break
                    elif "error" in data:
                        # Error response
                        print(f"❌ Error: {data['error']}")
                        break
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    if full_output:
                        print(f"Partial output: {full_output.strip()[:200]}...")
                    break
            
            # Test 3: Control command (kill if needed)
            print("\n📝 Test 3: Session info...")
            request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "control",
                "params": {
                    "action": "info"
                }
            }
            
            await websocket.send(json.dumps(request))
            print(f"Sent: {json.dumps(request, indent=2)}")
            
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(msg)
                print(f"Response: {json.dumps(data, indent=2)}")
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
            
            print("\n✅ WebSocket JSON-RPC tests completed!")
            
    except ConnectionRefusedError:
        print(f"❌ Connection refused - is the server running on {uri}?")
        print("   Run: python -m uvicorn cc_executor.core.main:app --port 8003")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Run the WebSocket test."""
    success = await test_websocket_jsonrpc()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())