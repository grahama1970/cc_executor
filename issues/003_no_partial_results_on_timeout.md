# No Partial Results Returned on Timeout

**STATUS: RESOLVED** - Fixed in commit [pending]

## Description

When CC Execute times out, it returns an error instead of partial results. For long-running tasks, users lose all progress even if 90% was completed successfully.

## Current Behavior

```python
# Task times out after 120s
result = await cc_execute(task, timeout=120)
# Returns: TimeoutError - all work lost!
```

Even if Claude completed 9 out of 10 sections, the user gets nothing.

## Expected Behavior

```python
# Task times out after 120s
result = await cc_execute(task, timeout=120)
# Returns: {"partial": true, "completed": 9, "total": 10, "results": [...]}
```

Users should receive whatever was completed before timeout.

## Root Cause

The current implementation raises TimeoutError without capturing stdout:

```python
# Current problematic code
try:
    await asyncio.wait_for(proc.wait(), timeout)
except asyncio.TimeoutError:
    raise  # All output lost!
```

## Proposed Fix

Capture and return partial results:

```python
try:
    await asyncio.wait_for(proc.wait(), timeout)
except asyncio.TimeoutError:
    # Gracefully collect what we have
    partial_output = ''.join(output_lines)
    
    # Try to parse partial JSON
    if json_mode:
        result = try_parse_partial_json(partial_output)
        if result:
            result['partial'] = True
            result['timeout_after'] = timeout
            return result
    
    # Return text output with metadata
    return {
        "output": partial_output,
        "partial": True,
        "timeout_after": timeout,
        "error": "Task timed out but partial results available"
    }
```

## Helper for Partial JSON

```python
def try_parse_partial_json(text: str) -> Optional[dict]:
    """Attempt to parse incomplete JSON by fixing common issues."""
    
    # Find last complete JSON object
    if '"sections"' in text:
        # Try to close unclosed arrays/objects
        brackets = []
        for char in text:
            if char in '{[':
                brackets.append(char)
            elif char in '}]':
                if brackets and brackets[-1] == '{' and char == '}':
                    brackets.pop()
                elif brackets and brackets[-1] == '[' and char == ']':
                    brackets.pop()
        
        # Add missing closing brackets
        for bracket in reversed(brackets):
            if bracket == '{':
                text += '}'
            elif bracket == '[':
                text += ']'
        
        try:
            return json.loads(text)
        except:
            pass
    
    return None
```

## Use Cases

1. **PDF Processing**: User processes 100 pages, timeout at page 90
   - Current: Lose everything
   - Fixed: Get 90 pages of results

2. **Batch Operations**: Processing 50 items, timeout at item 45  
   - Current: Start over
   - Fixed: Get 45 completed items

3. **Long Analysis**: Complex analysis times out near completion
   - Current: No insights
   - Fixed: Get most of the analysis

## Benefits

- Users don't lose work on timeout
- Can set aggressive timeouts without fear
- Enables incremental processing workflows
- Better user experience

## Testing

```python
async def test_partial_results():
    # Create task that outputs incrementally
    task = "Process these 10 items one by one: [...]"
    
    # Set timeout to interrupt mid-task
    result = await cc_execute(task, timeout=30)
    
    # Should have partial results
    assert result.get('partial') == True
    assert len(result.get('results', [])) > 0
    assert 'timeout_after' in result
```

## Priority

**High** - This causes data loss and user frustration. The fix is relatively simple but has high impact.

---

**Note from ArXiv MCP Server team**: We've lost hours of processing due to timeouts with no partial results. This would be a game-changer for long document processing.

## Resolution

**Fixed in executor.py** by changing timeout handling to return partial results instead of raising an exception:

1. **Graceful timeout handling**:
   - Collects all output before timeout
   - Saves partial results to a JSON file with "_PARTIAL" suffix
   - Returns collected output instead of raising TimeoutError

2. **JSON mode support**:
   - New `try_parse_partial_json()` function attempts to salvage incomplete JSON
   - Fixes unclosed brackets and arrays
   - Returns structured data when possible

3. **Text mode support**:
   - Appends timeout marker to output
   - Preserves all generated content

Example of returned partial result in JSON mode:
```json
{
  "result": "...",
  "partial": true,
  "timeout_after": 120,
  "error": "Task timed out but partial results available",
  "execution_uuid": "..."
}
```

This ensures users never lose work due to timeouts and can implement incremental processing workflows.