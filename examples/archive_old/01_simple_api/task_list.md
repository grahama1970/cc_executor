# Simple API Task List

Build a TODO API step by step using cc_execute.md for each task.

## Task 1: Create Models
Use ./prompts/cc_execute.md to create models.py with a Pydantic Todo model containing id (int), title (str), and completed (bool) fields.

## Task 2: Create API  
Use ./prompts/cc_execute.md to read models.py and create api.py with FastAPI endpoints for GET /todos and POST /todos using in-memory storage.

## Task 3: Create Tests
Use ./prompts/cc_execute.md to read both models.py and api.py, then create test_api.py with pytest tests for both endpoints.

## Task 4: Create Documentation
Use ./prompts/cc_execute.md to read all previous files and create README.md with API usage examples and setup instructions.