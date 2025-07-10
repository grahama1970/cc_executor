# MCP Integration Lessons Learned

## The Fundamental Lesson: Configuration ≠ Running Service

### The Pattern That Wastes Hours

1. **See MCP server in `.mcp.json`** → Assume it's available
2. **Try to use `mcp__server__tool`** → Doesn't work
3. **Debug integration, prefixes, registration** → Wrong direction
4. **Real issue: Server isn't running** → Need to reload Claude Code

### Always Check These First

```bash
# 1. Is the MCP server process running?
ps aux | grep "mcp\|cc_executor"

# 2. When was .mcp.json last modified?
stat ~/.claude/claude_code/.mcp.json

# 3. Has Claude Code been reloaded since then?
# If not, the server won't be running!
```

## MCP Server Lifecycle

### Starting MCP Servers

MCP servers are started by Claude Code when:
- Claude Code starts up
- You reload Claude Code (`Cmd/Ctrl + R`)
- You modify `.mcp.json` (sometimes triggers auto-reload)

### The "It's Not Working" Checklist

1. **Check if configured**: `cat ~/.claude/claude_code/.mcp.json | grep "your-server"`
2. **Check if running**: `ps aux | grep "your-server"`
3. **If not running**: Reload Claude Code
4. **Verify it started**: Check process list again
5. **Test the tool**: Try `mcp__your-server__tool-name`

## Common MCP Pitfalls

### 1. Project vs Global Configuration

```bash
# Project-level (often doesn't work due to bug)
/your/project/.mcp.json

# Global (always works)
~/.claude/claude_code/.mcp.json
```

**Lesson**: Always use global config with absolute paths.

### 2. Command Format Matters

```json
// WRONG - Direct Python
{
  "command": "python",
  "args": ["server.py"]
}

// RIGHT - Using uv with directory
{
  "command": "uv",
  "args": [
    "--directory",
    "/absolute/path/to/project",
    "run",
    "python",
    "src/server.py"
  ]
}
```

### 3. FastMCP vs Low-Level MCP SDK

```python
# WRONG - Low-level MCP SDK (complex)
from mcp.server import Server
from mcp.server.stdio import stdio_server

# RIGHT - FastMCP (simple)
from fastmcp import FastMCP
mcp = FastMCP(name="my-server")

@mcp.tool
async def my_tool(param: str) -> str:
    return f"Result: {param}"
```

### 4. stdio vs HTTP Transport

- **Claude Code uses stdio** (standard input/output)
- **Not HTTP/SSE** (even though many examples show this)
- **Communication is via JSON-RPC over stdio**

## Testing MCP Servers

### Manual Testing

```python
# Test MCP server manually
import subprocess
import json

proc = subprocess.Popen(
    ["python", "-m", "your_mcp_server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# Initialize
proc.stdin.write(json.dumps({
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "1.0",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    },
    "id": 1
}) + '\n')
proc.stdin.flush()

# List tools
proc.stdin.write(json.dumps({
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
}) + '\n')
proc.stdin.flush()
```

### Debugging Failed MCP Servers

```bash
# 1. Try running manually
cd /path/to/project
uv run python src/mcp_server.py

# 2. Check stderr output
# Look for import errors, missing dependencies, etc.

# 3. Verify stdio communication
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | uv run python src/mcp_server.py
```

## The "Basic Competent Minimum" for MCP

### Before Claiming MCP Integration Works

1. **Start the server**: Reload Claude Code
2. **Verify it's running**: `ps aux | grep your-server`
3. **Test with agent**: Use `mcp__your-server__tool`
4. **Verify anti-hallucination**: Check execution actually happened

### The One-Line Test

```bash
# If this works, your MCP integration is complete:
mcp__cc-execute__execute_task "echo 'MCP is working'"
```

## Environment Variables and MCP

### Setting Environment Variables

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "MY_API_KEY": "value",
        "SERVER_PORT": "8005"
      }
    }
  }
}
```

### Common Environment Issues

- Variables set in `env` are passed to the subprocess
- They don't affect your shell environment
- Server must read from environment, not expect CLI args

## The Ultimate MCP Debugging Tool

```bash
# Save this as debug_mcp.sh
#!/bin/bash

echo "=== MCP Debug Check ==="
echo "1. Checking .mcp.json..."
cat ~/.claude/claude_code/.mcp.json | jq .

echo -e "\n2. Checking running MCP processes..."
ps aux | grep -E "mcp|fastmcp" | grep -v grep

echo -e "\n3. Recent .mcp.json modifications..."
stat ~/.claude/claude_code/.mcp.json | grep Modify

echo -e "\n4. Test reminder..."
echo "After reloading Claude Code, test with:"
echo "  mcp__your-server__your-tool"
```

## Key Takeaways

1. **Configuration is not execution** - Servers must be started
2. **Reload Claude Code** - This starts MCP servers
3. **Use FastMCP** - Simpler than low-level SDK
4. **Global config with absolute paths** - Most reliable
5. **stdio not HTTP** - Claude uses subprocess communication
6. **Always verify with ps aux** - Don't assume it's running

Remember: If you can't use the MCP tool as an agent, the integration isn't complete!