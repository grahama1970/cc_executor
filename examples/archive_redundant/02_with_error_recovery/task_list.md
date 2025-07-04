# TODO API with Error Recovery

This task list includes error recovery helpers and learning from past failures.

## Setup Requirements

```bash
# Always run first
source .venv/bin/activate
uv pip install fastapi uvicorn pytest httpx
```

## Tasks

### Task 1: Create API with Error Handling

What is the implementation of a FastAPI TODO application with proper error handling? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints using in-memory storage.

**Common Errors & Fixes:**
- **Import Error**: `from fastapi import FastAPI, HTTPException` (not just FastAPI)
- **Missing validation**: Use Pydantic models for request/response
- **No error handling**: Return 404 for missing todos

**Past Attempts:**
- v1: Failed - forgot HTTPException import
- v2: Failed - no input validation  
- v3: Success ✓ - included all imports and validation

**Timeout**: 120s (increase if adding more features)

### Task 2: Write Comprehensive Tests

What tests are needed for the TODO API including error cases? Read todo_api/main.py and create todo_api/test_api.py with pytest tests covering all endpoints and error scenarios.

**Common Errors & Fixes:**
- **Import path**: Use `from main import app` (not `from todo_api.main`)
- **Client setup**: Use `TestClient` from fastapi.testclient
- **Async issues**: Tests should be sync when using TestClient

**Past Attempts:**
- v1: Failed - wrong import path
- v2: Success ✓ - fixed imports

**Timeout**: 120s

### Task 3: Add Update with Validation

How can I add a robust update endpoint? Read existing files and add PUT /todos/{id} with:
- Request validation
- 404 for missing IDs
- Partial updates support
- Comprehensive tests

**Common Errors & Fixes:**
- **Partial updates**: Use `Optional` fields in update model
- **Validation**: Separate model for updates vs creation
- **Test coverage**: Test both success and error cases

**Timeout**: 150s (complex feature)

## Error Recovery Configuration

### Retry Policy
- Max retries: 3
- Backoff: exponential (5s, 10s, 20s)
- On failure: Apply documented fixes

### Learning Mode
- Track all errors in `.error_recovery.json`
- Update task list with new error patterns
- Share solutions across similar tasks

## Execution Notes

1. **Pre-flight Check**: Verify all dependencies installed
2. **Monitor Execution**: Watch for import/syntax errors
3. **Auto-retry**: Failed tasks retry with fixes
4. **Knowledge Base**: Errors saved for future runs