# Comprehensive Troubleshooting Guide for CC Executor

This guide documents common issues, their root causes, and their solutions. It combines debugging techniques, known issues, and practical solutions based on the project's development history.

## Quick Start - VSCode Debugging

The easiest way to debug is using VSCode with the included launch configurations.

### 1. Open in VSCode
```bash
code /home/graham/workspace/experiments/cc_executor
```

### 2. Set Breakpoints
Common breakpoint locations:
- `websocket_handler.py:440` - When output is being sent to client
- `stream_handler.py:92` - When reading lines from process
- `stream_handler.py:171` - When large line is detected
- `process_manager.py:79` - When command is executed

### 3. Start Debugging
1. Press `F5` or click "Run and Debug" in sidebar
2. Select one of these configurations:
   - **Debug WebSocket Handler - Simple Test**: Quick 2+2 test
   - **Debug WebSocket Handler - Medium Test**: JSON output test  
   - **Debug WebSocket Handler - Large Test**: 5000-word story test
   - **Debug WebSocket Handler - Server Only**: Just the server, no client

### 4. Watch the Flow
The debugger will:
1. Start the WebSocket server on port 8004
2. Launch a test client (if using auto-demo)
3. Execute the Claude command
4. Stop at your breakpoints

## Command Line Testing

### Run the Test Server
```bash
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor

# Simple test (completes in seconds)
python core/websocket_handler.py --serve --auto-demo --test-case simple

# Medium test (JSON output)
python core/websocket_handler.py --serve --auto-demo --test-case medium

# Large test (5000-word story, 3-5 minutes)
python core/websocket_handler.py --serve --auto-demo --test-case large

# Server only (connect with your own client)
python core/websocket_handler.py --serve
```

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python core/websocket_handler.py --serve --auto-demo
```

## Common Issues and Solutions

### Problem: Process Hangs for 5 Minutes, Then Times Out

This is the most common and subtle failure mode. The service accepts a command, the `claude` process starts, but no output is ever received. The logs show a `stream_handler` timeout after 300 seconds.

**Root Cause: `stdin` Deadlock**

The `claude` executable, like many command-line tools, checks its standard input (`stdin`) pipe upon starting. If the pipe is open, it will politely wait for it to close before it begins processing. The `asyncio.subprocess.Process` in Python, by default, leaves this pipe open.

This creates a deadlock:
- The **`stream_handler`** is waiting for `claude` to write to `stdout`.
- The **`claude` process** is waiting for the `stream_handler`'s parent process to close the `stdin` pipe.

Neither event ever occurs, and the process hangs silently until a timeout is hit.

**Solution: Explicitly Close `stdin`**

The fix is to explicitly tell the subprocess that no `stdin` will be provided. This is done in `process_manager.py` by adding `stdin=asyncio.subprocess.DEVNULL` to the `create_subprocess_exec` call.

```python
# In process_manager.py
proc = await asyncio.create_subprocess_exec(
    *command_args,
    stdin=asyncio.subprocess.DEVNULL, # This line prevents the deadlock
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    # ...
)
```

### Problem: WebSocket Connection Drops After ~2 Minutes

This was an earlier issue where long-running `claude` commands would work for a while, but the WebSocket connection would suddenly close before the command finished.

**Root Cause: Network Idle Timeouts**

The WebSocket connection was idle from a "read" perspective. While the server was waiting for the `claude` process, no data was being sent *from* the client *to* the server. Many network components (reverse proxies, load balancers, and even the web server itself) have a default idle timeout (often 120 seconds) and will close a connection that has not received any data in that time.

**Solution: Server-Side WebSocket Keep-Alives**

The standard and most efficient way to solve this is to have the server periodically send low-level WebSocket `PING` frames to the client. The client will automatically respond with `PONG` frames. This traffic is invisible to the application but resets all network idle timers.

This is configured in the Uvicorn server settings in `websocket_handler.py`:

```python
# In websocket_handler.py, in the main execution block
config = uvicorn.Config(
    _app,
    # ...
    ws_ping_interval=20,  # Send a PING every 20 seconds
    ws_ping_timeout=20,   # Consider the connection dead if no PONG is received
)
```
With this setting, application-level heartbeats or ping/pong messages are unnecessary.

### Problem: `claude` Command Fails with "Invalid Arguments" (or similar)

The command runs perfectly in the local terminal but fails immediately when run through the WebSocket service. The `stderr` stream may contain a usage or argument error.

**Root Cause: Incorrect Shell-Level Parsing**

This occurs when the command is executed via a shell (`/bin/bash -c "..."`). A new shell does not have the same context as your interactive terminal and will incorrectly parse complex arguments, especially those with nested quotes.

**Solution: Execute Directly, Not Through a Shell**

The command string must be safely split into a list of arguments, and then executed directly. This bypasses any shell interpretation and ensures the process receives the exact same arguments it would from a well-behaved interactive terminal.

This is handled in `process_manager.py`:

```python
# In process_manager.py
import shlex

