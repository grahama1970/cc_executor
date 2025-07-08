# Final MCP Recommendation for CC Executor

**Date**: 2025-07-05
**Decision**: Use hybrid approach - FastAPI for standard clients, MCP optional for Claude integration

## Context

After reviewing both evaluations and understanding the latest architecture insights about WebSocket streaming for long-running executions, here's my analysis:

## The Real Question

Should CC Executor expose an MCP interface for Claude to call it as a tool?

## Key Insights

1. **MCP is just a protocol** - It's essentially JSON-RPC over WebSocket with a specific schema
2. **You already have WebSocket** - The core websocket_handler.py is working well
3. **The debate is about the wrapper** - Whether to add MCP protocol on top

## Recommendation: Pragmatic Hybrid Approach

### 1. Keep Current Architecture (Primary)

```
Client → FastAPI (auth/health) → WebSocket (execution)
```

This works well for:
- Web clients
- CLI tools  
- Direct API integration
- Testing

### 2. Add Lightweight MCP Endpoint (Optional)

Only if you need Claude to call CC Executor as a tool:

```python
# In FastAPI - just one endpoint
@app.get("/.well-known/mcp/cc-executor.json")
async def mcp_manifest():
    """Serve MCP manifest for Claude tool discovery."""
    return {
        "name": "cc-executor",
        "server_url": f"ws://{HOST}:8003/ws/mcp",
        "methods": {
            "execute": {
                "params": {"command": "string", "timeout": "int?"},
                "stream": True
            }
        }
    }
```

The WebSocket handler already speaks JSON-RPC, so it's MCP-compatible with minimal changes.

## Why This Works

### Pros of Adding MCP Endpoint:
- ✅ Claude can discover and call CC Executor as a tool
- ✅ Just ~20 lines of code (manifest endpoint)
- ✅ No changes to core websocket_handler.py
- ✅ Both protocols can coexist

### Cons Addressed:
- ❌ "MCP is brittle" → Only if you rebuild everything around it
- ❌ "Extra complexity" → Not if it's just a manifest endpoint
- ❌ "New dependencies" → None needed, you already have JSON-RPC

## Implementation Priority

1. **Don't add MCP unless you need it** - If prompt-based cc_execute.md works, keep using it
2. **If you need MCP** - Add just the manifest endpoint, no architectural changes
3. **Test thoroughly** - MCP with Claude has quirks around auth and streaming

## Decision Tree

```
Do you need Claude to call CC Executor as a tool?
├─ No → Use current architecture (FastAPI + WebSocket)
└─ Yes → Add MCP manifest endpoint
         └─ Does it work reliably?
             ├─ Yes → Keep it
             └─ No → Revert to prompt-based approach
```

## Code Example (If Needed)

```python
# Add to api/main.py
@app.get("/.well-known/mcp/cc-executor.json")
async def mcp_manifest():
    return {
        "name": "cc-executor",
        "description": "Execute commands via Claude Code",
        "server_url": f"ws://localhost:8003/ws",
        "protocol_version": "1.0",
        "methods": {
            "initialize": {"params": {}},
            "execute": {
                "params": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "optional": True}
                },
                "returns": {"type": "object"},
                "stream": True
            }
        }
    }
```

That's it. No other changes needed.

## Final Verdict

**MCP is neither inherently good nor bad** - it's just a protocol. The question is whether you need it:

- **For general use**: Current architecture is perfect
- **For Claude tool integration**: Add minimal MCP manifest
- **Don't rebuild everything**: Just add what you need

The original evaluation was right that rebuilding everything for MCP adds unnecessary complexity. But adding a simple manifest endpoint for Claude compatibility is pragmatic and low-risk.