# CC-Executor Core MCP Implementation

This directory contains the core MCP (Model Context Protocol) WebSocket service for bidirectional communication with long-running Claude Code instances.

## Files

- `implementation.py` - Main MCP WebSocket service with process control
- `T01_robust_logging.py` - Structured JSON logging implementation
- `T02_backpressure_handling.py` - Buffer management for high-output processes
- `T03_websocket_stress_tests.py` - Comprehensive stress test suite
- `T05_security_pass.py` - Command allow-list security configuration

## Running the Service

```bash
# Start the MCP service on port 8003
python implementation.py --port 8003

# Run with custom configuration
python implementation.py --port 8003 --log-level DEBUG
```

## Key Features

### Process Control
- Direct control via OS signals (SIGSTOP/SIGCONT/SIGTERM)
- Process group management for controlling entire process trees
- Graceful cleanup on cancellation

### Back-Pressure Handling
- Configurable buffer limits (size and line count)
- Automatic dropping of old data when limits exceeded
- Metrics tracking for dropped data

### WebSocket Protocol
- JSON-RPC 2.0 over WebSocket
- Request/response tracking with unique IDs
- Streaming output with progress notifications

## Testing

Run the stress tests to validate the implementation:

```bash
cd ../tests/stress
python unified_stress_test_executor.py
```

## Architecture

The service follows an event-driven architecture:

1. **WebSocket Connection** - Handles client connections
2. **Request Router** - Routes JSON-RPC requests to handlers
3. **Task Manager** - Manages subprocess execution and state
4. **Output Buffer** - Handles streaming with back-pressure
5. **Process Controller** - Direct OS-level process control

## Security

- Command allow-list prevents arbitrary command execution
- Input validation on all requests
- Process isolation via subprocess

## Performance

- Handles 10+ concurrent sessions
- Manages processes with >1MB/s output
- Sub-second PAUSE/RESUME operations
- Memory-efficient buffer management