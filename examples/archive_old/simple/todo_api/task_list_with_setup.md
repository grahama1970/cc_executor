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

## ⚠️ MANDATORY PRE-EXECUTION VALIDATION
Before executing ANY task:
1. Execute Task 0 (Setup) first
2. Validate each task is in question format
3. Ensure WebSocket server is running
4. Check Python environment is ready

## 🤖 TASK DEFINITIONS (Self-Improving)

### Task 0: Environment Setup (ALWAYS FIRST)
**Status**: Not Started
**Current Definition**: "What setup is needed before running tasks? Execute these commands: 1) source .venv/bin/activate, 2) export PYTHONPATH=./src, 3) Create examples/simple/todo_api/tmp/responses directory, 4) cd to project root /home/graham/workspace/experiments/cc_executor"
**Validation**: ✅ Setup task exempt from question format
**Critique**: Critical setup that enables all other tasks

#### Execution:
```bash
# Run these setup commands
source .venv/bin/activate
export PYTHONPATH=./src
mkdir -p examples/simple/todo_api/tmp/responses
cd /home/graham/workspace/experiments/cc_executor
```

### Task 1: Create TODO API Structure
**Status**: Not Started
**Current Definition**: "What is the implementation of a FastAPI TODO application? Create folder examples/simple/todo_api/todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields."
**Validation**: ✅ Compliant
**Critique**: Uses absolute path from project root

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

#### Execution Record:
- **Method Used**: cc_execute.md
- **Timeout**: 120s
- **Tools**: ["Write"]
- **Duration**: TBD
- **Result**: TBD

### Task 2: Test the API
**Status**: Not Started
**Current Definition**: "What tests are needed for the TODO API in examples/simple/todo_api/todo_api/main.py? Read the implementation and create examples/simple/todo_api/todo_api/test_api.py with pytest tests covering all endpoints (GET, POST, DELETE) including edge cases like deleting non-existent todos."
**Validation**: ✅ Compliant
**Critique**: Clear dependency on Task 1

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

#### Execution Record:
- **Method Used**: cc_execute.md
- **Timeout**: 120s
- **Tools**: ["Read", "Write"]
- **Duration**: TBD
- **Result**: TBD

### Task 3: Add Update Feature
**Status**: Not Started
**Current Definition**: "How can I add update functionality to the TODO API? Read examples/simple/todo_api/todo_api/main.py and examples/simple/todo_api/todo_api/test_api.py, then add PUT /todos/{id} endpoint for updating title and completed status. Include corresponding tests in test_api.py."
**Validation**: ✅ Compliant
**Critique**: Builds on previous tasks

#### Evolution History:
| Version | Definition | Issue | Fix Applied |
|---------|------------|-------|-------------|
| v1 | Current definition | - | - |

#### Execution Record:
- **Method Used**: cc_execute.md
- **Timeout**: 150s
- **Tools**: ["Read", "Edit", "Write"]
- **Duration**: TBD
- **Result**: TBD

## 📝 EXECUTION LOG

### Pre-Execution Checklist:
- [ ] Task 0 (Setup) completed
- [ ] Virtual environment activated
- [ ] PYTHONPATH set to ./src
- [ ] Working directory is project root
- [ ] tmp/responses directory exists

### Execution Session: [To be filled]

## 🔄 SELF-IMPROVEMENT PROTOCOL

### Auto-Fix Rules:
```python
def validate_and_fix_task(task_def):
    fixes = []
    
    # Fix: Ensure absolute paths from project root
    if "todo_api/" in task_def and "examples/simple" not in task_def:
        task_def = task_def.replace("todo_api/", "examples/simple/todo_api/todo_api/")
        fixes.append("Fixed path to be absolute from project root")
    
    # Fix: Add file extensions if missing
    if "main" in task_def and ".py" not in task_def:
        task_def = task_def.replace("main", "main.py")
        fixes.append("Added .py extension")
    
    return task_def, fixes
```

### Failure Recovery Strategies:
| Failure Type | Recovery Strategy |
|--------------|-------------------|
| "Module not found" | Check PYTHONPATH, re-run Task 0 |
| "Path does not exist" | Verify working directory, use absolute paths |
| "Permission denied" | Check file permissions, use different directory |
| "Tool not allowed" | Update cc_execute.md tools list |

## 🎯 COMPLETION CRITERIA

The task list is COMPLETE when:
- [ ] Setup completed successfully
- [ ] todo_api/main.py exists with 4 endpoints
- [ ] todo_api/test_api.py has comprehensive tests
- [ ] All tests pass when run with pytest
- [ ] Results saved to tmp/responses/

## 📋 FINAL CHECKLIST

- [ ] All tasks completed successfully
- [ ] Generated files in correct directories
- [ ] No hardcoded values or security issues
- [ ] Results properly logged to tmp/responses/
- [ ] Can run from project root without path issues