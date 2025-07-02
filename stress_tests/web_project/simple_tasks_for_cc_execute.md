# Web Project Tasks for cc_execute

Each task below should be executed by Claude using cc_execute.md.

## Task 1: Project Structure

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a Python script that sets up web project directories
Expect a timeout of 60 seconds and evaluate results based on:
1. Creates templates, static, src, tests folders
2. Uses os.makedirs or Path.mkdir
3. Handles existing directories gracefully
4. Includes if __name__ == "__main__" block
If the results fail, retry the task.

## Task 2: FastAPI Health

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a FastAPI application with health endpoint
Expect a timeout of 60 seconds and evaluate results based on:
1. Imports FastAPI and creates app instance
2. Has GET /health endpoint
3. Returns JSON with status and timestamp
4. Includes uvicorn.run for running the app
If the results fail, retry the task.

## Task 3: Todo Model

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create SQLAlchemy Todo model
Expect a timeout of 60 seconds and evaluate results based on:
1. Imports all SQLAlchemy requirements
2. Defines Todo class with Base
3. Has id, title, description, completed, created_at fields
4. Includes proper types and constraints
If the results fail, retry the task.

## Task 4: Docker Setup

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create Dockerfile for Python FastAPI application
Expect a timeout of 90 seconds and evaluate results based on:
1. Uses FROM python:3.10-slim
2. Handles requirements.txt properly
3. Exposes port 8000
4. Has CMD to run uvicorn
5. Includes docker-compose.yml
If the results fail, retry the task.

## Task 5: Unit Tests

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create pytest tests for todo API
Expect a timeout of 90 seconds and evaluate results based on:
1. Imports TestClient from fastapi
2. Tests GET /todos endpoint
3. Tests POST /todos endpoint
4. Tests DELETE /todos/{id} endpoint
5. Uses proper assertions
If the results fail, retry the task.