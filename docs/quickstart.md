# CC Executor Quickstart Guide

Get up and running with CC Executor in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- `uv` package manager ([install guide](https://github.com/astral-sh/uv))
- Claude CLI installed and configured
- Claude Max subscription ($200/month) - API keys don't work with Claude Max
- Redis (optional, for session management)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/grahama1970/cc_executor.git
   cd cc_executor
   ```

2. **Install with uv**:
   ```bash
   uv sync
   uv pip install -e .
   ```

3. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # - ANTHROPIC_API_KEY (required for Claude CLI)
   # - CC_EXECUTOR_SHELL=zsh (optional, defaults to zsh)
   # - PYTHONUNBUFFERED=1 (recommended)
   ```

## Quick Test

### Using the CLI (Recommended)

```bash
# Initialize environment
cc-executor init

# Start the server
cc-executor server start

# Run a simple test
cc-executor run "echo Hello, World!"

# Run a Claude command
cc-executor run "claude -p 'What is 2+2?'"
```

### Using the WebSocket Server Directly

```bash
cd src/cc_executor
python core/websocket_handler.py --serve --auto-demo --test-case simple
```

This runs a simple "2+2" test to verify everything is working.

### Try Different Test Cases

```bash
# Medium complexity test (JSON output)
cc-executor run 'claude -p "Generate a JSON object with 5 items"'

# Large output test (5000-word story, takes 3-5 minutes)
cc-executor run 'claude -p "Write a 5000 word story"'

# Test with hooks
cc-executor run 'claude -p "List Python files"' --hook pre_execution_hooks
```

## Basic Usage

### CLI Commands

```bash
# Server management
cc-executor server start    # Start the WebSocket server
cc-executor server stop     # Stop the server
cc-executor server status   # Check if server is running

# Execute commands
cc-executor run "your command here"
cc-executor run "claude -p 'your prompt'" --timeout 300

# View history
cc-executor history list
cc-executor history show <session_id>

# Run assessments
cc-executor test assess core
cc-executor test assess cli
cc-executor test assess hooks
```

### Programmatic Usage

```python
from cc_executor.core.client import WebSocketClient
import asyncio

async def main():
    client = WebSocketClient()
    
    # Execute a command
    result = await client.execute_command(
        command='claude -p "What is 2+2?"',
        timeout=30
    )
    
    if result["success"]:
        print(f"Output: {result['output_data']}")
    else:
        print(f"Error: {result['error']}")

asyncio.run(main())
```

### Environment Variables

```bash
# Core settings
export ANTHROPIC_API_KEY=your_key_here
export CC_EXECUTOR_SHELL=zsh           # Use zsh for Claude consistency
export PYTHONUNBUFFERED=1              # Real-time output streaming

# Optional settings
export CC_EXECUTOR_PORT=8003           # WebSocket port
export LOG_LEVEL=INFO                  # Logging verbosity
export MAX_BUFFER_SIZE=8388608         # 8MB buffer limit
export STREAM_TIMEOUT=600              # 10 minute timeout
## Common Commands

### Health Check
```bash
# Check server status
cc-executor server status

# Manual health check
curl http://localhost:8003/health
```

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG cc-executor server start
```

### Run with Custom Timeout
```bash
cc-executor run "claude -p 'complex task'" --timeout 600
```

## Next Steps

1. **Why this exists**: Read the [Main README](../README.md) to understand Claude Max limitations
2. **Learn about the architecture**: Read [How Claude Sees Code](architecture/how_claude_sees_code.md)
3. **Understand the protocol**: See [WebSocket MCP Protocol](architecture/websocket_mcp_protocol.md)
4. **Debug issues**: Check [Troubleshooting Guide](guides/troubleshooting.md)
5. **Deploy to production**: Follow [Operating the Service](guides/OPERATING_THE_SERVICE.md)

## Quick Troubleshooting

### Server won't start
- Check if port is already in use: `lsof -i:8003`
- Kill existing process: `cc-executor server stop`
- Try a different port: `CC_EXECUTOR_PORT=8005 cc-executor server start`

### No output from Claude
- Verify Claude CLI works: `claude -p "test"`
- Check API key: `echo $ANTHROPIC_API_KEY`
- Remember: Use `-p` NOT `--print` (common mistake)
- Enable debug logging: `LOG_LEVEL=DEBUG cc-executor run "claude -p 'test'"`

### Connection drops
- Usually a timeout issue with long-running prompts
- Increase timeout: `STREAM_TIMEOUT=1200 cc-executor server start`
- Check WebSocket keepalive is working (see logs for PING/PONG)

## Getting Help

- **Common issues**: Check [Troubleshooting Guide](guides/troubleshooting.md)
- **Known problems**: See [Known Issues](KNOWN_ISSUES.md)
- **Architecture details**: Read [Lessons Learned](LESSONS_LEARNED.md)
- **Memory concerns**: See [Memory Optimization](MEMORY_OPTIMIZATION.md)
- **Why this exists**: Understand [Claude Max limitations](../README.md#why-this-exists)

## Important Notes

- This is an **unofficial** workaround for Claude Max users
- Claude Max ($200/month) doesn't support API keys in the traditional sense
- Hooks are broken in the official Claude implementation
- This project aims to fill the gap until Anthropic provides official support

Last updated: 2025-07-03