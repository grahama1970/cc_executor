# MCP WebSocket Server Documentation

## Overview

The MCP server enables AI agents to orchestrate complex multi-step workflows using the Model Context Protocol.

## Starting the Server

```bash
# Method 1: Using the CLI
cc-executor start

# Method 2: Direct Python
python -m cc_executor.server

# Method 3: With custom port
cc-executor start --port 8005
```

## Connecting Your Agent

1. Connect to WebSocket endpoint: `ws://localhost:8003/ws/mcp`
2. Use the `cc_execute.md` prompt for orchestration
3. Tasks execute sequentially with fresh context

## How It Works

### The Orchestration Pattern

```
[Main Claude Agent]
    |
    v
[cc_execute.md prompt]
    |
    v
[MCP WebSocket Server]
    |
    +---> [Fresh Claude Instance 1] - Task 1
    |
    +---> [Fresh Claude Instance 2] - Task 2  
    |
    +---> [Fresh Claude Instance 3] - Task 3
```

### Key Benefits

1. **Sequential Execution** - Tasks run in order, not parallel
2. **Fresh Context** - Each task gets full 200K context window
3. **No Pollution** - Clean slate for each subtask
4. **Dependencies** - Task N can use outputs from 1 to N-1

## Using cc_execute.md

The orchestrator uses the special `cc_execute.md` prompt:

```markdown
I need to execute these tasks in order:
1. Create a Python web application
2. Add user authentication
3. Write comprehensive tests

Please use cc_execute.md to orchestrate these tasks.
```

## MCP Protocol Details

### Methods Available

- `execute` - Run a command
- `control` - PAUSE/RESUME/CANCEL execution
- `status` - Get execution status

### Example JSON-RPC Request

```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "command": "claude -p 'Create a REST API'"
  },
  "id": 1
}
```

## Process Control

### Pause Execution
```json
{
  "method": "control",
  "params": {
    "action": "PAUSE",
    "session_id": "abc123"
  }
}
```

### Resume Execution
```json
{
  "method": "control",
  "params": {
    "action": "RESUME",
    "session_id": "abc123"
  }
}
```

### Cancel Execution
```json
{
  "method": "control",
  "params": {
    "action": "CANCEL",
    "session_id": "abc123"
  }
}
```

## Hook System

### UUID Verification Hook

Automatically verifies execution UUIDs to prevent hallucination:

```json
{
  "hooks": {
    "uuid_verification": {
      "enabled": true,
      "fail_on_missing": true
    }
  }
}
```

## Best Practices

1. **Use cc_execute.md** for complex orchestration
2. **Monitor WebSocket** for real-time output
3. **Handle disconnections** gracefully
4. **Set appropriate timeouts** for long tasks
5. **Use process control** for interactive workflows

## Differences from Python API

| Feature | MCP Server | Python API |
|---------|------------|------------|
| Protocol | WebSocket + JSON-RPC | Direct function calls |
| Process Control | PAUSE/RESUME/CANCEL | No (just timeouts) |
| Orchestration | cc_execute.md prompt | Manual sequencing |
| Real-time Streaming | Always | Optional |
| Use Case | AI agents | Python apps |

## Troubleshooting

### Server Won't Start
- Check if port 8003 is already in use
- Ensure Redis is running: `redis-cli ping`

### Connection Refused
- Verify server is running: `cc-executor status`
- Check firewall settings

### Tasks Hanging
- Check Claude CLI is working: `claude --version`
- Verify no ANTHROPIC_API_KEY in environment
- Check browser authentication is active
