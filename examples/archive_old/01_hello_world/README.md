# Hello World Example

The simplest possible cc_executor example.

## How to Run

```bash
# From project root
source .venv/bin/activate

# Execute the task list
python src/cc_executor/prompts/cc_execute_utils.py \
    --task-list examples/01_hello_world/task_list.md
```

## What This Demonstrates

1. **Task 1** creates a Python file from scratch
2. **Task 2** reads that file and creates tests for it
3. Each task runs in a fresh Claude instance
4. No pre-written code needed!

## What Gets Created

After running the task list:
- `hello.py` - A greeting function (created by Task 1)
- `test_hello.py` - Tests for that function (created by Task 2)

Both files are created by Claude based on the task descriptions.