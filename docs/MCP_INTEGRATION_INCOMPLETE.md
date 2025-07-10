# MCP Integration Issue - CC Executor

## Problem Summary

The cc-execute MCP server is configured but **not usable by Claude agents**.

### Current State
1. ✅ MCP server implemented (`src/cc_executor/servers/mcp_cc_execute.py`)
2. ✅ Configuration exists in `/home/graham/.claude/claude_code/.mcp.json`
3. ❌ Server is NOT running (not in process list)
4. ❌ Server is NOT accessible via `mcp__cc-execute__*` tools
5. ❌ Cannot be used by Claude agents for orchestration

### Why This Matters
- The main interface for cc_executor (MCP tools) is not functional
- Claude agents cannot use the orchestration features
- The deployment is incomplete despite documentation claiming it's ready

### Evidence
```bash
# Other MCP servers are running and accessible:
mcp__perplexity-ask__perplexity_ask  # ✅ Works
mcp__brave-search__brave_web_search  # ✅ Works
mcp__github__*                       # ✅ Works

# But cc-execute is not:
mcp__cc-execute__execute_task        # ❌ Not available
mcp__cc-execute__verify_execution    # ❌ Not available
```

### Root Cause
The MCP server needs to:
1. Be started by the Claude environment (like other MCP servers)
2. Be registered in a way that exposes it to agents
3. Follow the same pattern as working MCP servers

### Current Workarounds
- Use Python API directly (`cc_execute()`)
- Use WebSocket API directly
- Use Docker deployment

But these defeat the purpose of MCP integration for agent orchestration.

## Solution Needed

Either:
1. Fix the MCP integration to make tools available to agents
2. Document that MCP is only for external clients, not agents
3. Create a different integration method for agent use

The user is correct: **"if you can't use it without having problems then you are not done debugging"**