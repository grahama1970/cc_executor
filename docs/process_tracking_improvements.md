# Process Tracking Improvements Summary

## Feedback from Perplexity and Gemini

### Key Issues Identified

1. **Race Conditions**
   - Problem: Processes could start between baseline recording and test start
   - Solution: Use parent-child relationships and unique environment variables

2. **Cross-Platform Compatibility**
   - Problem: `os.setsid` and `os.killpg` don't work on Windows
   - Solution: Use `CREATE_NEW_PROCESS_GROUP` on Windows, `os.setsid` on Unix

3. **Blocking Async Calls**
   - Problem: `psutil` calls block the event loop
   - Solution: Use `asyncio.run_in_executor` or `asyncio.to_thread`

4. **Unreliable Timestamp Tracking**
   - Problem: Clock skew and timing issues
   - Solution: Use parent-child process relationships via `psutil.Process.children()`

5. **Missing Error Handling**
   - Problem: No handling for permission errors, dead processes
   - Solution: Comprehensive try-except blocks with specific error types

## Implemented Improvements

### 1. Parent-Child Process Tracking
```python
parent = psutil.Process(self.ws_process.pid)
children = parent.children(recursive=True)  # Get all descendants
```

### 2. Unique Test Identifier
```python
# Mark our processes with environment variable
env[self.test_env_var] = self.test_id
```

### 3. Cross-Platform Process Groups
```python
if sys.platform == "win32":
    creation_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
else:
    creation_kwargs['preexec_fn'] = os.setsid
```

### 4. Non-Blocking Async Operations
```python
# Run psutil in executor to avoid blocking
children = await asyncio.get_event_loop().run_in_executor(None, get_children)
```

### 5. Stream Draining to Prevent Deadlocks
```python
# Drain stdout/stderr to prevent buffer deadlock
asyncio.create_task(self._drain_stream(self.ws_process.stdout, "STDOUT"))
asyncio.create_task(self._drain_stream(self.ws_process.stderr, "STDERR"))
```

### 6. Robust Cleanup Phases
1. **Graceful termination** with SIGTERM
2. **Wait period** for processes to exit
3. **Force kill** with SIGKILL
4. **Process group cleanup** for stragglers
5. **Reap zombie processes** with wait()

### 7. Comprehensive Error Handling
- `ProcessLookupError` - Process already gone
- `PermissionError` - No permission to kill
- `psutil.NoSuchProcess` - Process disappeared
- Fallback for when psutil not available

## Benefits

1. **More Reliable** - Parent-child tracking is deterministic
2. **Cross-Platform** - Works on Windows, Linux, macOS
3. **No Race Conditions** - Unique identifiers prevent confusion
4. **No Deadlocks** - Proper stream handling
5. **Clean Shutdown** - Multi-phase cleanup ensures no zombies
6. **Async-Safe** - No blocking of event loop

## Integration Steps

1. Replace existing process tracking in stress tests
2. Add psutil to requirements if not present
3. Test on multiple platforms
4. Monitor for any remaining edge cases