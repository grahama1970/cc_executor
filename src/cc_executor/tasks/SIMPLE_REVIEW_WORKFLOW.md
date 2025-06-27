# Simple O3-Claude Review Workflow

## Directory Structure

```
tasks/
├── orchestrator/           # O3's feedback and task lists
│   ├── T01_review.md      # O3's review of T01
│   └── T01_fixes.json     # Structured fix tasks
│
├── executor/              # Claude's implementations
│   ├── T01_implementation.py
│   └── T01_prompt.md
│
└── *.py                   # Completed implementations
```

## Simple Workflow

### 1. Claude implements in executor/
```bash
# Create implementation
vim tasks/executor/T01_implementation.py
vim tasks/executor/T01_prompt.md
```

### 2. O3 reviews and creates tasks in orchestrator/
```bash
# O3 creates review files
tasks/orchestrator/T01_review.md     # Human-readable feedback
tasks/orchestrator/T01_fixes.json    # Structured tasks
```

### 3. Claude fixes based on tasks
```bash
# Read O3's tasks
cat tasks/orchestrator/T01_fixes.json

# Update implementation
vim tasks/executor/T01_implementation.py

# When complete, move to tasks/
mv tasks/executor/T01_implementation.py tasks/
```

## Fix Task Format (T01_fixes.json)

```json
{
  "component": "T01_robust_logging",
  "fixes": [
    {
      "id": 1,
      "severity": "critical",
      "issue": "Missing error handling in line 45",
      "fix": "Add try-except block"
    }
  ]
}
```

## That's it! Simple and effective.