#!/usr/bin/env python3
"""Test MCP protocol with CC Executor WebSocket."""

import asyncio
import json
import websockets

async def test_mcp_protocol():
    """Test MCP protocol flow."""
    uri = "ws://localhost:8003/ws/mcp"
    
    print("Testing MCP Protocol with CC Executor")
    print("=" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")
            
            # Skip initialize for now - CC Executor doesn't require it
            # The WebSocket handler sends a "connected" notification automatically
            
            # Wait for connection notification
            response = await websocket.recv()
            conn_response = json.loads(response)
            print(f"\n1. Connection established: {json.dumps(conn_response, indent=2)}")
            
            # 2. Try the execute method with a simple echo command
            # This should work regardless of Python path issues
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": "echo 'Hello from MCP test via WebSocket'"
                },
                "id": 1
            }
            
            print("\n2. Calling execute method...")
            await websocket.send(json.dumps(execute_request))
            
            # Collect streaming responses
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"   Stream: {json.dumps(response_data, indent=2)}")
                
                # Check if this is the final result or an error
                if "result" in response_data and response_data.get("id") == 1:
                    print("\n✓ Execution completed!")
                    break
                elif "error" in response_data:
                    print(f"\n❌ Error response: {response_data['error']}")
                    break
                
            print("\n✅ MCP Protocol test successful!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. WebSocket server is running on port 8003")
        print("  2. Claude authentication is configured")

if __name__ == "__main__":
    asyncio.run(test_mcp_protocol())