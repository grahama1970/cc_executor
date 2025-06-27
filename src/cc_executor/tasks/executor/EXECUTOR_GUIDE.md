# Unified Executor Guide

## Overview
This guide consolidates all executor instructions into one clear document. When you receive tasks from the orchestrator, follow this guide.

## Directory Structure
```
executor/
├── incoming/    # Tasks from orchestrator
└── outgoing/    # Completed tasks to orchestrator
```

## Workflow

### 1. Receive Task File
Check `executor/incoming/` for new task files from orchestrator:
```json
{
  "review_id": "005_stress_test_system",
  "component": "stress_test_system",
  "fixes": [
    {
      "id": 1,
      "file": "core/websocket_handler.py",
      "line": 65,
      "issue": "Description of problem",
      "fix": "What to do",
      "verification": "How to test"
    }
  ]
}
```

### 2. Implement Fixes
For each fix in the JSON:
1. Navigate to the specified file and line
2. Implement the exact fix described
3. Test using the verification method
4. Update the JSON with results

### 3. Add Results to Original JSON
**CRITICAL**: Update the task file IN PLACE by adding a "result" node to each fix:

```json
{
  "id": 1,
  "file": "core/websocket_handler.py",
  "line": 65,
  "issue": "Description of problem",
  "fix": "What to do",
  "verification": "How to test",
  "result": {
    "status": "FIXED|NO_CHANGE_NEEDED|ALREADY_IMPLEMENTED|PARTIALLY_FIXED|FAILED",
    "finding": "What you discovered (if no change needed)",
    "changes_made": [
      "Line X: Changed Y to Z",
      "Line A: Added B"
    ],
    "problems_encountered": [
      "Issue faced and how resolved"
    ],
    "solution": "How you implemented the fix",
    "verification_command": "bash command to verify",
    "hallucination_check": "bash command to prove changes exist"
  }
}
```

### 4. Status Definitions
- **FIXED**: Implemented as requested
- **NO_CHANGE_NEEDED**: Code already correct
- **ALREADY_IMPLEMENTED**: Feature exists
- **PARTIALLY_FIXED**: Some aspects fixed
- **FAILED**: Could not implement

### 5. Verification Requirements

#### Each verification_command must:
- Be a single bash/zsh command
- Work from any directory
- Produce clear pass/fail output
- Be copy-pasteable

#### Each hallucination_check must:
- Prove the change was made
- Show file contents or grep results
- Fail if change wasn't made

### 6. Priority Order
Fix in this order:
1. **critical** - Crashes, data loss
2. **major** - Reliability issues
3. **minor** - Nice to have

### 7. Complexity Check
Before implementing, ask:
1. Is this solving a real problem?
2. Does this add brittleness?
3. Is there a simpler solution?

If unsure, use:
```python
mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"Is {fix_description} necessary for a dev tool, or over-engineering?"
    }]
})
```

### 8. Common Patterns

#### Process Cleanup
```python
try:
    proc = await asyncio.create_subprocess_exec(...)
finally:
    if proc and proc.returncode is None:
        proc.terminate()
        await proc.wait()
```

#### Buffer Limits
```python
if len(self.buffer) < MAX_LINES and self.total_size < MAX_SIZE:
    self.buffer.append(line)
else:
    self.dropped_lines += 1
```

### 9. Code Standards

Follow CODE_STANDARDS.md for all Python code:
- Max 500 lines per file
- Documentation header with third-party links
- Example input/output
- Usage function with real data
- Type hints on all functions
- Use loguru for logging

### 10. After Completion

#### Run File Checks
```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/check_file_rules.py modified_file.py
```

#### Verify No Hallucination
```bash
MARKER="TASK_$(date +%Y%m%d_%H%M%S)"
echo "$MARKER: Completed task"
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py "$MARKER"
```

## Example Complete Response

Original task:
```json
{
  "id": 1,
  "file": "tests/stress/websocket_test_executor.py",
  "issue": "Test expects wrong notification format",
  "fix": "Change 'output' to 'process.output'"
}
```

With result added:
```json
{
  "id": 1,
  "file": "tests/stress/websocket_test_executor.py",
  "issue": "Test expects wrong notification format",
  "fix": "Change 'output' to 'process.output'",
  "result": {
    "status": "FIXED",
    "changes_made": [
      "Line 67: Changed 'output' to 'process.output'",
      "Line 160: Updated extract method"
    ],
    "problems_encountered": [
      "Had to find all occurrences of the pattern"
    ],
    "solution": "Used grep to find all instances, then Edit tool to fix",
    "verification_command": "cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress && grep -n 'process.output' websocket_test_executor.py",
    "hallucination_check": "cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress && sed -n '67p' websocket_test_executor.py | grep 'process.output'"
  }
}
```

## DO NOT
- Create separate results files
- Bundle commands into scripts
- Claim success without verification
- Skip hallucination checks
- Add unnecessary complexity

## Remember
- Update the task file in place
- Each fix needs working verification commands
- Test the exact scenario identified
- Document what you actually did

## Submission

When complete, move the file to outgoing:
```bash
mv executor/incoming/XXX_component_fixes.json executor/outgoing/
```

The orchestrator will pick it up from there.