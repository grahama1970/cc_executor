#!/bin/bash

# Research Collaborator Runner v2 - Separated Question and Template
# ------------------------------------------------------------------------------
# This version keeps the research question separate from the template for clarity
# 
# Usage:
#   REQUEST="Your research question" bash run_research_collaborator_v2.sh
#
# Or with a question file:
#   QUESTION_FILE=/path/to/question.md bash run_research_collaborator_v2.sh
# ------------------------------------------------------------------------------

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$PROJECT_ROOT"

# Template is fixed
TEMPLATE_FILE="src/cc_executor/prompts/commands/research-collaborator-template.md"

# Question can come from REQUEST env var or QUESTION_FILE
if [[ -n "${REQUEST:-}" ]]; then
    # Create temporary question file from REQUEST
    QUESTION_FILE=$(mktemp "${TMPDIR:-/tmp}/research_question_XXXXXX.md")
    echo "# Research Question" > "$QUESTION_FILE"
    echo "" >> "$QUESTION_FILE"
    echo "$REQUEST" >> "$QUESTION_FILE"
    trap "rm -f $QUESTION_FILE" EXIT
elif [[ -n "${QUESTION_FILE:-}" ]]; then
    # Use provided question file
    if [[ ! -f "$QUESTION_FILE" ]]; then
        echo "ERROR: QUESTION_FILE does not exist: $QUESTION_FILE" >&2
        exit 1
    fi
else
    # Default to tmp/research_question.md
    QUESTION_FILE="tmp/research_question.md"
    if [[ ! -f "$QUESTION_FILE" ]]; then
        echo "ERROR: No REQUEST provided and default question file not found: $QUESTION_FILE" >&2
        echo "Usage: REQUEST=\"Your question\" $0" >&2
        exit 1
    fi
fi

echo "Using question file: $QUESTION_FILE"
echo "Question content:"
cat "$QUESTION_FILE"
echo ""

# Build the prompt by replacing the placeholder
PROMPT_CONTENT=$(cat "$TEMPLATE_FILE" | sed "s|@RESEARCH_QUESTION_FILE|@$PROJECT_ROOT/$QUESTION_FILE|g")

# Optional: Add timeout based on complexity
TIMEOUT="${TIMEOUT:-300}"  # 5 minutes default

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

# Execute with timeout
echo "Executing research with ${TIMEOUT}s timeout..."
echo "Command: ${CLAUDE_CMD[*]}"
echo "---"

if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT" "${CLAUDE_CMD[@]}"
else
    # Fallback without timeout
    "${CLAUDE_CMD[@]}"
fi