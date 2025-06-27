# Task Workflow

## Visual Flow

```
ORCHESTRATOR                           EXECUTOR
     |                                    |
     |  1. Create XXX_component_fixes.json |
     |------------------------------------>|
     |                                    |
     |                                    | 2. Implement fixes
     |                                    | 3. Add "result" to each fix
     |                                    | 4. Update same JSON file
     |<------------------------------------|
     |                                    |
     | 5. Run verification_command        |
     | 6. Run hallucination_check         |
     | 7. Confirm fixes work               |
     |                                    |
```

## File Structure

```
tasks/
├── WORKFLOW.md                    # This file
├── orchestrator/
│   ├── README.md                 # Quick reference
│   ├── ORCHESTRATOR_GUIDE.md     # Full guide
│   └── XXX_*_fixes.json         # Task files
└── executor/
    ├── README.md                 # Quick reference
    ├── UNIFIED_EXECUTOR_GUIDE.md # Full guide
    └── NAMING_CONVENTION.md      # Shared naming rules
```

## Key Rules

1. **One File**: Executor updates the ORIGINAL task file
2. **Clear Contract**: Each fix has specific requirements
3. **Verifiable**: Every change has two verification commands
4. **Consistent**: Follow naming and format conventions
5. **Code Standards**: All code must follow CODE_STANDARDS.md

## Example Lifecycle

1. **Orchestrator creates**: `005_stress_test_system_fixes.json`
2. **Executor updates**: Adds "result" to each fix in same file
3. **Orchestrator verifies**: Runs commands, confirms fixes
4. **If needed**: Create `006_stress_test_system_fixes.json` for follow-up