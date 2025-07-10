#!/bin/bash
# Start MCP local WebSocket server

cd /home/graham/workspace/experiments/cc_executor
export PYTHONPATH=/home/graham/workspace/experiments/cc_executor/src

# Kill any existing server on port 8003
lsof -ti:8003 | xargs -r kill -9

# Start the server
echo "Starting MCP Local WebSocket server on port 8003..."
python -m cc_executor.core.websocket_handler