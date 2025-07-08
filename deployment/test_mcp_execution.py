#!/usr/bin/env python3
"""Test MCP protocol with actual command execution."""

import asyncio
import json
import websockets
from loguru import logger

async def test_mcp_execution():
    """Test executing a real command through MCP protocol."""
    uri = "ws://localhost:8003/ws/mcp"
    
    print("Testing MCP Protocol with Real Command Execution")
    print("=" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")
            
            # Wait for connection notification
            response = await websocket.recv()
            conn_response = json.loads(response)
            print(f"\n1. Connection established:")
            print(f"   Session ID: {conn_response['params']['session_id']}")
            print(f"   Capabilities: {conn_response['params']['capabilities']}")
            
            # Execute a command to create a Python function
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": "claude -p 'Write a Python function that adds two numbers and saves it to /tmp/add_numbers.py'"
                },
                "id": 1
            }
            
            print("\n2. Sending execution request...")
            print(f"   Command: {execute_request['params']['command']}")
            await websocket.send(json.dumps(execute_request))
            
            # Collect streaming responses
            print("\n3. Receiving output:")
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Handle streaming output
                if response_data.get("method") == "process.output":
                    output = response_data["params"]["data"]
                    print(output, end='', flush=True)
                
                # Check for completion
                elif "result" in response_data and response_data.get("id") == 1:
                    result = response_data["result"]
                    print(f"\n\n✓ Execution completed!")
                    print(f"   Status: {result['status']}")
                    print(f"   Exit code: {result['exit_code']}")
                    
                    # Check if file was created
                    try:
                        with open('/tmp/add_numbers.py', 'r') as f:
                            print("\n4. Created file content:")
                            print("-" * 40)
                            print(f.read())
                            print("-" * 40)
                    except FileNotFoundError:
                        print("\n❌ File was not created at /tmp/add_numbers.py")
                    
                    break
                
                # Handle errors
                elif "error" in response_data:
                    print(f"\n❌ Error: {response_data['error']}")
                    break
            
            print("\n✅ MCP Protocol test completed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. WebSocket server is running on port 8003")
        print("  2. Claude is authenticated (claude /login)")
        print("  3. You have Claude CLI available")

if __name__ == "__main__":
    asyncio.run(test_mcp_execution())