# 1. Split the command string safely
command_args = shlex.split(command)

# 2. Execute the list of arguments directly
proc = await asyncio.create_subprocess_exec(
    *command_args,
    # ...
)
```

### Problem: No output received
1. Check StreamHandler logs for "Starting stdout streaming"
2. Look for "Read line" debug messages
3. Verify MAX_BUFFER_SIZE is large enough

### Problem: Connection drops at 112 seconds
1. Check Uvicorn ping/pong settings
2. Verify WebSocket keepalive is working
3. Look for proxy timeout issues

### Problem: Large outputs truncated
1. Check for "Line truncated at buffer boundary"
2. Increase MAX_BUFFER_SIZE
3. Look for "Completed reading large line" messages

## Key Log Messages to Watch

### Successful Flow
```
Starting stdout streaming with no timeout, buffer_size=1,048,576
[CLIENT] Connected!
[CLIENT] Running LARGE test - 5000 word story (3-5 minutes)
stdout: Large line #1 - 35,869 bytes
stdout progress: 100 lines, 102,400 bytes in 10.2s (10.0 KB/s)
[LARGE OUTPUT] stdout sending 35,869 chars
stdout completed: 156 lines, 38,203 bytes in 266.1s
[PROCESS COMPLETED] PID: 12345, Exit code: 0, Status: completed
```

### Problem Indicators
```
Line truncated at buffer boundary (1,048,576 bytes)  # Buffer too small
Stream ended while reading large line                # Incomplete data
Error streaming stdout after 10.1s: [error]          # Stream failure
[PROCESS COMPLETED] Exit code: 1, Status: failed    # Command failed
```

## Environment Variables for Debugging

```bash
# Increase verbosity
export LOG_LEVEL=DEBUG

# Increase buffer size for very large outputs
export MAX_BUFFER_SIZE=10485760  # 10MB

# Add timeouts for testing
export STREAM_TIMEOUT=30  # 30 seconds

# Limit sessions for testing
export MAX_SESSIONS=1
```

## Testing Different Scenarios

### 1. Test Buffer Overflow
```python
# In the debug console while paused:
self.max_line_size = 1024  # Temporarily reduce buffer
# Continue execution to see large line handling
```

### 2. Test Timeout Handling
```python
# Set a short timeout while debugging:
timeout = 5  # Force timeout after 5 seconds
```

### 3. Test Connection Loss
- Start the large test
- After ~1 minute, kill the client process
- Watch cleanup in server logs

## Debugging Tips

1. **Use gnomon for timing**: 
   ```bash
   claude -p "your prompt" | gnomon
   ```
   Shows timestamp for each output line

2. **Check transcripts**:
   ```bash
   rg "YOUR_MARKER" ~/.claude/projects/-*/*.jsonl
   ```

3. **Monitor process**:
   ```bash
   ps aux | grep claude
   ```

4. **Watch WebSocket traffic**:
   Use browser DevTools or `websocat` to monitor raw WebSocket messages

## Additional Resources

- See `guides/vscode_debugging.md` for advanced VSCode debugging techniques
- See `technical/asyncio_timeout_guide.md` for timeout handling details
- See `technical/environment_variables.md` for all configuration options
- See `hooks/README.md` for debugging hook-based integrations

Last updated: 2025-07-02