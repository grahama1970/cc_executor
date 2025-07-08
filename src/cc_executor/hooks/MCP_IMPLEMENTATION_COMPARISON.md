# MCP Implementation Comparison: cc_executor vs arxiv-mcp-server

## Overview

This document compares the MCP (Model Context Protocol) implementations between two projects:
- **cc_executor**: WebSocket-based MCP server with debugging tools
- **arxiv-mcp-server**: stdio-based MCP server following standard protocol

## Key Architectural Differences

### 1. Transport Layer

**cc_executor**:
- Uses WebSocket transport (`ws://localhost:8003/ws/mcp`)
- Implements custom JSON-RPC over WebSocket
- Provides real-time bidirectional communication
- Has heartbeat mechanism for connection health

**arxiv-mcp-server**:
- Uses stdio transport (standard input/output)
- Follows official MCP SDK patterns
- Communicates via process pipes
- No persistent connection needed

### 2. Server Implementation

**cc_executor**:
```python
# WebSocket-based with FastAPI
@app.websocket("/ws/mcp")
async def websocket_endpoint(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    await websocket_handler.handle_connection(websocket, session_id)
```

**arxiv-mcp-server**:
```python
# stdio-based with MCP SDK
async def main():
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], InitializationOptions(...))
```

### 3. Debugging Tools

**cc_executor** provides:
- `test_mcp_protocol.py` - WebSocket protocol tester
- Session management with IDs
- Process tracking with PID/PGID
- Streaming output with chunking
- Hook integration for pre/post execution
- Redis-based execution metrics

**arxiv-mcp-server** provides:
- Standard MCP tool registration
- Handler-based architecture
- Logging with loguru
- No custom debugging scripts

## Debugging Patterns from cc_executor

### 1. Protocol Testing Script

cc_executor's `test_mcp_protocol.py` demonstrates:
```python
async def test_mcp_protocol():
    uri = "ws://localhost:8003/ws/mcp"
    async with websockets.connect(uri) as websocket:
        # Send JSON-RPC request
        execute_request = {
            "jsonrpc": "2.0",
            "method": "execute",
            "params": {"command": "echo 'Hello'"},
            "id": 1
        }
        await websocket.send(json.dumps(execute_request))
        
        # Handle streaming responses
        while True:
            response = await websocket.recv()
            response_data = json.loads(response)
            if "result" in response_data:
                break
```

### 2. Connection Health Monitoring

cc_executor implements:
- Heartbeat mechanism (20s default)
- Session lifecycle tracking
- Graceful error handling with specific error codes
- Connection state notifications

### 3. Output Streaming

cc_executor handles large outputs by:
- Chunking messages (64KB chunks)
- Progress notifications
- Token limit detection
- Rate limit detection

## What arxiv-mcp-server Should Adopt

### 1. Debugging Scripts

Create `scripts/debug/test_mcp_connection.py`:
```python
#!/usr/bin/env python3
"""Test MCP connection and basic functionality."""

import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_arxiv_mcp():
    """Test ArXiv MCP Server functionality."""
    
    server_params = StdioServerParameters(
        command="python",
        args=["run_server.py"],
        env={}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✓ Connected to ArXiv MCP Server")
            
            # Initialize
            await session.initialize()
            
            # Test tool listing
            tools = await session.list_tools()
            print(f"✓ Found {len(tools.tools)} tools")
            
            # Test search
            result = await session.call_tool(
                "search_papers",
                arguments={"query": "quantum", "max_results": 1}
            )
            print("✓ Search completed")
            
            return True

if __name__ == "__main__":
    asyncio.run(test_arxiv_mcp())
```

### 2. Connection Monitoring

Add connection health checks:
```python
# In arxiv_mcp_server/server.py
@server.notification("ping")
async def handle_ping(params: dict) -> None:
    """Handle ping notifications for connection health."""
    logger.debug(f"Received ping: {params}")
    # Could track last ping time for monitoring
```

### 3. Enhanced Error Handling

Implement structured error responses like cc_executor:
```python
# Error codes
ERROR_TOOL_NOT_FOUND = -32001
ERROR_API_LIMIT = -32002
ERROR_PAPER_NOT_FOUND = -32003

# In error handling
return [TextContent(
    type="text", 
    text=json.dumps({
        "error": {
            "code": ERROR_API_LIMIT,
            "message": "API rate limit exceeded",
            "data": {"retry_after": 60}
        }
    })
)]
```

### 4. Execution Metrics

Add timing and metrics collection:
```python
# Track execution times
import time

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    start_time = time.time()
    try:
        result = await call_tool_handler(name, arguments)
        duration = time.time() - start_time
        logger.info(f"Tool {name} completed in {duration:.2f}s")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Tool {name} failed after {duration:.2f}s: {e}")
        raise
```

### 5. Session/Request Tracking

Add request ID tracking for debugging:
```python
# Generate request IDs for tracking
import uuid

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Calling tool: {name}")
    
    try:
        result = await call_tool_handler(name, arguments)
        logger.info(f"[{request_id}] Tool completed successfully")
        return result
    except Exception as e:
        logger.error(f"[{request_id}] Tool failed: {e}")
        raise
```

## Implementation Recommendations

1. **Create debugging directory**: `arxiv-mcp-server/scripts/debug/`
2. **Add connection tester**: Similar to cc_executor's `test_mcp_protocol.py`
3. **Implement health checks**: Add ping/pong or health endpoint
4. **Enhanced logging**: Add request IDs and execution metrics
5. **Error standardization**: Use consistent error codes and formats
6. **Output streaming**: Handle large responses gracefully
7. **Create MCP manifest**: Document available tools and capabilities

## MCP Configuration Differences

**cc_executor** (.mcp.json):
- Defines multiple MCP servers
- Includes arxiv-cc server pointing to Python script

**arxiv-mcp-server**:
- No .mcp.json file present
- Should create one for easier integration

### Recommended .mcp.json for arxiv-mcp-server:
```json
{
  "mcpServers": {
    "arxiv": {
      "command": "python",
      "args": [
        "/home/graham/workspace/mcp-servers/arxiv-mcp-server/run_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/graham/workspace/mcp-servers/arxiv-mcp-server/src"
      }
    }
  }
}
```

## Summary

The key debugging patterns from cc_executor that should be applied to arxiv-mcp-server are:

1. **Protocol testing scripts** for validating MCP communication
2. **Connection health monitoring** for reliability
3. **Structured error handling** with specific error codes
4. **Execution metrics** for performance tracking
5. **Request tracking** for debugging complex flows

These patterns would significantly improve the debuggability and reliability of the arxiv-mcp-server implementation.