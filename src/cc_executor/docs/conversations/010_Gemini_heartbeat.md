**Addressing the Failure**

I'm still grappling with the error; a glaring oversight, really. The user's frustration is justified, as my initial response was incomplete. I've re-evaluated the direct instructions, identifying where I went awry. I'm aiming for absolute clarity this time around.


**Acknowledging the Blunder**

I've acknowledged my mistake: the user's feedback was, of course, spot-on. My earlier response was a significant misstep, failing to deliver the complete code snippets. I now understand the user's need for copy-paste functionality, making manual editing unnecessary. My focus is now solely on providing the complete, unabridged file content to rectify the issue.


**Regenerating the Output**

Okay, I've fully recognized the original error and the user's justified frustration. To rectify this, I'm committed to providing the complete, unabridged file content as requested, ensuring it's fully copy-paste ready. I've reviewed the code, and identified the five files needing updates for the "heartbeat" fix. Now, the output generation is proceeding, providing the complete content, eliminating all abbreviation errors. I am meticulously reviewing the content for any remaining issues.


You are absolutely right. My apologies. I failed to follow your direct instructions to provide the complete, unabridged files. Leaving out sections with "..." comments was a mistake and I understand your frustration.

I will provide the full and complete code for every file that needs to be changed. You can copy and paste these directly.

---

### Executive Summary: The Fix for Long-Running Tasks

The core problem is that the test suite's simple timeouts cannot distinguish between a **slow, working task** and a **dead, hung task**. A legitimate `claude-code` process that takes several minutes is incorrectly flagged as a failure.

The solution is to implement a **heartbeat pattern**.

1.  **The Server (`implementation.py`) Sends Heartbeats:** When a long task begins, the server will now send a `statusUpdate: "RUNNING"` message every 30 seconds. This heartbeat signals to the client, "I'm still alive and working."
2.  **The Clients (`*_test.py`) Listen Patiently:** The test clients will now use a longer timeout (e.g., 180 seconds) *between messages*. As long as they receive either stream output or a heartbeat, their idle timer resets. They will now only fail if the server goes completely silent for an extended period, which correctly indicates a system hang.

This change makes the system robust, allowing it to handle tasks of any duration while still protecting against true failures.

---
### **1. `docker-simple/prompts/cc_executor_mcp/implementation.py` (FIXED & COMPLETE)**

This version includes the heartbeat mechanism to support long-running tasks without causing client-side idle timeouts.

