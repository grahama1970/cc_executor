# Basic Usage Example

This example demonstrates the simplest use of CC Executor - sequential task execution with cc_execute.

## What This Example Does

Builds a TODO API in 3 sequential steps:
1. Creates the FastAPI application
2. Writes comprehensive tests
3. Adds an update feature

Each task uses cc_execute for:
- Fresh 200K context per task
- Automatic UUID4 verification
- Error recovery with retries
- WebSocket reliability

## Running the Example

```bash
# From this directory
python run_example.py

# Or from project root
python examples/basic_usage/run_example.py
```

## Expected Output

```
==============================================================
CC Executor - Basic Usage Example
Building a TODO API in 3 sequential tasks
==============================================================

==============================================================
Task 1: Create API
==============================================================
🔐 Pre-hook: Generated execution UUID: a4f5c2d1-...
[CC_EXECUTE] Task modified with UUID4 requirements
[CC_EXECUTE] Calling websocket_handler.py...

🔐 UUID Verification: PASSED

✅ Task completed: success (attempts: 1)
   Output saved to: tmp/responses/task_1_20250704_120000.json
```

## Files Created

After successful execution:
```
todo_api/
├── main.py        # FastAPI application
└── test_api.py    # Pytest tests
```

## Understanding the Output

Check `tmp/responses/` for detailed JSON:
- Each task's full output
- UUID4 verification status  
- Execution attempts
- Error messages (if any)

Look for the `execution_uuid` at the END of each JSON file - this proves the task actually ran.

## Key Points

1. **All tasks use cc_execute** - Simple approach for learning
2. **UUID4 is automatic** - No configuration needed
3. **Sequential execution** - Task 2 waits for Task 1
4. **Fresh context** - Each task starts clean

## Why cc_execute for Everything?

In this basic example, we use cc_execute for all tasks to demonstrate:
- How it works
- What it provides (UUID4, retries, WebSocket)
- When you might need it

In production, you'd optimize by using direct execution for simple tasks (see advanced_usage).

## Next Steps

- Modify `task_list.md` to build something different
- Check the `advanced_usage` example for optimization patterns
- Create your own sequential workflows