# Web Project Tasks List Using cc_execute.md

**Instructions**: Each task should be executed using the cc_execute.md prompt pattern. The orchestrator will run these sequentially through WebSocket connections.

## Task 1: Initialize Project Structure

Use cc_execute.md to execute the following:
- **Prompt**: "What is a Python script that creates a web project directory structure with folders: templates, static, src, and tests? Include complete executable code."
- **Success Criteria**:
  1. Must use os.makedirs or Path.mkdir
  2. Creates all four directories 
  3. Handles existing directories gracefully
  4. Includes if __name__ == "__main__" block
- **Timeout**: Let Redis decide
- **Category**: project_setup

## Task 2: Create FastAPI Application

Use cc_execute.md to execute the following:
- **Prompt**: "What is a FastAPI application with a /health endpoint that returns {status: ok, timestamp: current_time}? Include all imports and uvicorn run code."
- **Success Criteria**:
  1. FastAPI import and app = FastAPI()
  2. GET /health endpoint defined
  3. Returns JSON with status and timestamp
  4. Includes uvicorn.run in main block
- **Timeout**: Let Redis decide
- **Category**: api_development

## Task 3: Create Database Models

Use cc_execute.md to execute the following:
- **Prompt**: "What is a SQLAlchemy Todo model with fields: id (Integer primary key), title (String 200), description (Text), completed (Boolean default False), created_at (DateTime default now)? Show all imports and base setup."
- **Success Criteria**:
  1. All SQLAlchemy imports included
  2. Todo class inherits from Base
  3. All five fields with correct types
  4. Includes __repr__ or __str__ method
- **Timeout**: Let Redis decide
- **Category**: database

## Task 4: Create API CRUD Endpoints

Use cc_execute.md to execute the following:
- **Prompt**: "What are FastAPI CRUD endpoints for todos? Include: GET /todos (list all), POST /todos (create), GET /todos/{id} (get one), DELETE /todos/{id}. Use Pydantic models for request/response."
- **Success Criteria**:
  1. All four CRUD endpoints defined
  2. Pydantic models for TodoCreate and TodoResponse
  3. Proper HTTP status codes
  4. Error handling for not found
- **Timeout**: Let Redis decide
- **Category**: api_development

## Task 5: Create Docker Configuration

Use cc_execute.md to execute the following:
- **Prompt**: "What is a Dockerfile for Python 3.10 FastAPI app? Include multi-stage build, requirements.txt handling, port 8000 exposure, and uvicorn CMD. Also show docker-compose.yml."
- **Success Criteria**:
  1. FROM python:3.10-slim base
  2. COPY requirements.txt and pip install
  3. EXPOSE 8000
  4. CMD with uvicorn command
  5. docker-compose.yml included
- **Timeout**: Let Redis decide
- **Category**: deployment

## Task 6: Create Unit Tests

Use cc_execute.md to execute the following:
- **Prompt**: "What are pytest unit tests for FastAPI /todos endpoints? Test: list todos, create todo, get specific todo, delete todo. Use TestClient and include all imports."
- **Success Criteria**:
  1. TestClient imported from fastapi.testclient
  2. Test functions for all operations
  3. Proper assertions on status codes
  4. Test data setup included
- **Timeout**: Let Redis decide
- **Category**: testing

## Task 7: Create Environment Configuration

Use cc_execute.md to execute the following:
- **Prompt**: "What is a pydantic Settings class for environment configuration? Include: DATABASE_URL, API_HOST, API_PORT, DEBUG_MODE, SECRET_KEY. Show .env file loading and example .env content."
- **Success Criteria**:
  1. Pydantic Settings class used
  2. All five config fields defined
  3. Shows .env file loading
  4. Example .env content provided
- **Timeout**: Let Redis decide
- **Category**: configuration

## Task 8: Create README Documentation

Use cc_execute.md to execute the following:
- **Prompt**: "What is a README.md for a FastAPI todo application? Include sections: Overview, Features, Installation, Usage, API Endpoints, Testing, Docker Deployment. Use proper markdown."
- **Success Criteria**:
  1. All seven sections included
  2. Proper markdown formatting
  3. Code blocks for commands
  4. Clear instructions throughout
- **Timeout**: Let Redis decide
- **Category**: documentation

## Task 9: Create GitHub Actions CI/CD

Use cc_execute.md to execute the following:
- **Prompt**: "What is a GitHub Actions workflow.yml for Python FastAPI CI/CD? Include jobs: run tests (pytest), lint (ruff), build Docker image. Use ubuntu-latest runner."
- **Success Criteria**:
  1. Valid GitHub Actions YAML syntax
  2. Test job with pytest
  3. Lint job with ruff
  4. Docker build job
  5. Uses ubuntu-latest
- **Timeout**: Let Redis decide
- **Category**: ci_cd

## Task 10: Create API Client Library

Use cc_execute.md to execute the following:
- **Prompt**: "What is a Python client library for the todo API? Include a TodoClient class with methods for all CRUD operations using httpx. Show usage example."
- **Success Criteria**:
  1. TodoClient class defined
  2. Methods for all CRUD operations
  3. Uses httpx for requests
  4. Usage example in main block
- **Timeout**: Let Redis decide
- **Category**: client_sdk

---

## Orchestrator Instructions

When executing these tasks:

1. For each task, use cc_execute.md pattern:
   - Pass the prompt and success criteria
   - Let Redis determine timeout unless specified
   - Evaluate response using two-stage pattern

2. Between tasks:
   - Log completion status
   - Save outputs to files
   - Brief pause before next task

3. After all tasks:
   - Generate summary report
   - Show success/failure rates
   - Total execution time