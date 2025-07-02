# Execute Web Project Tasks Using cc_execute.md

This demonstrates using cc_execute.md to run tasks with Claude Code instances.

## How to Use

For each task below, execute it using the cc_execute.md prompt:

```bash
claude -p "Use your ./cc_execute.md prompt to [task description here]"
```

---

## Task 1: Create Project Structure

```bash
claude -p "Use your ./cc_execute.md prompt to create a Python script that sets up a web project directory structure with folders: templates, static, src, and tests. Success criteria: 1) Must use os.makedirs or Path.mkdir, 2) Creates all four directories, 3) Handles existing directories gracefully, 4) Includes executable main block"
```

**Expected**: Python script that creates the directory structure

---

## Task 2: Create FastAPI Health Endpoint

```bash
claude -p "Use your ./cc_execute.md prompt to create a FastAPI application with a /health endpoint returning {status: ok, timestamp: current_time}. Success criteria: 1) FastAPI import and app initialization, 2) GET /health endpoint defined, 3) Returns JSON with status and timestamp, 4) Includes uvicorn.run in main block"
```

**Expected**: Complete FastAPI app with health check

---

## Task 3: Create Todo Model

```bash
claude -p "Use your ./cc_execute.md prompt to create a SQLAlchemy Todo model with fields: id (Integer primary key), title (String 200), description (Text), completed (Boolean default False), created_at (DateTime default now). Success criteria: 1) All SQLAlchemy imports included, 2) Todo class defined with Base, 3) All five fields with correct types, 4) Includes __repr__ method"
```

**Expected**: Complete SQLAlchemy model definition

---

## Task 4: Create Docker Configuration  

```bash
claude -p "Use your ./cc_execute.md prompt to create a Dockerfile for Python 3.10 FastAPI app with multi-stage build and docker-compose.yml. Success criteria: 1) FROM python:3.10-slim base, 2) Multi-stage build pattern, 3) EXPOSE 8000, 4) CMD with uvicorn, 5) docker-compose.yml with app service"
```

**Expected**: Dockerfile and docker-compose.yml

---

## Task 5: Create Unit Tests

```bash
claude -p "Use your ./cc_execute.md prompt to create pytest tests for a FastAPI /todos endpoint covering GET, POST, and DELETE operations. Success criteria: 1) TestClient import from fastapi.testclient, 2) Test function for each operation, 3) Proper assertions for status codes, 4) Test data setup"
```

**Expected**: Complete pytest test suite

---

## Batch Execution Script

To run all tasks sequentially:

```bash
#!/bin/bash
# execute_all_tasks.sh

echo "Task 1: Project Structure"
claude -p "Use your ./cc_execute.md prompt to create a Python script that sets up a web project directory structure with folders: templates, static, src, and tests. Success criteria: 1) Must use os.makedirs or Path.mkdir, 2) Creates all four directories, 3) Handles existing directories gracefully, 4) Includes executable main block"

echo -e "\n\nTask 2: FastAPI Health"  
claude -p "Use your ./cc_execute.md prompt to create a FastAPI application with a /health endpoint returning {status: ok, timestamp: current_time}. Success criteria: 1) FastAPI import and app initialization, 2) GET /health endpoint defined, 3) Returns JSON with status and timestamp, 4) Includes uvicorn.run in main block"

echo -e "\n\nTask 3: Todo Model"
claude -p "Use your ./cc_execute.md prompt to create a SQLAlchemy Todo model with fields: id (Integer primary key), title (String 200), description (Text), completed (Boolean default False), created_at (DateTime default now). Success criteria: 1) All SQLAlchemy imports included, 2) Todo class defined with Base, 3) All five fields with correct types, 4) Includes __repr__ method"

echo -e "\n\nTask 4: Docker Config"
claude -p "Use your ./cc_execute.md prompt to create a Dockerfile for Python 3.10 FastAPI app with multi-stage build and docker-compose.yml. Success criteria: 1) FROM python:3.10-slim base, 2) Multi-stage build pattern, 3) EXPOSE 8000, 4) CMD with uvicorn, 5) docker-compose.yml with app service"

echo -e "\n\nTask 5: Unit Tests"
claude -p "Use your ./cc_execute.md prompt to create pytest tests for a FastAPI /todos endpoint covering GET, POST, and DELETE operations. Success criteria: 1) TestClient import from fastapi.testclient, 2) Test function for each operation, 3) Proper assertions for status codes, 4) Test data setup"
```

---

## Verification

After each task, cc_execute.md will:
1. Execute the request via WebSocket  
2. Perform Stage 1 evaluation (internal)
3. Return structured results for Stage 2 evaluation (orchestrator)

The two-stage evaluation ensures quality outputs that meet all criteria.