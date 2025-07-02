# WebSocket Handler Enhancements

## Overview

This document describes the enhancements made to the WebSocket handler to address timeout issues with long-running Claude prompts.

## Problem Statement

The original WebSocket handler would timeout when Claude took a long time to "think" before producing output. This was particularly problematic for:
- Complex prompts requiring deep reasoning
- Long-form content generation (e.g., 5000-word stories)
- Tasks where Claude needs to plan before outputting

## Solution: Enhanced WebSocket Handler

### 1. Heartbeat Mechanism

The enhanced handler sends periodic heartbeat messages to keep the connection alive:

```python
# Heartbeat sent every 20 seconds (configurable)
{
    "jsonrpc": "2.0",
    "method": "heartbeat",
    "params": {
        "timestamp": 1234567890.123,
        "session_id": "uuid-here",
        "status": "alive"
    }
}
```

### 2. Activity Monitoring

When a process goes 30+ seconds without output, the handler sends status updates:

```python
{
    "jsonrpc": "2.0",
    "method": "process.status",
    "params": {
        "status": "running",
        "pid": 12345,
        "pgid": 12345,
        "inactive_seconds": 45,
        "message": "Process is thinking... (no output yet)"
    }
}
```

### 3. Enhanced Process Unbuffering

The process manager now applies `stdbuf -o0 -e0` to various CLI tools:
- `claude` - Claude CLI
- `python` - Python scripts
- `node`, `npm`, `npx` - Node.js tools

This ensures output is sent immediately without buffering.

### 4. No Timeout on Stream Processing

The enhanced handler removes timeouts on the streaming process, allowing Claude to think as long as needed:

```python
# Original: timeout=300 (5 minutes)
# Enhanced: timeout=None (no timeout)
await self.streamer.multiplex_streams(
    process.stdout,
    process.stderr,
    send_output_with_activity,
    timeout=None  # Let process complete naturally
)
```

## Usage

### Using the Enhanced Handler

```python
from cc_executor.core.websocket_handler_enhanced import EnhancedWebSocketHandler

# Create enhanced handler with custom heartbeat interval
handler = EnhancedWebSocketHandler(
    session_manager,
    process_manager,
    stream_handler,
    heartbeat_interval=20  # seconds
)
```

### Environment Variables

- `WEBSOCKET_HEARTBEAT_INTERVAL`: Set heartbeat interval (default: 20 seconds)
- `PYTHONUNBUFFERED`: Automatically set to '1' for Python processes
- `NODE_NO_READLINE`: Automatically set to '1' for Node.js processes

## Testing

### Test the Enhanced Handler

```bash
# Start the enhanced server
python -m cc_executor.core.websocket_handler_enhanced

# In another terminal, run tests
python test_websocket_enhanced.py --test story

# Run all tests
python test_websocket_enhanced.py --all
```

### Test Cases

1. **Simple Echo** - Basic connectivity test
2. **Math Question** - Quick Claude response
3. **Haikus** - Medium-length task
4. **Thinking Task** - Complex reasoning with long thinking time
5. **Story Generation** - 5000-word output test

## Comparison with Original Handler

| Feature | Original | Enhanced |
|---------|----------|----------|
| Heartbeat | ❌ No | ✅ Yes (20s) |
| Activity Monitoring | ❌ No | ✅ Yes (30s threshold) |
| Stream Timeout | ⚠️ 300s | ✅ None |
| Process Unbuffering | ⚠️ Limited | ✅ Enhanced |
| Long Thinking Support | ❌ Timeouts | ✅ Full support |

## Integration

To integrate the enhanced handler into your application:

1. Replace `WebSocketHandler` with `EnhancedWebSocketHandler`
2. Ensure client handles new message types (`heartbeat`, `process.status`)
3. Configure heartbeat interval as needed
4. Test with long-running prompts

## Monitoring

The enhanced handler provides better visibility:

```
[ENHANCED] Accepting WebSocket connection
[HEARTBEAT] Starting heartbeat loop (interval: 20s)
[ACTIVITY] Starting activity monitor
[ACTIVITY] Process inactive for 45s, sending status
[HEARTBEAT] Sent heartbeat
[STREAM] Starting enhanced streaming (no timeout)
[PROCESS COMPLETED] PID: 12345, Exit code: 0
```

## Future Improvements

1. **Adaptive Heartbeat**: Adjust interval based on process activity
2. **Progress Estimation**: Estimate completion based on output patterns
3. **Resource Monitoring**: Include CPU/memory stats in status updates
4. **Reconnection Support**: Handle temporary disconnections gracefully