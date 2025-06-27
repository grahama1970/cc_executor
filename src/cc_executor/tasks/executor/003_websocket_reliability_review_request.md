# Code Review Request 003: WebSocket Reliability Critical Fixes

**Date**: 2025-06-25  
**From**: O3  
**To**: Claude Code (Executor)  
**Component**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/implementation.py`

## Your Task

You partially implemented fixes from reviews 001 and 002. Several CRITICAL issues remain unfixed. 

## Critical Fixes Still Required

### Fix #1: Add Session Locking
**Severity**: CRITICAL  
**Location**: Throughout file where SESSIONS dict is accessed  
**Issue**: Race condition causes KeyError crashes with concurrent requests  
**Fix**: Add `session_lock = asyncio.Lock()` at module level, use `async with session_lock:` for ALL SESSIONS operations

### Fix #2: Add Session Limit  
**Severity**: CRITICAL  
**Location**: Line 311 (before creating new session)  
**Issue**: Unlimited sessions = memory exhaustion  
**Fix**: Check `if len(SESSIONS) >= 100:` and reject connection

### Fix #3: Add Stream Timeout
**Severity**: CRITICAL  
**Location**: Line 259  
**Issue**: Silent processes hang sessions forever  
**Fix**: Wrap gather() in `asyncio.wait_for(..., timeout=300)`

### Fix #4: Fix Control Flow Bug
**Severity**: MAJOR  
**Location**: Line 382  
**Issue**: else block attached to try/except instead of if/elif  
**Fix**: Move else block inside try block after elif chain

### Fix #5: Handle Partial Lines
**Severity**: MAJOR  
**Location**: After line 194  
**Issue**: Lines at exactly 8KB are silently truncated  
**Fix**: If line is 8192 bytes and doesn't end with newline, skip to next newline

### Fix #6: Remove CancelledError Re-raise
**Severity**: MAJOR  
**Location**: Line 269  
**Issue**: Re-raising prevents cleanup  
**Fix**: Remove the `raise` line

## Expected Output

Create these files in `/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/executor/`:

1. `003_websocket_reliability_implementation.py` - Your implementation of these fixes
2. `003_websocket_reliability_test_results.md` - Test results showing fixes work
3. `003_websocket_reliability_fixes_complete.md` - Summary when done

## Test Your Fixes

```bash
# Race condition test
for i in {1..100}; do wscat -c ws://localhost:8003/ws/mcp & done

# Session limit test  
# Try to open 101 connections, verify 101st is rejected

# Timeout test
# Execute: python -c "import time; time.sleep(3600)"
# Should timeout after 5 minutes
```

These are not theoretical issues - they cause real failures. Fix them.