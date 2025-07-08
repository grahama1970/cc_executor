#!/usr/bin/env python3
"""Test WebSocket connection to CC Executor."""

import asyncio
import json
import websockets

async def test_websocket():
    """Test basic WebSocket connection and command execution."""
    uri = "ws://localhost:8003/ws"
    
    async with websockets.connect(uri) as websocket:
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            },
            "id": 1
        }
        
        await websocket.send(json.dumps(init_request))
        response = await websocket.recv()
        print(f"Initialize response: {response}")
        
        # Send a simple command
        command_request = {
            "jsonrpc": "2.0",
            "method": "cc_execute/execute",
            "params": {
                "command": "echo 'Hello from Docker WebSocket!'"
            },
            "id": 2
        }
        
        await websocket.send(json.dumps(command_request))
        
        # Receive responses
        while True:
            response = await websocket.recv()
            print(f"Command response: {response}")
            response_data = json.loads(response)
            
            # Check if it's the final result
            if "result" in response_data and response_data.get("id") == 2:
                break

if __name__ == "__main__":
    asyncio.run(test_websocket())