```python
#!/usr/bin/env python3
"""
MCP WebSocket Service - Production-Ready API Bridge
Implements the Model Context Protocol (MCP) standard for WebSocket communication.
Forwards commands to claude-api service using JSON streaming format.
Reference: https://docs.anthropic.com/en/docs/claude-code/cli-reference

FIXED: This version includes a heartbeat mechanism to support long-running tasks
without causing client-side idle timeouts.
"""
import asyncio
import json
import os
import uuid
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
import httpx

app = FastAPI(title="MCP WebSocket to HTTP Bridge")

# Configuration
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "http://claude-api:8000")
CLAUDE_STREAM_ENDPOINT = f"{CLAUDE_API_URL}/execute/claude-stream"
SESSIONS: Dict[str, Dict[str, Any]] = {}
HEARTBEAT_INTERVAL = 30  # Send a heartbeat every 30 seconds


async def send_heartbeats(websocket: WebSocket, msg_id: Any):
    """
    Periodically sends a 'RUNNING' status to keep the client connection alive
    and prevent idle timeouts on the client side for long-running tasks.
    """
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if websocket.client_state == WebSocketState.CONNECTED:
                print(f"DEBUG: Sending heartbeat for msg_id: {msg_id}")
                await websocket.send_json(mcp_status_update("RUNNING", msg_id))
            else:
                # Websocket is no longer connected, stop sending heartbeats.
                break
        except asyncio.CancelledError:
            # Task was cancelled, so stop gracefully.
            break
        except Exception as e:
            print(f"ERROR: Could not send heartbeat for msg_id {msg_id}: {e}")
            break


async def process_claude_stream(websocket: WebSocket, command: str, msg_id: Any):
    """
    Connects to the claude-api, sends the command, and processes the resulting
    JSON event stream, translating events into MCP messages for the client.
    """
    async for event in forward_command_to_claude_stream(command):
        etype = event.get("type")

        if etype == "user":
            message = event.get("message", {})
            for item in message.get("content", []):
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    await websocket.send_json(mcp_output_message(item.get("content", ""), msg_id))
        elif etype == "assistant":
            message = event.get("message", {})
            for item in message.get("content", []):
                if isinstance(item, dict) and item.get("type") == "text":
                    await websocket.send_json(mcp_output_message(item.get("text", ""), msg_id))
        elif etype == "error":
            await websocket.send_json(mcp_error(event.get("error", "Unknown error"), msg_id))
            await websocket.send_json(mcp_status_update("FAILED", msg_id))
            return  # Stop processing on fatal error
        elif etype == "complete":
            await websocket.send_json(mcp_status_update("COMPLETED", msg_id))
            return  # Stop processing on completion


async def handle_execute(websocket: WebSocket, session_id: str, command: str, msg_id: Any):
    """
    Orchestrates command execution by running the main processing task and a
    heartbeat task concurrently. Ensures the heartbeat is cancelled when execution ends.
    """
    heartbeat_task = None
    try:
        # Start heartbeat to signal ongoing activity.
        heartbeat_task = asyncio.create_task(send_heartbeats(websocket, msg_id))
        
        print(f"INFO: Executing command for session {session_id}: {command}")
        
        # Await the main processing task.
        await process_claude_stream(websocket, command, msg_id)

    except asyncio.CancelledError:
        print(f"INFO: Task cancelled for session {session_id}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(mcp_status_update("CANCELLED", msg_id))
        raise
    except Exception as e:
        print(f"ERROR: Execution error for session {session_id}: {type(e).__name__}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(mcp_error(f"Execution error: {str(e)}", msg_id))
            await websocket.send_json(mcp_status_update("FAILED", msg_id))
    finally:
        # CRITICAL: Always cancel the heartbeat task when execution finishes for any reason.
        if heartbeat_task:
            heartbeat_task.cancel()
            print(f"DEBUG: Heartbeat task cancelled for msg_id: {msg_id}.")


async def forward_command_to_claude_stream(command: str):
    """Forwards the command to the /execute/claude-stream endpoint and yields the received JSON events."""
    timeout = httpx.Timeout(10.0, read=None) # Long read timeout, as streams can be slow.
    headers = {"Content-Type": "application/json"}
    payload = {"question": command}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", CLAUDE_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            yield {"type": "text", "text": line}
        except httpx.RequestError as e:
            yield {"type": "error", "error": f"HTTP Request Error: {e}"}
        except Exception as e:
            yield {"type": "error", "error": str(e)}

# --- MCP Protocol Message Helpers ---
def mcp_output_message(content: str, msg_id: Any = None) -> Dict:
    return {"jsonrpc": "2.0", "method": "output", "params": {"type": "stdout", "content": content}, "id": msg_id}

def mcp_status_update(status: str, msg_id: Any = None) -> Dict:
    return {"jsonrpc": "2.0", "method": "statusUpdate", "params": {"status": status}, "id": msg_id}

def mcp_error(error_msg: str, msg_id: Any = None) -> Dict:
    return {"jsonrpc": "2.0", "error": {"code": -32000, "message": error_msg}, "id": msg_id}

def mcp_connected(session_id: str) -> Dict:
    return {"jsonrpc": "2.0", "method": "connected", "params": {"sessionId": session_id}}

@app.websocket("/ws/mcp")
async def mcp_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"websocket": websocket, "task": None}
    await websocket.send_json(mcp_connected(session_id))
    print(f"INFO: Client connected. Session: {session_id}. Total: {len(SESSIONS)}")
    
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            msg_id = req.get("id")

            if req.get("method") == "execute":
                if SESSIONS[session_id].get('task') and not SESSIONS[session_id]['task'].done():
                    await websocket.send_json(mcp_error("A task is already running", msg_id))
                    continue
                
                command = req.get("params", {}).get("command")
                if not command:
                    await websocket.send_json(mcp_error("Missing 'command' parameter", msg_id))
                    continue

                task = asyncio.create_task(handle_execute(websocket, session_id, command, msg_id))
                SESSIONS[session_id]['task'] = task
            else:
                await websocket.send_json(mcp_error("Unknown method", msg_id))

    except (WebSocketDisconnect, ConnectionError):
        print(f"INFO: Client {session_id} disconnected.")
    except Exception as e:
        print(f"ERROR: Unhandled exception in websocket loop for session {session_id}: {e}")
    finally:
        if session_id in SESSIONS:
            task = SESSIONS[session_id].get('task')
            if task and not task.done():
                task.cancel()
                print(f"INFO: Cancelled active task for session {session_id}")
            del SESSIONS[session_id]
            print(f"INFO: Cleaned up session {session_id}. Active sessions: {len(SESSIONS)}")
```

### **2. `docker-simple/prompts/cc_executor_mcp/tests/test_e2e_client.py` (FIXED & COMPLETE)**

