#!/bin/bash

# start_dashboard_background.sh - Launch the Logger Agent Dashboard as background processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"
LOG_DIR="$PROJECT_ROOT/logs/dashboard"

# Create directories
mkdir -p "$PID_DIR" "$LOG_DIR"

echo "🚀 Starting Logger Agent Dashboard in background..."

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   cd $PROJECT_ROOT && uv venv --python=3.10.11 .venv"
    exit 1
fi

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Check if ArangoDB is running
if ! curl -s http://localhost:8529/_api/version > /dev/null 2>&1; then
    echo "❌ ArangoDB is not running. Please start it first:"
    echo "   docker-compose up -d"
    exit 1
fi

# Function to check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Initialize database if needed
echo "📊 Initializing database..."
cd "$PROJECT_ROOT"
python src/arango_init.py

# Start API server if not already running
API_PID_FILE="$PID_DIR/api_server.pid"
if is_running "$API_PID_FILE"; then
    echo "⚠️  API server already running (PID: $(cat $API_PID_FILE))"
else
    echo "🔧 Starting API server on port 8002..."
    PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH" nohup python -m uvicorn src.api.dashboard_server:app \
        --host 0.0.0.0 \
        --port 8002 \
        --reload \
        > "$LOG_DIR/api_server.log" 2>&1 &
    
    API_PID=$!
    echo $API_PID > "$API_PID_FILE"
    echo "✅ API server started (PID: $API_PID)"
fi

# Give API server time to start
sleep 3

# Check if dashboard directory exists
if [ ! -d "$PROJECT_ROOT/dashboard" ]; then
    echo "❌ Dashboard directory not found. Please run setup_dashboard.sh first."
    exit 1
fi

# Start Vue dashboard if not already running
DASHBOARD_PID_FILE="$PID_DIR/dashboard.pid"
if is_running "$DASHBOARD_PID_FILE"; then
    echo "⚠️  Dashboard already running (PID: $(cat $DASHBOARD_PID_FILE))"
else
    echo "🎨 Starting Vue dashboard on port 5173..."
    cd "$PROJECT_ROOT/dashboard"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing dashboard dependencies..."
        npm install
    fi
    
    # Start dashboard in background
    nohup npm run dev > "$LOG_DIR/dashboard.log" 2>&1 &
    
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > "$DASHBOARD_PID_FILE"
    echo "✅ Dashboard started (PID: $DASHBOARD_PID)"
fi

echo ""
echo "✅ Logger Agent Dashboard is running in background!"
echo ""
echo "📊 API Server: http://localhost:8002"
echo "🎨 Dashboard: http://localhost:5173"
echo "📚 API Docs: http://localhost:8002/docs"
echo ""
echo "📁 Log files:"
echo "   - API: $LOG_DIR/api_server.log"
echo "   - Dashboard: $LOG_DIR/dashboard.log"
echo ""
echo "To stop services, run: ./scripts/stop_dashboard.sh"
echo "To check status, run: ./scripts/status_dashboard.sh"