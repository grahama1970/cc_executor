#!/usr/bin/env python3
"""
Simple WebSocket test for CC Executor MCP server.
Tests the WebSocket connection without importing any cc_executor modules.
"""

import asyncio
import json
import websockets
import uuid
import sys


async def test_websocket_connection():
    """Test basic WebSocket connection to MCP server."""
    print("Testing WebSocket connection to CC Executor MCP server...")
    
    uri = "ws://localhost:8003/ws/mcp"
    
    try:
        # Connect to the WebSocket
        async with websockets.connect(uri, ping_interval=None) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Test 1: Simple echo test
            print("\n📝 Test 1: Echo test...")
            session_id = str(uuid.uuid4())
            request = {
                "type": "execute",
                "command": "echo 'Hello from WebSocket test'",
                "session_id": session_id,
                "timeout": 10
            }
            
            await websocket.send(json.dumps(request))
            print(f"Sent: {json.dumps(request, indent=2)}")
            
            # Collect responses
            responses = []
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(msg)
                    responses.append(data)
                    print(f"Received: {json.dumps(data, indent=2)}")
                    
                    if data.get("type") == "result" or data.get("type") == "error":
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
            
            # Test 2: Math calculation
            print("\n📝 Test 2: Math calculation...")
            session_id = str(uuid.uuid4())
            request = {
                "type": "execute",
                "command": "What is 25 + 17? Just respond with the number.",
                "session_id": session_id,
                "timeout": 30
            }
            
            await websocket.send(json.dumps(request))
            print(f"Sent: {json.dumps(request, indent=2)}")
            
            # Collect responses
            full_output = ""
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(msg)
                    print(f"Received type: {data.get('type')}")
                    
                    if data.get("type") == "stream":
                        chunk = data.get("data", "")
                        full_output += chunk
                        print(f"Stream chunk: {chunk[:100]}...")
                    elif data.get("type") == "result":
                        result = data.get("result", full_output)
                        print(f"✅ Result: {result}")
                        break
                    elif data.get("type") == "error":
                        print(f"❌ Error: {data.get('error')}")
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
            
            print("\n✅ WebSocket tests completed!")
            
    except ConnectionRefusedError:
        print(f"❌ Connection refused - is the server running on {uri}?")
        print("   Run: python -m uvicorn cc_executor.core.main:app --port 8003")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False
    
    return True


async def main():
    """Run the WebSocket test."""
    success = await test_websocket_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())