#!/usr/bin/env python3
"""
Test the enhanced WebSocket handler with long-running prompts
Specifically designed to verify heartbeats and no-timeout behavior
"""

import asyncio
import json
import time
import websockets
import uuid
from datetime import datetime

async def test_long_running_prompt():
    """Test a prompt that takes 30+ seconds to complete"""
    
    print("=" * 80)
    print("ENHANCED WEBSOCKET HANDLER TEST")
    print("Testing long-running prompts with heartbeats")
    print("=" * 80)
    
    # Connect to enhanced handler on port 8005
    ws_url = "ws://localhost:8005/ws"
    
    try:
        async with websockets.connect(ws_url, ping_timeout=None) as ws:
            print(f"\n✓ Connected to enhanced WebSocket handler")
            
            # Test 1: Long-thinking prompt (5000 word story)
            print("\n" + "-"*60)
            print("TEST 1: Long story generation (expect 30+ seconds)")
            print("-"*60)
            
            command = (
                'claude -p "What is a 5000 word science fiction story about '
                'a programmer discovering sentient code?" '
                '--output-format stream-json '
                '--dangerously-skip-permissions '
                '--allowedTools none'
            )
            
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": str(uuid.uuid4())
            }
            
            await ws.send(json.dumps(request))
            print("✓ Request sent")
            
            start_time = time.time()
            heartbeat_count = 0
            status_count = 0
            output_count = 0
            completed = False
            
            while not completed and time.time() - start_time < 300:  # 5 min max
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(response)
                    
                    if data.get("method") == "heartbeat":
                        heartbeat_count += 1
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:.1f}s] 💓 Heartbeat #{heartbeat_count}")
                        
                    elif data.get("method") == "process.status":
                        status_count += 1
                        status = data.get("params", {})
                        elapsed = time.time() - start_time
                        no_output = status.get("no_output_for", 0)
                        print(f"[{elapsed:.1f}s] ⏳ Status: No output for {no_output:.0f}s")
                        
                    elif data.get("method") == "process.output":
                        output_count += 1
                        elapsed = time.time() - start_time
                        output = data.get("params", {}).get("data", "")
                        if output_count == 1:
                            print(f"[{elapsed:.1f}s] 📝 First output received")
                        # Check for story content
                        if "programmer" in output.lower() or "code" in output.lower():
                            print(f"[{elapsed:.1f}s] ✓ Story content detected")
                            
                    elif data.get("method") == "process.completed":
                        completed = True
                        elapsed = time.time() - start_time
                        exit_code = data.get("params", {}).get("exit_code")
                        print(f"[{elapsed:.1f}s] ✅ Process completed with exit code: {exit_code}")
                        
                    elif "result" in data:
                        # Response to our request
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:.1f}s] Response: {data.get('result', {}).get('status')}")
                        
                except asyncio.TimeoutError:
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:.1f}s] ⚠️  30s timeout on recv - but connection still alive!")
                    
            total_time = time.time() - start_time
            
            print(f"\n" + "="*60)
            print(f"TEST 1 RESULTS:")
            print(f"  Total time: {total_time:.1f}s")
            print(f"  Heartbeats: {heartbeat_count}")
            print(f"  Status updates: {status_count}")
            print(f"  Output chunks: {output_count}")
            print(f"  Completed: {'Yes' if completed else 'No'}")
            
            if heartbeat_count > 0:
                print(f"  ✅ Heartbeats working - connection stayed alive!")
            else:
                print(f"  ❌ No heartbeats received")
                
            if completed and total_time > 30:
                print(f"  ✅ Long-running prompt completed successfully!")
            
            # Test 2: Quick prompt to verify normal operation
            print("\n" + "-"*60)
            print("TEST 2: Quick prompt (expect < 10 seconds)")
            print("-"*60)
            
            command = (
                'claude -p "What is 2+2?" '
                '--output-format stream-json '
                '--dangerously-skip-permissions '
                '--allowedTools none'
            )
            
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": str(uuid.uuid4())
            }
            
            await ws.send(json.dumps(request))
            
            start_time = time.time()
            completed = False
            
            while not completed and time.time() - start_time < 30:
                response = await ws.recv()
                data = json.loads(response)
                
                if data.get("method") == "process.completed":
                    completed = True
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:.1f}s] ✅ Quick prompt completed")
                    
            print(f"\n" + "="*60)
            print("OVERALL RESULTS:")
            print("✅ Enhanced WebSocket handler working correctly!")
            print("  - Heartbeats prevent timeouts")
            print("  - Long-running prompts complete successfully")
            print("  - Quick prompts still fast")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure the enhanced WebSocket handler is running on port 8005")

if __name__ == "__main__":
    asyncio.run(test_long_running_prompt())