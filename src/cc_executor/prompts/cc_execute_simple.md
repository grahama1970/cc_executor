# CC_Execute — Simple Task Executor

> **PURPOSE**: When the orchestrator needs to execute Task N with a fresh Claude instance, use this prompt to spawn it via websocket_handler.py

## How to Use

When you need to execute a task:

```python
# 1. Parse what needs to be done
task = "Your specific task description"
timeout = 120  # or whatever is appropriate

# 2. Build the Claude command
tools = ["Read", "Write", "Edit"]  # Select appropriate tools
tools_str = ",".join(tools)
cmd = f'claude -p "{task}" --output-format stream-json --verbose --allowedTools {tools_str}'

# 3. Execute via websocket_handler
import subprocess
result = subprocess.run(
    ["python", "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py", 
     "--execute", cmd, 
     "--timeout", str(timeout)],
    capture_output=True,
    text=True
)

# 4. Return result to orchestrator
print(result.stdout)
```

## Example

Orchestrator says: "Use cc_execute.md to create a FastAPI app"

```python
task = "Create a FastAPI application in app.py with a root endpoint"
cmd = f'claude -p "{task}" --output-format stream-json --verbose --allowedTools Write'

# Call websocket_handler.py
result = subprocess.run(
    ["python", "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py",
     "--execute", cmd,
     "--timeout", "60"],
    capture_output=True,
    text=True
)
```

That's it! The websocket_handler.py takes care of:
- Managing the WebSocket connection
- Streaming output
- Handling timeouts
- Ensuring sequential execution