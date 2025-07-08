# Code Review Round 1 – Deployment Readiness Fixes (Request 027)

This assessment is based on a full-file static+manual review of the **CC Executor** codebase as requested in `027_CODE_REVIEW_REQUEST_DEPLOYMENT_READY.md`.

## Critical Issues (Must Fix Before Deploy)

1. **Event-Loop Blocking via `subprocess.run()`**  
   *Files*: `core/websocket_handler.py` (~3 call sites), `hooks/*`, others.  
   *Problem*: Synchronous `subprocess.run()` is executed inside async request handlers, freezing the event loop and breaking concurrent sessions.  
   *Fix*: Replace with `asyncio.create_subprocess_exec` wrapped in helper `run_subprocess_async(cmd, timeout)`; keep sync fallback for non-async contexts.

2. **Unbounded WebSocket Payloads**  
   *File*: `core/websocket_handler.py` (server instantiation).  
   *Problem*: `websockets.serve()` defaults to `max_size=None`, allowing arbitrarily large frames → memory exhaustion / DoS.  
   *Fix*: Add `max_size=10 * 1024 * 1024` (10 MB default) + CLI flag/env override.

3. **Redis Connection Pool Not Configurable**  
   *File*: `core/session_manager.py:75-90`.  
   *Problem*: Uses default pool size (10) which becomes a bottleneck under load.  
   *Fix*: Expose `REDIS_POOL_SIZE` env/CLI option; pass to `redis.ConnectionPool(max_connections=pool_size)`.

4. **Shell Execution of Composite Strings**  
   *File*: `hooks/claude_instance_pre_check.py:178-187`.  
   *Problem*: `subprocess.run(cmd, shell=True)` with formatted string containing project path → risk if path is compromised.  
   *Fix*: Use list form `['bash','-c',...]` or better `uv pip install -e .` via `subprocess.run([...])` without shell; validate inputs.

5. **File Path Sanitisation for `files_created` Output**  
   *File*: `client/cc_execute.py` (write operations).  
   *Problem*: Allows arbitrary relative paths from LLM; could overwrite host files.  
   *Fix*: Restrict writes to `WORK_DIR` and reject paths containing `..` after `Path.resolve()` check.

6. **Naïve Timeout Estimation**  
   *File*: `client/cc_execute.py:62-120`.  
   *Problem*: Hard-coded heuristic under-estimates for complex prompts → orphan processes.  
   *Fix*: Compute timeout as `base + k*token_count`; expose override; add safeguard to terminate after `max_timeout`.

## High Priority (Should Fix)
* WebSocket heartbeat / ping-pong keep-alive missing → idle disconnects.
* `simple.py` uses blocking `subprocess.run()` in CLI demo.
* `resource_monitor.py` calls `free -m` via subprocess; consider `psutil`.

## Medium / Low Priority
* Code formatting: 138 Ruff warnings (E501 lines > 120 chars).  
* Bandit: B603 (subprocess without shell), B605 low severity.

## Summary
Six blockers above must be addressed to ensure stability and security for production deployment. Subsequent rounds can tackle performance and DX polish.
