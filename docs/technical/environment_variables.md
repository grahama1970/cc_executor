# Environment Variables Configuration

All hardcoded values have been removed from the cc_executor codebase. The system is now fully configurable through environment variables.

## Core Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_PORT` | 8003 | WebSocket server port |
| `MAX_SESSIONS` | 100 | Maximum concurrent WebSocket sessions |
| `SESSION_TIMEOUT` | 3600 | Session timeout in seconds (1 hour) |
| `HEALTH_CHECK_INTERVAL` | 30 | Health check interval in seconds |

## Stream Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAM_TIMEOUT` | 600 | Stream read timeout in seconds (10 minutes) |
| `MAX_BUFFER_SIZE` | 8192 | Maximum line size for stdout/stderr |
| `PROCESS_CLEANUP_TIMEOUT` | 10 | Timeout for process cleanup operations |

## WebSocket Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_PING_INTERVAL` | 20.0 | WebSocket ping interval in seconds |
| `WS_PING_TIMEOUT` | 30.0 | WebSocket pong timeout in seconds |
| `WS_MAX_SIZE` | 10485760 | Maximum WebSocket message size (10MB) |
| `WS_OPEN_TIMEOUT` | 30 | WebSocket connection handshake timeout |
| `WS_CLOSE_TIMEOUT` | 10 | WebSocket close timeout |
| `WS_RECV_TIMEOUT` | 1.0 | WebSocket receive timeout for polling |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | 30 | Application-level heartbeat interval |

## Task Execution Timeouts

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_TASK_TIMEOUT` | 300 | Default task timeout in seconds |
| `DEFAULT_STALL_TIMEOUT` | 120 | Default stall detection timeout |
| `STALL_TIMEOUT_PERCENTAGE` | 0.4 | Stall timeout as percentage of total timeout |
| `EXTREME_STALL_TIMEOUT` | 300 | Stall timeout for extreme complexity tasks |

## Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis server host |
| `REDIS_PORT` | 6379 | Redis server port |
| `REDIS_DB` | 0 | Redis database number |
| `TASK_TIMING_TTL` | 604800 | Redis key TTL (7 days) |

## Dynamic Timeout Overrides

You can override timeouts for specific tasks:

```bash
# Override timeout for a specific task ID
export TIMEOUT_OVERRIDE_long_1=900  # 15 minutes for long_1 task

# Override timeout for all extreme complexity tasks
export EXTREME_STALL_TIMEOUT=600  # 10 minutes stall timeout
```

## Example Usage

```bash
# Run with custom configuration
export STREAM_TIMEOUT=1200  # 20 minutes for very long tasks
export WS_PING_INTERVAL=10  # More frequent pings
export MAX_SESSIONS=50      # Limit concurrent sessions
export DEFAULT_PORT=8005    # Use different port

python -m core.main --host 0.0.0.0
```

## Debugging Long-Running Tasks

For tasks like 5000-word story generation:

```bash
# Extend all timeouts for extreme tasks
export STREAM_TIMEOUT=1800      # 30 minutes
export EXTREME_STALL_TIMEOUT=600 # 10 minutes before output
export WS_PING_INTERVAL=10       # Keep connection alive
export WS_PING_TIMEOUT=60        # More lenient pong timeout
```

## Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_COMMANDS` | None | Comma-separated list of allowed commands |

Example:
```bash
export ALLOWED_COMMANDS="echo,ls,cat,grep,python"
```

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEBUG` | false | Enable debug mode |
| `TEST_MODE` | false | Enable test mode |

## Notes

1. All timeout values are in seconds unless otherwise specified
2. Environment variables override all default values
3. No hardcoded values remain in the codebase
4. The system adapts dynamically based on task complexity and Redis historical data
5. Use `gnomon` or similar tools to measure actual task durations for tuning