# CC Executor Quick Start Guide

## ⚠️ IMPORTANT: CC Executor is for Sequential Task Lists

**CC Executor is designed for executing MULTIPLE RELATED TASKS in sequence**, not individual calls.

If you just need to run a single Claude command, use the Claude CLI directly. CC Executor's value is in:
- Maintaining context across multiple tasks
- Sequential execution with fresh 200K context for each task
- Preventing context contamination between tasks
- Anti-hallucination hooks across a workflow

## For Developers Using CC Executor in Their Projects

### Option 1: Install from GitHub (Recommended for Now)

Add to your `pyproject.toml`:
```toml
[project.dependencies]
cc-executor = { git = "https://github.com/grahama1970/cc_executor.git", branch = "master" }
```

Or with pip:
```bash
pip install git+https://github.com/grahama1970/cc_executor.git
```

### Option 2: Install from PyPI (Coming Soon)

Once published to PyPI:
```bash
pip install cc-executor
```

### Using the Python API

CC Executor provides a simple Python API for single tasks, workflows, and concurrent execution:

```python
from cc_executor.client.cc_execute import cc_execute
import asyncio

# Single task (simple string response)
async def example():
    result = await cc_execute("Create a Python function to calculate fibonacci")
    print(result)

asyncio.run(example())

# Single task with JSON mode (structured response)
async def json_example():
    result = await cc_execute(
        "Create a FastAPI endpoint for user registration",
        json_mode=True  # Returns dict with 'result', 'files_created', etc.
    )
    print(f"Files created: {result['files_created']}")
    print(f"Summary: {result['summary']}")

asyncio.run(json_example())

# For multi-task workflows
from cc_executor.client.cc_execute import cc_execute_task_list

async def task_list_example():
    tasks = [
        "Task 1: Create a FastAPI project structure with user authentication",
        "Task 2: Set up SQLAlchemy models for users and sessions",
        "Task 3: Implement JWT authentication endpoints",
        "Task 4: Add middleware for auth validation",
        "Task 5: Create unit tests for all auth endpoints"
    ]
    
    # Execute all tasks sequentially
    results = await cc_execute_task_list(tasks)
    
    # Check results (results is a list of strings)
    for i, result in enumerate(results):
        # Truncate long results for display
        display_result = result if len(result) < 50 else result[:50] + "..."
        print(f"✅ Task {i+1} completed: {display_result}")

asyncio.run(task_list_example())

# Concurrent execution with controlled parallelism
async def concurrent_example():
    """Execute multiple independent tasks concurrently with rate limiting."""
    from asyncio import Semaphore, gather, as_completed
    from tqdm.asyncio import tqdm
    
    # Tasks that can run independently
    tasks = [
        "Generate a README for a Python project",
        "Create a GitHub Actions workflow for CI/CD",
        "Write unit tests for a calculator module",
        "Generate API documentation in OpenAPI format",
        "Create a Docker compose file for a web app",
        "Write a contributing guide for open source",
        "Generate SQL migration scripts",
        "Create a security policy document"
    ]
    
    # Limit concurrent executions to prevent overload
    semaphore = Semaphore(3)  # Max 3 concurrent cc_execute calls
    
    async def execute_with_limit(task: str, index: int):
        async with semaphore:
            result = await cc_execute(task)
            return {"task": task, "index": index, "result": result}
    
    # Create all tasks
    coroutines = [execute_with_limit(task, i) for i, task in enumerate(tasks)]
    
    # Execute with progress bar
    results = []
    async for future in tqdm(as_completed(coroutines), total=len(tasks), desc="Processing"):
        result = await future
        results.append(result)
        print(f"✅ Completed task {result['index']+1}: {result['task'][:40]}...")
    
    # Sort results back to original order
    results.sort(key=lambda x: x['index'])
    return results

asyncio.run(concurrent_example())

# Batch processing with gather
async def batch_example():
    """Process tasks in batches using asyncio.gather."""
    tasks = [
        "Analyze code complexity for module A",
        "Analyze code complexity for module B", 
        "Analyze code complexity for module C",
        "Analyze code complexity for module D"
    ]
    
    batch_size = 2
    results = []
    
    # Process in batches
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"\n🔄 Processing batch {i//batch_size + 1}...")
        
        # Execute batch concurrently
        batch_results = await gather(*[cc_execute(task) for task in batch])
        results.extend(batch_results)
        
        print(f"✅ Batch {i//batch_size + 1} complete")
    
    return results

asyncio.run(batch_example())
```

## Recent Updates (v1.3.0)

