# Refactoring Suggestion: Rename `return_json` to `json_mode`

## Current State
The cc_execute function currently uses `return_json` as the parameter name:
```python
async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    return_json: bool = False,  # <-- Current name
    generate_report: bool = False,
    amend_prompt: bool = False
) -> Union[str, Dict[str, Any]]:
```

## Proposed Change
Rename to `json_mode` for consistency with industry standards:
```python
async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,  # <-- New name
    generate_report: bool = False,
    amend_prompt: bool = False
) -> Union[str, Dict[str, Any]]:
```

## Rationale

### Industry Standards
- **OpenAI**: `response_format={"type": "json_object"}` 
- **Anthropic**: `response_format={"type": "json_object"}`
- **LiteLLM**: `json_mode=True` (simplified parameter)
- **Gemini**: `response_mime_type="application/json"`

The term `json_mode` is widely recognized in the LLM community as requesting structured JSON output.

### Benefits
1. **Consistency**: Aligns with established LLM API conventions
2. **Discoverability**: Developers familiar with OpenAI/LiteLLM will immediately understand
3. **Clarity**: `json_mode` clearly indicates it changes the response format mode
4. **Future-proof**: If we later support `response_format` dict, `json_mode` can be a shorthand

## Implementation Plan

### Option 1: Simple Rename (Breaking Change)
```python
# Just rename the parameter
json_mode: bool = False
```

### Option 2: Backward Compatible (Recommended)
```python
async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,  # New parameter
    return_json: bool = None,  # Deprecated parameter
    generate_report: bool = False,
    amend_prompt: bool = False
) -> Union[str, Dict[str, Any]]:
    """
    Execute a complex Claude task.
    
    Args:
        json_mode: Return structured JSON output (replaces return_json)
        return_json: Deprecated, use json_mode instead
    """
    # Handle backward compatibility
    if return_json is not None:
        logger.warning("Parameter 'return_json' is deprecated, use 'json_mode' instead")
        json_mode = return_json
```

### Option 3: Full Response Format Support (Future)
```python
# Future enhancement to match OpenAI/Anthropic exactly
response_format: Optional[Union[Dict[str, str], bool]] = None

# Where response_format can be:
# - {"type": "json_object"}  # Full compatibility
# - True  # Shorthand for JSON mode
# - None/False  # Text mode
```

## Recommendation

Start with **Option 2** (backward compatible) to:
1. Avoid breaking existing code
2. Give users time to migrate
3. Establish the new convention

Later, consider Option 3 for full API compatibility with OpenAI/Anthropic.