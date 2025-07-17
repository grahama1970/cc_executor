#!/bin/bash

# stop_dashboard.sh - Stop the Logger Agent Dashboard background processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"

echo "🛑 Stopping Logger Agent Dashboard..."

# Function to stop a process
stop_process() {
    local name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping $name (PID: $pid)..."
            kill "$pid"
            # Wait a moment for graceful shutdown
            sleep 2
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force stopping $name..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo "✅ $name stopped"
        else
            echo "⚠️  $name not running (stale PID file)"
        fi
        rm -f "$pid_file"
    else
        echo "⚠️  $name not running (no PID file)"
    fi
}

# Stop API server
stop_process "API server" "$PID_DIR/api_server.pid"

# Stop Vue dashboard
stop_process "Dashboard" "$PID_DIR/dashboard.pid"

# Kill any remaining uvicorn processes (in case of reload)
pkill -f "uvicorn src.api.dashboard_server:app" 2>/dev/null || true

# Kill any remaining npm/node processes for the dashboard
pkill -f "vite.*dashboard" 2>/dev/null || true

echo ""
echo "✅ All dashboard services stopped"