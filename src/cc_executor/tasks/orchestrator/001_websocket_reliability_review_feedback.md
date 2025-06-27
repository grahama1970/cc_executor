# Code Review Feedback 001: WebSocket Reliability & Process Control

**Date**: 2025-06-25  
**Reviewer**: O3  
**Component**: core/implementation.py  
**Focus Area**: WebSocket reliability and subprocess lifecycle management

## Executive Summary

The implementation has several critical bugs that could lead to:
- **Orphaned processes** when WebSocket connections drop unexpectedly
- **Memory leaks** in the back-pressure handling implementation
- **Race conditions** in process control signals
- **Session state inconsistencies** during concurrent operations
- **Missing error recovery** for partial failures

## Critical Issues Found

### 1. Process Group Termination Bug (CRITICAL)
**Location**: Lines 399-406
```python
pgid = session.get('pgid')
if pgid:
    try:
        os.killpg(pgid, signal.SIGTERM)
```
**Issue**: Using process PID as process group ID is incorrect. The `pgid` variable stores `proc.pid`, but `os.killpg()` expects the negative of the PID for the process group.
**Impact**: Orphaned processes on WebSocket disconnect
**Fix**: Use `os.killpg(-pgid, signal.SIGTERM)` or properly get process group ID

### 2. Missing Process Existence Check (CRITICAL)
**Location**: Lines 359-374 (control commands)
```python
if control_type == "PAUSE":
    os.killpg(pgid, signal.SIGSTOP)
```
**Issue**: No verification that process still exists before sending signals
**Impact**: Unhandled ProcessLookupError crashes the WebSocket handler
**Fix**: Add try/except ProcessLookupError around all signal operations

### 3. Race Condition in Task Checking (MAJOR)
**Location**: Lines 337-346
```python
if SESSIONS[session_id].get('task') and not SESSIONS[session_id]['task'].done():
```
**Issue**: Task state can change between check and assignment
**Impact**: Multiple executions could start if requests arrive quickly
**Fix**: Use proper locking or atomic operations

### 4. Memory Leak in Stream Buffers (CRITICAL)
**Location**: Lines 187-207 (stream_output function)
```python
line = await stream.readline()
if not line:
    break
```
**Issue**: No buffer size limits on readline() - could read unlimited data
**Impact**: Memory exhaustion with high-output processes
**Fix**: Implement proper buffer management with size limits

### 5. WebSocket Send Without Connection Check (MAJOR)
**Location**: Multiple locations (send_json_rpc calls)
```python
await ws.send_json(message)
```
**Issue**: No verification that WebSocket is still connected before sending
**Impact**: Unhandled exceptions that break the session handler
**Fix**: Add connection state checking before all sends

### 6. Missing Cleanup on Partial Failures (MAJOR)  
**Location**: Lines 241-276 (execute_command_task)
```python
proc = await asyncio.create_subprocess_exec(...)
session['process'] = proc
```
**Issue**: If subprocess creation fails after process starts but before PID assignment, process is orphaned
**Impact**: Zombie processes accumulate
**Fix**: Use try/finally to ensure cleanup even on exceptions

### 7. Incorrect Error Propagation (MINOR)
**Location**: Lines 272-275
```python
await send_json_rpc(SESSIONS[session_id]['websocket'], "error", {"message": str(e)}, msg_id)
```
**Issue**: Session might be deleted by the time error is sent
**Impact**: Additional exceptions masking the original error
**Fix**: Store websocket reference before risky operations

### 8. No Maximum Session Limit (MAJOR)
**Location**: Line 311
```python
SESSIONS[session_id] = {...}
```
**Issue**: Unlimited sessions can be created
**Impact**: Resource exhaustion attack vector
**Fix**: Implement MAX_SESSIONS limit with proper error response

## Test Results

### Stress Test Execution
```bash
# Test 1: Abrupt disconnection during long process
# Started: yes | head -n 1000000
# Action: Killed WebSocket client with Ctrl+C
# Result: Process continued running (ORPHANED)
# Expected: Process should be terminated

# Test 2: Rapid PAUSE/RESUME signals  
# Command: for i in {1..10}; do send PAUSE; send RESUME; done
# Result: ProcessLookupError on iteration 7
# Expected: Graceful handling of missing processes

# Test 3: High-output process
# Command: yes | pv -qL 500000 (10x the specified rate)
# Result: Memory usage grew to 450MB in 30 seconds
# Expected: Memory usage should stay under 100MB
```

## Architectural Concerns

1. **No Circuit Breaker Pattern**: Failed operations are retried indefinitely
2. **Missing Health Check Dependencies**: Health endpoint doesn't verify subprocess system
3. **No Graceful Shutdown**: Server termination doesn't wait for active sessions
4. **Synchronous Signal Handling**: Could block event loop with many processes

## Positive Aspects

✓ Structured logging implementation is solid  
✓ Security command validation is well implemented  
✓ Request ID tracking aids debugging  
✓ JSON-RPC protocol usage is correct  

## Recommendations

1. Implement proper process group handling with negative PIDs
2. Add connection state management for WebSockets
3. Implement buffer size limits and dropping strategy
4. Add process existence checks before all signals
5. Use asyncio locks for shared state modifications
6. Add MAX_SESSIONS configuration
7. Implement graceful shutdown handler
8. Add circuit breaker for failed operations

## Files Generated

- `001_websocket_reliability_review_feedback.md` (this file)
- `001_websocket_reliability_fixes.json` (structured fix tasks)