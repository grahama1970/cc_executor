#!/usr/bin/env python3
"""
Test token limit detection in the updated websocket_handler.py
"""

import asyncio
import json
import websockets

async def test_token_detection():
    """Test that token limit errors are properly detected and notified."""
    
    # Connect to the standard WebSocket handler
    uri = "ws://localhost:8005/ws"
    
    print("Token Limit Detection Test")
    print("=" * 60)
    print(f"Connecting to {uri}")
    
    async with websockets.connect(uri, ping_timeout=None) as websocket:
        # Get connection message
        msg = await websocket.recv()
        session_data = json.loads(msg)
        print(f"✅ Connected: {session_data['params']['session_id']}")
        
        # Send a command that should trigger token limit
        command = {
            "jsonrpc": "2.0",
            "method": "execute",
            "params": {
                "command": 'claude -p "Write a comprehensive 10000 word technical guide on Python decorators. Include extensive code examples for every concept." --output-format stream-json --dangerously-skip-permissions --allowedTools none --verbose'
            },
            "id": "token-test"
        }
        
        print("\nSending request for 10000 word guide...")
        await websocket.send(json.dumps(command))
        
        # Monitor for token limit notification
        token_limit_detected = False
        timeout_count = 0
        
        while timeout_count < 10:  # Limit iterations
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(msg)
                
                method = data.get("method", "")
                
                if method == "error.token_limit_exceeded":
                    token_limit_detected = True
                    params = data["params"]
                    print(f"\n✅ TOKEN LIMIT NOTIFICATION RECEIVED!")
                    print(f"   Session ID: {params.get('session_id')}")
                    print(f"   Error Type: {params.get('error_type')}")
                    print(f"   Token Limit: {params.get('limit'):,}")
                    print(f"   Message: {params.get('message')}")
                    print(f"   Suggestion: {params.get('suggestion')}")
                    print(f"   Recoverable: {params.get('recoverable')}")
                    
                elif method == "error.rate_limit_exceeded":
                    params = data["params"]
                    print(f"\n⚠️ RATE LIMIT NOTIFICATION RECEIVED!")
                    print(f"   Error Type: {params.get('error_type')}")
                    print(f"   Message: {params.get('message')}")
                    print(f"   Recoverable: {params.get('recoverable')}")
                    break
                    
                elif method == "process.completed":
                    params = data["params"]
                    print(f"\n✅ Process completed")
                    print(f"   Status: {params.get('status')}")
                    print(f"   Exit code: {params.get('exit_code')}")
                    break
                    
                elif method == "heartbeat":
                    print("💓", end="", flush=True)
                    
            except asyncio.TimeoutError:
                timeout_count += 1
                print(f"\n⏱️ Timeout #{timeout_count}")
                
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        if token_limit_detected:
            print("✅ Token limit detection is working!")
            print("   The WebSocket handler successfully:")
            print("   1. Detected the token limit error in Claude's output")
            print("   2. Sent a special notification to the client")
            print("   3. Provided actionable suggestions for retry")
        else:
            print("⚠️ Token limit was not detected")
            print("   This could mean:")
            print("   1. The prompt didn't exceed token limits")
            print("   2. Rate limits were hit instead")
            print("   3. The test needs adjustment")


if __name__ == "__main__":
    print("Make sure the WebSocket handler is running on port 8005")
    print("Start it with: python -m cc_executor.core.websocket_handler")
    print()
    
    try:
        asyncio.run(test_token_detection())
    except KeyboardInterrupt:
        print("\n\nTest interrupted")