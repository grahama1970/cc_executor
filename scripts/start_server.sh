#!/bin/bash
# Start CC Executor server in the background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.cc_executor"
LOG_FILE="$LOG_DIR/server.log"
PID_FILE="/tmp/cc_executor.pid"

# Create log directory
mkdir -p "$LOG_DIR"

# Kill any existing server
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID: $OLD_PID)"
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Start the server
echo "Starting CC Executor server..."
cd "$PROJECT_ROOT"

# Use nohup with disown to properly detach
nohup python -m uvicorn cc_executor.core.main:app \
    --host 127.0.0.1 \
    --port 8003 \
    >> "$LOG_FILE" 2>&1 &

# Save PID
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# Disown the process so it survives shell exit
disown $SERVER_PID

# Wait a moment for server to start
sleep 2

# Check if server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ Server started successfully (PID: $SERVER_PID)"
    echo "   WebSocket URL: ws://127.0.0.1:8003/ws/mcp"
    echo "   Log file: $LOG_FILE"
    echo "   PID file: $PID_FILE"
else
    echo "❌ Failed to start server"
    echo "   Check log file: $LOG_FILE"
    exit 1
fi