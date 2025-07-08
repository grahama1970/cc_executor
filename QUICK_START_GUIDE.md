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

### Then Use It For Task Lists (NOT Individual Calls!)

⚠️ **CRITICAL**: CC Executor exists specifically for multi-task workflows. Using it for single calls defeats its entire purpose.

```python
from cc_executor import cc_execute_task_list

# Define your multi-step workflow
tasks = [
    "Task 1: Create a FastAPI project structure with user authentication",
    "Task 2: Set up SQLAlchemy models for users and sessions",
    "Task 3: Implement JWT authentication endpoints",
    "Task 4: Add middleware for auth validation",
    "Task 5: Create unit tests for all auth endpoints"
]

# Execute all tasks sequentially
results = cc_execute_task_list(tasks)

# Check results
for i, result in enumerate(results):
    status = "✅" if result['exit_code'] == 0 else "❌"
    print(f"{status} Task {i+1}: {result['task'][:50]}...")
```

## Basic Usage - Task List Execution

### 1. Sequential Task List Execution (Primary Use Case)

```python
import asyncio
from cc_executor import WebSocketClient

async def execute_task_list(task_list_path: str):
    """Execute a multi-step task list maintaining context."""
    client = WebSocketClient()
    await client.connect()
    
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
    
    await client.disconnect()
    return results

# Execute a complete workflow
results = asyncio.run(execute_task_list("django_auth_tasks.md"))
print(f"✅ Completed {len(results)} tasks")
```

### 2. Using the WebSocket Client

```python
import asyncio
from cc_executor.client import WebSocketClient

async def main():
    client = WebSocketClient()
    await client.connect()
    
    # Execute command
    result = await client.execute_command("echo 'Hello World'")
    print(f"Exit code: {result['exit_code']}")
    
    await client.disconnect()

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
2. **Redis** (optional, will fallback to in-memory if not available)
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
- ✅ Token limit detection and retry
- ✅ Session management with Redis fallback
- ✅ Process control and streaming output

## Examples

Check out the `examples/` directory for more usage patterns:
- `basic_usage/` - Simple task execution
- `with_error_recovery/` - Error handling examples
- `with_hooks/` - Custom hook integration
- `advanced_usage/` - Complex multi-step workflows