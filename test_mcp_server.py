#!/usr/bin/env python3
"""Test MCP WebSocket server directly"""

import asyncio
import websockets
import json

async def test_mcp_server():
    """Test connection to MCP server"""
    urls = [
        "ws://localhost:8004/ws",  # Docker port
        "ws://127.0.0.1:8004/ws",  # Docker port
        "ws://localhost:8003/ws",  # Local port
        "ws://127.0.0.1:8003/ws",  # Local port
    ]
    
    for url in urls:
        print(f"\nTrying {url}...")
        try:
            async with websockets.connect(url) as ws:
                print(f"✅ Connected to {url}")
                
                # Send a test request
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {"command": "echo 'Hello MCP'"},
                    "id": 1
                }
                await ws.send(json.dumps(request))
                print("Sent test request")
                
                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"Response: {response}")
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    print(f"\nTest {'succeeded' if success else 'failed'}")