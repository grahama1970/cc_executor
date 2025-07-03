# Timeout Management Guide

This guide consolidates all timeout-related documentation, strategies, and best practices for CC Executor.

## Overview

Timeout management is critical for CC Executor because:
- Claude operations can take 30 seconds to 5+ minutes
- Network connections have implicit timeout limits
- Process execution requires careful timeout coordination
- Users need feedback even during long operations

## Timeout Hierarchy

### 1. Network Level (WebSocket)
- **Default timeout**: 120 seconds (many proxies/load balancers)
- **Solution**: WebSocket ping/pong frames every 20 seconds
- **Configuration**: In `websocket_handler.py`:
  ```python
  config = uvicorn.Config(
      ws_ping_interval=20,  # Send PING every 20 seconds
      ws_ping_timeout=20,   # Consider dead if no PONG
  )
  ```

### 2. Process Level (StreamHandler)
- **Default timeout**: 300 seconds (5 minutes)
- **Configurable via**: `STREAM_TIMEOUT` environment variable
- **Purpose**: Prevent zombie processes from consuming resources

### 3. Application Level (Claude Operations)
- **Typical durations**:
  - Simple prompts: 5-30 seconds
  - Complex analysis: 1-3 minutes
  - Large content generation: 3-5 minutes
- **Strategy**: Progressive timeout scaling

## The ACK Pattern: Last Line of Defense

"ACK" is a minimal acknowledgment pattern that forces Claude to respond immediately with a short confirmation before processing the main request.

### Why ACK Works

1. **Immediate Response**: Claude must respond within 2-3 seconds
2. **Breaks Thinking-Timeout Cycle**: Prevents silent timeouts during processing
3. **Connection Keepalive**: Any data keeps WebSocket alive
4. **Diagnostic Value**: Confirms Claude received and started processing

### ACK Implementation Levels

#### Level 1: Friendly Acknowledgment
```python
prompt = """Please acknowledge this request with "Processing your request..." 
then provide a Python implementation of merge sort."""
```

#### Level 2: Explicit ACK
```python
prompt = """First output: "ACK" (nothing else)
Second output: Python merge sort implementation

Begin with ACK immediately."""
```

#### Level 3: Urgent ACK
```python
prompt = """URGENT: Type "ACK" NOW then answer: What is 2+2?"""
```

#### Level 4: Nuclear ACK (Last Resort)
```python
prompt = """ACK
merge sort?"""
```

### Progressive ACK Strategy
```python
class AckStrategy:
    """Implements progressive ACK enforcement"""
    
    def __init__(self):
        self.strategies = [
            self.polite_ack,
            self.firm_ack,
            self.urgent_ack,
            self.nuclear_ack
        ]
    
    async def wait_for_ack(self, process, timeout=5):
        """Wait for ACK with very short timeout"""
        try:
            output = await asyncio.wait_for(
                process.stdout.read(100),
                timeout=timeout
            )
            response = output.decode()
            if any(ack in response.upper() for ack in ['ACK', 'PROCESSING', 'RECEIVED']):
                return True, response
            return False, response
        except asyncio.TimeoutError:
            return False, None
```

## Agent-Specific Timeout Configuration

### Understanding Load-Based Timeouts

CC Executor implements dynamic timeout adjustment based on system load:

```python
def calculate_dynamic_timeout(base_timeout: int, load_factor: float) -> int:
    """Adjust timeout based on system load"""
    # Load factor 1.0 = normal, 2.0 = double load
    adjusted = base_timeout * (1 + (load_factor - 1) * 0.5)
    return min(adjusted, base_timeout * 2)  # Cap at 2x
```

### Environment Variables

```bash
# Base timeout for stream operations
export STREAM_TIMEOUT=300  # 5 minutes default

# Maximum buffer size for large outputs
export MAX_BUFFER_SIZE=10485760  # 10MB

# WebSocket-specific timeouts
export WS_PING_INTERVAL=20
export WS_PING_TIMEOUT=20

# Process management
export MAX_SESSIONS=10  # Limit concurrent operations
```

