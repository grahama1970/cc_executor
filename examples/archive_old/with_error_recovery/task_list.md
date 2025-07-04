# API Task List with Error Recovery

## Task 1: Create API
Use `src/cc_executor/prompts/cc_execute.md` to create a FastAPI application in api.py.

### Common Errors & Fixes:
- **Import error**: Run `uv pip install fastapi` first
- **Timeout**: Increase to 120s for complex APIs
- **File exists**: Use Edit tool instead of Write

### Past Failures:
- v1: Failed - forgot to import HTTPException (fixed in v2)
- v2: Success ✓

## Task 2: Create Tests  
Use `src/cc_executor/prompts/cc_execute.md` to create comprehensive tests in test_api.py.

### Common Errors & Fixes:
- **Module not found**: Ensure PYTHONPATH includes current directory
- **Test discovery fails**: Name file `test_*.py` not `*_test.py`

## Task 3: Run Tests
Use `bash` to run: `pytest test_api.py -v`

### Common Errors & Fixes:
- **pytest not found**: Run `uv pip install pytest` first
- **Import errors**: Check that api.py exists from Task 1