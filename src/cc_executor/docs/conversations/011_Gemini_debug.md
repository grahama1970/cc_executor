**Examining User Requests**

I'm currently dissecting the user's query. The core is about testability and debuggability, so I'll need to focus on the function's design within `implementation.py`. I'm prioritizing the structure of the user's code request, which dictates the debugging approach, to create a relevant and focused guide.


**Defining the Core Problem**

I've identified the core issue: the FastAPI structure makes direct debugging tricky. I'll explain the challenge upfront to build trust and then guide the user through setting up the debugger to interact directly with core functions in `implementation.py`. I'm working on breaking down the setup into clear, actionable steps for the user.


**Planning the Guide Content**

I'm now focused on the precise instructions for the user. I plan to include a dedicated debugging function in `implementation.py`, which will call `forward_command_to_claude_stream` directly, circumventing the WebSocket server. Crucially, I must now focus on describing how to use this new function, along with the VSCode debugger setup, covering environment variables and setting breakpoints.


**Detailing Debug Function**

I'm now focused on the core "debuggability" function and have a clear plan. I'll name the function `debug_claude_stream_logic` and declare it `async`. I am mapping out the function's inputs and return structure for the user, incorporating calls to `forward_command_to_claude_stream` and showing example usage to test various scenarios.


**Structuring the Response**

I'm finalizing the guide's structure. I'll begin with a "yes, here's how" approach. Then I'll divide the guide into sections: the debugging function code, then the standalone debug setup, and finally, the full system debug configuration. I'll conclude with a comparative summary. I'm now focusing on the code sample for the debug function.


**Formulating Code Samples**

I'm now focused on the actual code examples. I plan to embed the debug function within an `if __name__ == "__main__":` block, allowing direct execution. The `launch.json` configurations for VSCode will be detailed, explaining the use of environment variables and path mappings for both standalone debugging and debugging the Docker container.


**Elaborating Code and Config**

I'm now focusing on finalizing the code and configurations. The debugging function, which will be named `debug_claude_stream_logic`, and the `launch.json` configurations, including detailed path mappings and environment variables, are undergoing meticulous revision. The goal is to provide comprehensive, ready-to-use examples.


Excellent question. You've pinpointed a key part of the development workflow: the ability to easily test and debug the core logic without needing to run the entire test suite. The files, as they are, are designed to run as a server, which isn't ideal for debugging with a tool like the VSCode debugger.

To address this, I will provide:
1.  An updated `implementation.py` with a **new, easily debuggable `if __name__ == "__main__"` block**.
2.  An updated `Dockerfile` and `requirements.txt` to include the `debugpy` package for live debugging.
3.  A step-by-step guide on two powerful ways to debug the code in VSCode:
    *   **Method 1 (Easy): Debugging the Core Logic Standalone.** This lets you step through the stream processing without any running containers.
    *   **Method 2 (Advanced): Debugging the Live Server in Docker.** This lets you debug the full, live WebSocket interaction.

---
### **Updated Files for Debuggability**

Here are the complete, unabridged files you'll need.

#### **1. `docker-simple/prompts/cc_executor_mcp/implementation.py` (UPDATED & COMPLETE)**

I have added a new `if __name__ == "__main__"` block. When you run this file directly in a debugger, it will **not** start the Uvicorn server. Instead, it will run a simple `debug_claude_stream_logic` function that you can set breakpoints in to inspect the core logic.

