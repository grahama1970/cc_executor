#!/usr/bin/env python3
"""
Simple test to verify MCP WebSocket is working
"""

import asyncio
import json
import websockets

async def test_mcp_websocket():
    """Test the MCP WebSocket endpoint"""
    uri = "ws://127.0.0.1:8003/ws/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Send a simple test request
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": "What is 2+2? Just the number."
                },
                "id": 1
            }
            
            print(f"📤 Sending: {json.dumps(request, indent=2)}")
            await websocket.send(json.dumps(request))
            
            # Receive response
            print("\n📥 Receiving responses:")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    print(f"  Response: {json.dumps(data, indent=2)}")
                    
                    # Check if this is the final result
                    if "result" in data or "error" in data:
                        break
                except asyncio.TimeoutError:
                    print("⏱️  Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Connection failed: {e}")

async def test_docker_websocket():
    """Test the Docker WebSocket endpoint"""
    uri = "ws://localhost:8004/ws/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"\n✅ Connected to Docker {uri}")
            
            # Send a simple test request
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": "What is 3+3? Just the number."
                },
                "id": 2
            }
            
            print(f"📤 Sending: {json.dumps(request, indent=2)}")
            await websocket.send(json.dumps(request))
            
            # Receive response
            print("\n📥 Receiving responses:")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    print(f"  Response: {json.dumps(data, indent=2)}")
                    
                    # Check if this is the final result
                    if "result" in data or "error" in data:
                        break
                except asyncio.TimeoutError:
                    print("⏱️  Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Docker connection failed: {e}")

async def main():
    print("🧪 Testing MCP WebSocket Endpoints\n")
    
    # Test local MCP
    await test_mcp_websocket()
    
    # Test Docker
    await test_docker_websocket()

if __name__ == "__main__":
    asyncio.run(main())