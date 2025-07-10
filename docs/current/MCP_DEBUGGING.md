# MCP Debugging Guide

> How to verify that the **cc-executor** MCP tool and underlying WebSocket service are working, both on the host and inside the Docker container.

---

## 1. Prerequisites

* Python dependencies installed (`uv`, `pytest`, etc.)
* Claude CLI authenticated (`claude /login`) if you plan to run end-to-end tests with Claude.
* WebSocket server accessible (either via `uvicorn` locally or through `docker-compose`).
* `.mcp.json` manifest present in the project root and pointing to `ws://localhost:8003/ws/mcp`.

```bash
jq '.tools["cc-executor"].server_url' .mcp.json
# -> "ws://localhost:8003/ws/mcp"
```

---

## 2. Start the WebSocket Service Locally

```bash
export LOGURU_LEVEL=DEBUG   # verbose logs
uvicorn cc_executor.core.main:app --port 8003 --reload
```

If you prefer Docker:

```bash
docker compose up -d websocket  # or simply: docker compose up -d
```

Verify the port is listening:

```bash
lsof -i :8003
```

---

## 3. Smoke-Test the Raw WebSocket

Install **wscat** if you do not already have it:

```bash
npm i -g wscat
```

Connect and issue a minimal JSON-RPC request:

```bash
wscat -c ws://localhost:8003/ws/mcp
# Paste the following line and press <Enter>
{"jsonrpc":"2.0","id":"ping","method":"execute","params":{"command":"echo hello"}}
```

Expected output (abbreviated):

```json
{"jsonrpc":"2.0","method":"process.output",...}
{"jsonrpc":"2.0","result":{"status":"finished","exit_code":0},"id":"ping"}
```

If you do **not** see any response:

1. Check server logs for JSON parse errors.
2. Ensure the URL matches the one configured in `.mcp.json`.
3. Confirm no firewall or proxy is blocking WebSocket upgrades.

---

## 4. End-to-End Test with Claude CLI

```bash
claude -p --verbose \
  --mcp-config .mcp.json \
  --allowedTools "mcp__cc-executor" \
  --output-format stream-json \
  'Use cc-executor tool to run `echo 42`'
```

You should see `process.output` streaming tokens followed by the final result.  The `--verbose` flag prints tool handshake details—helpful for verifying the manifest was loaded.

Common errors:

| Error Message | Likely Cause | Fix |
|---------------|-------------|------|
| `tool unavailable` | Wrong path in `--mcp-config` or manifest missing `cc-executor` entry | Double-check `.mcp.json` location and content |
| `connection refused` | WebSocket service not running or wrong port | Start service or correct `server_url` |
| `parse error` | Malformed JSON typed in manual `wscat` session | Ensure valid JSON-RPC format |

---

## 5. Stand-Alone Debug Script (preferred)

Create `scripts/debug_mcp_execute.py`:

```python
#!/usr/bin/env python3
"""Quick sanity-check for the cc-executor MCP endpoint.

Usage:
    # Local host (default):
    python scripts/debug_mcp_execute.py

    # Inside Docker container (exec into it):
    python /app/scripts/debug_mcp_execute.py --uri ws://localhost:8003/ws/mcp

    # From host but hitting the container:
    python scripts/debug_mcp_execute.py --uri ws://127.0.0.1:8003/ws/mcp
"""

import argparse
import asyncio
import json
import sys
from loguru import logger
import websockets

DEFAULT_URI = "ws://localhost:8003/ws/mcp"

parser = argparse.ArgumentParser(description="Debug cc-executor MCP endpoint")
parser.add_argument("--uri", default=DEFAULT_URI, help="WebSocket URI (override for Docker, staging, etc.)")
args = parser.parse_args()

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time}</green> | <level>{level}</level> | {message}")
logger.info(f"Connecting to {args.uri}")

async def main():
    try:
        async with websockets.connect(args.uri) as ws:
            req = {
                "jsonrpc": "2.0",
                "id": "demo",
                "method": "execute",
                "params": {"command": "echo 123"}
            }
            await ws.send(json.dumps(req))
            logger.info("→ sent execute request")

            async for msg in ws:
                logger.debug(f"← {msg}")
                data = json.loads(msg)
                if data.get("id") == "demo":  # final response
                    logger.success("Execution finished")
                    break
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

*When running **inside** the Docker container* the URI is `ws://localhost:8003/ws/mcp` (internal port). From the **host machine** hitting the container you use the mapped port `ws://127.0.0.1:8004/ws/mcp` (external port).

---

## 6. Debugging Inside Docker

```bash
# Tail WebSocket service logs
docker compose logs -f websocket

# Exec into the running container
docker exec -it cc_execute /bin/bash

# Repeat wscat or curl tests inside the container to rule out network issues
```

Ensure the container has the same `.mcp.json` (mounted volume) or supply it via an environment variable in your CI job.

---

## 7. Enabling Connection Tracing

Set the following environment variables before starting the service:

```bash
export WEBSOCKET_DEBUG=1        # custom flag respected by websocket_handler.py
export LOGURU_LEVEL=DEBUG       # highest verbosity
```

This will log every received and sent JSON-RPC envelope, making it easier to pinpoint protocol mismatches.

---

## 8. Checklist for Common Pitfalls

- [ ] `.mcp.json` present and valid JSON
- [ ] `server_url` reachable from the client
- [ ] WebSocket service active (port 8003 local, 8004 Docker)
- [ ] Claude CLI authenticated if running full end-to-end flow
- [ ] No corporate proxy stripping WebSocket upgrade headers
- [ ] Adequate CPU/RAM limits in Docker (avoid OOM-kill)

Keep this checklist handy when onboarding new contributors or setting up CI pipelines.

---

Happy debugging!  If you discover new failure modes, update this document so the team benefits.
