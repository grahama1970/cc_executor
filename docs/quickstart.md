# CC Executor Quickstart Guide

Get up and running with CC Executor in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- `uv` package manager
- Claude CLI installed and configured
- Active virtual environment

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cc_executor
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env to set PYTHONPATH=./src
   ```

## Quick Test

### 1. Start the WebSocket Server

```bash
cd src/cc_executor
python core/websocket_handler.py --serve --auto-demo --test-case simple
```

This runs a simple "2+2" test to verify everything is working.

### 2. Run Your First Command

In a new terminal:
```bash
cd src/cc_executor
python examples/websocket_client_usage.py
```

### 3. Try Different Test Cases

```bash
# Medium complexity test (JSON output)
python core/websocket_handler.py --serve --auto-demo --test-case medium

# Large output test (5000-word story, takes 3-5 minutes)
python core/websocket_handler.py --serve --auto-demo --test-case large
```

## Basic Usage

### Starting the Server

```bash
# Start server on default port (8004)
python core/websocket_handler.py --serve

# Start on custom port
python core/websocket_handler.py --serve --port 8005
```

### Using the Client

```python
import asyncio
import websockets
import json

async def run_command():
    async with websockets.connect("ws://localhost:8004") as websocket:
        # Send execute command
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "execute",
            "params": {
                "command": 'claude -p "What is 2+2?"'
            },
            "id": "1"
        }))
        
        # Read responses
        async for message in websocket:
            data = json.loads(message)
            if data.get("method") == "process.output":
                print(data["params"]["data"], end="")
            elif data.get("method") == "process.completed":
                break

asyncio.run(run_command())
```

## Common Commands

### Health Check
```bash
# Check if server is running
curl http://localhost:8004/health
```

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python core/websocket_handler.py --serve
```

### Run with Timeout
```bash
STREAM_TIMEOUT=60 python core/websocket_handler.py --serve
```

## Next Steps

1. **Learn about the architecture**: Read [How Claude Sees Code](architecture/how_claude_sees_code.md)
2. **Understand the protocol**: See [WebSocket MCP Protocol](architecture/websocket_mcp_protocol.md)
3. **Debug issues**: Check [Troubleshooting Guide](guides/troubleshooting.md)
4. **Deploy to production**: Follow [Operating the Service](guides/OPERATING_THE_SERVICE.md)

## Quick Troubleshooting

### Server won't start
- Check if port 8004 is already in use: `lsof -i:8004`
- Kill existing process: `kill $(lsof -t -i:8004)`

### No output from Claude
- Verify Claude CLI works: `claude -p "test"`
- Check environment variables: `echo $ANTHROPIC_API_KEY`
- Enable debug logging to see detailed errors

### Connection drops
- This is usually a timeout issue
- See [Timeout Management](technical/timeout_management.md) for solutions

## Getting Help

- Check [Known Issues](KNOWN_ISSUES.md) for common problems
- Read [Lessons Learned](LESSONS_LEARNED.md) for operational insights
- See [Troubleshooting Guide](guides/troubleshooting.md) for debugging

Last updated: 2025-07-02