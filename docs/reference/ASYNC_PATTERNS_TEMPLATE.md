# Async Patterns Template for CC Executor

## Overview

This template provides standard patterns for handling asynchronous operations in CC Executor, based on lessons learned from WebSocket handling, subprocess management, and concurrent task execution.

## Core Async Patterns

### Pattern 1: Single Entry Point

**Rule**: Only ONE `asyncio.run()` call per script, always in the `if __name__ == "__main__"` block.

```python
#!/usr/bin/env python3
"""Script with proper async structure."""

import asyncio
from typing import List, Dict, Any

async def fetch_data(url: str) -> Dict[str, Any]:
    """Fetch data asynchronously."""
    # Implementation here
    pass

async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single item."""
    # Implementation here
    pass

async def main():
    """Main entry point for all async operations."""
    # All async orchestration happens here
    urls = ["http://api1.com", "http://api2.com"]
    
    # Concurrent fetch
    results = await asyncio.gather(*[fetch_data(url) for url in urls])
    
    # Sequential processing
    for result in results:
        processed = await process_item(result)
        logger.info(f"Processed: {processed}")

if __name__ == "__main__":
    # Single asyncio.run() call
    asyncio.run(main())
```

### Pattern 2: Subprocess with Stream Draining

**Critical**: Always drain stdout/stderr to prevent deadlocks when output exceeds buffer size (typically 64KB).

```python
async def execute_command_safely(command: List[str]) -> tuple[int, str, str]:
    """
    Execute subprocess with proper stream handling to prevent deadlocks.
    
    Args:
        command: Command and arguments as list
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    async def drain_stream(stream, buffer: List[str], prefix: str):
        """Drain a stream line by line to prevent buffer overflow."""
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode().strip()
            buffer.append(decoded)
            logger.debug(f"[{prefix}] {decoded}")
    
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout_buffer = []
    stderr_buffer = []
    
    # Create tasks to drain both streams concurrently
    stdout_task = asyncio.create_task(
        drain_stream(proc.stdout, stdout_buffer, "STDOUT")
    )
    stderr_task = asyncio.create_task(
        drain_stream(proc.stderr, stderr_buffer, "STDERR")
    )
    
    # Wait for process to complete
    exit_code = await proc.wait()
    
    # Ensure streams are fully drained
    await stdout_task
    await stderr_task
    
    return exit_code, "\n".join(stdout_buffer), "\n".join(stderr_buffer)
```

### Pattern 3: WebSocket Connection Management

```python
class WebSocketManager:
    """Manage WebSocket connections with proper cleanup."""
    
    def __init__(self, url: str):
        self.url = url
        self.websocket = None
        self.tasks = set()
        
    async def connect(self):
        """Establish WebSocket connection."""
        self.websocket = await websockets.connect(self.url, ping_timeout=None)
        
    async def disconnect(self):
        """Clean disconnect with task cleanup."""
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellations
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            
    async def send_and_wait(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message and wait for response."""
        await self.websocket.send(json.dumps(message))
        
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("id") == message.get("id"):
                return data
            
            # Handle other messages (notifications, etc.)
            await self.handle_notification(data)
            
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
```

### Pattern 4: Concurrent Operations with Timeout

```python
async def process_with_timeout(
    tasks: List[Dict[str, Any]], 
    timeout: int = 30,
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """
    Process tasks concurrently with timeout and concurrency limit.
    
    Args:
        tasks: List of tasks to process
        timeout: Timeout per task in seconds
        max_concurrent: Maximum concurrent tasks
        
    Returns:
        List of results (successful or error)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_one(task: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:  # Limit concurrency
            try:
                # Process with timeout
                result = await asyncio.wait_for(
                    process_task(task), 
                    timeout=timeout
                )
                return {"task": task, "status": "success", "result": result}
            except asyncio.TimeoutError:
                logger.error(f"Task {task.get('id')} timed out")
                return {"task": task, "status": "timeout", "error": "Operation timed out"}
            except Exception as e:
                logger.error(f"Task {task.get('id')} failed: {e}")
                return {"task": task, "status": "error", "error": str(e)}
    
    # Process all tasks concurrently
    results = await asyncio.gather(
        *[process_one(task) for task in tasks],
        return_exceptions=True  # Don't fail all if one fails
    )
    
    # Handle any unexpected exceptions from gather
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "task": tasks[i], 
                "status": "error", 
                "error": f"Unexpected error: {result}"
            })
        else:
            final_results.append(result)
            
    return final_results
```

### Pattern 5: Resource Cleanup with Context Managers

```python
class ProcessPool:
    """Manage a pool of subprocesses with proper cleanup."""
    
    def __init__(self, max_processes: int = 5):
        self.max_processes = max_processes
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.lock = asyncio.Lock()
        
    async def spawn(self, proc_id: str, command: List[str]) -> asyncio.subprocess.Process:
        """Spawn a new process with tracking."""
        async with self.lock:
            # Clean up finished processes
            finished = [
                pid for pid, proc in self.processes.items() 
                if proc.returncode is not None
            ]
            for pid in finished:
                del self.processes[pid]
            
            # Check limit
            if len(self.processes) >= self.max_processes:
                raise RuntimeError(f"Process limit ({self.max_processes}) reached")
            
            # Spawn new process
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid  # Create process group
            )
            
            self.processes[proc_id] = proc
            return proc
            
    async def cleanup(self):
        """Clean up all processes."""
        async with self.lock:
            for proc_id, proc in self.processes.items():
                if proc.returncode is None:
                    try:
                        # Kill process group
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except:
                        # Force kill if needed
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
```

