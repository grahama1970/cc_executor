# Debugging Guide for CC Executor

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

## Common Issues and Solutions

### Issue: No output received
1. Check StreamHandler logs for "Starting stdout streaming"
2. Look for "Read line" debug messages
3. Verify MAX_BUFFER_SIZE is large enough

### Issue: Connection drops at 112 seconds
1. Check Uvicorn ping/pong settings
2. Verify WebSocket keepalive is working
3. Look for proxy timeout issues

### Issue: Large outputs truncated
1. Check for "Line truncated at buffer boundary"
2. Increase MAX_BUFFER_SIZE
3. Look for "Completed reading large line" messages

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