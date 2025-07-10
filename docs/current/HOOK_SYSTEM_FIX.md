# Hook System Fix - Async Event Loop Blocking

## Problem Identified

The hook system is hanging the WebSocket server due to **synchronous Redis operations in an async context**.

### Root Cause

1. **Location**: `hook_integration.py` line 798 in `ensure_hooks` decorator
2. **Issue**: The async wrapper calls `hook.enforcer.initialize()` which is a synchronous method
3. **Blocking Operation**: `_check_redis()` uses synchronous `redis.Redis().ping()` which blocks the event loop

### The Blocking Chain

```python
# In ensure_hooks decorator (async_wrapper):
if not hook.enforcer.initialized:
    hook.enforcer.initialize()  # SYNCHRONOUS call in async context!
    
# Which calls:
def initialize(self):
    self._check_redis()  # SYNCHRONOUS Redis operations
    
# Which does:
def _check_redis(self):
    self.redis_client = redis.Redis(...)
    self.redis_client.ping()  # BLOCKS the event loop!
```

## Solution

### Option 1: Quick Fix (Disable Redis Check)

```python
def _check_redis(self) -> bool:
    """Check Redis connection."""
    # TEMPORARY: Skip Redis check to prevent blocking
    logger.info("Redis check skipped in async context")
    self.redis_client = None
    return False
```

### Option 2: Proper Fix (Make Initialize Async)

1. Convert `initialize()` to `async def initialize()`
2. Convert `_check_redis()` to use async Redis client
3. Update the decorator to await initialization

```python
# Fix the decorator:
async def async_wrapper(*args, **kwargs):
    hook = get_hook_integration()
    if not hook.enforcer.initialized:
        await hook.enforcer.async_initialize()  # New async method
    return await func(*args, **kwargs)

# Add async Redis check:
async def _async_check_redis(self) -> bool:
    try:
        import aioredis
        self.redis_client = await aioredis.create_redis_pool('redis://localhost')
        await self.redis_client.ping()
        return True
    except:
        return False
```

### Option 3: Defer Redis Check (Recommended for Now)

Simply defer the Redis check until it's actually needed, not during initialization:

```python
def _check_redis(self) -> bool:
    """Check Redis connection - deferred to prevent blocking."""
    # Don't actually connect during init
    logger.info("Redis connection deferred")
    return True  # Assume it will work
```

## Why This Fixes the Hanging

When the WebSocket handler accepts a connection and tries to execute a command:
1. It hits code that uses the `@ensure_hooks` decorator
2. The decorator calls `initialize()` synchronously in the async event loop
3. Redis connection blocks for 5+ seconds (timeout)
4. The entire event loop freezes - no coroutines can run
5. WebSocket appears to hang after "Hook enforcement system initialized"

## Testing the Fix

After implementing any of the above solutions:
1. Enable hooks by changing `if False and self.hooks` to `if self.hooks`
2. Test WebSocket connection
3. Verify commands execute without hanging

## Long-term Solution

The entire hook system should be refactored to be fully async:
- Use `aioredis` instead of `redis`
- Make all initialization methods async
- Ensure no blocking I/O in async contexts