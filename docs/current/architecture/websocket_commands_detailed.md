# WebSocket MCP Commands - Detailed Reference

## Overview

The CC-Executor MCP (Model Context Protocol) server provides a WebSocket interface that enables real-time bidirectional communication between clients and the server. This document provides detailed explanations of each available command, how they work internally, and their relationship with the MCP server architecture.

## Architecture Overview

```
┌─────────────┐         WebSocket          ┌─────────────────┐
│   Client    │◄──────────────────────────►│   MCP Server    │
│ (Stress Test│      JSON-RPC 2.0          │                 │
│  or Other)  │                            │ ┌─────────────┐ │
└─────────────┘                            │ │WebSocket    │ │
                                          │ │Handler      │ │
                                          │ └─────┬───────┘ │
                                          │       │         │
                                          │ ┌─────▼───────┐ │
                                          │ │Session      │ │
                                          │ │Manager      │ │
                                          │ └─────┬───────┘ │
                                          │       │         │
                                          │ ┌─────▼───────┐ │
                                          │ │Process      │ │
                                          │ │Manager      │ │
                                          │ └─────┬───────┘ │
                                          └───────┼─────────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  OS Process   │
                                          │(Claude, bash) │
                                          └───────────────┘
```

## Client-to-Server Commands

### 1. `execute` Command

**Purpose**: Start a new process execution on the server.

**How it works**:
1. Client sends execute request with a command string
2. WebSocket handler validates the command against allowed list
3. Session manager checks if a process is already running
4. Process manager spawns the command using `asyncio.create_subprocess_exec`
5. Stream handler begins monitoring stdout/stderr
6. Server responds with process ID and group ID

**Detailed Flow**:
```python
# Client sends:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "execute",
  "params": {
    "command": "claude --print 'Write a haiku'"
  }
}

# Server internal processing:
1. WebSocketHandler._handle_execute() receives request
2. Validates command: validate_command(command, ALLOWED_COMMANDS)
3. Checks session state: no existing process running
4. ProcessManager.execute_command() called:
   - Creates process with os.setsid() for group control
   - Captures stdout/stderr pipes
5. StreamHandler.multiplex_streams() starts:
   - Monitors both stdout and stderr asynchronously
   - Sends each line as process.output notification
6. Returns process info to client

# Server responds:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "started",
    "pid": 12345,      # Process ID
    "pgid": 12345      # Process Group ID (for control)
  }
}
```

**Key Features**:
- **Command Validation**: Only whitelisted commands can execute
- **Process Isolation**: Each command runs in its own process group
- **Async Execution**: Non-blocking process management
- **Stream Capture**: Both stdout and stderr are captured

**Error Cases**:
- Command not in allowed list → Error -32002
- Process already running → Error -32602
- Command execution fails → Error -32603

### 2. `control` Command

**Purpose**: Control a running process (pause, resume, or cancel).

**How it works**:
1. Client sends control request with action type
2. Server validates that a process is running
3. Process manager sends appropriate signal to process group
4. Server confirms action completion

**Detailed Flow for Each Control Type**:

#### PAUSE
```python
# Client sends:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "control",
  "params": {"type": "PAUSE"}
}

# Server processing:
1. Retrieves process group ID from session
2. Sends SIGSTOP to entire process group:
   os.killpg(pgid, signal.SIGSTOP)
3. Process and all children are suspended
4. Streaming continues but no new output

# Server responds:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {"status": "paused"}
}
```

#### RESUME
```python
# Client sends:
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "control",
  "params": {"type": "RESUME"}
}

# Server processing:
1. Sends SIGCONT to process group:
   os.killpg(pgid, signal.SIGCONT)
2. Process and children resume execution
3. Output streaming resumes

# Server responds:
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {"status": "resumed"}
}
```

#### CANCEL
```python
# Client sends:
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "control",
  "params": {"type": "CANCEL"}
}

# Server processing:
1. Sends SIGTERM for graceful shutdown:
   os.killpg(pgid, signal.SIGTERM)
2. Starts 10-second timer
3. If process still alive after 10s:
   os.killpg(pgid, signal.SIGKILL)
4. Cleans up resources

# Server responds:
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {"status": "cancelled"}
}
```

