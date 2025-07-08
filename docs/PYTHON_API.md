# CC Executor Python API Documentation

## Overview

The Python API provides direct programmatic access to CC Executor without needing a WebSocket server.

## Installation

```bash
pip install cc-executor
```

## Quick Start

```python
from cc_executor.client import cc_execute
import asyncio

async def main():
    result = await cc_execute("What is 2+2?")
    print(result)  # "4"

asyncio.run(main())
```

## API Reference

### cc_execute()

Execute a single task with Claude.

```python
async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    return_json: bool = False,
    generate_report: bool = False,
    amend_prompt: bool = False
) -> Union[str, Dict[str, Any]]
```

**Parameters:**
- `task`: The task/prompt to execute
- `config`: Optional configuration object
- `stream`: Stream output in real-time (default: True)
- `return_json`: Return structured JSON response (default: False)
- `generate_report`: Generate execution assessment report (default: False)
- `amend_prompt`: Automatically fix problematic prompts (default: False)

**Returns:**
- String response (default) or dictionary (if return_json=True)

### cc_execute_list()

Execute multiple tasks sequentially.

```python
async def cc_execute_list(
    tasks: List[str],
    **kwargs
) -> List[Union[str, Dict[str, Any]]]
```

**Parameters:**
- `tasks`: List of tasks to execute in order
- `**kwargs`: Same options as cc_execute()

**Returns:**
- List of results (one per task)

## Examples

### Basic Usage

```python
from cc_executor.client import cc_execute
import asyncio

async def generate_code():
    code = await cc_execute(
        "Write a Python function to validate email addresses"
    )
    print(code)

asyncio.run(generate_code())
```

### JSON Response Mode

```python
result = await cc_execute(
    "Create a user authentication system",
    return_json=True
)

print(result["files_created"])  # List of created files
print(result["summary"])        # Summary of what was done
print(result["execution_uuid"]) # UUID for verification
```

### Sequential Task Execution

```python
tasks = [
    "Create a Flask web application",
    "Add user authentication",
    "Create API endpoints for CRUD operations",
    "Write unit tests",
    "Add Docker configuration"
]

results = await cc_execute_list(tasks, return_json=True)

for i, result in enumerate(results):
    print(f"Task {i+1}: {result['summary']}")
    print(f"Files: {result['files_created']}")
```

### With Progress Monitoring

```python
async def execute_with_progress():
    print("Starting complex task...")
    
    result = await cc_execute(
        "Build a complete REST API with authentication",
        stream=True,  # See output as it's generated
        generate_report=True  # Get detailed report
    )
    
    print(f"\nTask completed!")
    print(f"Result: {result[:200]}...")

asyncio.run(execute_with_progress())
```

## Configuration

```python
from cc_executor.client import CCExecutorConfig

config = CCExecutorConfig(
    timeout=600,  # 10 minutes
    model="claude-3-opus-20240229",
    temperature=0.7
)

result = await cc_execute("Complex task", config=config)
```

## Error Handling

```python
try:
    result = await cc_execute("Invalid task")
except TimeoutError:
    print("Task timed out")
except Exception as e:
    print(f"Error: {e}")
```

## Best Practices

1. **Use return_json=True** for programmatic processing
2. **Enable streaming** for long-running tasks to see progress
3. **Set appropriate timeouts** for complex tasks
4. **Use amend_prompt=True** to automatically fix problematic prompts
5. **Generate reports** for important tasks to verify execution

## Differences from MCP Server

| Feature | Python API | MCP Server |
|---------|------------|------------|
| Setup | Import and use | Start server first |
| Protocol | Direct subprocess | WebSocket + JSON-RPC |
| Use Case | Python applications | AI agent orchestration |
| Streaming | Optional | Always enabled |
| Control | Function calls | PAUSE/RESUME/CANCEL |
