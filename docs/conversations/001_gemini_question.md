# Gemini: Help Debug MCP Local Server Startup Failure

## Context
I have a CC Executor MCP WebSocket server that works perfectly in Docker but fails to start locally. The stress test results show:
- MCP Local: 0% success rate (exit code -1 on all tests)
- Docker: 100% success rate
- Python API: 100% success rate

## Current Situation

### What Works
1. Docker deployment on port 8004: 100% success
2. Python API direct calls: 100% success
3. Port 8003 is free and available

### What Fails
MCP Local WebSocket server fails to start with these symptoms:
- All connection attempts return exit code -1
- No process is running on port 8003
- The server seems to crash immediately on startup

## Code Structure

### 1. Main Server Entry Point (`/src/cc_executor/core/main.py`)
```python
if __name__ == "__main__":
    # Check if being run with --server flag to start actual server
    if len(sys.argv) > 1 and "--server" in sys.argv:
        main()
    else:
        # Runs usage function instead of server
```

This has a usage function that runs by default unless `--server` flag is provided.

### 2. Server Runner Wrapper (`/src/cc_executor/core/server_runner.py`)
```python
#!/usr/bin/env python3
import uvicorn
from main import app
from config import DEFAULT_PORT, SERVICE_NAME, SERVICE_VERSION

def run_server(port=DEFAULT_PORT, host="0.0.0.0"):
    """Run the server directly."""
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION} on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,
        ws_ping_interval=float(os.environ.get("WS_PING_INTERVAL", "20.0")),
        ws_ping_timeout=float(os.environ.get("WS_PING_TIMEOUT", "30.0")),
        ws_max_size=int(os.environ.get("WS_MAX_SIZE", str(10 * 1024 * 1024)))
    )
```

### 3. CLI Start Command (`/src/cc_executor/cli/main.py`)
```python
# Build command - use server_runner to avoid usage function
cmd = [
    sys.executable,
    str(Path(__file__).parent.parent / "core" / "server_runner.py"),
    "--port", str(actual_port),
    "--host", host
]

process = subprocess.Popen(
    cmd,
    env=env,
    stdout=subprocess.PIPE if not debug else None,
    stderr=subprocess.PIPE if not debug else None,
    start_new_session=True
)
```

### 4. Docker Deployment (Working)
```dockerfile
# Uses Python 3.11.13
CMD ["python", "-m", "uvicorn", "cc_executor.core.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

## Specific Questions for Gemini

### Question 1: Import and Module Issues
The server seems to crash immediately. When running `python -m cc_executor.core.main`, I get:
```
RuntimeWarning: 'cc_executor.core.main' found in sys.modules after import of package 'cc_executor.core', but prior to execution of 'cc_executor.core.main'; this may result in unpredictable behaviour
```

Could this be causing the immediate crash? How should I restructure the imports to avoid this?

### Question 2: Process Management
The server starts but immediately dies. The subprocess.Popen command returns a PID, but the process is gone when checked moments later. What are common reasons for Python asyncio/FastAPI servers to die immediately after startup?

### Question 3: Server Runner Architecture
I created `server_runner.py` to bypass the usage function in `main.py`. Is this approach problematic? Should I instead:
a) Modify main.py to not have a usage function
b) Use a different entry point
c) Start uvicorn differently

### Question 4: Environment Differences
Docker works perfectly with:
```bash
python -m uvicorn cc_executor.core.main:app --host 0.0.0.0 --port 8003
```

But locally, the same command (with --server flag) fails. What environment differences between Docker and local could cause this?

### Question 5: Debugging Strategy
Given that:
- The server starts (gets PID) but dies immediately
- No error output is captured
- Docker version works perfectly

What's the best debugging strategy? Should I:
1. Add more logging to server_runner.py?
2. Run the server in foreground to see errors?
3. Use strace/ltrace to see system calls?
4. Check for missing dependencies?

## Code Examples

### Stress Test WebSocket Connection (Failing)
```python
async def test_websocket(command, expected_substring, timeout=10):
    try:
        async with websockets.connect("ws://localhost:8003/ws/mcp") as websocket:
            request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": 1
            }
            await websocket.send(json.dumps(request))
            # Connection fails here with exit code -1
```

### Docker WebSocket Connection (Working)
```python
# Same code but connects to ws://localhost:8004/ws/mcp
# Works perfectly with 100% success rate
```

## Request for Gemini

Please analyze this situation and provide:
1. The most likely cause of the local server startup failure
2. A step-by-step debugging approach
3. Code fixes for the import/module warning
4. Best practices for MCP server architecture
5. Any specific asyncio/FastAPI/uvicorn gotchas that could cause immediate crashes

The goal is to have both local and Docker deployments working with 100% success rate.