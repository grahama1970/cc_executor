# Task Assignment Template for Orchestrator

## Purpose
When creating task files for executors, use this template to ensure executors know they must return results in the proper format.

## Task File Structure
```json
{
  "review_id": "XXX_component_name",
  "component": "component_name",
  "date": "YYYY-MM-DD",
  "assigned_to": "executor_name",
  "instructions": "Executor must add 'result' node to each fix - see EXECUTOR_RESPONSE_TEMPLATE.md",
  "fixes": [
    {
      "id": 1,
      "severity": "critical|major|minor",
      "file": "path/to/file.py",
      "line": 123,
      "issue": "Description of the problem",
      "fix": "What needs to be done",
      "verification": "How to verify the fix works"
    }
  ]
}
```

## Instructions to Include
Always add this instruction field to make expectations clear:
```json
"instructions": "Add 'result' node to each fix with: status, changes_made, problems_encountered, solution, verification_command, and hallucination_check. Update THIS file, do not create a separate results file."
```

## Example Complete Task
```json
{
  "review_id": "001_websocket_security",
  "component": "websocket_handler",
  "date": "2025-06-26",
  "assigned_to": "Claude",
  "instructions": "Add 'result' node to each fix per EXECUTOR_RESPONSE_TEMPLATE.md",
  "fixes": [
    {
      "id": 1,
      "severity": "critical",
      "file": "core/websocket_handler.py",
      "line": 45,
      "issue": "No authentication on WebSocket connection",
      "fix": "Add origin checking and optional token validation",
      "verification": "Connection from unauthorized origin should be rejected"
    }
  ]
}
```

## What Executors Must Return
The same JSON file with each fix containing:
```json
{
  "id": 1,
  "severity": "critical",
  "file": "core/websocket_handler.py",
  "line": 45,
  "issue": "No authentication on WebSocket connection",
  "fix": "Add origin checking and optional token validation",
  "verification": "Connection from unauthorized origin should be rejected",
  "result": {
    "status": "FIXED",
    "changes_made": ["Line 45: Added origin check", "Line 50: Added token validation"],
    "problems_encountered": ["Had to find the connection handler first"],
    "solution": "Added middleware to validate origin header",
    "verification_command": "curl -H 'Origin: http://evil.com' ws://localhost:8003/ws/mcp 2>&1 | grep -q '403'",
    "hallucination_check": "grep -n 'check_origin' /path/to/websocket_handler.py"
  }
}
```

## Verification Process
1. Orchestrator assigns task with clear instructions
2. Executor implements and updates the SAME file
3. Orchestrator/Human runs verification_command for each fix
4. Orchestrator/Human runs hallucination_check to ensure changes exist
5. Task is marked complete only if all commands pass