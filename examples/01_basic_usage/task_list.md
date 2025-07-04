# TODO API - Basic Usage Example

This task list demonstrates sequential execution with cc_execute.md.

## Tasks

### Task 1: Create API
What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing:
- GET /todos - list all todos
- POST /todos - create a new todo  
- DELETE /todos/{id} - delete a todo
Use in-memory storage with a simple list.

### Task 2: Write Tests  
What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all three endpoints.

### Task 3: Add Update Feature
How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint with corresponding tests.

## Notes

- Each task uses cc_execute.md automatically
- Tasks run sequentially, building on previous outputs
- Generated files go in todo_api/ directory