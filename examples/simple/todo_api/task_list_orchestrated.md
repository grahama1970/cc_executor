# TODO API Development — Orchestrated Task List

## 📊 TASK LIST METRICS & HISTORY
- **Total Tasks**: 4 (including setup)
- **Completed Successfully**: 0
- **Failed & Improved**: 0
- **Current Success Rate**: 0%
- **Last Updated**: 2025-01-04
- **Status**: Not Started

## 🏛️ CORE PURPOSE (Immutable)
Build a TODO API with full CRUD operations using sequential task execution via cc_execute.md.

## ⚠️ MANDATORY SETUP TASK (Task 0)

### Task 0: Initialize Environment
**Always execute this first!**

1. First, activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Then create and run the setup script:
```python
import os
from pathlib import Path

# First, determine the project root dynamically
current_dir = Path(os.getcwd())
project_root = current_dir

# Look for project markers (pyproject.toml or .git)
while project_root.parent != project_root:
    if (project_root / "pyproject.toml").exists() or (project_root / ".git").exists():
        break
    project_root = project_root.parent

print(f"Found project root: {project_root}")

# Read the setup template from its proper location
template_path = project_root / 'src/cc_executor/prompts/setup_template.py'
with open(template_path, 'r') as f:
    setup_code = f.read()

# Customize for this task list with actual paths
setup_code = setup_code.replace('PLACEHOLDER_PROJECT_ROOT', str(project_root))
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_NAME', 'TODO API Example')
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_PATH', 'examples/simple/todo_api')

# Write customized setup script
with open('examples/simple/todo_api/tmp/setup_todo_api.py', 'w') as f:
    f.write(setup_code)

# Run the setup
exec(open('examples/simple/todo_api/tmp/setup_todo_api.py').read())
```

## 🤖 TASK DEFINITIONS (Orchestrated by You)

### Task 1: Create TODO API Structure
**Method**: cc_execute.md  
**Fresh Context**: Yes (200K tokens)

Use cc_execute.md to answer: "What is the implementation of a FastAPI TODO application? Create folder examples/simple/todo_api/todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields."

**Configuration**:
```python
from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

result = execute_task_via_websocket(
    task="What is the implementation of a FastAPI TODO application? Create folder examples/simple/todo_api/todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields.",
    timeout=120,
    tools=["Write"]
)
```

### Task 2: Test the API
**Method**: cc_execute.md  
**Fresh Context**: Yes (can read Task 1 output)

Use cc_execute.md to answer: "What tests are needed for the TODO API in examples/simple/todo_api/todo_api/main.py? Read the implementation and create examples/simple/todo_api/todo_api/test_api.py with pytest tests covering all endpoints."

**Configuration**:
```python
result = execute_task_via_websocket(
    task="What tests are needed for the TODO API in examples/simple/todo_api/todo_api/main.py? Read the implementation and create examples/simple/todo_api/todo_api/test_api.py with pytest tests covering all endpoints.",
    timeout=120,
    tools=["Read", "Write"]
)
```

### Task 3: Add Update Feature  
**Method**: cc_execute.md  
**Fresh Context**: Yes (can read all previous work)

Use cc_execute.md to answer: "How can I add update functionality to the TODO API? Read examples/simple/todo_api/todo_api/main.py and examples/simple/todo_api/todo_api/test_api.py, then add PUT /todos/{id} endpoint with tests."

**Configuration**:
```python
result = execute_task_via_websocket(
    task="How can I add update functionality to the TODO API? Read examples/simple/todo_api/todo_api/main.py and examples/simple/todo_api/todo_api/test_api.py, then add PUT /todos/{id} endpoint with tests.",
    timeout=150,
    tools=["Read", "Edit"]
)
```

## 📝 EXECUTION INSTRUCTIONS

As the ORCHESTRATOR, you should:

1. **First**: Execute Task 0 to set up the environment
2. **Then**: Execute Tasks 1-3 sequentially using cc_execute.md
3. **Track**: Save results to `tmp/responses/` after each task
4. **Verify**: Check outputs before proceeding to next task

## 🎯 SUCCESS CRITERIA

- [ ] Environment properly initialized (Task 0)
- [ ] API created with 3 endpoints (Task 1)  
- [ ] Tests written and passing (Task 2)
- [ ] PUT endpoint added with tests (Task 3)
- [ ] All results saved to tmp/responses/

## 💡 KEY INSIGHT

Each cc_execute.md call spawns a FRESH Claude instance with 200K context. This is the magic - no context pollution between tasks!