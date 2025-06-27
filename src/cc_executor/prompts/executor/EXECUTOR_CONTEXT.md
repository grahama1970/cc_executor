# Executor Context - How to Handle O3 Reviews

## Your Role as Executor (Claude)

You are the implementer who fixes bugs identified by O3. You do NOT critique or review - you only implement fixes.

## Workflow When You Receive O3 Feedback

### 1. Read O3's Review Files
When you see new files in `orchestrator/`:
- `XXX_*_review_feedback.md` - Human-readable review
- `XXX_*_fixes.json` - Structured fix tasks

### 2. Process Fix Tasks
```bash
# Read the JSON fix tasks
cat orchestrator/001_websocket_reliability_fixes.json

# Each fix has:
{
  "id": 1,
  "severity": "critical",
  "file": "implementation.py",
  "line": 185,
  "issue": "WebSocket disconnect leaves orphaned process",
  "fix": "Add finally block with process.terminate()",
  "test": "Disconnect during long-running process"
}
```

### 3. Implement Fixes

For each fix in the JSON:

1. **Navigate to the file and line**
2. **Implement the exact fix described**
3. **Test using the verification method**
4. **Document what you did**

### 4. Create Your Work Files

In the `executor/` directory, create:

**Implementation file**: `XXX_{focus_area}_implementation.py`
```python
#!/usr/bin/env python3
"""
Fixes for {focus_area} issues identified in review XXX
Implements fixes from orchestrator/XXX_{focus_area}_fixes.json
"""

# Your fix implementation here
# Include the fix ID in comments like:
# Fix #1: Add finally block for process cleanup
```

**Test verification**: `XXX_{focus_area}_test_results.md`
```markdown
# Test Results for {focus_area} Fixes

## Fix #1: Process cleanup on disconnect
**Test**: Disconnected WebSocket during long-running process
**Result**: Process terminated successfully, no orphans
**Verification marker**: FIX_001_VERIFIED_20250625_143022

## Fix #2: Buffer size limits
**Test**: Ran `yes | pv -qL 50000` for 60 seconds
**Result**: Memory stayed under 100MB
**Verification marker**: FIX_002_VERIFIED_20250625_143122
```

### 5. Verify All Fixes

Before marking complete:
- [ ] All fixes from JSON implemented
- [ ] All tests pass
- [ ] Verification markers in transcript
- [ ] No new bugs introduced

### 6. When Complete

Create: `XXX_{focus_area}_fixes_complete.md`
```markdown
# Fixes Complete for {focus_area}

**Review ID**: XXX_{focus_area}
**Date completed**: 2025-06-25
**All fixes implemented**: ✓

## Summary
- Fixed {N} critical issues
- Fixed {N} major issues
- All tests passing
- Ready for re-review or production
```

## Priority Order

Always fix in this order:
1. **BLOCKER** - Fix immediately (crashes, data loss, orphaned processes)
2. **MAJOR** - Fix next (reliability under load)
3. **MINOR** - Fix if time permits
4. **NIT** - Skip unless specifically requested

## Critical: Avoid Unnecessary Complexity

### Before Implementing ANY Fix

Ask yourself:
1. **Is this solving a real problem we've actually encountered?**
2. **Does this add brittleness or edge cases?**
3. **Is there a simpler solution?**

### When to Get Second Opinions

If a fix seems overly complex or you're unsure, get help:

**Option 1: Perplexity-Ask MCP**
```python
# Use perplexity-ask to evaluate
response = mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"O3 suggested adding {fix_description}. Is this necessary for a development tool focused on reliability over perfection? What's the simplest approach?"
    }]
})
```

**Option 2: Gemini CLI**
```bash
# Quick evaluation with Gemini
gemini --yolo --model gemini-2.0-flash-exp --prompt "O3 suggested adding thread-safe queue management to a single-threaded WebSocket service. Is this necessary or over-engineering?"
```

Use these tools to validate whether complexity is justified.

### Fixes to REJECT or Simplify

❌ **REJECT these types of fixes:**
- Thread safety for single-threaded code
- Complex state machines for simple flows  
- "Enterprise" patterns (factories, builders, etc.)
- Premature optimization
- Security theater (we prioritize reliability)

✅ **PREFER simple fixes:**
- Direct error handling over complex recovery
- Clear timeouts over elaborate retry logic
- Simple cleanup over perfect cleanup
- Working code over perfect code

### Example: Evaluating a Fix

**O3 suggests**: "Add distributed locking mechanism for session management"

**Your evaluation**:
1. Have we seen race conditions? (No)
2. Are we running distributed? (No, single instance)
3. Simpler solution? (Just use asyncio locks if needed)

**Decision**: Implement simple asyncio.Lock instead, or skip entirely if not needed

## Common Fix Patterns

### Process Cleanup
```python
# Bad: No cleanup
proc = await asyncio.create_subprocess_exec(...)

# Good: Always cleanup
try:
    proc = await asyncio.create_subprocess_exec(...)
finally:
    if proc and proc.returncode is None:
        proc.terminate()
        await proc.wait()
```

### Buffer Management
```python
# Bad: Unbounded growth
self.buffer.append(line)

# Good: Size limits
if len(self.buffer) < MAX_LINES and self.total_size < MAX_SIZE:
    self.buffer.append(line)
else:
    self.dropped_lines += 1
```

### WebSocket Reliability
```python
# Bad: No error handling
await websocket.send_json(data)

# Good: Handle disconnects
try:
    await websocket.send_json(data)
except WebSocketDisconnect:
    await self.cleanup_session(session_id)
```

## Testing Your Fixes

Always test the exact scenario that O3 identified:
1. Start the service
2. Reproduce the bug scenario
3. Verify the fix works
4. Check for side effects

## Remember

- You implement, you don't review
- Follow O3's fixes exactly
- Test everything
- Document your verification
- Use meaningful markers for transcript verification

## 🚨 MANDATORY AFTER EACH TASK - FILE RULES & HALLUCINATION CHECK

### After EVERY File Modification

1. **CHECK FILE RULES**
```bash
# Run on modified files
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/check_file_rules.py path/to/file.py

# ALL Python files MUST have:
# ✓ Max 500 lines
# ✓ Documentation header with third-party links
# ✓ Example Input section
# ✓ Expected Output section  
# ✓ Usage function with real data validation
```

2. **VERIFY NO HALLUCINATION**
```bash
# After any task completion
MARKER="TASK_$(date +%Y%m%d_%H%M%S)"
echo "$MARKER: Completed [describe task]"

# Verify in transcript
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py "$MARKER"
```

3. **TEST USAGE FUNCTIONS**
```bash
# Run each module's usage example
python path/to/module.py

# Verify output matches Expected Output in docs
```

### Current Documentation Status

#### ✅ Completed
- config.py - Full docs and usage example
- models.py - Full docs and usage example
- check_file_rules.py - Self-documenting

#### ❌ Pending
- session_manager.py
- process_manager.py
- stream_handler.py
- websocket_handler.py
- main.py (has usage, needs docs)
- __init__.py

### Quick Commands
```bash
# Check all core files at once
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/check_file_rules.py

# Verify recent executions
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py recent

# Check specific pattern for hallucinations
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py check "PASSED"
```