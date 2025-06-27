# Claude Stream JSON Format Analysis

**Date**: 2025-06-24
**Agent**: Claude (Implementer)

## Discovery

The `/execute/claude-stream` endpoint DOES work! It outputs JSON events from `claude --output-format=stream-json`.

## Actual JSON Event Structure

```json
// Tool execution result (this contains our output!)
{"type":"user","message":{"role":"user","content":[{"tool_use_id":"...","type":"tool_result","content":"RESULT:::168","is_error":false}]},...}

// Assistant response
{"type":"assistant","message":{"content":[{"type":"text","text":"168"}]},...}

// Completion event
{"type": "complete", "execution_id": "...", "status": "success", "timestamp": "..."}
```

## The Fix

We need to parse:
1. Events with `type: "user"` that contain `tool_result` - this has the actual command output
2. Events with `type: "assistant"` that contain text responses
3. Events with `type: "complete"` to know when to send COMPLETED status

The current implementation was looking for wrong event types (`text`, `tool_use`) when it should look for `user` and `assistant` events.