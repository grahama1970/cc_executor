# CC Executor Hook Integration with Logger Agent Dashboard

## Overview

This document explains how to integrate CC Executor's hooks with the Logger Agent Dashboard to capture all Pre/Post tool use events and display them in real-time.

## Hook Flow

```
Claude Code (in CC Executor)
    ↓
CC Executor Hook System
    ↓
.claude/settings.json (hooks configuration)
    ↓
send_event.py (Logger Agent hook script)
    ↓
Logger Agent Dashboard API (port 8000)
    ↓
ArangoDB (storage + graph relationships)
    ↓
Vue Dashboard (port 5173) - Real-time display
```

## Setup Instructions

### 1. Ensure Logger Agent Dashboard is Set Up

```bash
cd /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent
./scripts/setup_dashboard.sh
```

### 2. Run Integration Script

```bash
./scripts/integrate_cc_executor.sh
```

This script:
- Copies hook configuration to CC Executor
- Creates symlinks to Logger Agent hooks
- Sets up environment variables

### 3. Start Logger Agent Dashboard

```bash
cd /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent
./scripts/start_dashboard_background.sh
```

### 4. Verify Integration

In CC Executor directory:
```bash
cd /home/graham/workspace/experiments/cc_executor

# Check hooks are configured
cat .claude/settings.json

# Test with a simple command
claude "list files in the current directory"
```

## Hook Configuration Details

The `.claude/settings.json` in CC Executor will contain:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.claude/hooks/send_event.py --source-app cc-executor --event-type PreToolUse"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.claude/hooks/send_event.py --source-app cc-executor --event-type PostToolUse"
      }]
    }]
  }
}
```

## What Gets Logged

### PreToolUse Events
- Tool name (Bash, Read, Write, etc.)
- Tool input parameters
- Session ID
- Timestamp
- Source app (cc-executor)

### PostToolUse Events
- Tool execution results
- Exit codes
- Output data
- Execution time
- Error messages (if any)

## Viewing Events in Dashboard

1. Open http://localhost:5173
2. Events appear in real-time as Claude executes
3. Filter by:
   - Source App: `cc-executor`
   - Event Type: `PreToolUse`, `PostToolUse`
   - Session ID: Specific Claude session
4. Search using BM25:
   - `error` - Find all errors
   - `tool:Bash pytest` - Find pytest executions
   - `"import error"` - Exact phrase search

## Graph Relationships Created

When CC Executor triggers hooks, the following graph nodes and relationships are created:

### Nodes
- **agent_sessions**: Each Claude session
- **tool_executions**: Each tool use (Bash, Read, etc.)
- **errors_and_failures**: Any errors that occur
- **code_artifacts**: Files created/modified

### Edges
- **agent_flow**: Sequence of tool executions
- **error_causality**: Links errors to their causes
- **tool_dependencies**: Shows which tools depend on others

## Troubleshooting

### Events Not Appearing

1. **Check Dashboard is Running**:
   ```bash
   ./scripts/status_dashboard.sh
   ```

2. **Verify Hooks Configuration**:
   ```bash
   cat /home/graham/workspace/experiments/cc_executor/.claude/settings.json
   ```

3. **Test Hook Manually**:
   ```bash
   echo '{"tool_name": "test", "session_id": "test123"}' | \
   uv run /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.claude/hooks/send_event.py \
   --source-app cc-executor --event-type PreToolUse
   ```

4. **Check API Logs**:
   ```bash
   tail -f /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/logs/dashboard/api_server.log
   ```

### Permission Issues

Ensure the hook script is executable:
```bash
chmod +x /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.claude/hooks/send_event.py
```

### Port Conflicts

If ports 8000 or 5173 are in use:
```bash
# Find what's using the port
lsof -i:8000
lsof -i:5173

# Kill the process or change ports in configuration
```

## Advanced Usage

### Custom Event Types

Add custom hooks for CC Executor specific events:

```json
{
  "hooks": {
    "TaskExecution": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run /path/to/send_event.py --source-app cc-executor --event-type TaskExecution"
      }]
    }]
  }
}
```

### Filtering CC Executor Events

In the dashboard, create saved filters:
- CC Executor Errors: `source:cc-executor AND error`
- Python Executions: `source:cc-executor AND tool:Bash AND python`
- File Operations: `source:cc-executor AND (tool:Read OR tool:Write)`

### Analyzing Execution Patterns

Use the graph view to:
1. See tool execution sequences
2. Identify common error patterns
3. Find performance bottlenecks
4. Track file modifications

## Benefits

1. **Real-time Monitoring**: See what Claude is doing as it happens
2. **Error Tracking**: Quickly identify and debug failures
3. **Performance Analysis**: Measure tool execution times
4. **Audit Trail**: Complete history of all operations
5. **Pattern Discovery**: Learn from past executions

The integration provides complete observability into CC Executor's operations through the Logger Agent Dashboard!