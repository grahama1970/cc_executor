# Executor Task Directory

## Essential Files (Keep These)

### 1. `UNIFIED_EXECUTOR_GUIDE.md`
**The main guide for executors.** Contains:
- How to process task files from orchestrator
- Required "result" node format
- Verification command requirements
- Common code patterns

### 2. `NAMING_CONVENTION.md`
**File naming rules.** Format: `{SEQUENCE}_{FOCUS_AREA}_{TYPE}.{ext}`

### 3. Task Files (`XXX_*_fixes.json`)
**Actual work assignments** from orchestrator with your results added.

## What Executors Do

1. **Receive** task file from orchestrator (e.g., `005_stress_test_system_fixes.json`)
2. **Implement** each fix listed
3. **Update** the SAME file by adding "result" to each fix
4. **Verify** with working bash commands

## Example Result Format

```json
"result": {
  "status": "FIXED",
  "changes_made": ["Line 67: Changed X to Y"],
  "verification_command": "grep -n 'process.output' file.py",
  "hallucination_check": "sed -n '67p' file.py | grep 'process.output'"
}
```