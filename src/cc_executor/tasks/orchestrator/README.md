# Orchestrator Task Directory

## Essential Files

### 1. `ORCHESTRATOR_GUIDE.md`
Complete guide for creating and verifying task assignments.

### 2. `../executor/NAMING_CONVENTION.md`
Shared naming rules: `{SEQUENCE}_{FOCUS_AREA}_{TYPE}.{ext}`

### 3. Task Files (`XXX_*_fixes.json`)
Work assignments you create for executors.

## Quick Reference

### Creating a Task File

```json
{
  "review_id": "006_component_name",
  "component": "component_name",
  "date": "2025-06-26",
  "assigned_to": "executor",
  "instructions": "Add 'result' node to each fix. Update THIS file.",
  "fixes": [
    {
      "id": 1,
      "severity": "critical",
      "file": "path/to/file.py",
      "line": 123,
      "issue": "What's broken",
      "fix": "How to fix it",
      "verification": "How to test it"
    }
  ]
}
```

### What You'll Get Back

Same file with each fix containing:
```json
"result": {
  "status": "FIXED",
  "changes_made": ["Line X: What changed"],
  "verification_command": "bash command that proves it works",
  "hallucination_check": "bash command that proves changes exist"
}
```

### Verification Process

1. Run `verification_command` → Should pass
2. Run `hallucination_check` → Should show changes
3. If status is not "FIXED", check why

## File Organization

```
orchestrator/
├── README.md                           # This file
├── ORCHESTRATOR_GUIDE.md              # Detailed instructions
├── 001_websocket_reliability_fixes.json   # Task assignments
├── 002_process_control_fixes.json         # (with results added)
└── 003_memory_management_fixes.json       # by executor
```