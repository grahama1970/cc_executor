# Output Buffer Deadlock Causes Timeout on Long-Running Tasks

**STATUS: RESOLVED** - Fixed in commit [pending]

## Description

When using CC Execute to process tasks that generate significant output, the process hangs indefinitely due to output buffer deadlock. This makes CC Execute unusable for complex tasks like PDF processing, code generation, or detailed analysis.

## Current Behavior

- Tasks with minimal output (e.g., "What is 2+2?") complete successfully in ~7 seconds
- Tasks that generate lots of output hang indefinitely, even with `timeout=3600` (1 hour)
- No streaming output is visible during execution
- The process times out without returning any results

## Expected Behavior

- Tasks should complete regardless of output volume
- Streaming output should be visible during execution
- On timeout, partial results should be returned (not an exception)

## Root Cause

The issue is in `_execute_claude_command()` around line 348-363:

```python
# Current problematic code
await asyncio.wait_for(
    proc.wait(),  # Waits for process exit
    timeout=config.timeout
)
# Only THEN tries to read output - too late!
await stdout_task
await stderr_task
```

**The Problem**: 
1. Claude CLI writes output to stdout/stderr
2. OS pipe buffer (typically 64KB) fills up
3. Claude blocks waiting for buffer space
4. `proc.wait()` waits for process exit that never comes
5. Deadlock!

## Steps to Reproduce

1. Run any task that generates >64KB of output:
```python
task = "Write a detailed 5000 word essay on AI"
result = await cc_execute(task, timeout=300)
```

2. Observe that it times out after 300s without returning results

## Proposed Fix

Replace the current wait pattern with concurrent reading:

```python
# Fix: Wait for BOTH process completion AND stream reading
try:
    await asyncio.wait_for(
        asyncio.gather(
            proc.wait(),
            stdout_task,
            stderr_task,
            return_exceptions=True
        ),
        timeout=config.timeout
    )
except asyncio.TimeoutError:
    # Don't raise - return partial results
    logger.info(f"Returning partial output after timeout")
    # Continue to return what we have...
```

## Alternative Solutions

1. **Use `communicate()`** (simpler but less flexible):
```python
stdout, stderr = await asyncio.wait_for(
    proc.communicate(),
    timeout=config.timeout
)
```

2. **Redirect to files** to avoid pipe buffers entirely

3. **Increase pipe buffer size** (platform-specific)

## Impact

This bug makes CC Execute unusable for:
- PDF processing pipelines
- Large code generation tasks
- Detailed analysis requests
- Any task producing >64KB output

## Verification

Run this test to confirm the issue:
```python
# This will hang with current code, work with the fix
task = """Generate 100 paragraphs of Lorem Ipsum text. 
Each paragraph should be at least 200 words."""
result = await cc_execute(task, timeout=60)
```

## Environment

- Python 3.x with asyncio
- Claude CLI 
- OS: Linux/macOS/Windows (all affected)
- CC Execute version: latest

## References

- [Python subprocess deadlock documentation](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait)
- [AsyncIO subprocess handling](https://docs.python.org/3/library/asyncio-subprocess.html)
- Similar issue: [nodejs/node#4236](https://github.com/nodejs/node/issues/4236)

## Priority

**High** - This is a blocking issue for production use of CC Execute with any non-trivial tasks.

---

**Note from ArXiv MCP Server team**: We've been unable to use CC Execute for our PDF processing pipeline due to this issue. The MCP interface works fine, but direct Python integration is broken. Happy to test any fixes!

## Resolution

**Fixed in executor.py** by changing the wait pattern to use `asyncio.gather()` to wait for BOTH process completion AND stream reading concurrently:

```python
await asyncio.wait_for(
    asyncio.gather(
        proc.wait(),
        stdout_task,
        stderr_task,
        return_exceptions=True
    ),
    timeout=config.timeout
)
```

This ensures that:
1. Output is continuously drained from buffers while the process runs
2. The process won't block waiting for buffer space
3. Large outputs (>64KB) are handled correctly

The fix has been tested with tasks generating >1MB of output and no longer deadlocks.