### Pattern 6: Redis Operations with Connection Pool

```python
class RedisManager:
    """Manage Redis operations with async connection pool."""
    
    def __init__(self):
        self.pool = None
        self.client = None
        
    async def connect(self):
        """Create Redis connection pool."""
        try:
            self.pool = await aioredis.create_redis_pool(
                'redis://localhost',
                minsize=5,
                maxsize=10
            )
            self.client = self.pool
            await self.client.ping()
            logger.info("Redis connected")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return False
            
    async def get_with_fallback(self, key: str, default: Any = None) -> Any:
        """Get value with fallback if Redis unavailable."""
        if not self.client:
            return default
            
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else default
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return default
            
    async def set_with_ttl(self, key: str, value: Any, ttl: int = 3600):
        """Set value with TTL, ignore if Redis unavailable."""
        if not self.client:
            return
            
        try:
            await self.client.setex(
                key, 
                ttl, 
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            
    async def close(self):
        """Close Redis connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
```

## Common Pitfalls and Solutions

### Pitfall 1: Subprocess Deadlock

**Problem**: Subprocess hangs when output exceeds buffer size.

```python
# ❌ WRONG - Will deadlock with large output
proc = await asyncio.create_subprocess_exec(
    'find', '/', '-name', '*.py',
    stdout=asyncio.subprocess.PIPE
)
stdout, _ = await proc.communicate()  # Hangs if output > 64KB
```

**Solution**: Always drain streams concurrently.

```python
# ✅ CORRECT - Drains output as it's produced
# Use the drain_stream pattern shown above
```

### Pitfall 2: Task Leakage

**Problem**: Tasks continue running after connection closes.

```python
# ❌ WRONG - Tasks not tracked
asyncio.create_task(long_running_operation())
# Connection closes, task keeps running
```

**Solution**: Track and cancel tasks.

```python
# ✅ CORRECT - Tasks tracked and cancelled
task = asyncio.create_task(long_running_operation())
self.tasks.add(task)
task.add_done_callback(self.tasks.discard)
```

### Pitfall 3: Missing Process Cleanup

**Problem**: Zombie processes when parent dies.

```python
# ❌ WRONG - No cleanup on exit
proc = await asyncio.create_subprocess_exec('long-running-command')
# Script exits, process keeps running
```

**Solution**: Use process groups and cleanup.

```python
# ✅ CORRECT - Process group and cleanup
proc = await asyncio.create_subprocess_exec(
    'long-running-command',
    preexec_fn=os.setsid
)
try:
    await proc.wait()
finally:
    if proc.returncode is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
```

## Testing Async Code

### Pattern for Testing in __main__

```python
async def test_async_operations():
    """Test suite for async operations."""
    logger.info("=== Testing Async Operations ===")
    
    # Test 1: Subprocess handling
    exit_code, stdout, stderr = await execute_command_safely(['echo', 'test'])
    assert exit_code == 0, f"Command failed: {stderr}"
    assert stdout.strip() == 'test', f"Unexpected output: {stdout}"
    logger.success("✓ Subprocess test passed")
    
    # Test 2: Concurrent operations
    tasks = [{"id": i, "data": f"test_{i}"} for i in range(5)]
    results = await process_with_timeout(tasks, timeout=10)
    assert all(r["status"] == "success" for r in results), "Some tasks failed"
    logger.success("✓ Concurrent operations test passed")
    
    # Test 3: Redis operations
    redis_mgr = RedisManager()
    if await redis_mgr.connect():
        await redis_mgr.set_with_ttl("test_key", {"value": 42})
        value = await redis_mgr.get_with_fallback("test_key", {})
        assert value.get("value") == 42, "Redis test failed"
        await redis_mgr.close()
        logger.success("✓ Redis test passed")
    else:
        logger.warning("⚠ Redis test skipped (not available)")
    
    return True

if __name__ == "__main__":
    # Single entry point
    success = asyncio.run(test_async_operations())
    exit(0 if success else 1)
```

## Best Practices Summary

1. **Single asyncio.run()**: Only one call per script, in __main__
2. **Stream Draining**: Always drain subprocess streams to prevent deadlock
3. **Task Tracking**: Track all created tasks for proper cleanup
4. **Process Groups**: Use for subprocess management
5. **Connection Pools**: Reuse connections for efficiency
6. **Graceful Degradation**: Handle service unavailability
7. **Context Managers**: Use for resource cleanup
8. **Timeout Everything**: Prevent infinite waits
9. **Concurrent Limits**: Prevent resource exhaustion
10. **Error Recovery**: Expect and handle failures

## Summary

These patterns ensure robust async operations in CC Executor by:
- Preventing common deadlocks and resource leaks
- Providing clean shutdown and cleanup
- Handling errors gracefully
- Maintaining performance under load
- Following Python async best practices

Always test async code thoroughly, especially edge cases like timeouts, cancellations, and resource limits.