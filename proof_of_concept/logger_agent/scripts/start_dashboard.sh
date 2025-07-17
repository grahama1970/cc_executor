#!/bin/bash

# start_dashboard.sh - Launch the Logger Agent Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Starting Logger Agent Dashboard..."

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

# Initialize database if needed
echo "📊 Initializing database..."
cd "$PROJECT_ROOT"
python src/arango_init.py

# Start the API server
echo "🔧 Starting API server on port 8000..."
python -m uvicorn src.api.dashboard_server:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Give API server time to start
sleep 3

# Check if dashboard directory exists
if [ ! -d "$PROJECT_ROOT/dashboard" ]; then
    echo "❌ Dashboard directory not found. Please run setup_dashboard.sh first."
    kill $API_PID
    exit 1
fi

# Start the Vue dashboard
echo "🎨 Starting Vue dashboard on port 5173..."
cd "$PROJECT_ROOT/dashboard"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dashboard dependencies..."
    npm install
fi

# Start dashboard
npm run dev &
DASHBOARD_PID=$!

echo ""
echo "✅ Logger Agent Dashboard is running!"
echo ""
echo "📊 API Server: http://localhost:8000"
echo "🎨 Dashboard: http://localhost:5173"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $API_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true
    echo "✅ Services stopped"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Wait for both processes
wait $API_PID $DASHBOARD_PID