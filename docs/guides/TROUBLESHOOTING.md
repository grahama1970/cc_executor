# Troubleshooting Guide

This guide documents common issues, their root causes, and their solutions. It is based on the debugging history of this project and is intended to be the first place to look when encountering unexpected behavior.

## Problem: Process Hangs for 5 Minutes, Then Times Out

This is the most common and subtle failure mode. The service accepts a command, the `claude` process starts, but no output is ever received. The logs show a `stream_handler` timeout after 300 seconds.

**Root Cause: `stdin` Deadlock**

The `claude` executable, like many command-line tools, checks its standard input (`stdin`) pipe upon starting. If the pipe is open, it will politely wait for it to close before it begins processing. The `asyncio.subprocess.Process` in Python, by default, leaves this pipe open.

This creates a deadlock:
- The **`stream_handler`** is waiting for `claude` to write to `stdout`.
- The **`claude` process** is waiting for the `stream_handler`'s parent process to close the `stdin` pipe.

Neither event ever occurs, and the process hangs silently until a timeout is hit.

**Solution: Explicitly Close `stdin`**

The fix is to explicitly tell the subprocess that no `stdin` will be provided. This is done in `process_manager.py` by adding `stdin=asyncio.subprocess.DEVNULL` to the `create_subprocess_exec` call.

```python
# In process_manager.py
proc = await asyncio.create_subprocess_exec(
    *command_args,
    stdin=asyncio.subprocess.DEVNULL, # This line prevents the deadlock
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    # ...
)
```

## Problem: WebSocket Connection Drops After ~2 Minutes

This was an earlier issue where long-running `claude` commands would work for a while, but the WebSocket connection would suddenly close before the command finished.

**Root Cause: Network Idle Timeouts**

The WebSocket connection was idle from a "read" perspective. While the server was waiting for the `claude` process, no data was being sent *from* the client *to* the server. Many network components (reverse proxies, load balancers, and even the web server itself) have a default idle timeout (often 120 seconds) and will close a connection that has not received any data in that time.

**Solution: Server-Side WebSocket Keep-Alives**

The standard and most efficient way to solve this is to have the server periodically send low-level WebSocket `PING` frames to the client. The client will automatically respond with `PONG` frames. This traffic is invisible to the application but resets all network idle timers.

This is configured in the Uvicorn server settings in `websocket_handler.py`:

```python
# In websocket_handler.py, in the main execution block
config = uvicorn.Config(
    _app,
    # ...
    ws_ping_interval=20,  # Send a PING every 20 seconds
    ws_ping_timeout=20,   # Consider the connection dead if no PONG is received
)
```
With this setting, application-level heartbeats or ping/pong messages are unnecessary.

## Problem: `claude` Command Fails with "Invalid Arguments" (or similar)

The command runs perfectly in the local terminal but fails immediately when run through the WebSocket service. The `stderr` stream may contain a usage or argument error.

**Root Cause: Incorrect Shell-Level Parsing**

This occurs when the command is executed via a shell (`/bin/bash -c "..."`). A new shell does not have the same context as your interactive terminal and will incorrectly parse complex arguments, especially those with nested quotes.

**Solution: Execute Directly, Not Through a Shell**

The command string must be safely split into a list of arguments, and then executed directly. This bypasses any shell interpretation and ensures the process receives the exact same arguments it would from a well-behaved interactive terminal.

This is handled in `process_manager.py`:

```python
# In process_manager.py
import shlex

# 1. Split the command string safely
command_args = shlex.split(command)

# 2. Execute the list of arguments directly
proc = await asyncio.create_subprocess_exec(
    *command_args,
    # ...
)
```
