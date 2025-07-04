# Basic Usage Example

This example demonstrates the fundamental concept of cc_executor: sequential task execution with fresh context for each task.

## What You'll Learn

- How to write a simple task list that references cc_execute.md
- How tasks build on each other's outputs
- Why fresh context per task is valuable

## The Example

We'll build a simple TODO API in three sequential tasks:
1. Create the API endpoints
2. Write tests for the API
3. Add an update feature

Each task gets a fresh 200K token context window and full model attention.

## Files in This Example

- `task_list.md` - The task definitions
- `run_example.py` - Script to execute the tasks
- After execution: `todo_api/` directory with generated code

## How to Run

```bash
cd examples/01_basic_usage
python run_example.py
```

## Key Concepts Demonstrated

1. **Sequential Execution**: Task 2 waits for Task 1 to complete
2. **File Dependencies**: Task 2 reads files created by Task 1  
3. **Fresh Context**: Each task starts clean, no pollution
4. **cc_execute.md Reference**: Tasks use the standard prompt format