```python
#!/usr/bin/env python3
"""
MCP WebSocket Service - Production-Ready API Bridge
Implements the Model Context Protocol (MCP) standard for WebSocket communication.
Forwards commands to claude-api service using JSON streaming format.
Reference: https://docs.anthropic.com/en/docs/claude-code/cli-reference

FIXED: This version includes a heartbeat mechanism to support long-running tasks
without causing client-side idle timeouts.
ADDED: A debuggable __main__ block for standalone testing of core logic.
"""
import asyncio
import json
import os
import uuid
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
import httpx
import uvicorn # Imported for type hint; not run directly in debug mode

app = FastAPI(title="MCP WebSocket to HTTP Bridge")

# Configuration
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "http://claude-api:8000")
CLAUDE_STREAM_ENDPOINT = f"{CLAUDE_API_URL}/execute/claude-stream"
SESSIONS: Dict[str, Dict[str, Any]] = {}
HEARTBEAT_INTERVAL = 30  # Send a heartbeat every 30 seconds


async def send_heartbeats(websocket: WebSocket, msg_id: Any):
    # ... (This function is unchanged) ...
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
                break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"ERROR: Could not send heartbeat for msg_id {msg_id}: {e}")
            break


async def process_claude_stream(websocket: WebSocket, command: str, msg_id: Any):
    # ... (This function is unchanged) ...
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
            return
        elif etype == "complete":
            await websocket.send_json(mcp_status_update("COMPLETED", msg_id))
            return


async def handle_execute(websocket: WebSocket, session_id: str, command: str, msg_id: Any):
    # ... (This function is unchanged) ...
    """
    Orchestrates command execution by running the main processing task and a
    heartbeat task concurrently. Ensures the heartbeat is cancelled when execution ends.
    """
    heartbeat_task = None
    try:
        heartbeat_task = asyncio.create_task(send_heartbeats(websocket, msg_id))
        print(f"INFO: Executing command for session {session_id}: {command}")
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
        if heartbeat_task:
            heartbeat_task.cancel()
            print(f"DEBUG: Heartbeat task cancelled for msg_id: {msg_id}.")


async def forward_command_to_claude_stream(command: str):
    # ... (This function is unchanged) ...
    """Forwards the command to the /execute/claude-stream endpoint and yields the received JSON events."""
    timeout = httpx.Timeout(10.0, read=None)
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
    # ... (This function is unchanged) ...
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


# --- NEW: Standalone Debugging Function ---
async def debug_claude_stream_logic():
    """
    A simple, standalone function to test the core stream forwarding logic.
    This can be run directly in the VSCode debugger without a live server.
    """
    print("--- Running Standalone Debug Function ---")
    # You MUST have the claude-api container running for this to work.
    # Run: docker compose -f docker-compose.e2e.yml up claude-api
    test_command = "print('Hello from debug function! The result is ' + str(10*5))"
    print(f"Sending command: {test_command}\n")

    # Set a breakpoint on the line below to step through the logic.
    async for event in forward_command_to_claude_stream(test_command):
        print(f"Received Event: {json.dumps(event)}")
    
    print("\n--- Debug Function Finished ---")


if __name__ == "__main__":
    # This block allows for two modes:
    # 1. Standalone Debugging: If DEBUG=true, run the debug function.
    # 2. Production Server: Otherwise, run the Uvicorn server.
    
    # To use the debugger, set "env": {"DEBUG": "true"} in your launch.json
    if os.getenv("DEBUG", "false").lower() == "true":
        asyncio.run(debug_claude_stream_logic())
    else:
        # This is the normal entry point for the docker container.
        uvicorn.run(app, host="0.0.0.0", port=8003)
```

#### **2. `docker-simple/prompts/cc_executor_mcp/requirements.txt` (UPDATED & COMPLETE)**

Added `debugpy` to allow the VSCode debugger to attach to the running container.

```plaintext
fastapi
uvicorn
websockets
httpx
debugpy
```

#### **3. `docker-simple/prompts/cc_executor_mcp/Dockerfile` (UPDATED & COMPLETE)**