```python
#!/usr/bin/env python3
import asyncio
import json
import websockets
import sys

async def run_e2e_test():
    uri = "ws://localhost:8003/ws/mcp"
    print("\n--> Connecting to MCP bridge service...")
    try:
        async with websockets.connect(uri, open_timeout=20) as websocket:
            msg = await websocket.recv()
            data = json.loads(msg)
            assert data['method'] == 'connected', f"Expected 'connected' msg, got {data}"
            print(f"✅ Connected. Session ID: {data['params']['sessionId']}")

            test_command = "result = 24 * 7; print(f'RESULT:::{result}')"
            expected_result = "RESULT:::168"
            
            print(f"--> Sending EXECUTE command: '{test_command}'")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "method": "execute", "params": {"command": test_command}
            }))

            is_completed = False
            final_output = []
            print("<-- Awaiting stream...")
            
            # This loop now waits up to 180s for EACH message (output or heartbeat)
            while not is_completed:
                # FIXED: Increased timeout to 180s to handle long idle periods
                msg = await asyncio.wait_for(websocket.recv(), timeout=180)
                data = json.loads(msg)
                
                if data.get('method') == 'output':
                    content = data['params'].get('content', '')
                    final_output.append(content)
                    print(f" [STREAM] {content.strip()}")
                elif data.get('method') == 'statusUpdate':
                    status = data['params'].get('status')
                    if status == 'COMPLETED':
                        print("\n✅ Received COMPLETED status.")
                        is_completed = True
                    elif status == 'RUNNING':
                        print(" [HEARTBEAT] Received RUNNING status.")

            assert is_completed, "Task never reached a COMPLETED state."
            
            full_output_str = "".join(final_output)
            assert expected_result in full_output_str, \
                f"Expected to find '{expected_result}' in the output. Got: '{full_output_str}'"
            print(f"✅ Found expected result '{expected_result}' in stream.")
            
            print("\n✅✅✅ E2E Test PASSED ✅✅✅")

    except asyncio.TimeoutError:
        print("\n❌ TEST FAILED: Timed out waiting for a message (output or heartbeat).")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e.__class__.__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
```

### **3. `docker-simple/prompts/cc_executor_mcp/tests/mcp_stress_test.py` (FIXED & COMPLETE)**

```python
#!/usr/bin/env python3
"""
MCP WebSocket Stress Test - Validates actual Claude execution through WebSocket bridge
"""
import asyncio
import json
import websockets
import sys
import time

async def run_single_test(test_name: str, command: str, expected_content: str, timeout: int = 180):
    """Run a single test case and verify output"""
    uri = "ws://localhost:8003/ws/mcp"
    
    try:
        async with websockets.connect(uri, open_timeout=20) as websocket:
            msg = await websocket.recv()
            data = json.loads(msg)
            assert data['method'] == 'connected', f"Expected 'connected' msg, got {data}"
            
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "method": "execute", "params": {"command": command}
            }))
            
            is_completed = False
            output_chunks = []
            
            while not is_completed:
                # FIXED: Increased timeout to 180s to handle long idle periods
                msg = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                data = json.loads(msg)
                
                if data.get('method') == 'output':
                    output_chunks.append(data['params'].get('content', ''))
                elif data.get('method') == 'statusUpdate':
                    status = data['params'].get('status')
                    if status == 'COMPLETED':
                        is_completed = True
                    elif status == 'RUNNING':
                        pass # Ignore heartbeats
                    elif status in ['FAILED', 'CANCELLED']:
                        return False, f"Task failed with status: {status}"
            
            full_output = ''.join(output_chunks)
            if expected_content in full_output:
                return True, f"Found expected content"
            else:
                return False, f"Expected content not found. Got: {full_output[:200]}..."
            
    except asyncio.TimeoutError:
        return False, f"Timeout after {timeout}s of inactivity"
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}"

async def run_stress_tests():
    """Run comprehensive stress tests for MCP WebSocket bridge"""
    test_cases = [
        {"name": "Basic Math", "command": "print(42 * 17)", "expected": "714"},
        {"name": "String Reversal", "command": "print('hello'[::-1])", "expected": "olleh"},
        {"name": "JSON Output", "command": "import json; print(json.dumps({'name': 'test'}))", "expected": '"name": "test"'},
        {"name": "Multi-line Output", "command": "for i in range(1, 6): print(i)", "expected": "5"},
        {"name": "Error Handling", "command": "try: raise ValueError('oops')\nexcept ValueError as e: print(e)", "expected": "oops"},
        {"name": "Factorial", "command": "print(f'Result: {5*4*3*2*1}')", "expected": "Result: 120"},
        {"name": "List Ops", "command": "print(sum([1,2,3,4,5]))", "expected": "15"},
        {"name": "Simple Finish", "command": "print('COMPLETE')", "expected": "COMPLETE"}
    ]
    
    print(f"=== MCP WEBSOCKET STRESS TEST: {len(test_cases)} tests ===\n")
    passed, failed = 0, 0
    
    for test in test_cases:
        print(f"Test: {test['name']}")
        print(f"  Command: {test['command'][:50].replace Bipassed}")
        
        success, message = await run_single_test(test['name'], test['command'], test['expected'])
        
        if success:
            print(f"  ✅ PASSED - {message}")
            passed += 1
        else:
            print(f"  ❌ FAILED - {message}")
            failed += 1
        print()
        await asyncio.sleep(1)
    
    print(f"{'='*50}")
    print(f"RESULTS: {passed}/{len(test_cases)} passed, {failed} failed")
    success_rate = (passed / len(test_cases)) * 100
    print(f"Success rate: {success_rate:.0f}%")
    print(f"{'='*50}")

    return passed == len(test_cases)

async def main():
    try:
        success = await run_stress_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ STRESS TEST FAILED: {e.__class__.__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### **4. `docker-simple/prompts/cc_executor_mcp/tests/mcp_concurrent_test.py` (FIXED & COMPLETE)**

```python
#!/usr/bin/env python3
"""
MCP WebSocket Concurrent Connections Test - Validates multiple simultaneous connections
"""
import asyncio
import json
import websockets
import time
import sys

