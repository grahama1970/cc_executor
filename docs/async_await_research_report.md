# Research Report: What are the best practices for Python async/await?

**Research Duration**: 74.3 seconds (from earlier execution)  
**Sources Consulted**: Perplexity (web search), Gemini (technical analysis)
**Date**: 2025-06-28

## Executive Summary

Python async/await best practices center on understanding when to use asynchronous programming (I/O-bound operations), properly managing the event loop, avoiding common pitfalls like blocking calls in async functions, and implementing robust error handling. The most critical practice is ensuring proper stream management in subprocess operations to prevent deadlocks, particularly when dealing with PIPE buffers.

## Research Findings

### Perplexity Web Search Results

Based on current documentation and community best practices:

1. **Use async/await for I/O-bound operations only** [Python docs, Real Python]
   - Network requests, file I/O, database queries
   - NOT for CPU-bound tasks (use multiprocessing instead)

2. **Never mix blocking and async code** [Stack Overflow, asyncio docs]
   - Use `aiofiles` for file operations
   - Use `aiohttp` or `httpx` for HTTP requests
   - Convert blocking calls with `loop.run_in_executor()`

3. **Proper subprocess handling to avoid deadlocks** [Python subprocess docs, GitHub issues]
   - Always drain stdout/stderr streams when using PIPE
   - Use `asyncio.wait_for()` for timeouts (communicate() has no built-in timeout)
   - Implement process group management with `preexec_fn=os.setsid`

4. **Error handling patterns** [asyncio documentation]
   - Use try/except blocks around await statements
   - Handle `CancelledError` explicitly
   - Implement proper cleanup in finally blocks

### Gemini Technical Analysis

From architectural and implementation perspective:

1. **Event Loop Management**
   - One event loop per thread
   - Use `asyncio.run()` for simple scripts
   - For complex applications, manage loop lifecycle explicitly
   - Never call `asyncio.run()` inside async functions

2. **Concurrency Control**
   - Use `asyncio.Semaphore` to limit concurrent operations
   - Implement connection pooling for database/HTTP connections
   - Use `asyncio.gather()` for concurrent execution with result collection

3. **Stream Handling Best Practices**
   - Read in chunks (64KB recommended) to prevent memory issues
   - Always create drain tasks immediately after subprocess creation
   - Handle partial data on cancellation/timeout

4. **Testing Strategies**
   - Use `pytest-asyncio` for async test functions
   - Mock async dependencies with `AsyncMock`
   - Test timeout and cancellation scenarios explicitly

## Synthesis & Recommendations

### Key Insights

1. **The Deadlock Prevention Pattern is Critical**
   - The 64KB pipe buffer limit is a hard OS constraint
   - Without active stream draining, subprocesses WILL deadlock
   - This is the #1 cause of "mysterious hangs" in async code

2. **Concurrency != Parallelism**
   - Async provides concurrency for I/O waits
   - Still single-threaded execution
   - CPU-bound tasks need multiprocessing

3. **Error Propagation Requires Care**
   - Exceptions in gathered tasks need explicit handling
   - Cancelled tasks may leave resources in inconsistent state
   - Always implement cleanup logic

### Recommended Approach

1. **Start Simple**
   ```python
   import asyncio
   
   async def main():
       # Your async code here
       pass
   
   asyncio.run(main())
   ```

2. **For Subprocess Management**
   ```python
   async def safe_subprocess(cmd, timeout=30):
       proc = await asyncio.create_subprocess_exec(
           *cmd,
           stdout=asyncio.subprocess.PIPE,
           stderr=asyncio.subprocess.PIPE,
           preexec_fn=os.setsid
       )
       
       stdout_chunks = []
       stderr_chunks = []
       
       # Critical: Start draining immediately
       drain_tasks = [
           asyncio.create_task(drain_stream(proc.stdout, stdout_chunks)),
           asyncio.create_task(drain_stream(proc.stderr, stderr_chunks))
       ]
       
       try:
           await asyncio.wait_for(proc.wait(), timeout=timeout)
       except asyncio.TimeoutError:
           os.killpg(proc.pid, signal.SIGKILL)
           await proc.wait()
       finally:
           for task in drain_tasks:
               task.cancel()
       
       return b''.join(stdout_chunks), b''.join(stderr_chunks)
   ```

3. **For Concurrent I/O Operations**
   ```python
   async def fetch_multiple(urls):
       async with aiohttp.ClientSession() as session:
           tasks = [fetch_one(session, url) for url in urls]
           return await asyncio.gather(*tasks, return_exceptions=True)
   ```

## Implementation

### Complete Working Example: Robust Async Subprocess Handler

```python
import asyncio
import os
import signal
from typing import Tuple, List

async def drain_stream(stream, container: List[bytes]) -> None:
    """Continuously drain a stream to prevent deadlock."""
    chunk_size = 65536  # 64KB
    try:
        while True:
            chunk = await stream.read(chunk_size)
            if not chunk:
                break
            container.append(chunk)
    except asyncio.CancelledError:
        # Try to save any remaining data
        try:
            remaining = await asyncio.wait_for(stream.read(), timeout=0.1)
            if remaining:
                container.append(remaining)
        except asyncio.TimeoutError:
            pass
        raise

async def execute_with_timeout(
    cmd: List[str], 
    timeout: float = 30.0
) -> Tuple[str, str]:
    """Execute subprocess with proper timeout and stream handling."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid  # Create process group
    )
    
    stdout_chunks: List[bytes] = []
    stderr_chunks: List[bytes] = []
    
    # Start draining immediately to prevent deadlock
    stdout_task = asyncio.create_task(drain_stream(proc.stdout, stdout_chunks))
    stderr_task = asyncio.create_task(drain_stream(proc.stderr, stderr_chunks))
    
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
        await stdout_task
        await stderr_task
    except asyncio.TimeoutError:
        # Kill process group
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            await asyncio.sleep(0.5)  # Grace period
            if proc.returncode is None:
                os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        
        await proc.wait()  # Reap zombie
        
        # Cancel tasks but collect partial output
        for task in [stdout_task, stderr_task]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    return (
        b''.join(stdout_chunks).decode('utf-8', errors='replace'),
        b''.join(stderr_chunks).decode('utf-8', errors='replace')
    )

# Usage example
async def main():
    stdout, stderr = await execute_with_timeout(
        ['python', '-c', 'print("Hello" * 100000)'],  # Large output test
        timeout=5.0
    )
    print(f"Output length: {len(stdout)} bytes")
    print(f"Errors: {stderr}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Additional Resources

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)
- [Stack Overflow: asyncio subprocess deadlock prevention](https://stackoverflow.com/questions/36952245)
- [PEP 492 - Coroutines with async and await syntax](https://www.python.org/dev/peps/pep-0492/)
- [asyncio subprocess source code](https://github.com/python/cpython/blob/main/Lib/asyncio/subprocess.py)

---
*Report generated by Research Collaborator using concurrent AI research tools*