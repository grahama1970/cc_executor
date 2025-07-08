# Critical Fix Required: WebSocket Handler Blocking Event Loop

## Issue
The WebSocket handler (`websocket_handler.py`) has **3 instances** of `subprocess.run()` that block the async event loop:

1. **Line 518** - In `_handle_execute()` method (already partially fixed)
2. **Line 1244** - In direct `execute()` function 
3. **Line 1310** - In direct `execute()` function (post-execution hooks)

## Impact
- **Severity**: CRITICAL
- **Effect**: Entire WebSocket server freezes while subprocess runs
- **User Experience**: All connected clients hang during hook execution

## Root Cause
Using blocking `subprocess.run()` in async functions prevents the event loop from handling other connections or messages.

## Solution

### Option 1: Use Existing HookIntegration (Recommended)
The WebSocket handler already imports and initializes `HookIntegration` which has async-safe methods:
- `async_pre_execute_hook()` - For pre-execution hooks
- `async_post_execute_hook()` - For post-execution hooks

### Option 2: Convert to asyncio.create_subprocess_exec
Replace all `subprocess.run()` with async subprocess calls.

## Code Changes Needed

### 1. Fix line 1244 (pre-execution hooks in direct execute):
```python
# OLD (blocking):
subprocess.run([sys.executable, str(hook_path)], check=True, cwd=cwd)

# NEW (async-safe):
proc = await asyncio.create_subprocess_exec(
    sys.executable, str(hook_path),
    cwd=cwd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await proc.communicate()
if proc.returncode != 0:
    logger.warning(f"[EXECUTE] {hook} failed: {stderr.decode()}")
else:
    logger.info(f"[EXECUTE] {hook} completed")
```

### 2. Fix line 1310 (post-execution hooks):
```python
# OLD (blocking):
result = subprocess.run(
    cmd,
    env=hook_env,
    capture_output=True,
    text=True,
    timeout=10
)

# NEW (async-safe):
proc = await asyncio.create_subprocess_exec(
    *cmd,
    env=hook_env,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
try:
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
    if proc.returncode == 0:
        logger.info(f"[EXECUTE] Post-hook {hook} completed")
    else:
        logger.warning(f"[EXECUTE] Post-hook {hook} failed: {stderr.decode()}")
except asyncio.TimeoutError:
    proc.kill()
    logger.warning(f"[EXECUTE] Post-hook {hook} timed out")
```

## Testing
After fixing, verify:
1. WebSocket server remains responsive during hook execution
2. Multiple concurrent connections work properly
3. Hooks still execute correctly

## Prevention
- Add linting rule to catch `subprocess.run()` in async functions
- Use `# noqa` only where synchronous execution is explicitly required
- Document that all WebSocket handlers must be fully async