# Orchestrator Guide

## Overview
This guide explains how orchestrators (O3/Claude) create task assignments for executors and verify completed work.

## Directory Structure
```
orchestrator/
├── outgoing/    # Tasks you create for executor
└── incoming/    # Completed tasks from executor
```

## Workflow

### 1. Identify Issues to Fix
Review code and identify specific bugs, issues, or improvements needed.

### 2. Create Task File
Create a JSON file in `orchestrator/outgoing/` following the naming convention: `{SEQUENCE}_{FOCUS_AREA}_fixes.json`

```json
{
  "review_id": "005_stress_test_system",
  "component": "stress_test_system",
  "date": "2025-06-26",
  "assigned_to": "executor",
  "instructions": "Add 'result' node to each fix with status, changes_made, verification_command, and hallucination_check. Update THIS file, do not create separate results file.",
  "fixes": [
    {
      "id": 1,
      "severity": "critical|major|minor",
      "file": "path/to/file.py",
      "line": 123,
      "issue": "Clear description of the problem",
      "fix": "Specific instructions on what to change",
      "verification": "How to test that the fix works"
    }
  ]
}
```

### 3. Severity Levels
- **critical**: Crashes, data loss, security issues
- **major**: Reliability problems, performance issues
- **minor**: Code quality, nice-to-have improvements

### 4. Writing Good Fix Instructions

#### Bad Example:
```json
{
  "issue": "Code is messy",
  "fix": "Clean it up"
}
```

#### Good Example:
```json
{
  "issue": "WebSocket disconnect leaves orphaned processes",
  "fix": "Add finally block to websocket_handler.py line 185 that calls process.terminate() and process.wait()",
  "verification": "Start long process, disconnect WebSocket, verify no orphan processes with 'ps aux | grep [process]'"
}
```

### 5. Getting Completed Tasks

Check `orchestrator/incoming/` for completed tasks. The executor will have updated your JSON file by adding a "result" node to each fix:

```json
{
  "id": 1,
  "severity": "critical",
  "file": "core/websocket_handler.py",
  "line": 185,
  "issue": "WebSocket disconnect leaves orphaned processes",
  "fix": "Add finally block that calls process.terminate() and process.wait()",
  "verification": "Start long process, disconnect WebSocket, verify no orphan processes",
  "result": {
    "status": "FIXED",
    "changes_made": [
      "Line 185: Added try-finally block",
      "Line 192: Added process.terminate() call",
      "Line 193: Added await process.wait()"
    ],
    "problems_encountered": [
      "Had to handle case where process was already None"
    ],
    "solution": "Wrapped existing code in try block, added finally with null check",
    "verification_command": "python3 -c \"import asyncio; asyncio.run(test_orphan_cleanup())\"",
    "hallucination_check": "grep -A5 'finally:' /path/to/websocket_handler.py | grep 'terminate'"
  }
}
```

### 6. Verifying Completed Work

For each fix with a result:

1. **Run verification_command** - Should show the fix works
2. **Run hallucination_check** - Should prove changes exist in code
3. **Check status** - Understand why any fixes weren't completed

### 7. Status Types You'll See
- **FIXED**: Completed as requested
- **NO_CHANGE_NEEDED**: Code was already correct
- **ALREADY_IMPLEMENTED**: Feature already existed
- **PARTIALLY_FIXED**: Some aspects completed
- **FAILED**: Couldn't implement (check problems_encountered)

### 8. Creating Follow-up Tasks

If fixes reveal more issues or some fixes failed:

1. Create new task file with incremented sequence: `006_stress_test_system_fixes.json`
2. Reference previous task in description
3. Include any failed fixes that still need addressing

## Best Practices

### DO:
- Be specific about file paths and line numbers
- Provide clear reproduction steps
- Include expected behavior after fix
- Group related fixes in one task file
- Use appropriate severity levels

### DON'T:
- Create vague fix instructions
- Ask for "refactoring" without specific goals  
- Request complex architectural changes as "fixes"
- Bundle unrelated fixes together
- Skip verification instructions

## Contract with Executors

### You Provide:
1. Clear task file with specific fixes
2. Line numbers and file paths
3. Verification methods

### Executor Provides:
1. Updates to YOUR file (not a new file)
2. Working verification commands
3. Proof that changes were made
4. Explanation of any failures

### Verification Commands Must:
- Be single-line bash/zsh commands
- Work from any directory
- Return clear pass/fail status
- Be copy-pasteable without modification

## Example Task Creation

1. **Identify Problem**: 
   "Stress tests expect HTTP endpoint but service only provides WebSocket"

2. **Create Specific Fix**:
   ```json
   {
     "id": 2,
     "severity": "critical",
     "file": "tests/stress/unified_stress_test_executor_v3.py",
     "line": 85,
     "issue": "Executor uses HTTP POST /stream which is not implemented",
     "fix": "Replace HTTP logic with WebSocket client to ws://localhost:8003/ws/mcp",
     "verification": "Run test and verify it connects successfully"
   }
   ```

3. **Wait for Result**:
   Executor will update the file with implementation details and verification commands

4. **Verify**:
   Run both commands to ensure fix works and code was actually changed

## Consistency Rules

### File Naming
Always follow: `{SEQUENCE}_{FOCUS_AREA}_{TYPE}.{ext}`
- Sequence: 3-digit (001, 002, 003...)
- Focus area: snake_case (websocket_reliability, stress_test_system)
- Type: fixes, review_request, etc.

### Required Fields
Every fix must have:
- `id`: Unique within the file
- `severity`: critical, major, or minor
- `file`: Full path from project root
- `line`: Specific line number (or range)
- `issue`: What's wrong
- `fix`: What to do
- `verification`: How to test

### Code Standards Checks
Also check for violations of CODE_STANDARDS.md:
- Files over 500 lines
- Missing documentation headers
- No usage function
- Missing type hints
- Not using loguru for logging

### Result Fields
Every result must have:
- `status`: One of the 5 defined statuses
- `verification_command`: Working bash command
- `hallucination_check`: Proof of changes
- Either `changes_made` (if fixed) or `finding` (if not)

### Communication
- Keep the same review_id throughout a fix cycle
- Increment sequence for follow-up tasks
- Reference previous tasks in new ones