# Build API Example

Creates a complete TODO API step-by-step, demonstrating sequential task dependencies.

## Setup

```bash
cd /home/graham/workspace/experiments/cc_executor
source .venv/bin/activate
cd examples/02_build_api
```

## Tasks

### Task 1: Create Data Models

What data structure should a TODO API use? Create `models.py` with a Pydantic model for Todo items containing id (int), title (str), completed (bool), and created_at (datetime).

### Task 2: Build the API

How do I create a REST API for todos? Read `models.py` and create `api.py` with FastAPI endpoints for: GET /todos (list all), POST /todos (create), GET /todos/{id} (get one), PUT /todos/{id} (update), DELETE /todos/{id} (delete). Use an in-memory list for storage.

### Task 3: Add Tests  

What tests ensure the API works? Read both `models.py` and `api.py`, then create `test_api.py` with pytest tests covering all CRUD operations including edge cases like invalid IDs and missing fields.

### Task 4: Create Documentation

How should developers use this API? Read all previous files and create `API_GUIDE.md` with endpoint documentation, example requests/responses, and a quick start guide.

## Expected Results

A working TODO API with:
- Type-safe data models
- Full CRUD endpoints  
- Comprehensive test suite
- Developer documentation

## Why This Example?

Demonstrates cc_executor's key value:
1. Each task builds on previous work
2. Sequential execution ensures dependencies exist
3. Fresh context prevents confusion
4. Complex project built step-by-step