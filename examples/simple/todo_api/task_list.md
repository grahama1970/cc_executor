# TODO API - Simple Task List

A straightforward example showing cc_execute.md's sequential task execution.

## Tasks

### Task 1: Create API
**Question**: What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints using in-memory storage.

**Tools**: ["Write"]  
**Timeout**: 120s

### Task 2: Write Tests  
**Question**: What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all endpoints.

**Tools**: ["Read", "Write"]  
**Timeout**: 120s

### Task 3: Add Feature
**Question**: How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint with tests.

**Tools**: ["Read", "Edit"]  
**Timeout**: 150s

## Value Demonstrated

Each task gets fresh 200K context while building on previous outputs. No context pollution between tasks.