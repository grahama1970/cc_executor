# Operating the Service

This guide provides the essential commands for running, testing, and interacting with the CC-Executor service.

## Running the Service

There are two primary ways to run the service: via Docker (recommended for production and stable testing) or locally (for active development).

### With Docker (Recommended)

This method uses the configuration in `docker-compose.yml` to run the service in an isolated container.

```bash
# Navigate to the project's source directory
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor

# Start the service in detached mode
docker compose up -d

# Check the health of the running service
curl http://localhost:8003/health

# View live logs from the container
docker logs -f cc_executor_mcp

# Stop and remove the service containers
docker compose down
```

### Locally (for Development)

This method runs the server directly on your host machine, which is useful for rapid development and debugging.

```bash
# Ensure dependencies are installed
# Assumes you are in the project root
pip install -r src/cc_executor/requirements.txt

# Start the MCP service
python src/cc_executor/core/implementation.py --port 8003
```

## Interacting with the Service

Once the service is running, you can interact with it via its WebSocket endpoint.

### Basic WebSocket Connection Test

This simple Python snippet connects to the server, receives the initial "connected" message, and prints it.

```python
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8003/ws/mcp"
    async with websockets.connect(uri) as ws:
        response = await ws.recv()
        print("Received from server:")
        print(json.dumps(json.loads(response), indent=2))

asyncio.run(test_connection())
```

### Running a `claude` Command

To execute a `claude` command, you send a JSON-RPC `execute` message. The following is a comprehensive example that uses tool configurations.

```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "command": "claude -p --output-format stream-json --verbose --mcp-config .mcp.json --allowedTools \"mcp__perplexity-ask mcp__brave-search mcp__github mcp__ripgrep mcp__puppeteer\" --dangerously-skip-permissions \"Write a 5000 word science fiction story about a programmer who discovers their code is sentient.\""
  },
  "id": "claude-long-story-1"
}
```

### Viewing `claude` Transcripts

The `claude` tool saves its final, official output to a `.jsonl` transcript file. You can stream the most recent transcript using this helper function (assuming it is in your shell's environment, e.g., `.zshrc`).

```bash
# This function finds and streams the latest transcript
claude_transcript_stream
```

## Running Tests

The project includes a suite of stress tests to verify the reliability of the WebSocket handler.

```bash
# Navigate to the stress test directory
cd src/cc_executor/tests/stress

# Run all stress tests
python unified_stress_test_executor.py

# Run only specific categories of tests
python unified_stress_test_executor.py --categories simple parallel
```