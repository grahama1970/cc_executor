#!/bin/bash
# This script sets the correct environment and runs the WebSocket server.

# Add the local claude commands to the PATH
export PATH="$HOME/.claude/commands:$PATH"

# Activate the virtual environment and run the server
# The `uv run` command correctly handles the virtual environment's python.
echo "Starting WebSocket server with corrected PATH..."
uv run python src/cc_executor/core/websocket_handler.py
