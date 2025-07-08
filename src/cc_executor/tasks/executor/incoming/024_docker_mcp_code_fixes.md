# 024 – Docker + MCP Targeted Code Fixes

These are the concrete changes applied to get the container running and the MCP bridge working without adding complexity.

## 1 Docker Compose
* **Removed source bind-mount** (`..:/app`) and stray ` /app/.venv` mount so packaged files aren’t overwritten.
* Container now relies on image content; rebuild with `docker compose build` after code edits.

## 2 Dockerfile
* CMD already points to `deployment/start_services.py`; no change needed.
* `uv pip install --system -e .` keeps editable install and avoids venv.

## 3 Manifest / MCP
* Manifest lives at `.mcp.json`; no runtime change—WebSocket URL unchanged.
* FastAPI optionally serves the manifest at `/.well-known/mcp/cc-executor.json`.

## 4 Debug Script
* Added `scripts/debug_mcp_execute.py` with Loguru logging and `--uri` flag for host vs container testing.

## 5 Documentation
* Added `docs/MCP_DEBUGGING.md`.
* README now mentions MCP option.

## 6 Tips for Claude Code Execution

1. **Wait-for-it health loop** – Before issuing MCP calls, poll `http://localhost:8001/health` (FastAPI) or open a short WebSocket ping to `ws://localhost:8003/ws/mcp` until you receive a `connected` notification. This avoids race conditions on cold container start.
2. **Set `CLICOLOR_FORCE=1`** in Claude’s environment if you want colorized output; the WebSocket handler strips ANSI sequences safely.
3. **Memory limits** – If you run large code generations, increase Docker memory limit (e.g. `--memory 2g`) or adjust compose `mem_limit` to prevent OOM kills.
4. **Timeout tuning** – Override per-task timeout with `WEBSOCKET_EXEC_TIMEOUT` env var or `params.timeout` in the MCP call.
5. **API key vs Browser auth** – When using Claude Max, ensure the host’s `~/.claude` is mounted read-only; for API-key plans export `ANTHROPIC_API_KEY` instead.
6. **Rebuild trigger** – After code changes run `docker compose build cc_execute && docker compose up -d --force-recreate` to guarantee the new image is used.

## ✅ Definition of Done
1. `docker compose build --no-cache && docker compose up -d` succeeds.
2. Hitting `ws://localhost:8003/ws/mcp` inside container returns `connected`.
3. Claude CLI call with `--allowedTools "mcp__cc-executor"` streams output.

> No other code paths touched; sequential execution behaviour unchanged.
