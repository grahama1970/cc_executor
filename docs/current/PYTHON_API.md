# CC Executor Python API Documentation

## Overview

The Python API provides direct programmatic access to CC Executor without needing a WebSocket server.

## Installation

```bash
pip install cc-executor
```

## Quick Start

```python
from cc_executor.client.cc_execute import cc_execute

# Simple usage - synchronous, returns string
result = cc_execute("What is 2+2?")
print(result)  # "4"

# With JSON mode - returns structured data
result = cc_execute("Create a TODO list app", json_mode=True)
print(result['files_created'])  # List of created files
print(result['summary'])        # Summary of what was done
```

## API Reference

### cc_execute()

Execute a single task with Claude.

```python
def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,
    return_json: Optional[bool] = None,  # Deprecated
    generate_report: bool = False,
    amend_prompt: bool = False,
    validation_prompt: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: Optional[int] = None,
    execution_uuid: Optional[str] = None
) -> Union[str, Dict[str, Any]]
```

**Parameters:**
- `task`: The task/prompt to execute
- `config`: Optional configuration object
- `stream`: Stream output in real-time (default: True)
- `json_mode`: Return structured JSON response (default: False)
- `return_json`: **Deprecated** - use `json_mode` instead
- `generate_report`: Generate execution assessment report (default: False)
- `amend_prompt`: Automatically fix problematic prompts (default: False)
- `validation_prompt`: Optional validation prompt to check the response. Use {response} placeholder.
                     Spawns fresh Claude instance to validate. Only works with json_mode=True.
                     No internal retry - orchestrator handles retry logic.
- `session_id`: Track execution in a specific session (default: auto-generated)
- `timeout`: Override timeout in seconds (default: smart estimation based on task)
- `execution_uuid`: Provide specific UUID for anti-hallucination verification

**Returns:**
- String response (default) 
- Dictionary with structured data (if `json_mode=True`):
  ```python
  {
      "result": str,               # Main output/answer
      "files_created": List[str],  # Files created during execution
      "files_modified": List[str], # Files modified
      "summary": str,              # Brief summary of what was done
      "execution_uuid": str,       # UUID for verification
      # If validation_prompt provided:
      "validation": dict,          # Validation response
      "is_valid": bool            # True if validation passed (defaults to True on errors)
  }
  ```

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

1. **Use json_mode=True** for programmatic processing (returns structured data)
2. **Enable streaming** for long-running tasks to see progress
3. **Set appropriate timeouts** for complex tasks
4. **Use amend_prompt=True** to automatically fix problematic prompts
5. **Generate reports** for important tasks to verify execution

## Key Features

### Robust JSON Parsing
When using `json_mode=True`, CC Executor automatically handles:
- Markdown-wrapped JSON (````json ... ````)
- Malformed JSON that can be repaired
- Mixed text and JSON content
- Nested JSON structures

### Non-Blocking Execution
All subprocess operations use async patterns to prevent blocking:
- WebSocket server remains responsive during execution
- Multiple concurrent connections supported
- Hooks execute without freezing the event loop

### Smart Timeout Estimation
CC Executor analyzes your task and estimates appropriate timeouts:
- Simple queries: 30-60 seconds
- Code generation: 60-120 seconds
- Complex refactoring: 120-300 seconds
- Override with `timeout` parameter when needed

## Differences from MCP Server

| Feature | Python API | MCP Server |
|---------|------------|------------|
| Setup | Import and use | Start server first |
| Protocol | Direct subprocess | WebSocket + JSON-RPC |
| Use Case | Python applications | AI agent orchestration |
| Streaming | Optional | Always enabled |
| Control | Function calls | PAUSE/RESUME/CANCEL |