async def execute_command(session_num: int, command: str):
    """Execute a command through WebSocket and return result"""
    uri = "ws://localhost:8003/ws/mcp"
    
    try:
        async with websockets.connect(uri, open_timeout=10) as websocket:
            msg = await websocket.recv()
            data = json.loads(msg)
            session_id = data['params']['sessionId']
            print(f"  Session {session_num}: Connected ({session_id[:8]}...)")
            
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "method": "execute", "params": {"command": command}
            }))
            
            output, completed = [], False
            while not completed:
                # FIXED: Increased timeout to 180s to handle long idle periods
                msg = await asyncio.wait_for(websocket.recv(), timeout=180)
                data = json.loads(msg)
                
                if data.get('method') == 'output':
                    output.append(data['params'].get('content', ''))
                elif data.get('method') == 'statusUpdate':
                    if data['params'].get('status') == 'COMPLETED':
                        completed = True
                    elif data['params'].get('status') == 'RUNNING':
                        pass # Ignore heartbeat
            
            return True, ''.join(output)
            
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

async def test_concurrent_connections():
    """Test multiple concurrent WebSocket connections"""
    print("=== CONCURRENT CONNECTIONS TEST ===\n")
    
    commands = [
        ("print(10 + 20)", "30"),
        ("print(15 * 3)", "45"),
        ("print(100 // 4)", "25"),
        ("print(7 * 8)", "56"),
        ("print(99 - 33)", "66")
    ]
    
    print(f"Starting {len(commands)} concurrent connections...")
    start_time = time.time()
    
    tasks = [execute_command(i + 1, cmd) for i, (cmd, _) in enumerate(commands)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_time
    passed = 0
    for i, result in enumerate(results):
        expected_output = commands[i][1]
        if isinstance(result, tuple) and result[0] and expected_output in result[1]:
            print(f"  Session {i+1}: ✅ Success - found {expected_output}")
            passed += 1
        else:
            print(f"  Session {i+1}: ❌ Failed - {result}")
    
    print(f"\nCompleted in {duration:.1f}s")
    print(f"Results: {passed}/{len(commands)} passed")
    return passed == len(commands)

async def test_rapid_reconnections():
    """Test rapid connect/disconnect cycles"""
    print("\n=== RAPID RECONNECTION TEST ===\n")
    uri = "ws://localhost:8003/ws/mcp"
    successes = 0
    
    for i in range(5):
        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                msg = await ws.recv()
                data = json.loads(msg)
                if data['method'] == 'connected':
                    successes += 1
                    print(f"  Connection {i+1}: ✅ Connected")
                await ws.close()
        except Exception as e:
            print(f"  Connection {i+1}: ❌ Failed - {e}")
        await asyncio.sleep(0.5)
    
    print(f"\nResults: {successes}/5 successful connections")
    return successes == 5

async def main():
    """Run all concurrent tests"""
    concurrent_passed = await test_concurrent_connections()
    reconnect_passed = await test_rapid_reconnections()
    
    print(f"\n{'='*50}")
    print("CONCURRENT TEST SUMMARY:")
    print(f"  Concurrent connections: {'PASS' if concurrent_passed else 'FAIL'}")
    print(f"  Rapid reconnections: {'PASS' if reconnect_passed else 'FAIL'}")
    
    all_passed = concurrent_passed and reconnect_passed
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    print(f"{'='*50}")
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### **5. `docker-simple/prompts/cc_executor_mcp/tests/mcp_hallucination_test.py` (FIXED & COMPLETE)**

```python
#!/usr/bin/env python3
"""
MCP WebSocket Hallucination Test - Validates that outputs are real, not hallucinated
"""
import asyncio
import json
import websockets
import sys
import time
import subprocess
from pathlib import Path

def check_transcript_for_content(content: str) -> bool:
    """Check if content appears in recent transcript entries using ripgrep."""
    home = Path.home()
    projects_dir = home / ".claude/projects"
    if not projects_dir.exists():
        print(f"  ⚠️ Transcript projects directory not found: {projects_dir}")
        return False

    project_dirs = list(projects_dir.glob("*"))
    if not project_dirs:
        print(f"  ⚠️ No project directories found in {projects_dir}")
        return False

    # Check the most recently modified project directory, likely the current one.
    latest_project_dir = max(project_dirs, key=lambda p: p.stat().st_mtime)
    
    try:
        # rg is much faster than grep for this.
        # -q (--quiet) suppresses output and just returns the status code.
        result = subprocess.run(['rg', '-q', content, str(latest_project_dir)], timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        print("  ⚠️ 'rg' (ripgrep) not found. Cannot verify transcript.")
        return False # Cannot verify, treat as failure.
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ Timeout searching transcript for '{content}'")
        return False

async def run_hallucination_test(test_name: str, command: str, expected_content: str):
    """Run a test and verify output is not hallucinated"""
    uri = "ws://localhost:8003/ws/mcp"
    print(f"\n--- Running test: {test_name} ---")
    try:
        async with websockets.connect(uri, open_timeout=20) as websocket:
            await websocket.recv()  # Consume connected message
            
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "method": "execute", "params": {"command": command}
            }))
            
            output_chunks, completed = [], False
            while not completed:
                # FIXED: Increased timeout to 180s to handle long idle periods
                msg = await asyncio.wait_for(websocket.recv(), timeout=180)
                data = json.loads(msg)
                
                if data.get('method') == 'output':
                    output_chunks.append(data['params'].get('content', ''))
                elif data.get('method') == 'statusUpdate':
                    if data['params'].get('status') == 'COMPLETED':
                        completed = True
                    # Ignore heartbeats

            full_output = ''.join(output_chunks)
            output_found = expected_content in full_output
            print(f"  Expected content found in WS output: {'✅ YES' if output_found else '❌ NO'}")

            await asyncio.sleep(2)  # Give transcript time to flush to disk
            
            output_in_transcript = check_transcript_for_content(expected_content)
            print(f"  Expected content found in transcript: {'✅ YES' if output_in_transcript else '❌ NO'}")

            is_hallucination = output_found and not output_in_transcript
            if is_hallucination:
                print(f"  🚨 HALLUCINATION DETECTED!")
                return False
            elif not output_found:
                 print(f"  ❌ FAILED: Expected output not received via WebSocket.")
                 return False
            else:
                print(f"  ✅ VERIFIED: Output is real.")
                return True

    except Exception as e:
        print(f"  ❌ ERROR during test: {type(e).__name__}: {e}")
        return False

async def run_all_hallucination_tests():
    """Run comprehensive hallucination detection tests"""
    test_cases = [
        {"name": "Simple Math Verification", "command": "print(17 * 13)", "expected": "221"},
        {"name": "Code Execution Result", "command": "def fib(n):\n  if n <= 1: return n\n  return fib(n-1) + fib(n-2)\nprint(fib(10))", "expected": "55"},
        {"name": "Error Message Verification", "command": "try:\n  import fakemodule123\nexcept ImportError as e:\n  print(str(e))", "expected": "No module named"},
    ]
    
    print("=== HALLUCINATION DETECTION TEST SUITE ===")
    passed = 0
    for test in test_cases:
        if await run_hallucination_test(test['name'], test['command'], test['expected']):
            passed += 1
        await asyncio.sleep(2)
    
    print("\n" + "="*50)
    print(f"Hallucination Test Summary: {passed}/{len(test_cases)} PASSED")
    print("="*50)
    return passed == len(test_cases)

async def main():
    try:
        success = await run_all_hallucination_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Hallucination test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```