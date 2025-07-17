# Hook Best Practices for Comprehensive Logging

## Overview

The logger_agent dashboard can capture much more than basic event metadata. This guide shows how to configure hooks for maximum observability.

## Available Hook Events

### 1. PreToolUse
Fired before any tool execution. Captures:
- Tool name and parameters
- Session context
- User intent

### 2. PostToolUse
Fired after tool execution. Should capture:
- **Raw tool output** (stdout, stderr, return codes)
- **Full file contents** (for Read operations)
- **Diffs and changes** (for Edit/Write operations)
- **Execution time and performance metrics**

### 3. Stop
Fired when agent completes a task. Should capture:
- **Final response to user**
- **Token usage statistics**
- **Tools used during session**
- **Total execution time**

### 4. AgentResponse (Custom)
New event type for capturing agent's messages to users:
- **Full response text**
- **Code blocks included**
- **Response type** (explanation, code, error, etc.)

### 5. Error
Captures failures and exceptions:
- **Full error messages and stack traces**
- **Context when error occurred**
- **Recovery attempts**

## Enhanced Configuration

### 1. Update ArangoDB Schema

Add collections for raw data:

```javascript
// In ArangoDB
db._create("raw_responses", {
  // Store full tool outputs
  schema: {
    rule: {
      type: "object",
      properties: {
        event_id: { type: "string" },
        tool_name: { type: "string" },
        raw_output: { type: "object" },
        timestamp: { type: "string" }
      }
    }
  }
});

db._create("agent_messages", {
  // Store what Claude writes to users
  schema: {
    rule: {
      type: "object",
      properties: {
        session_id: { type: "string" },
        message: { type: "string" },
        message_type: { type: "string" },
        includes_code: { type: "boolean" },
        timestamp: { type: "string" }
      }
    }
  }
});
```

### 2. Update Dashboard API

Enhance the dashboard server to handle raw data:

```python
@app.post("/events/raw")
async def receive_raw_event(request: Request):
    """Handle events with full raw data."""
    event_data = await request.json()
    
    # Store in appropriate collection based on event type
    if event_data["event_type"] == "PostToolUse":
        collection = "raw_responses"
    elif event_data["event_type"] == "AgentResponse":
        collection = "agent_messages"
    else:
        collection = "log_events"
    
    # Store with full raw data
    await manager.store_raw_event(event_data, collection)
    
    return {"status": "success"}
```

### 3. Configure Claude Code Settings

Use the enhanced configuration:

```bash
# Copy enhanced settings to Claude Code config
cp /home/graham/workspace/experiments/cc_executor/.claude/settings_enhanced.json \
   ~/.claude/settings.json
```

### 4. Enable Comprehensive Capture

Set environment variables for maximum capture:

```bash
export CLAUDE_CAPTURE_RAW_RESPONSES=true
export CLAUDE_LOG_LEVEL=debug
export CLAUDE_INCLUDE_EXECUTION_CONTEXT=true
```

## Usage Examples

### Example 1: Capturing Bash Output

When Claude runs a bash command, the full output is captured:

```json
{
  "event_type": "PostToolUse",
  "tool_name": "Bash",
  "raw_output": {
    "command": "pytest tests/ -v",
    "stdout": "============================= test session starts ==============================\nplatform linux -- Python 3.10.11, pytest-7.4.0\ncollected 15 items\n\ntests/test_api.py::test_create_user PASSED                               [  6%]\ntests/test_api.py::test_get_user PASSED                                 [ 13%]\n...",
    "stderr": "",
    "return_code": 0,
    "duration_ms": 2340
  }
}
```

### Example 2: Capturing File Edits

When Claude edits a file, capture the full diff:

```json
{
  "event_type": "PostToolUse",
  "tool_name": "Edit",
  "raw_output": {
    "file_path": "/src/main.py",
    "diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -10,7 +10,7 @@\n-def calculate():\n+def calculate_total():\n     return sum(values)",
    "changes_made": {
      "lines_added": 1,
      "lines_removed": 1,
      "functions_modified": ["calculate"]
    }
  }
}
```

### Example 3: Capturing Agent Responses

Capture what Claude actually tells the user:

```json
{
  "event_type": "AgentResponse",
  "response_content": {
    "message": "I've successfully refactored the calculate function to calculate_total for better clarity. The function now:\n\n1. Has a more descriptive name\n2. Maintains the same functionality\n3. All tests are still passing\n\nThe change has been applied to `/src/main.py`.",
    "response_type": "explanation",
    "includes_code": false
  }
}
```

## Benefits

1. **Complete Audit Trail**: Every action and response is logged
2. **Debugging**: Full context when things go wrong
3. **Learning**: Analyze patterns in successful vs failed executions
4. **Compliance**: Complete record of all changes made
5. **Performance Analysis**: Track execution times and resource usage

## Best Practices

1. **Storage Management**: Raw responses can be large. Implement retention policies:
   ```python
   # Prune old raw responses after 30 days
   await manager.prune_raw_responses(older_than_days=30)
   ```

2. **Selective Capture**: For sensitive projects, filter what gets logged:
   ```python
   # In hook script
   if "password" in raw_output or "secret" in raw_output:
       raw_output = "[REDACTED]"
   ```

3. **Compression**: Compress large outputs before storage:
   ```python
   import gzip
   compressed = gzip.compress(raw_output.encode())
   ```

4. **Real-time Analysis**: Use WebSocket for live monitoring:
   ```javascript
   ws.onmessage = (event) => {
     const data = JSON.parse(event.data);
     if (data.raw_output && data.tool_name === "Bash") {
       // Display live command output
       terminal.write(data.raw_output.stdout);
     }
   };
   ```

## Testing Enhanced Hooks

Test the enhanced capture:

```bash
cd /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent
python .claude/hooks/capture_raw_responses.py working
```

## Future Enhancements

1. **Replay Capability**: Re-run exact tool sequences
2. **Diff Visualization**: Visual diff viewer in dashboard
3. **Pattern Detection**: ML-based analysis of successful patterns
4. **Export Formats**: Export sessions as Jupyter notebooks
5. **Collaboration**: Share and annotate agent sessions