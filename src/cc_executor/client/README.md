# CC Executor Python Client

Python API for executing Claude tasks through cc_executor.

## Usage

```python
from cc_executor.client import cc_execute, cc_execute_list

# Simple execution
result = await cc_execute("What is 2+2?")

# JSON response mode
result = await cc_execute(
    "Write a Python function",
    json_mode=True,
    stream=True
)

# Execute multiple tasks
results = await cc_execute_list([
    "Create a todo list class",
    "Add persistence", 
    "Write tests"
])
```

## Features

- Direct Python API (no WebSocket required)
- Streaming output support
- JSON response mode  
- Task list execution
- Redis-based timeout estimation
- Assessment report generation
- Prompt amendment for reliability

## Differences from MCP Interface

- **MCP**: Used by agents, WebSocket-based, real-time streaming
- **Python Client**: Direct API, subprocess-based, programmatic access
