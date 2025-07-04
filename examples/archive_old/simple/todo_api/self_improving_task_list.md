# TODO API Development — Self-Improving Task List

## 📊 TASK LIST METRICS & HISTORY
- **Total Tasks**: 4 (including setup)
- **Completed Successfully**: 0
- **Failed & Improved**: 0
- **Current Success Rate**: 0%
- **Last Updated**: 2025-01-04
- **Status**: Not Started

## 🏛️ CORE PURPOSE (Immutable)
Build a TODO API with full CRUD operations using sequential task execution. Demonstrates cc_execute.md's value through fresh context per task.

## ⚠️ MANDATORY PRE-EXECUTION SETUP

### Task 0: Initialize Environment
**Always execute this FIRST before any other tasks!**

```bash
# Step 1: Activate virtual environment
source .venv/bin/activate

# Step 2: Create and run customized setup script
cat > setup_todo_api.py << 'EOF'
# Read the setup template
from pathlib import Path
template_path = Path.cwd() / 'src/cc_executor/prompts/setup_template.py'
with open(template_path, 'r') as f:
    setup_code = f.read()

# Customize for this task list
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_NAME', 'TODO API Example')

# Write to current directory (will find project root dynamically)
with open('setup_env.py', 'w') as f:
    f.write(setup_code)

# Run the setup
exec(open('setup_env.py').read())
EOF

python setup_todo_api.py
```

## 🤖 TASK DEFINITIONS (Self-Improving)

### Task 1: Create TODO API Structure
**Status**: Not Started  
**Current Definition**: "What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields."  
**Validation**: ✅ Compliant  
**Critique**: Clear requirements, uses relative paths

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

#### Execution Record:
- **Method Used**: cc_execute.md
- **Duration**: TBD
- **Result**: TBD
- **Validation Passed**: TBD

#### cc_execute.md Configuration:
```python
from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

result = execute_task_via_websocket(
    task="What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields.",
    timeout=120,
    tools=["Write"]
)

# Save result to tmp/responses/
import json
from datetime import datetime
output_path = Path("tmp/responses") / f"task1_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
```

### Task 2: Test the API
**Status**: Not Started  
**Current Definition**: "What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all endpoints (GET, POST, DELETE) including edge cases like deleting non-existent todos."  
**Validation**: ✅ Compliant  
**Critique**: Depends on Task 1 output

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

#### Execution Record:
- **Method Used**: cc_execute.md
- **Duration**: TBD
- **Result**: TBD
- **Validation Passed**: TBD

### Task 3: Add Update Feature
**Status**: Not Started  
**Current Definition**: "How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint for updating title and completed status. Include corresponding tests in test_api.py."  
**Validation**: ✅ Compliant  
**Critique**: Builds on previous tasks

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

## 📝 EXECUTION LOG

### Pre-Execution Checklist:
- [ ] Virtual environment activated
- [ ] Setup script executed successfully
- [ ] Working directory is project root
- [ ] tmp/responses/ directory exists
- [ ] All tasks in question format

### Execution Session: [To be filled]

## 🔄 SELF-IMPROVEMENT PROTOCOL

### Auto-Fix Rules:
```python
def validate_and_fix_task(task_def):
    """Auto-fix common task definition issues."""
    fixes = []
    
    # Fix: Not a question
    if not task_def.strip().endswith("?"):
        # Find the main verb and convert to question
        if "Create" in task_def:
            task_def = task_def.replace("Create", "What is the implementation of")
        elif "Add" in task_def:
            task_def = task_def.replace("Add", "How can I add")
        elif "Write" in task_def:
            task_def = task_def.replace("Write", "What tests are needed for")
        
        if not task_def.endswith("?"):
            task_def = task_def.rstrip(".") + "?"
        fixes.append("Converted to question format")
    
    # Fix: Absolute paths (convert to relative)
    if "/home/" in task_def:
        task_def = task_def.replace("/home/graham/workspace/experiments/cc_executor/", "")
        fixes.append("Converted absolute paths to relative")
    
    # Fix: Missing file extensions
    if "main" in task_def and "main.py" not in task_def:
        task_def = task_def.replace("main", "main.py")
        fixes.append("Added .py extension")
    
    return task_def, fixes
```

### Failure Recovery Strategies:
| Failure Type | Recovery Strategy |
|--------------|-------------------|
| "Module not found" | Check PYTHONPATH, re-run setup |
| "Path does not exist" | Create parent directories first |
| "Timeout exceeded" | Increase timeout, simplify task |
| "Tool not allowed" | Add tool to cc_execute.md call |
| "Ambiguous prompt" | Add specific examples |

## 🎯 COMPLETION CRITERIA

The task list is COMPLETE when:
- [ ] All tasks executed successfully
- [ ] todo_api/main.py has all 4 CRUD endpoints
- [ ] todo_api/test_api.py has comprehensive tests
- [ ] All tests pass when run with pytest
- [ ] Results saved to tmp/responses/

## 🔍 DEBUGGING PATTERNS

### When ANY task fails:
1. **FIRST**: Check execution logs in tmp/responses/
2. **SECOND**: Use both research tools concurrently:
   ```python
   # Run both queries in parallel
   from concurrent.futures import ThreadPoolExecutor
   with ThreadPoolExecutor() as executor:
       perplexity_future = executor.submit(perplexity_ask, "FastAPI TypeError solutions")
       gemini_future = executor.submit(ask_gemini, "FastAPI best practices 2025")
   ```
3. **THIRD**: Only ask human after autonomous debugging

### Common Issues:
- Import errors → Ensure PYTHONPATH is set
- Path not found → Check working directory with `pwd`
- Timeout → Start with smaller scope, increase incrementally

## 📋 FINAL CHECKLIST

- [ ] Setup completed (Task 0)
- [ ] All tasks completed successfully
- [ ] Generated code follows FastAPI patterns
- [ ] Tests cover edge cases
- [ ] No hardcoded values
- [ ] All results in tmp/responses/