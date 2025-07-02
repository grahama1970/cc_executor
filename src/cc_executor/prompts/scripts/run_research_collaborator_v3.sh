#!/bin/bash

# Research Collaborator Runner v3 - Multi-Turn with UUID Verification
# ------------------------------------------------------------------------------
# This version supports multi-turn research with both perplexity and gemini
# 
# Usage:
#   REQUEST="Your multi-turn research request" bash run_research_collaborator_v3.sh
#
# Or with a request file:
#   REQUEST_FILE=/path/to/request.md bash run_research_collaborator_v3.sh
# ------------------------------------------------------------------------------

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$PROJECT_ROOT"

# Template is the multi-turn version
TEMPLATE_FILE="src/cc_executor/prompts/commands/research-collaborator-multi-turn.md"

# Request can come from REQUEST env var or REQUEST_FILE
if [[ -n "${REQUEST:-}" ]]; then
    # Create temporary request file from REQUEST
    REQUEST_FILE=$(mktemp "${TMPDIR:-/tmp}/research_request_XXXXXX.md")
    echo "# Research Request" > "$REQUEST_FILE"
    echo "" >> "$REQUEST_FILE"
    echo "$REQUEST" >> "$REQUEST_FILE"
    trap "rm -f $REQUEST_FILE" EXIT
elif [[ -n "${REQUEST_FILE:-}" ]]; then
    # Use provided request file
    if [[ ! -f "$REQUEST_FILE" ]]; then
        echo "ERROR: REQUEST_FILE does not exist: $REQUEST_FILE" >&2
        exit 1
    fi
else
    # Default to tmp/multi_turn_research_request.md
    REQUEST_FILE="tmp/multi_turn_research_request.md"
    if [[ ! -f "$REQUEST_FILE" ]]; then
        echo "ERROR: No REQUEST provided and default request file not found: $REQUEST_FILE" >&2
        echo "Usage: REQUEST=\"Your multi-turn request\" $0" >&2
        exit 1
    fi
fi

echo "Using request file: $REQUEST_FILE"
echo "Request content:"
cat "$REQUEST_FILE"
echo ""
echo "---"

# Build the prompt by replacing the placeholder
PROMPT_CONTENT=$(cat "$TEMPLATE_FILE" | sed "s|@RESEARCH_REQUEST_FILE|@$PROJECT_ROOT/$REQUEST_FILE|g")

# Multi-turn requests need more time
TIMEOUT="${TIMEOUT:-900}"  # 15 minutes default for multi-turn

# Build Claude command
CLAUDE_CMD=(
    claude -p "$PROMPT_CONTENT"
    --dangerously-skip-permissions
)

# Add MCP config if it exists
MCP_FILE="$PROJECT_ROOT/.mcp.json"
if [[ -f "$MCP_FILE" ]]; then
    CLAUDE_CMD+=(--mcp-config "$MCP_FILE")
fi

# Add allowed tools including both perplexity and brave-search
CLAUDE_CMD+=(--allowedTools "mcp__perplexity-ask mcp__brave-search")

# Execute with timeout
echo "Executing multi-turn research with ${TIMEOUT}s timeout..."
echo "Command: ${CLAUDE_CMD[*]}"
echo "---"

# Generate UUID for this execution
EXEC_UUID=$(uuidgen)
echo "Execution UUID: $EXEC_UUID"
echo "---"

if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT" "${CLAUDE_CMD[@]}"
else
    # Fallback without timeout
    "${CLAUDE_CMD[@]}"
fi

echo ""
echo "---"
echo "Verifying execution UUID in output..."
if grep -q "$EXEC_UUID" <<< "$OUTPUT" 2>/dev/null; then
    echo "✅ UUID verified in output"
else
    echo "⚠️  UUID not found in output (may need to check logs)"
fi