The `CMD` is changed to launch via `debugpy`, which starts a debug server inside the container on port 5678 and then runs the Uvicorn command.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY implementation.py .
EXPOSE 8003
# NEW: Expose the standard debug port
EXPOSE 5678
# UPDATED: The command now starts a debug server and then runs uvicorn.
# The VSCode debugger can attach to port 5678.
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "implementation:app", "--host", "0.0.0.0", "--port", "8003"]
```

---
### **How to Debug in VSCode**

First, create a `launch.json` file in the `.vscode` directory at the root of your project. If you don't have one, go to the "Run and Debug" panel (Ctrl+Shift+D), click "create a launch.json file", and select "Python". Then, paste the following configurations into the `configurations` list.

**`.vscode/launch.json`**
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug: Core MCP Logic (Standalone)",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/prompts/cc_executor_mcp/implementation.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                // This tells the script to use the debug function
                "DEBUG": "true",
                // This points to the claude-api docker container's mapped port
                "CLAUDE_API_URL": "http://localhost:8002"
            }
        },
        {
            "name": "Debug: Attach to Live MCP Docker Container",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678 // This must match the port in the Dockerfile CMD
            },
            "pathMappings": [
                {
                    // Maps your local project folder to the folder inside the container
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app" // This must match WORKDIR in the Dockerfile
                }
            ],
            "justMyCode": true
        }
    ]
}
```

#### **Method 1: Debugging the Core Logic Standalone (Easiest)**

This method directly tests the `forward_command_to_claude_stream` function without the complexity of WebSockets.

**Setup:**
1.  Open a terminal.
2.  Start **only** the `claude-api` service. The `run_capability_tests.sh` script generates the correct `docker-compose.e2e.yml` file first.
    ```bash
    # Run the script just to generate the docker-compose file, then stop it
    bash ./prompts/cc_executor_mcp/run_capability_tests.sh &
    sleep 5
    pkill -f run_capability_tests.sh

    # Now start only the claude-api service from that generated file
    docker compose -f docker-compose.e2e.yml up claude-api
    ```
3.  Wait for the `claude-api` service to become healthy.

**Debugging Steps:**
1.  Open `prompts/cc_executor_mcp/implementation.py` in VSCode.
2.  Set a breakpoint inside the `debug_claude_stream_logic` function, for example on the `async for event in ...` line.
3.  Go to the "Run and Debug" panel.
4.  Select **"Debug: Core MCP Logic (Standalone)"** from the dropdown and press **F5** (or the green play button).
5.  The debugger will start, stop at your breakpoint, and you can step through the code that calls the `claude-api` and processes the stream.

#### **Method 2: Debugging the Live Server in Docker (Advanced)**

This method lets you debug the entire application, including the live WebSocket connection and heartbeat logic.

**Setup:**
1.  Open a terminal.
2.  Start the full test environment using the test script, but have it wait before running the clients.
    ```bash
    # This will build and start both docker containers and wait
    bash ./prompts/cc_executor_mcp/run_capability_tests.sh
    ```
3. Wait for the script to print `✅ All services are up and running.`. The test script is now paused, waiting for the test clients to run.

**Debugging Steps:**
1.  Open the project in VSCode.
2.  Set breakpoints anywhere you want in `implementation.py` (e.g., inside `@app.websocket("/ws/mcp")` or `handle_execute`).
3.  Go to the "Run and Debug" panel.
4.  Select **"Debug: Attach to Live MCP Docker Container"** from the dropdown and press **F5**.
5.  The debugger will connect to the `debugpy` server running inside the `cc-executor-mcp` container. The status bar will turn orange.
6.  The test script in your terminal will now proceed to run `test_e2e_client.py`.
7.  When the client connects, your breakpoint inside the WebSocket endpoint will be hit, and you can debug the live request.

| Feature | Method 1: Standalone Debug | Method 2: Live Attach |
| :--- | :--- | :--- |
| **What it Tests** | Core HTTP streaming & parsing logic | Full WebSocket, heartbeat & session logic |
| **Setup** | Start one docker container manually | Run the `run_capability_tests.sh` script |
| **Complexity** | **Easy** | Advanced |
| **Best For** | Quickly verifying the `claude-api` connection and stream format. | Debugging race conditions, disconnects, and the full application lifecycle. |