**Why Process Groups?**
- Controls parent and all child processes
- Prevents orphaned processes
- Essential for complex commands that spawn subprocesses

## Server-to-Client Notifications

### 1. `connected` Notification

**When sent**: Immediately upon WebSocket connection establishment

**Purpose**: Confirms connection and provides session identifier

```json
{
  "method": "connected",
  "params": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": "1.0.0"
  }
}
```

**Internal Implementation**:
```python
async def handle_websocket(websocket, path):
    session_id = str(uuid.uuid4())
    await sessions.create_session(session_id, websocket)
    
    # Send immediate connection notification
    await websocket.send(json.dumps({
        "method": "connected",
        "params": {
            "session_id": session_id,
            "version": SERVICE_VERSION
        }
    }))
```

### 2. `process.started` Notification

**When sent**: After process successfully spawns

**Purpose**: Confirms process is running with PID info

```json
{
  "method": "process.started",
  "params": {
    "status": "started",
    "pid": 12345,
    "pgid": 12345,
    "exit_code": null,
    "error": null
  }
}
```

### 3. `process.output` Notification

**When sent**: Continuously as process generates output

**Purpose**: Stream real-time output to client

```json
{
  "method": "process.output",
  "params": {
    "type": "stdout",    # or "stderr"
    "data": "Hello, world!\n",
    "truncated": false   # true if line > MAX_BUFFER_SIZE
  }
}
```

**Stream Handling Details**:
```python
async def multiplex_streams(stdout, stderr, callback):
    """Read from both streams concurrently"""
    
    async def read_stream(stream, stream_type):
        while True:
            line = await stream.readline()
            if not line:
                break
                
            # Decode and check size
            text = line.decode('utf-8', errors='replace')
            if len(text) > MAX_BUFFER_SIZE:
                text = text[:MAX_BUFFER_SIZE] + "...\n"
                truncated = True
            else:
                truncated = False
                
            # Send to callback for WebSocket transmission
            await callback(stream_type, text, truncated)
    
    # Run both stream readers concurrently
    await asyncio.gather(
        read_stream(stdout, "stdout"),
        read_stream(stderr, "stderr")
    )
```

### 4. `process.completed` Notification

**When sent**: When process terminates (naturally or killed)

**Purpose**: Indicate final process state

```json
{
  "method": "process.completed",
  "params": {
    "status": "completed",  # or "failed" if non-zero exit
    "pid": 12345,
    "pgid": 12345,
    "exit_code": 0,        # Actual process exit code
    "error": null
  }
}
```

**Exit Code Meanings**:
- `0`: Successful completion
- `1-255`: Process-specific error codes
- `-1`: Killed by SIGHUP
- `-2`: Killed by SIGINT
- `-15`: Killed by SIGTERM
- `-9`: Killed by SIGKILL

### 5. Control Status Notifications

**When sent**: After successful control operations

**Types**:
- `process.paused`
- `process.resumed`
- `process.cancelled`

```json
{
  "method": "process.paused",
  "params": {
    "status": "paused",
    "pid": 12345,
    "pgid": 12345,
    "exit_code": null,
    "error": null
  }
}
```

## MCP Server Integration

### How Commands Flow Through the MCP Server

1. **WebSocket Layer** (`websocket_handler.py`)
   - Handles connection lifecycle
   - Routes JSON-RPC messages to appropriate handlers
   - Manages bidirectional communication

2. **Session Layer** (`session_manager.py`)
   - Tracks WebSocket ↔ Process associations
   - Enforces one-process-per-session rule
   - Handles cleanup on disconnection

3. **Process Layer** (`process_manager.py`)
   - Spawns actual OS processes
   - Manages process groups for control
   - Handles signal delivery

4. **Stream Layer** (`stream_handler.py`)
   - Multiplexes stdout/stderr
   - Handles line buffering
   - Manages backpressure

### Real-World Example: Claude Execution

