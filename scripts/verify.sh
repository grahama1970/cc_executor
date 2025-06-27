#!/bin/bash
# Quick verification wrapper

HELPER_PATH="/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py"

if [ $# -eq 0 ]; then
    # Generate marker
    python "$HELPER_PATH"
else
    # Verify marker or check pattern
    python "$HELPER_PATH" "$@"
fi