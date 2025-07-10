# WebSocket Test Fixes for CC Executor

## Issues Identified

### 1. Module Import Conflicts
**Problem**: The comprehensive test imports `cc_executor` modules which conflicts with the running server.

**Solution**: Remove all imports of `cc_executor` modules. Use direct WebSocket connections instead:
```python
# Don't do this:
from cc_executor.client.cc_execute import cc_execute

# Do this instead:
import websockets
async with websockets.connect(uri) as websocket:
    # Direct WebSocket communication
```

### 2. Docker Authentication (403 Forbidden)
**Problem**: Docker container returns 403 because it requires authentication headers.

**Solution**: Add proper authentication headers when connecting:
```python
auth_token = os.environ.get('CC_EXECUTOR_AUTH_TOKEN', 'default-token')
headers = {
    "Authorization": f"Bearer {auth_token}",
    "X-API-Key": auth_token  # Some implementations check both
}
async with websockets.connect(uri, extra_headers=headers) as websocket:
    # Authenticated connection
```

### 3. Incorrect Message Format
**Problem**: Tests were sending custom format instead of JSON-RPC.

**Solution**: Use proper JSON-RPC 2.0 format:
```python
# Correct format:
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "execute",
    "params": {
        "command": "echo 'Hello'",
        "timeout": 30
    }
}
```

### 4. MCP Server Not Running
**Problem**: Tests assume servers are running but they may not be.

**Solution**: Check and start servers as needed:
```python
# Check if port is in use
result = subprocess.run(['lsof', '-ti:8003'], capture_output=True)
if not result.stdout.strip():
    # Start server
    subprocess.Popen([
        sys.executable, '-m', 'uvicorn',
        'cc_executor.core.main:app',
        '--port', '8003'
    ])
```

## Fixed Test Structure

### 1. No CC Executor Imports
The fixed tests use only standard libraries and websockets:
```python
import asyncio
import json
import websockets
import uuid
import sys
import os
```

### 2. Proper WebSocket Communication
```python
# Connect
async with websockets.connect(uri, ping_interval=None) as websocket:
    # Wait for connection message
    msg = await websocket.recv()
    data = json.loads(msg)
    session_id = data["params"]["session_id"]
    
    # Send JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "execute",
        "params": {"command": "...", "timeout": 30}
    }
    await websocket.send(json.dumps(request))
    
    # Handle responses
    while True:
        msg = await websocket.recv()
        data = json.loads(msg)
        # Process based on message type
```

### 3. Authentication for Docker
```python
# For Docker connections
auth_token = os.environ.get('CC_EXECUTOR_AUTH_TOKEN', 'test-token')
headers = {"Authorization": f"Bearer {auth_token}"}
async with websockets.connect(uri, extra_headers=headers) as websocket:
    # Authenticated connection
```

## Running the Fixed Tests

### 1. Start Local MCP Server
```bash
python -m uvicorn cc_executor.core.main:app --port 8003
```

### 2. Start Docker Container (with auth)
```bash
docker run -p 8004:8003 \
  -e AUTH_TOKEN=your-secret-token \
  cc-executor:latest
```

### 3. Set Environment Variable
```bash
export CC_EXECUTOR_AUTH_TOKEN=your-secret-token
```

### 4. Run Tests
```bash
python tests/stress/test_websocket_final.py
```

## Test Files Created

1. **`test_websocket_simple.py`** - Basic connection test
2. **`test_websocket_jsonrpc.py`** - JSON-RPC format test
3. **`test_websocket_final.py`** - Complete test suite with all fixes
4. **`comprehensive_test_fixed.py`** - Fixed comprehensive test

## Key Differences from Original

1. **No imports** of `cc_executor` modules
2. **Authentication headers** for Docker
3. **JSON-RPC format** for all messages
4. **Server startup checks** before testing
5. **Proper error handling** for connection issues

## Expected Output

When everything is working correctly:
```
🚀 CC Executor WebSocket Test Suite
============================================================

🏠 Testing Local MCP Server (port 8003)...
  ✅ Connected to ws://localhost:8003/ws/mcp
  📋 Session ID: abc123...
  ✅ Local MCP echo test: Test from MCP local

🐳 Testing Docker MCP Server (port 8004)...
  ✅ Connected to ws://localhost:8004/ws/mcp (with auth)
  📋 Session ID: def456...
  ✅ Docker MCP echo test: Test from Docker MCP

📊 Report saved to: tests/stress_test_results/websocket_test_20250709_144800.md

============================================================
Summary: 2/2 tests passed
```