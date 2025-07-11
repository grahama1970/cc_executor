# JSON Mode Parsing Failures

**STATUS: RESOLVED** - Fixed in commit [pending]

## Description

CC Execute's `json_mode=True` frequently fails to parse Claude's response, even when Claude returns valid JSON. This forces users to implement fragile parsing workarounds.

## Current Behavior

```python
result = await cc_execute(prompt, json_mode=True)
# Often returns: "Execution error" or raw text instead of parsed JSON
```

The JSON parsing is too strict and doesn't handle:
- Markdown code blocks
- Extra text before/after JSON
- Pretty-printed JSON with extra whitespace
- Escaped characters in strings

## Expected Behavior

```python
result = await cc_execute(prompt, json_mode=True)
# Always returns: dict (parsed JSON) or raises clear error
```

## Root Cause

Current implementation expects pure JSON:
```python
# Too strict - fails on any extra content
result = json.loads(output)
```

But Claude often returns:
```
I'll process your PDF sections:

```json
{
  "sections": [
    {
      "id": 0,
      "blocks": [...]
    }
  ]
}
```

The analysis shows 3 fixes were applied.
```

## Proposed Fix

Implement robust JSON extraction:

```python
def extract_json_from_response(text: str) -> dict:
    """Extract JSON from Claude's response, handling various formats."""
    
    # Method 1: Look for ```json blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Method 2: Find JSON by looking for { } boundaries
    # Find the first { and last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace >= 0 and last_brace > first_brace:
        json_candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            # Try fixing common issues
            json_candidate = fix_common_json_issues(json_candidate)
            try:
                return json.loads(json_candidate)
            except:
                pass
    
    # Method 3: Look for array responses
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')
    
    if first_bracket >= 0 and last_bracket > first_bracket:
        json_candidate = text[first_bracket:last_bracket + 1]
        try:
            return json.loads(json_candidate)
        except:
            pass
    
    # If all methods fail, raise informative error
    raise ValueError(
        f"Could not extract valid JSON from response. "
        f"Response started with: {text[:200]}..."
    )

def fix_common_json_issues(json_str: str) -> str:
    """Fix common JSON formatting issues."""
    
    # Fix trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix single quotes (Claude sometimes uses them)
    # But be careful not to break quoted strings
    # This is tricky - maybe skip for safety
    
    # Fix unescaped newlines in strings
    json_str = re.sub(r'("(?:[^"\\]|\\.)*")', 
                      lambda m: m.group(0).replace('\n', '\\n'), 
                      json_str)
    
    return json_str
```

## Additional Improvements

1. **Better error messages**:
```python
except json.JSONDecodeError as e:
    raise ValueError(
        f"JSON parsing failed at line {e.lineno}, column {e.colno}: {e.msg}\n"
        f"Near: ...{json_str[max(0, e.pos-50):e.pos+50]}..."
    )
```

2. **Validation mode**:
```python
result = await cc_execute(prompt, json_mode=True, validate_schema=schema)
# Ensures result matches expected structure
```

3. **Fallback to text**:
```python
result = await cc_execute(prompt, json_mode=True, fallback_to_text=True)
# Returns {"text": raw_output} if JSON parsing fails
```

## Real Examples That Fail

Example 1:
```
Sure! Here's the processed JSON:

```json
{"sections": [...]}
```
```

Example 2:
```
{"result": "Here's the analysis...", "data": {...}}

Note: 3 transformations were applied.
```

Example 3:
```
{
  "sections": [
    {
      "text": "This has an unescaped
newline"
    }
  ]
}
```

## Testing

```python
test_responses = [
    '```json\n{"valid": true}\n```',
    'Here is the result:\n\n{"valid": true}',
    '{"valid": true}\n\nDone!',
    'Sure!\n\n```json\n{\n  "valid": true\n}\n```\n\nHope this helps!',
]

for response in test_responses:
    result = extract_json_from_response(response)
    assert result == {"valid": True}
```

## Priority

**High** - This affects nearly every json_mode=True call, forcing users to implement their own parsing.

---

**Note from ArXiv MCP Server team**: We've had to wrap every cc_execute call with try/except and custom JSON extraction. A robust built-in solution would save us hundreds of lines of error-prone parsing code.

## Resolution

**Fixed in executor.py** with a new robust `extract_json_from_response()` function that handles all common Claude response formats:

1. **Multiple extraction methods** (tried in order):
   - Uses existing `clean_json_string()` utility first
   - Extracts from markdown code blocks (```json)
   - Finds JSON by brace boundaries { }
   - Handles array responses [ ]
   - Pattern matching for common fields

2. **Common issue fixes** via `fix_common_json_issues()`:
   - Removes trailing commas
   - Fixes unescaped newlines in strings
   - Adds missing commas between objects
   - Removes comments (// and /* */)

3. **Graceful fallback**:
   - Always returns a dict (never throws)
   - Includes parse error information
   - Returns raw text as "result" if all parsing fails

Example handling:
```python
# All of these now parse correctly:
"Here's the JSON:\n```json\n{\"result\": \"test\"}\n```"
"{\"result\": \"test\"}\n\nDone!"
"Sure! {\"data\": \"value\", }"  # trailing comma fixed
```

This eliminates the need for custom parsing code in user applications.