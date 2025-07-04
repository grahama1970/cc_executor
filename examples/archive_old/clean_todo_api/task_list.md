# TODO API Task List

A clean example showing cc_executor's sequential task execution.

## Setup

```bash
# From project root
source .venv/bin/activate

# Create working directories
mkdir -p examples/clean_todo_api/tmp/responses
mkdir -p examples/clean_todo_api/reports
cd examples/clean_todo_api
```

## Task Execution

### Task 1: Create API
```python
from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

result = execute_task_via_websocket(
    task="What is a simple FastAPI TODO application? Create main.py with GET /todos and POST /todos endpoints using in-memory list storage.",
    timeout=60,
    tools=["Write"]
)

# Save result
import json
with open("tmp/responses/task1_result.json", "w") as f:
    json.dump(result, f, indent=2)
```

### Task 2: Create Tests
```python
result = execute_task_via_websocket(
    task="What tests verify the TODO API works? Read main.py and create test_api.py with pytest tests for both endpoints.",
    timeout=60,
    tools=["Read", "Write"]
)

# Save result
with open("tmp/responses/task2_result.json", "w") as f:
    json.dump(result, f, indent=2)
```

### Task 3: Add Documentation
```python
result = execute_task_via_websocket(
    task="What documentation helps developers use this API? Read main.py and test_api.py, then create README.md with usage examples.",
    timeout=60,
    tools=["Read", "Write"]
)

# Save result
with open("tmp/responses/task3_result.json", "w") as f:
    json.dump(result, f, indent=2)
```

## Expected Results

After running all tasks:
- `main.py` - FastAPI TODO application
- `test_api.py` - Comprehensive tests
- `README.md` - API documentation
- `tmp/responses/` - Execution results for each task
- `reports/` - Final execution report (from post-hook)