# Web Project Task List

This task list is for the orchestrator to execute using cc_execute.md.

## Task 1: Project Structure

```
Task: Create a Python script that sets up web project directories
Timeout: 60
Success Criteria:
- Creates templates, static, src, tests folders
- Uses os.makedirs or Path.mkdir
- Handles existing directories gracefully
- Includes if __name__ == "__main__" block
```

## Task 2: FastAPI Health Endpoint

```
Task: Create a FastAPI application with health endpoint
Timeout: 60
Success Criteria:
- Imports FastAPI and creates app instance
- Has GET /health endpoint
- Returns JSON with status and timestamp
- Includes uvicorn.run for running the app
```

## Task 3: SQLAlchemy Todo Model

```
Task: Create SQLAlchemy Todo model
Timeout: 60
Success Criteria:
- Imports all SQLAlchemy requirements
- Defines Todo class with Base
- Has id, title, description, completed, created_at fields
- Includes proper types and constraints
```

## Task 4: Docker Configuration

```
Task: Create Dockerfile for Python FastAPI application
Timeout: 90
Success Criteria:
- Uses FROM python:3.10-slim
- Handles requirements.txt properly
- Exposes port 8000
- Has CMD to run uvicorn
- Includes docker-compose.yml
```

## Task 5: Unit Tests

```
Task: Create pytest tests for todo API
Timeout: 90
Success Criteria:
- Imports TestClient from fastapi
- Tests GET /todos endpoint
- Tests POST /todos endpoint
- Tests DELETE /todos/{id} endpoint
- Uses proper assertions
```

---

## Orchestrator Instructions

For each task above, the orchestrator should:

1. Read the task details
2. Build the cc_execute command:
   ```
   claude -p "Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: [task description]
   Expect a timeout of [timeout] seconds and evaluate results based on:
   [success criteria list]
   If the results fail, retry the task." --output-format stream-json --verbose
   ```
3. Send this command via WebSocket
4. Wait for cc_execute.md to complete (it will spawn another Claude to do the work)
5. Log the results
6. Move to next task