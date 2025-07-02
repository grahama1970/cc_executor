#!/usr/bin/env python3
"""Final verification test for sequential Claude command execution.

This test runs multiple Claude commands in rapid succession to verify
that the process group cleanup logic is working correctly. If any command
hangs, it indicates a zombie process issue.
"""

import asyncio
import json
import websockets
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def run_single_test(ws_url: str, command: str) -> bool:
    """Runs a single command and waits for completion."""
    print(f"---\nExecuting: {command[:50]}...")
    start_time = time.time()
    try:
        async with websockets.connect(ws_url) as websocket:
            # Execute command
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": 1
            }))

            # Wait for completion message
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                data = json.loads(response)
                if data.get("method") == "process.completed":
                    exit_code = data.get("params", {}).get("exit_code", -1)
                    duration = time.time() - start_time
                    if exit_code == 0:
                        print(f"  ✓ SUCCESS in {duration:.1f}s (Exit Code: 0)")
                        return True
                    else:
                        print(f"  ✗ FAILED in {duration:.1f}s (Exit Code: {exit_code})")
                        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False

async def main():
    """Main function to run the sequential test suite."""
    ws_url = "ws://localhost:8004/ws"
    print("=" * 60)
    print("Final Verification: Sequential Command Execution")
    print("=" * 60)
    print("This test will run 5 Claude commands in rapid succession.")
    print("If any command hangs, it indicates a zombie process issue.")
    print()

    commands = [
        'claude "What is 2+2?" --output-format json',
        'claude "What is 5+5?" --output-format json',
        'claude "What is 10+10?" --output-format json',
        'claude "What is 3*3?" --output-format json',
        'claude "What is 100/10?" --output-format json',
    ]

    success_count = 0
    for i, command in enumerate(commands):
        print(f"Running test {i+1}/{len(commands)}...")
        success = await run_single_test(ws_url, command)
        if success:
            success_count += 1
        # Short pause to ensure cleanup completes
        await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)
    print(f"Total tests: {len(commands)}")
    print(f"Successful:  {success_count}")
    print(f"Failed:      {len(commands) - success_count}")

    if success_count == len(commands):
        print("\n✅ All tests passed. The zombie process issue is resolved.")
        return 0
    else:
        print("\n❌ Some tests failed. The issue may persist.")
        return 1

if __name__ == "__main__":
    # Assumes the websocket_handler.py server is running
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
