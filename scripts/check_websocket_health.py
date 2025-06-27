#!/usr/bin/env python3
"""Check WebSocket server health and diagnose connection issues"""

import asyncio
import aiohttp
import websockets
import json
import sys

async def check_health():
    """Check HTTP health endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8003/health', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ HTTP Health Check OK: {data}")
                    return True
                else:
                    print(f"❌ HTTP Health Check Failed: Status {resp.status}")
                    return False
    except asyncio.TimeoutError:
        print("❌ HTTP Health Check Timeout")
        return False
    except Exception as e:
        print(f"❌ HTTP Health Check Error: {e}")
        return False

async def check_websocket():
    """Test WebSocket connection"""
    try:
        print("\nTesting WebSocket connection...")
        async with websockets.connect(
            'ws://localhost:8003/ws/mcp',
            open_timeout=10,
            close_timeout=5
        ) as ws:
            # Should receive session info
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            print(f"✅ WebSocket Connected: {data}")
            
            # Try sending a simple command
            test_msg = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "id": "health_check",
                    "command": "echo 'WebSocket test'",
                    "path": "/tmp"
                },
                "id": "test_1"
            }
            await ws.send(json.dumps(test_msg))
            print("✅ Test message sent")
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            print(f"✅ Response received: {response[:100]}...")
            return True
            
    except asyncio.TimeoutError:
        print("❌ WebSocket connection timeout")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {type(e).__name__}: {e}")
        return False

async def main():
    print("=== WebSocket Server Health Check ===")
    
    # Check if server is listening
    import subprocess
    result = subprocess.run(['lsof', '-i:8003'], capture_output=True, text=True)
    if 'LISTEN' in result.stdout:
        print("✅ Server is listening on port 8003")
    else:
        print("❌ No server listening on port 8003")
        print("Run: cd src/cc_executor && python -m core.main")
        return
    
    # Check HTTP health
    http_ok = await check_health()
    
    # Check WebSocket
    ws_ok = await check_websocket()
    
    if http_ok and ws_ok:
        print("\n✅ Server is healthy and ready for tests")
    else:
        print("\n❌ Server has issues - restart recommended")
        print("Run: pkill -f 'python.*core.main' && cd src/cc_executor && python -m core.main")

if __name__ == "__main__":
    asyncio.run(main())