### Redis Integration for Timeout Coordination

When Redis is available, timeouts are coordinated across the system:

```python
async def get_recommended_timeout(operation_type: str) -> int:
    """Get timeout recommendation from Redis-backed metrics"""
    if redis_client:
        # Check recent operation durations
        recent_ops = await redis_client.get(f"cc:metrics:{operation_type}")
        if recent_ops:
            p95_duration = calculate_p95(recent_ops)
            return int(p95_duration * 1.5)  # 50% buffer
    
    # Fallback to defaults
    return DEFAULT_TIMEOUTS.get(operation_type, 300)
```

## Common Timeout Scenarios and Solutions

### Scenario 1: Initial Connection Timeout
**Problem**: Claude doesn't respond within first 30 seconds
**Solution**: Use ACK pattern to force immediate response

### Scenario 2: Mid-Operation Timeout
**Problem**: Long operation exceeds network timeout
**Solution**: WebSocket ping/pong maintains connection

### Scenario 3: Process Hanging
**Problem**: Claude process exists but produces no output
**Root Cause**: Usually stdin not closed properly
**Solution**: Always use `stdin=asyncio.subprocess.DEVNULL`

### Scenario 4: Large Output Timeout
**Problem**: Massive output overwhelms buffers
**Solution**: Stream processing with progress indicators

## Timeout Best Practices

### 1. Set Realistic Timeouts
```python
TIMEOUT_DEFAULTS = {
    'simple_prompt': 60,      # 1 minute
    'complex_analysis': 180,  # 3 minutes
    'code_generation': 300,   # 5 minutes
    'large_content': 600      # 10 minutes
}
```

### 2. Implement Progress Indicators
```python
async def stream_with_progress(stream, timeout):
    last_output = time.time()
    total_bytes = 0
    
    while True:
        if time.time() - last_output > timeout:
            raise TimeoutError(f"No output for {timeout}s")
        
        line = await stream.readline()
        if not line:
            break
            
        total_bytes += len(line)
        last_output = time.time()
        
        # Send progress every 100KB
        if total_bytes % 102400 == 0:
            await send_progress(total_bytes)
```

### 3. Use Timeout Cascades
```python
async def execute_with_cascading_timeouts(command):
    timeouts = [30, 60, 120, 300]  # Escalating timeouts
    
    for timeout in timeouts:
        try:
            return await asyncio.wait_for(
                run_command(command),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            if timeout == timeouts[-1]:
                raise
            logger.warning(f"Timeout at {timeout}s, retrying with {timeouts[timeouts.index(timeout)+1]}s")
```

### 4. Monitor and Adjust
```python
# Log timeout events for analysis
async def log_timeout_event(operation, timeout, actual_duration):
    await redis_client.zadd(
        "cc:timeout_events",
        {f"{operation}:{timestamp}": actual_duration}
    )
    
    # Adjust future timeouts if needed
    if actual_duration > timeout * 0.9:
        logger.warning(f"Operation {operation} used 90% of timeout")
```

## Debugging Timeout Issues

### 1. Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python core/websocket_handler.py --serve
```

### 2. Check Key Indicators
- "Starting stdout streaming" - Process started
- "ACK received" - Claude responding
- "Stream timeout after Xs" - Where timeout occurred
- "WebSocket ping timeout" - Network issue

### 3. Use Test Cases
```bash
# Test ACK response time
python core/websocket_handler.py --serve --auto-demo --test-case ack

# Test timeout handling
python core/websocket_handler.py --serve --auto-demo --test-case timeout
```

## Summary

Effective timeout management requires:
1. **Multiple layers**: Network, process, and application timeouts
2. **ACK pattern**: Ensure immediate response for long operations
3. **Dynamic adjustment**: Based on system load and operation type
4. **Progress indicators**: Keep connections alive during processing
5. **Proper monitoring**: Track and adjust based on real performance

The ACK pattern remains the most reliable last line of defense, ensuring that even if the full operation times out, the user knows their request was received and processing began.

Last updated: 2025-07-02