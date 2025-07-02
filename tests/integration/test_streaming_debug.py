#!/usr/bin/env python3
"""Debug version of stress test to check streaming behavior"""

import asyncio
import json
import time
import sys
from pathlib import Path
import websockets

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_streaming():
    """Test WebSocket streaming with debug output"""
    ws_url = "ws://localhost:8003/ws/mcp"
    
    print("Connecting to WebSocket...")
    async with websockets.connect(ws_url) as websocket:
        # Wait for connection message
        connect_msg = await websocket.recv()
        connect_data = json.loads(connect_msg)
        
        if connect_data.get('method') == 'connected':
            session_id = connect_data['params']['session_id']
            print(f"✓ Connected. Session: {session_id}")
        
        # Send a simple command to test streaming
        marker = f"MARKER_{int(time.time())}"
        prompt = f"{marker}\\n\\nWrite a short haiku about Python programming."
        command = f'bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH claude --print \\"{prompt}\\""'
        
        execute_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {
                "command": command
            }
        }
        
        await websocket.send(json.dumps(execute_msg))
        print(f"→ Sent command")
        print("Waiting for responses...")
        
        chunk_count = 0
        start_time = time.time()
        
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                method = response_data.get('method')
                
                if method == 'process.output':
                    chunk_count += 1
                    data = response_data['params'].get('data', '')
                    type_ = response_data['params'].get('type', 'stdout')
                    
                    print(f"\n[CHUNK {chunk_count} - {type_} - {time.time()-start_time:.2f}s]")
                    print(f"Data: {repr(data)}")
                    print(f"Actual output: {data}", end="", flush=True)
                    
                elif method == 'process.completed':
                    exit_code = response_data['params'].get('exit_code')
                    print(f"\n\n✓ Process completed with exit code: {exit_code}")
                    print(f"Total chunks received: {chunk_count}")
                    print(f"Total time: {time.time()-start_time:.2f}s")
                    break
                    
                elif method == 'process.started':
                    print(f"Process started: {response_data['params']}")
                    
                elif response_data.get('error'):
                    print(f"\n❌ Error: {response_data['error']}")
                    break
                else:
                    print(f"\nOther message: {method} - {response_data}")
                    
            except asyncio.TimeoutError:
                print(".", end="", flush=True)
                continue


if __name__ == "__main__":
    asyncio.run(test_streaming())