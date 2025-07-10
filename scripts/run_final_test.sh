#!/bin/bash
# Run final comprehensive test with all services

echo "🚀 Starting CC Executor Comprehensive Test"
echo "=========================================="

# Kill any existing processes on ports
echo "Cleaning up existing processes..."
lsof -ti:8003 | xargs -r kill -9 2>/dev/null
sleep 1

# Start MCP local server
echo "Starting MCP local server on port 8003..."
python src/cc_executor/core/websocket_handler.py > logs/mcp_local_final_run.log 2>&1 &
MCP_PID=$!
echo "MCP server started with PID $MCP_PID"

# Wait for server to be ready
echo "Waiting for server to be ready..."
sleep 5

# Check if server is running
if ps -p $MCP_PID > /dev/null; then
    echo "✅ MCP server is running"
else
    echo "❌ MCP server failed to start. Check logs/mcp_local_final_run.log"
    exit 1
fi

# Run the comprehensive test
echo -e "\nRunning comprehensive test..."
python tests/stress/comprehensive_test_final.py

# Kill the MCP server
echo -e "\nCleaning up..."
kill $MCP_PID 2>/dev/null

echo -e "\nTest complete!"