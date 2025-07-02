# WebSocket Large Output Fix Summary

## Problem
"Generate [large number] word essay" prompts were failing when executed through the cc_executor WebSocket handler but worked fine when called directly in the terminal.

## Root Cause
The WebSocket handler's test commands were missing the `--output-format stream-json` flag that was present in the documentation examples. Without this flag:
- Claude outputs plain text instead of structured JSON
- Large essays create extremely long lines without proper line breaks
- The streaming infrastructure struggles with these massive plain text blocks

## Solution Applied

### 1. Added `--output-format stream-json` Flag
Modified the `build_claude_tests()` function in `websocket_handler.py`:
```python
# Before:
base_cmd = 'claude -p'

# After:
base_cmd = 'claude -p --output-format stream-json'
```

### 2. Increased WebSocket Chunk Size
Increased the chunk size from 4KB to 64KB for more efficient handling:
```python
# Before:
MAX_CHUNK_SIZE = 4096  # 4KB chunks

# After:
MAX_CHUNK_SIZE = 65536  # 64KB chunks
```

## Why This Fixes the Issue

1. **Structured Output**: With `--output-format stream-json`, Claude outputs each part of the response as a separate JSON line, preventing massive single-line outputs.

2. **Better Streaming**: JSON format naturally breaks the output into manageable chunks that align with the streaming infrastructure.

3. **Efficient Chunking**: The larger 64KB chunk size reduces overhead when transmitting large text blocks through WebSocket frames.

## Testing
Created `test_websocket_large_output.py` to verify the fix handles:
- Small outputs (both JSON and plain text)
- Medium outputs (500 word essays)
- Large outputs (2000+ word essays)

## Key Takeaway
Always ensure command-line tools use consistent output formats when integrating with streaming infrastructure. The `--output-format stream-json` flag is essential for Claude CLI when handling large outputs programmatically.