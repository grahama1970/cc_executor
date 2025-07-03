# Project Setup Task List

## Task 1: Setup Virtual Environment

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Setup the venv with uv venv --python=3.10.11 .venv. Then source .venv/bin/activate. Expect an execution time using the redis prompt of 90 seconds. Evaluate the response based on calling `which python` to confirm that the python environment is correct. Retry if the task fails.

## Task 2: Install Dependencies

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Install dependencies with uv pip install -e . in the activated venv. Expect a timeout of 120 seconds. Evaluate the response based on: 1) No error messages during installation, 2) Running `uv pip list` shows the project installed. Retry if the task fails.

## Task 3: Create Project Structure

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a basic web project structure with directories for src/app, tests, and docs. Expect a timeout of 60 seconds. Evaluate the response based on verifying all directories exist with `ls -la`. Retry if the task fails.

## Task 4: Create FastAPI App

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a minimal FastAPI application in src/app/main.py with a health endpoint. Expect a timeout of 90 seconds. Evaluate the response based on: 1) File exists at src/app/main.py, 2) Contains FastAPI import and app instance, 3) Has /health endpoint. Retry if the task fails.

## Task 5: Create Basic Test

Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a pytest test in tests/test_main.py that tests the health endpoint. Expect a timeout of 90 seconds. Evaluate the response based on: 1) File exists at tests/test_main.py, 2) Imports TestClient from fastapi, 3) Has test function for health endpoint. Retry if the task fails.