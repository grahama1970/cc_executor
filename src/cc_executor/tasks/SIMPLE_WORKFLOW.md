# Simple Task Workflow

## Directory Structure
```
tasks/
├── orchestrator/
│   ├── outgoing/     # Tasks TO executor
│   └── incoming/     # Completed tasks FROM executor
└── executor/
    ├── incoming/     # Tasks FROM orchestrator
    └── outgoing/     # Completed tasks TO orchestrator
```

## Workflow

### 1. Orchestrator Creates Task
```bash
# Orchestrator creates:
tasks/orchestrator/outgoing/005_stress_test_fixes.json
```

### 2. Executor Receives Task
```bash
# Copy to executor incoming:
cp orchestrator/outgoing/005_stress_test_fixes.json executor/incoming/

# Or symlink for transparency:
ln -s ../../orchestrator/outgoing/005_stress_test_fixes.json executor/incoming/
```

### 3. Executor Works on Task
```bash
# Edit the file directly in executor/incoming/
# Add "result" node to each fix
```

### 4. Executor Sends Back
```bash
# Move completed file:
mv executor/incoming/005_stress_test_fixes.json executor/outgoing/
```

### 5. Orchestrator Receives
```bash
# Copy to orchestrator incoming:
cp executor/outgoing/005_stress_test_fixes.json orchestrator/incoming/
```

## Benefits
- Clear ownership at each step
- No confusion about where files belong
- Easy to see what's pending (incoming) vs done (outgoing)
- No duplicate files or naming confusion

## Current Mess
We currently have files scattered everywhere because we didn't establish this simple pattern first.