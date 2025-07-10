#!/bin/bash
# Start CC Executor server in a tmux session

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HOME/.cc_executor/server.log"
PID_FILE="/tmp/cc_executor.pid"
SESSION_NAME="cc_executor"

# Kill any existing tmux session
tmux kill-session -t "$SESSION_NAME" 2>/dev/null

# Kill any existing server process
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID: $OLD_PID)"
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Create log directory
mkdir -p "$HOME/.cc_executor"

# Start server in tmux session
echo "Starting CC Executor server in tmux session..."
cd "$PROJECT_ROOT"

# Create a detached tmux session and run the server
tmux new-session -d -s "$SESSION_NAME" "python -m uvicorn cc_executor.core.main:app --host 127.0.0.1 --port 8003 2>&1 | tee -a '$LOG_FILE'"

# Wait for server to start
sleep 3

# Get the PID of the uvicorn process
SERVER_PID=$(pgrep -f "uvicorn cc_executor.core.main:app")

if [ -n "$SERVER_PID" ]; then
    echo "$SERVER_PID" > "$PID_FILE"
    echo "✅ Server started successfully (PID: $SERVER_PID)"
    echo "   Tmux session: $SESSION_NAME"
    echo "   WebSocket URL: ws://127.0.0.1:8003/ws/mcp"
    echo "   Log file: $LOG_FILE"
    echo "   "
    echo "   To view logs: tmux attach -t $SESSION_NAME"
    echo "   To detach: Ctrl+B then D"
else
    echo "❌ Failed to start server"
    echo "   Check tmux session: tmux attach -t $SESSION_NAME"
    exit 1
fi