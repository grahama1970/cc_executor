# Claude Code SDK vs Subprocess Comparison

## Current Implementation: Subprocess Approach

### How it works:
```python
# From process_manager.py
process = await asyncio.create_subprocess_shell(
    command,
    stdin=asyncio.subprocess.DEVNULL,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env,
    preexec_fn=os.setsid,  # Creates new process group
    limit=8 * 1024 * 1024  # 8MB buffer limit
)
```

### Advantages:
1. **Full Control**: Complete control over process execution, environment, buffering
2. **Real-time Streaming**: Direct access to stdout/stderr for streaming to WebSocket
3. **Process Management**: Can pause/resume/cancel with signals (SIGSTOP, SIGCONT, SIGTERM)
4. **No Dependencies**: Works with any Claude installation (CLI)
5. **Battle-tested**: Currently working in production
6. **Hook Workaround**: Can manually run setup scripts before execution

### Disadvantages:
1. **Complex Stream Handling**: Must manage async streams, buffering, deadlocks
2. **Environment Issues**: Need to handle PYTHONUNBUFFERED, stdbuf, etc.
3. **Process Cleanup**: Must carefully manage process groups to avoid zombies
4. **No Structured Output**: Parse text output instead of structured responses

## Proposed: Claude Code SDK

### How it would work:
```python
# From poc.py
async for message in query(
    prompt="Write a haiku about foo.py",
    options=ClaudeCodeOptions(max_turns=3)
):
    messages.append(message)
```

### Potential Advantages:
1. **Simpler API**: High-level abstraction for Claude interactions
2. **Structured Responses**: Get typed Message objects instead of raw text
3. **Built-in Features**: May handle retries, rate limiting, etc.
4. **Official Support**: Maintained by Anthropic

### Potential Disadvantages:
1. **Less Control**: Can't manage process lifecycle (pause/resume/cancel)
2. **Streaming Uncertainty**: Unclear if supports real-time streaming to WebSocket
3. **Dependency**: Adds external dependency that may change/break
4. **Limited Use Case**: Only works for Claude queries, not general command execution

## Key Questions for SDK:

1. **Does it support real-time streaming?** Critical for WebSocket updates
2. **Can you cancel mid-execution?** Currently we use SIGTERM/SIGKILL
3. **How does it handle long-running queries?** Timeout management?
4. **Does it work with Claude Max?** Or only API keys?
5. **Performance overhead?** Is it faster/slower than subprocess?

## Why the POC is Failing:

The POC code appears to hang, likely because:
1. Missing authentication setup
2. SDK may not be compatible with Claude Max
3. Possible missing configuration

## Recommendation:

**Stick with subprocess approach** unless SDK provides:
- Real-time streaming capability
- Process control (cancel/timeout)
- Better performance
- Clear documentation on WebSocket integration

The subprocess approach, while complex, gives us the control needed for a WebSocket-based execution service.