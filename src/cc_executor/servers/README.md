# CC-Executor MCP Servers

This directory contains MCP (Model Context Protocol) servers for the cc_executor project.

## Main Server

### `mcp_cc_execute.py` - CC-Orchestration Support Tools

**IMPORTANT**: This server provides orchestration SUPPORT tools, not direct execution!

CC-Executor is designed to be used by a Claude orchestrator managing multi-step task lists. The orchestrator uses cc_execute.md prompts to spawn fresh Claude instances for complex tasks.

**Key Purpose:**
- Help orchestrators analyze and plan task execution
- Provide WebSocket server health monitoring
- Validate task lists before execution
- Suggest optimal execution strategies
- Track execution history for learning

**Available Tools:**

1. **`check_websocket_status()`** - Verify WebSocket server is running
   ```python
   status = await check_websocket_status()
   # Returns: {"status": "running", "port": "8005", "health": {...}}
   ```

2. **`get_task_complexity(task)`** - Analyze task complexity
   ```python
   complexity = await get_task_complexity("Create a FastAPI app")
   # Returns complexity score and execution recommendations
   ```

3. **`validate_task_list(tasks)`** - Pre-flight validation
   ```python
   validation = await validate_task_list([
       "Task 1: Create API",
       "Task 2: Add tests"
   ])
   # Returns validation results, warnings, estimated time
   ```

4. **`monitor_execution(session_id=None)`** - Check running executions
   ```python
   status = await monitor_execution()
   # Returns active sessions and recent activity from logs
   ```

5. **`get_execution_history(limit=10)`** - Review past executions
   ```python
   history = await get_execution_history()
   # Returns execution statistics and success rates
   ```

6. **`get_hook_status()`** - Check hook configuration
   ```python
   hooks = await get_hook_status()
   # Returns hook status and UUID4 verification info
   ```

7. **`suggest_execution_strategy(task_list)`** - Get execution recommendations
   ```python
   strategy = await suggest_execution_strategy(tasks)
   # Returns which tasks should use cc_execute.md vs direct execution
   ```

**Usage Pattern (for Orchestrators):**

```markdown
## Task List Execution Plan

1. Check server status with check_websocket_status()
2. Validate tasks with validate_task_list()
3. Get strategy with suggest_execution_strategy()

For each task:
- If strategy recommends cc_execute.md:
  Use cc_execute.md prompt to spawn fresh Claude instance
- If strategy recommends direct:
  Execute directly in current context
```

**What This Is NOT:**
- NOT a direct execution tool
- NOT a replacement for cc_execute.md
- NOT meant to execute tasks itself

**What This IS:**
- Orchestration support and planning
- Task complexity analysis
- Execution monitoring via logs
- Strategy recommendations

## Other Files

### Active/In-Use:
- `mcp_server_fastmcp.py` - FastMCP server implementation
- `arxiv_mcp_server.py` - ArXiv paper search and analysis MCP server

### Deprecated/Test Files:
- `mcp_cc_execute_enhanced.py` - Features merged into main `mcp_cc_execute.py`
- `mcp_server.py` - Old implementation
- `mcp_server_enhanced.py` - Old enhanced version
- `mcp_server_http.py` - HTTP-based server (not used)
- `poc_mcp.py` - Proof of concept
- `poc_mcp_http.py` - HTTP proof of concept
- `test_mcp_minimal.py` - Minimal test implementation
- `mcp_ai_backends_template.py` - Template for AI backends
- `mcp_gemini_execute.py` - Gemini-specific implementation

## Configuration

The MCP servers are configured in `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "cc-orchestration": {
      "command": "uv",
      "args": ["run", "python", "src/cc_executor/servers/mcp_cc_execute.py"],
      "env": {
        "CC_EXECUTOR_PORT": "8005"
      }
    }
  }
}
```

**Note**: The server name changed from "cc-execute" to "cc-orchestration" to better reflect its purpose as an orchestration support tool.

## Logs

All MCP server logs are written to:
- `/logs/mcp/mcp_cc_execute_YYYYMMDD_HHMMSS.log`

State files are saved to:
- `/state/mcp_executions/`

## Development

To test the enhanced MCP server:

```bash
# Run tests
python src/cc_executor/servers/mcp_cc_execute.py --test

# Start server directly
python src/cc_executor/servers/mcp_cc_execute.py
```

## Future Enhancements

When Claude Code adds streaming support, the following features will automatically become available:
- Real-time progress updates visible in Claude UI
- Live streaming of task output
- Interactive user prompts during execution (user elicitation)

The infrastructure for these features is already implemented and ready.