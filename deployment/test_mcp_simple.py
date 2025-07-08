#!/usr/bin/env python3
"""Test MCP protocol with a simple echo command."""

import asyncio
import json
import websockets

async def test_mcp_simple():
    """Test executing a simple echo command through MCP protocol."""
    uri = "ws://localhost:8003/ws/mcp"
    
    print("Testing MCP Protocol with Simple Echo Command")
    print("=" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")
            
            # Wait for connection notification
            response = await websocket.recv()
            conn_response = json.loads(response)
            print(f"\n1. Connection established:")
            print(f"   Session ID: {conn_response['params']['session_id']}")
            
            # Execute a simple echo command
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": "echo 'def add_numbers(a, b):\\n    return a + b' > /tmp/add_numbers.py && echo 'File created successfully'"
                },
                "id": 1
            }
            
            print("\n2. Sending execution request...")
            print(f"   Command: echo command to create Python file")
            await websocket.send(json.dumps(execute_request))
            
            # Collect streaming responses
            print("\n3. Receiving output:")
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Handle streaming output
                if response_data.get("method") == "process.output":
                    output = response_data["params"]["data"]
                    print(f"   Output: {output.strip()}")
                
                # Check for completion
                elif "result" in response_data and response_data.get("id") == 1:
                    result = response_data["result"]
                    print(f"\n✓ Execution completed!")
                    print(f"   Status: {result['status']}")
                    print(f"   Exit code: {result['exit_code']}")
                    
                    # Verify file was created
                    try:
                        with open('/tmp/add_numbers.py', 'r') as f:
                            print("\n4. Created file content:")
                            print("-" * 40)
                            print(f.read())
                            print("-" * 40)
                    except FileNotFoundError:
                        print("\n❌ File was not created")
                    
                    break
                
                # Handle errors
                elif "error" in response_data:
                    print(f"\n❌ Error: {response_data['error']}")
                    break
            
            print("\n✅ MCP Protocol test completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_simple())