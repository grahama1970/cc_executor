#!/bin/bash

# status_dashboard.sh - Check status of Logger Agent Dashboard services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"
LOG_DIR="$PROJECT_ROOT/logs/dashboard"

echo "📊 Logger Agent Dashboard Status"
echo "================================"

# Function to check process status
check_process() {
    local name=$1
    local pid_file=$2
    local port=$3
    local log_file=$4
    
    echo ""
    echo "🔍 $name:"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "   ✅ Running (PID: $pid)"
            
            # Check if port is listening
            if [ -n "$port" ]; then
                if lsof -i:$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                    echo "   ✅ Listening on port $port"
                else
                    echo "   ❌ Not listening on port $port"
                fi
            fi
            
            # Show recent log entries
            if [ -f "$log_file" ]; then
                echo "   📄 Recent logs:"
                tail -5 "$log_file" | sed 's/^/      /'
            fi
        else
            echo "   ❌ Not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        echo "   ❌ Not running"
    fi
}

# Check ArangoDB
echo ""
echo "🔍 ArangoDB:"
if curl -s http://localhost:8529/_api/version > /dev/null 2>&1; then
    echo "   ✅ Running on port 8529"
else
    echo "   ❌ Not running"
fi

# Check API server
check_process "API Server" "$PID_DIR/api_server.pid" "8000" "$LOG_DIR/api_server.log"

# Check dashboard
check_process "Vue Dashboard" "$PID_DIR/dashboard.pid" "5173" "$LOG_DIR/dashboard.log"

# Check API health endpoint
echo ""
echo "🔍 API Health Check:"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    health_response=$(curl -s http://localhost:8000/health)
    echo "   ✅ API is healthy"
    echo "   📊 Response: $health_response"
else
    echo "   ❌ API health check failed"
fi

# Show resource usage
echo ""
echo "📈 Resource Usage:"
if [ -f "$PID_DIR/api_server.pid" ] && ps -p $(cat "$PID_DIR/api_server.pid") > /dev/null 2>&1; then
    api_pid=$(cat "$PID_DIR/api_server.pid")
    api_stats=$(ps -p $api_pid -o %cpu,%mem,etime,comm | tail -1)
    echo "   API Server: $api_stats"
fi

if [ -f "$PID_DIR/dashboard.pid" ] && ps -p $(cat "$PID_DIR/dashboard.pid") > /dev/null 2>&1; then
    dash_pid=$(cat "$PID_DIR/dashboard.pid")
    dash_stats=$(ps -p $dash_pid -o %cpu,%mem,etime,comm | tail -1)
    echo "   Dashboard: $dash_stats"
fi

echo ""
echo "================================"
echo "To start services: ./scripts/start_dashboard_background.sh"
echo "To stop services: ./scripts/stop_dashboard.sh"
echo "To view logs: tail -f $LOG_DIR/*.log"