#!/bin/bash

# Generic runner for self-improving markdown prompts (research-collaborator by default)
# ------------------------------------------------------------------------------
# Environment variables recognised:
#   PROMPT_FILE  – Path (relative to repo root) of the markdown prompt file to feed Claude.
#                  Default: src/cc_executor/prompts/commands/research-collaborator.md
#   REQUEST      – Natural-language request appended after the prompt include. Required.
#   METATAGS     – Optional metadata tags appended before ${REQUEST} (e.g. "[category:stress_test]").
#   TIMEOUT      – Overall execution timeout (seconds) forwarded to Claude via --timeout parameter.
#   STALL_TIMEOUT– Stall timeout (seconds) forwarded as --stall-timeout.
#   ALLOWED_TOOLS – Comma separated list passed to --allowedTools (falls back to defaults inside prompt).
#   CLAUDE_ARGS  – Extra flags appended verbatim to the Claude command.
#
# Usage example:
#   REQUEST="How to fix sequential subprocess hangs?" \
#   METATAGS="[category:research][complexity:simple]" \
#   bash src/cc_executor/prompts/scripts/run_research_collaborator.sh
# ------------------------------------------------------------------------------

set -euo pipefail
set -x

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$PROJECT_ROOT"

PROMPT_FILE="${PROMPT_FILE:-src/cc_executor/prompts/commands/research-collaborator.md}"
REQUEST="${REQUEST:-}"
if [[ -z "$REQUEST" ]]; then
  echo "ERROR: REQUEST variable is required" >&2
  exit 1
fi

METATAGS="${METATAGS:-}"
TIMEOUT="${TIMEOUT:-}"               # optional
STALL_TIMEOUT="${STALL_TIMEOUT:-}"   # optional
ALLOWED_TOOLS="${ALLOWED_TOOLS:-}"   # optional
CLAUDE_ARGS="${CLAUDE_ARGS:-}"       # passthrough

# ------------------------------------------------------------------------------
# 1. Ensure PATH / PYTHONPATH for cc_executor modules
export PATH="$HOME/.claude/commands:$PATH"
export PYTHONPATH="$PROJECT_ROOT/src"

# 2. Start WebSocket server (if not already running on :8004)
WEBSOCKET_PORT="8004"
if ! lsof -i:"$WEBSOCKET_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Starting cc_executor WebSocket server on port $WEBSOCKET_PORT …"
  if command -v uv >/dev/null 2>&1; then
  uv run python -m cc_executor.core.websocket_handler >ws_server.log 2>&1 &
else
  python -m cc_executor.core.websocket_handler >ws_server.log 2>&1 &
fi
  SERVER_PID=$!
  trap 'echo "Cleaning up server PID $SERVER_PID"; kill $SERVER_PID' EXIT
  # give server a moment to come up
  sleep 3
else
  echo "WebSocket server already running on port $WEBSOCKET_PORT – re-using it."
  SERVER_PID=""
fi

# 3. Build Claude command template
# Read prompt file and replace placeholder
PROMPT_CONTENT=$(cat "$PROMPT_FILE" | sed "s/\[QUESTION_HERE\]/${REQUEST}/g")

# We'll pipe the prompt content to claude via stdin
BASE_CMD=(claude -p - --output-format stream-json --verbose --dangerously-skip-permissions)
# Add MCP config flag if file exists
MCP_FILE="$PROJECT_ROOT/.mcp.json"
if [[ -f "$MCP_FILE" ]]; then
  BASE_CMD+=(--mcp-config "$MCP_FILE")
fi
# Note: Claude CLI doesn't support --timeout or --stall-timeout flags
# These were removed as they cause "unknown option" errors
[[ -n "$ALLOWED_TOOLS" ]] && BASE_CMD+=(--allowedTools "$ALLOWED_TOOLS")
[[ -n "$CLAUDE_ARGS" ]]   && BASE_CMD+=($CLAUDE_ARGS)

CLAUDE_COMMAND="echo '$PROMPT_CONTENT' | ${BASE_CMD[*]}"
export CLAUDE_COMMAND
export PROMPT_CONTENT

# 4. Use minimal Python client to send execute via WebSocket (avoids duplicating logic in websocket_handler)
python - << 'PY'
import asyncio, json, os, sys, websockets

WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8004/ws")
COMMAND       = os.getenv("CLAUDE_COMMAND")

async def main():
    print(f"--- Executing via WebSocket ---\n{COMMAND}\n--------------------------------\n", flush=True)
    try:
        async with websockets.connect(WEBSOCKET_URL, ping_timeout=None) as ws:
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": COMMAND},
                "id": "1"
            }))
            while True:
                msg = await ws.recv()
                print(msg)
                if isinstance(msg, bytes):
                    continue
                try:
                    data = json.loads(msg)
                    if data.get("method") == "process.completed":
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Client error: {e}", file=sys.stderr)
        sys.exit(1)

asyncio.run(main())
PY

# No temp file to cleanup anymore

# The trap (if server was started) cleans up.
