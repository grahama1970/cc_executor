# CC Executor Examples

This directory contains working examples demonstrating cc_executor capabilities.

## Directory Structure

```
examples/
├── simple/                    # Basic examples for quick understanding
│   └── todo_api/             # Simple TODO API demonstration
│       ├── task_list.md      # Task definitions
│       ├── run_example.py    # Script to execute tasks
│       └── tmp/              # Outputs and logs
│           └── responses/    # JSON results
└── advanced/                  # Complex workflows
    └── redis_cache/          # Research → Build → Review workflow
        ├── task_list.md      # Full self-improving format
        ├── run_example.py    # Orchestration script
        └── tmp/              
            └── responses/    # Results and logs
```

## Quick Start

### Simple Example (TODO API)
```bash
cd examples/simple/todo_api
python run_example.py
```
This builds a TODO API in 3 steps, demonstrating sequential execution with fresh context per task.

### Advanced Example (Redis Cache)
```bash
cd examples/advanced/redis_cache
python run_example.py
```
This shows a full workflow with external tools: Research → Build → Review → Improve.

## Key Concepts Demonstrated

1. **Sequential Execution**: Each task waits for the previous one
2. **Fresh Context**: Each task gets 200K tokens
3. **No Pollution**: Tasks don't see each other's generation process
4. **Tool Integration**: MCP tools, LiteLLM, etc. (advanced example)

## Output Organization

Each example maintains its own `tmp/responses/` directory:
- Execution results as timestamped JSON
- Generated code in appropriate directories
- No pollution of the examples directory

## Notes

- Examples in README are simplified for clarity
- Full production formats with self-improvement features are in the actual task_list.md files
- Error recovery and retries are built into the execution scripts