```python
# Complete flow for executing Claude
async def execute_claude_with_mcp():
    # 1. Connect to MCP server
    websocket = await websockets.connect("ws://localhost:8003/ws/mcp")
    
    # 2. Receive connection confirmation
    connected = json.loads(await websocket.recv())
    session_id = connected['params']['session_id']
    
    # 3. Execute Claude command
    await websocket.send(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "execute",
        "params": {
            "command": "bash -c 'PATH=/path/to/claude:$PATH claude --print \"Write a haiku\"'"
        }
    }))
    
    # 4. Process messages
    while True:
        msg = json.loads(await websocket.recv())
        
        if msg.get('id') == 1:  # Execute response
            print(f"Process started: PID {msg['result']['pid']}")
            
        elif msg.get('method') == 'process.started':
            print("Claude is initializing...")
            
        elif msg.get('method') == 'process.output':
            # Stream Claude's output in real-time
            print(msg['params']['data'], end='', flush=True)
            
        elif msg.get('method') == 'process.completed':
            exit_code = msg['params']['exit_code']
            status = "success" if exit_code == 0 else "failed"
            print(f"\nClaude {status} with exit code {exit_code}")
            break
```

### Advanced: Handling Claude's Stream-JSON Format

When using `claude --output-format stream-json`, the MCP server perfectly handles the JSONL output:

```python
# Each line from Claude becomes a separate process.output notification
{
  "method": "process.output",
  "params": {
    "type": "stdout",
    "data": "{\"type\":\"system\",\"subtype\":\"init\",...}\n"
  }
}

# Client can parse each line as JSON
if msg.get('method') == 'process.output':
    line = msg['params']['data'].strip()
    if line:
        claude_event = json.loads(line)
        if claude_event['type'] == 'assistant':
            # Handle Claude's response
            pass
```

## Security Considerations

### Command Whitelisting

The MCP server enforces command whitelisting through environment variables:

```python
# In docker-compose.yml
environment:
  - ALLOWED_COMMANDS=bash,claude,python,node,npm,git,ls,cat,echo,pwd

# Validation in websocket_handler.py
def validate_command(command, allowed_commands):
    if not allowed_commands:
        return True  # No restrictions
        
    cmd_parts = command.strip().split()
    base_command = cmd_parts[0]
    
    for allowed in allowed_commands:
        if base_command == allowed:
            return True
            
    return False
```

### Session Isolation

Each WebSocket connection gets its own session:
- Can only control its own processes
- Cannot see or affect other sessions
- Automatic cleanup on disconnect

### Process Group Isolation

Using `os.setsid()` creates new process groups:
- Signals don't affect the MCP server
- Child processes are properly controlled
- Clean termination of process trees

## Performance Characteristics

### Streaming Performance
- **Line buffering**: Output sent line-by-line
- **Max line size**: 8192 bytes (configurable)
- **Backpressure handling**: Automatic flow control
- **Typical latency**: <10ms from process output to WebSocket

### Scalability
- **Max sessions**: 100 concurrent (configurable)
- **Process overhead**: ~10MB per session
- **WebSocket overhead**: ~100KB per connection
- **CPU usage**: Minimal when idle, scales with output volume

## Common Patterns

### Pattern 1: Execute with Timeout
```python
async def execute_with_timeout(cmd, timeout_sec=300):
    # Execute command
    await send_execute(cmd)
    
    # Set deadline
    deadline = time.time() + timeout_sec
    
    while time.time() < deadline:
        msg = await recv_with_timeout(1.0)
        
        if is_completed(msg):
            return get_output()
    
    # Timeout - cancel process
    await send_control("CANCEL")
```

### Pattern 2: Progress Monitoring
```python
async def monitor_progress():
    last_output = time.time()
    
    while True:
        msg = await recv()
        
        if is_output(msg):
            last_output = time.time()
            show_progress()
            
        elif time.time() - last_output > 120:
            print("Warning: No output for 2 minutes")
            await check_if_should_cancel()
```

### Pattern 3: Resilient Execution
```python
async def resilient_execute(cmd, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await execute_with_monitoring(cmd)
        except WebSocketError:
            if attempt < max_retries - 1:
                await reconnect()
            else:
                raise
```

## Conclusion

The WebSocket MCP protocol provides a complete solution for real-time process execution and control. Its bidirectional nature enables sophisticated orchestration scenarios while maintaining simplicity and security. The combination of JSON-RPC 2.0 standards and WebSocket transport creates a robust foundation for building command execution services.