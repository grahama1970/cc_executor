# WebSocket Client for CC Executor

A production-ready WebSocket client with automatic handler restart capability to ensure 100% reliability when executing Claude CLI commands.

## Features

- **Automatic handler restart** (default behavior) - Ensures clean state for each command
- **Configurable restart strategies** - Per-task, every N tasks, or disabled
- **Minimal overhead** - Only ~800ms restart time
- **100% reliability** - Prevents hanging or blocked connections
- **Batch execution** - Run multiple tasks with progress tracking

## Installation

```python
from cc_executor.client.websocket_client import WebSocketClient
```

## Quick Start

```python
import asyncio
from cc_executor.client.websocket_client import WebSocketClient

async def main():
    client = WebSocketClient()
    
    # Execute a Claude command (auto-restarts by default)
    result = await client.execute_command(
        command='claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
        timeout=30
    )
    
    if result["success"]:
        print(f"Success! Duration: {result['duration']:.1f}s")
    else:
        print(f"Failed: {result['error']}")
    
    await client.cleanup()

asyncio.run(main())
```

## API Reference

### WebSocketClient

#### `execute_command(command, timeout=120, restart_handler=True)`

Execute a single command via WebSocket.

**Parameters:**
- `command` (str): Command to execute
- `timeout` (int): Maximum time to wait for completion in seconds (default: 120)
- `restart_handler` (bool): Whether to restart handler before execution (default: True)

**Returns:**
Dictionary with:
- `success` (bool): Whether command completed successfully
- `exit_code` (int): Process exit code (if successful)
- `duration` (float): Execution time in seconds
- `restart_overhead` (float): Time spent restarting handler
- `outputs` (int): Number of output messages received
- `output_data` (list): Actual output content
- `error` (str): Error message (if failed)

#### `execute_batch(tasks, restart_per_task=True, restart_every_n=None)`

Execute multiple tasks with configurable restart strategy.

**Parameters:**
- `tasks` (list): List of (name, command, timeout) tuples
- `restart_per_task` (bool): Restart handler for each task (default: True)
- `restart_every_n` (int): Restart handler every N tasks (overrides restart_per_task)

**Returns:**
List of execution results (same format as execute_command)

## Usage Examples

### Production Use (40-50 Claude Tasks)

```python
async def run_production_tasks():
    client = WebSocketClient()
    
    tasks = [
        ("Generate Report", 'claude -p "Generate quarterly report" ...', 120),
        ("Analyze Data", 'claude -p "Analyze sales trends" ...', 90),
        # ... more tasks
    ]
    
    # Execute with automatic restart for each task (default)
    results = await client.execute_batch(tasks)
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"Success rate: {successful}/{len(results)}")
    
    await client.cleanup()
```

### Optimized Usage

```python
# For simple commands, disable restart
result = await client.execute_command(
    command='echo "test"',
    restart_handler=False  # No restart needed for echo
)

# For Claude commands, use default (restart=True)
result = await client.execute_command(
    command='claude -p "Complex task" ...'
    # restart_handler=True is the default
)
```

### Restart Every N Tasks

```python
# Restart every 5 tasks instead of each task
results = await client.execute_batch(
    tasks=tasks,
    restart_every_n=5
)
```

## Best Practices

1. **Always use restart for Claude commands** (default behavior)
   - Prevents hanging due to stream completion issues
   - Ensures 100% reliability
   - Only ~800ms overhead

2. **Disable restart for simple commands** if needed
   - Commands like `echo`, `ls`, etc. don't need restart
   - Save ~800ms per command

3. **Clean up after use**
   ```python
   await client.cleanup()
   ```

4. **Monitor restart overhead**
   - Check `restart_overhead` in results
   - Typical overhead: 700-900ms
   - For 50 tasks: ~40 seconds total

## Performance Characteristics

- **Restart time**: ~800ms (0.8 seconds)
- **Overhead for 50 tasks**: ~40 seconds
- **Success rate with restart**: 100%
- **Success rate without restart**: ~70-90% (for Claude commands)

## Why Restart by Default?

Claude CLI has known issues where it outputs short responses but keeps streams open indefinitely. This causes the WebSocket handler to hang. The restart strategy ensures:

- Clean state for each command
- No accumulated issues
- 100% reliability
- Minimal overhead (< 1 second)