### 🧠 Intelligent Timeout Prediction (Now Default!)
- **RedisTaskTimer**: Sophisticated ML-style timeout prediction is now the default
- **Task Classification**: Automatically categorizes tasks (calculation, code, data, general, file)
- **Complexity Assessment**: Determines task complexity (trivial, low, medium, high, extreme)
- **Historical Learning**: Learns from past executions to improve timeout predictions
- **90th Percentile**: Uses outlier-resistant calculations for reliable timeouts
- **System Load Awareness**: Adjusts timeouts based on current system load

### 🧹 Project Cleanup
- Temporary files moved to `archive/temp_files_20250109/`
- Cleaner project root for better maintainability
- All core functionality preserved

## Basic Usage - Task List Execution

### 1. Sequential Task List Execution (Primary Use Case)

```python
import asyncio
from cc_executor.client.client import WebSocketClient

async def execute_task_list(task_list_path: str):
    """Execute a multi-step task list maintaining context."""
    # WebSocketClient connects to an already-running server
    client = WebSocketClient(host="localhost", port=8003)
    
    # Execute each task in sequence with fresh context
    tasks = [
        "Task 1: Set up the Django project structure with authentication",
        "Task 2: Create the user model with custom fields", 
        "Task 3: Implement the authentication views and templates",
        "Task 4: Add tests for the authentication flow",
        "Task 5: Create API endpoints for user management"
    ]
    
    results = []
    for i, task in enumerate(tasks, 1):
        print(f"\n📋 Executing task {i}/{len(tasks)}: {task[:50]}...")
        
        # Each task gets fresh 200K context but maintains workflow coherence
        result = await client.execute_command(
            f'claude -p --task-file task_{i}.md "{task}"'
        )
        results.append(result)
        
        if result['exit_code'] != 0:
            print(f"❌ Task {i} failed")
            break
    
    return results

# Execute a complete workflow
results = asyncio.run(execute_task_list("django_auth_tasks.md"))
print(f"✅ Completed {len(results)} tasks")
```

### 2. Using the WebSocket Client

```python
import asyncio
from cc_executor.client.client import WebSocketClient

async def main():
    # Connect to running server
    client = WebSocketClient(host="localhost", port=8003)
    
    # Execute command via WebSocket
    result = await client.execute_command("echo 'Hello World'")
    print(f"Exit code: {result['exit_code']}")
    print(f"Output: {result['output_data']}")

asyncio.run(main())
```

### 3. Using the CLI

```bash
# Start the server
cc-executor server start

# Run a command
cc-executor run "ls -la"

# Check server status
cc-executor server status
```

## When to Use CC Executor

✅ **USE CC Executor when you have:**
- Multiple related tasks that need sequential execution
- Complex workflows that would exceed Claude's context window
- Tasks that need fresh context to avoid confusion
- Multi-step code generation or refactoring projects

❌ **DON'T USE CC Executor for:**
- Single one-off Claude queries (just use `claude -p` directly)
- Simple questions or explanations
- Tasks that fit easily in one context

## Minimal Setup Requirements

1. **Python 3.10+**
2. **Redis** (recommended for timeout prediction, will fallback to simple estimates if not available)
3. **Claude Code** (cc-executor calls the Claude CLI under the hood)

## Environment Variables (Optional)

```bash
# Optional Redis URL (defaults to localhost)
export REDIS_URL=redis://localhost:6379

# Optional shell preference (defaults to zsh)
export CC_EXECUTOR_SHELL=bash

# For Docker deployments - disable venv wrapping
export DISABLE_VENV_WRAPPING=1
```

## MCP (Model Context Protocol) Support

CC Executor now supports MCP for easier tool integration:

```python
# 1. Start the WebSocket server with MCP support
cc-executor server start

# 2. The MCP manifest is automatically available at:
# http://localhost:8001/.well-known/mcp/cc-executor.json

# 3. Configure Claude or other LLMs to use CC Executor:
# Add to .mcp.json in your project:
{
  "tools": {
    "cc-executor": {
      "server_url": "ws://localhost:8003/ws/mcp"
    }
  }
}

# 4. Use in Claude:
# "Use cc-executor to run these tasks:
#  Task 1: Create a FastAPI app
#  Task 2: Add authentication
#  Task 3: Write tests"
```

## That's It!

No complex configuration needed. CC Executor handles:
- ✅ Automatic UUID4 anti-hallucination hooks
- ✅ Intelligent timeout prediction with RedisTaskTimer (default)
- ✅ Token limit detection and retry
- ✅ Session management with Redis fallback
- ✅ Process control and streaming output
- ✅ Task execution history tracking and learning

## Examples

Check out the `examples/` directory for more usage patterns:
- `basic_usage/` - Simple task execution
- `with_error_recovery/` - Error handling examples
- `with_hooks/` - Custom hook integration
- `advanced_usage/` - Complex multi-step workflows