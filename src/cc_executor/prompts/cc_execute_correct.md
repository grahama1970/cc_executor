# CC_Execute — Spawn Fresh Claude via WebSocket Handler

> **PURPOSE**: When the orchestrator needs a fresh Claude instance for Task N, use this prompt to execute it through websocket_handler.py

## The Simple Approach

```python
import subprocess
import sys

# 1. Parse the task
task = "Your specific task here"
timeout = 120  # seconds

# 2. Build the Claude command
tools = ["Read", "Write", "Edit"]  # Select based on task
tools_str = ",".join(tools)
claude_cmd = f'claude -p "{task}" --output-format stream-json --verbose --allowedTools {tools_str}'

# 3. Call websocket_handler.py
# Note: websocket_handler.py needs to support --execute flag
handler_path = "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py"

result = subprocess.run([
    sys.executable,
    handler_path,
    "--execute", claude_cmd,
    "--timeout", str(timeout),
    "--no-server"  # Don't start the server, just execute and exit
], capture_output=True, text=True)

# 4. Return output to orchestrator
print(result.stdout)
if result.stderr:
    print(f"STDERR: {result.stderr}", file=sys.stderr)
```

## What This Does

1. **Orchestrator decides** Task N needs fresh Claude
2. **Builds command** with appropriate tools
3. **Calls websocket_handler.py** which:
   - Manages the WebSocket connection
   - Ensures sequential execution
   - Handles timeouts and streaming
   - Returns when complete
4. **Fresh Claude executes** with 200K context
5. **Results return** to orchestrator

## Why This Works

- The orchestrator maintains workflow state
- Each task gets fresh 200K context
- WebSocket handler ensures completion before returning
- No complex evaluation logic needed here

## Implementation Note

Currently websocket_handler.py doesn't support the `--execute` flag. It needs to be modified to:
1. Accept `--execute "command"` argument
2. Run that command instead of predefined tests
3. Exit after completion (with --no-server)