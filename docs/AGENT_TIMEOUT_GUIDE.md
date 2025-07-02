# Agent Timeout Guide for cc_executor

When you (the agent) call Claude via cc_executor, you have two options for timeout handling:

## Option 1: Let Redis Determine Timeout (Recommended)

Simply don't specify a timeout - the system will automatically determine it based on:
- Historical execution data from Redis
- Task complexity analysis
- System load monitoring

```python
# Agent code - no timeout specified
result = await client.execute_command(
    command='claude -p "Write a haiku about Python" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
    # NO timeout parameter - let Redis decide
)
```

The WebSocket handler will:
1. Analyze the command complexity
2. Search Redis for similar historical executions
3. Apply appropriate timeout with safety margins
4. Monitor system load and adjust if needed

## Option 2: Agent Specifies Timeout

For special cases where you know the task complexity better than the system:

```python
# Agent code - explicit timeout
result = await client.execute_command(
    command='claude -p "Generate 100 test cases" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
    timeout=600  # 10 minutes for complex generation
)
```

## How Redis Timeout Estimation Works

1. **Command Classification**:
   - Category: claude, system, redis, testing, etc.
   - Complexity: trivial, simple, medium, complex, extreme
   - Question type: math, creative_writing, code_generation, etc.

2. **Timeout Sources** (in priority order):
   - Exact historical match (same command type)
   - Similar task history (same complexity/type)
   - Heuristic defaults with 3x multiplier for Claude
   - Conservative fallback (10 minutes minimum for unknown)

3. **Example Estimations**:
   - "What is 2+2?" → ~45s (trivial)
   - "Write 5 haikus" → ~180s (simple)
   - "Write a 1000 word essay" → ~2700s (extreme)
   - Unknown prompt → 600s minimum (10 minutes)

## System Load Adjustment

If CPU usage > 14% or high GPU usage detected:
- All timeouts multiplied by 3x
- Prevents false failures during high load

## Best Practices for Agents

1. **Default behavior**: Don't specify timeout - let Redis handle it
2. **Override only when necessary**: 
   - You have specific knowledge about the task
   - Task has unusual requirements
   - Iterative/interactive tasks

3. **Monitor results**: The system learns from each execution
   - Successful runs update Redis history
   - Future similar tasks get better timeout estimates

## Example Agent Implementation

```python
async def agent_execute_claude(prompt: str, timeout: Optional[int] = None):
    """
    Execute Claude command with intelligent timeout handling.
    
    Args:
        prompt: The prompt to send to Claude
        timeout: Optional timeout override (seconds). If None, Redis estimates.
    """
    command = f'claude -p "{prompt}" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'
    
    # Let cc_executor handle timeout estimation if not specified
    result = await client.execute_command(command, timeout=timeout)
    
    if not result['success']:
        # Check if it was a timeout issue
        if 'timed out' in result.get('error', ''):
            # Could retry with longer timeout or simplified prompt
            pass
    
    return result
```

## Redis History Benefits

Over time, the system becomes more accurate:
- First "write essay" task: Uses conservative defaults
- After 10 essay tasks: Accurate timeout predictions
- Handles variations: 500 words vs 2000 words
- Adapts to system performance changes