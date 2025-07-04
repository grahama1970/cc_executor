# CC Executor MCP Architecture Decision

## Executive Summary

**Decision**: Implement CC Executor as an MCP tool that acts as a bridge to the existing WebSocket handler infrastructure.

This approach preserves the unique capability of spawning fresh Claude instances with 200K context while adding all the benefits of MCP's structured protocol.

## Architecture Overview

```
┌─────────────┐     MCP Protocol      ┌──────────────┐     WebSocket      ┌─────────────────┐
│   Claude    │ ──────────────────>   │  MCP Tool    │ ──────────────>    │ WebSocket       │
│ (Orchestr.) │                       │  (Bridge)    │                    │ Handler         │
└─────────────┘                       └──────────────┘                    └────────┬────────┘
                                                                                    │
                                                                                    │ Spawns
                                                                                    ▼
                                                                          ┌─────────────────┐
                                                                          │  Fresh Claude   │
                                                                          │  (200K context) │
                                                                          └─────────────────┘
```

## Why This Works

### 1. MCP Tools Are Not Limited to Claude's Context

Initial assumption: MCP tools execute "within" Claude's context and share its limitations.

**Reality**: MCP tools can:
- Make network requests (HTTP, WebSocket, gRPC)
- Connect to external services
- Spawn processes
- Act as proxies or bridges
- Have their own execution environment

### 2. The Bridge Pattern Preserves Core Functionality

The MCP tool acts as a **client** to the WebSocket handler:

```python
@mcp.tool()
async def execute_task(task: str) -> Dict[str, Any]:
    # MCP tool connects to WebSocket handler
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        # WebSocket handler spawns fresh Claude
        # Full 200K context available!
        await ws.send(execute_command)
        return await collect_results(ws)
```

### 3. Best of Both Worlds

**From MCP Protocol:**
- ✅ Structured interface with JSON schemas
- ✅ Tool discovery and documentation
- ✅ Protocol-level error handling
- ✅ Integration with other MCP tools
- ✅ Standardized auditing and permissions

**From WebSocket Handler:**
- ✅ Fresh 200K context for each task
- ✅ Sequential execution guarantees
- ✅ Process management capabilities
- ✅ Hook system integration
- ✅ Proven reliability (10:1 success ratio)

## Implementation Benefits

### 1. No Core Changes Required

The WebSocket handler (`websocket_handler.py`) remains unchanged. We're adding an interface layer, not replacing core functionality.

### 2. Gradual Migration Path

Can run both approaches simultaneously:
- Existing prompt-based orchestrators continue working
- New implementations can use MCP tools
- A/B testing between approaches

### 3. Better Integration

Other MCP tools can now interact with cc_executor:
```python
# Example: Combine with other tools
result = await mcp.call_tool("github.get_file_contents", {...})
analysis = await mcp.call_tool("cc_executor.execute_task", {
    "task": f"Analyze this code: {result['content']}"
})
```

### 4. Enhanced Observability

MCP provides structured logging:
- Every tool invocation is logged
- Parameters and results are captured
- Errors are standardized
- Metrics can be collected

## Implementation Plan

### Phase 1: Core MCP Bridge (Week 1)
- [x] Create `cc_executor_mcp.py` with basic bridge
- [ ] Implement `execute_task` tool
- [ ] Add WebSocket client functionality
- [ ] Test with simple tasks

### Phase 2: Enhanced Features (Week 2)
- [ ] Add `execute_task_list` tool
- [ ] Implement `get_execution_status` tool
- [ ] Add `control_execution` (pause/resume/cancel)
- [ ] Hook status integration

### Phase 3: Production Readiness (Week 3)
- [ ] Error handling and retry logic
- [ ] Connection pooling for WebSocket
- [ ] Performance optimization
- [ ] Comprehensive testing

### Phase 4: Documentation & Migration (Week 4)
- [ ] Update all documentation
- [ ] Create migration guide
- [ ] Update task list templates
- [ ] Train users on new approach

## Risk Mitigation

### Risk 1: WebSocket Connection Overhead
**Mitigation**: Implement connection pooling and reuse for multiple requests.

### Risk 2: Additional Point of Failure
**Mitigation**: MCP tool includes fallback to direct subprocess if WebSocket unavailable.

### Risk 3: Learning Curve
**Mitigation**: Provide clear examples and maintain backward compatibility.

## Conclusion

The MCP bridge architecture is the optimal solution because it:

1. **Preserves unique capabilities** - Fresh 200K context per task
2. **Adds protocol benefits** - Structured, discoverable, reliable
3. **Requires no core changes** - WebSocket handler remains proven
4. **Enables better integration** - Works with MCP ecosystem
5. **Provides migration path** - Both approaches can coexist

This is not a replacement but an **enhancement** - adding a structured interface to our proven execution engine.