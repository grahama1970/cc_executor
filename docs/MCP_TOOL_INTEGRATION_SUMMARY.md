# MCP Tool Integration Summary

## Overview

I've analyzed and designed how an MCP (Model Context Protocol) tool could interface with the existing cc_executor WebSocket handler infrastructure. This integration preserves the key benefit of "fresh 200K context" by spawning new Claude instances through the WebSocket service.

## Architecture Components Created

### 1. **Architecture Documentation**
- **File**: `docs/architecture/mcp_tool_websocket_bridge.md`
- **Content**: Comprehensive architecture showing how MCP tools bridge to WebSocket handler
- **Key Points**:
  - Detailed flow diagram showing Claude → MCP Tool → WebSocket → Fresh Claude Instance
  - Preserves process isolation and streaming capabilities
  - Maintains all error handling and timeout features

### 2. **MCP Tool Implementation**
- **File**: `src/cc_executor/mcp_bridge/mcp_tool.py`
- **Features**:
  - Complete MCP tool that connects to WebSocket handler
  - Supports both general command execution and Claude-specific invocations
  - Real-time output streaming back through MCP protocol
  - Comprehensive error handling including token/rate limits

### 3. **Usage Examples**
- **File**: `examples/mcp_tool_usage.py`
- **Demonstrates**:
  - Simple command execution
  - Python script execution
  - Fresh Claude context invocation
  - Complex tasks with MCP tools
  - Long-running task handling

## How It Works

### Flow Diagram
```
Claude Instance 1 → MCP Tool → WebSocket Client → WebSocket Handler → Claude Instance 2
     (Original)        ↓              ↓                  ↓              (Fresh 200K)
                   Bridge Code    ws://8004/ws      Process Manager
```

### Key Benefits

1. **Fresh 200K Context Window**
   - Each MCP tool invocation spawns a completely fresh Claude instance
   - No context pollution from the parent Claude
   - Full token window available for large tasks

2. **Process Isolation**
   - Commands run in separate processes
   - Proper cleanup and resource management
   - Process group handling prevents orphans

3. **Streaming Support**
   - Real-time output streaming
   - Progress monitoring for long tasks
   - Chunked output for large responses

4. **Error Handling**
   - Token limit detection and reporting
   - Rate limit handling with retry information
   - Timeout management at multiple levels

## Example Usage

### From Claude's Perspective

```python
# Simple command execution
result = await mcp__cc_executor__execute({
    "command": "python analyze_codebase.py",
    "timeout": 300
})

# Fresh Claude instance with full context
analysis = await mcp__cc_executor__execute_claude({
    "prompt": "Analyze this 150K token codebase for security issues",
    "timeout": 1200,
    "allowed_tools": ["mcp__github", "mcp__ripgrep"]
})
```

### MCP Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "cc-executor": {
      "command": "python",
      "args": ["-m", "cc_executor.mcp_bridge.mcp_tool"],
      "env": {
        "CC_EXECUTOR_WEBSOCKET_URL": "ws://localhost:8004/ws",
        "CC_EXECUTOR_DEFAULT_TIMEOUT": "600"
      }
    }
  }
}
```

## Technical Details

### WebSocket Protocol
- Uses existing JSON-RPC 2.0 protocol
- Maintains bidirectional streaming
- Supports all control operations (pause/resume/cancel)

### MCP Protocol Integration
- Receives JSON-RPC requests from Claude
- Translates to WebSocket messages
- Streams output back through MCP protocol
- Handles notifications and errors

### Security Considerations
- Command whitelisting through ALLOWED_COMMANDS
- Optional authentication tokens
- Rate limiting support
- Output size limits to prevent memory issues

## Testing

Run the examples to see the integration in action:

```bash
# Start WebSocket service
python -m cc_executor.core.websocket_handler

# In another terminal, run examples
python examples/mcp_tool_usage.py
```

## Conclusion

The MCP tool bridge successfully enables Claude to spawn fresh instances of itself or execute other commands while preserving the full 200K context window. This architecture leverages the existing robust WebSocket infrastructure while adding a clean MCP interface for Claude to use.