#!/bin/bash
# Kill zombie MCP server processes before starting Claude
# This prevents registration failures due to old processes

echo "🧹 Cleaning up zombie MCP server processes..."

# Count existing MCP processes
ZOMBIE_COUNT=$(ps aux | grep -E "mcp_(arango|d3|tool|kilocode|logger)" | grep -v grep | wc -l)

if [ $ZOMBIE_COUNT -gt 0 ]; then
    echo "Found $ZOMBIE_COUNT zombie MCP processes"
    
    # Kill all MCP server processes
    ps aux | grep -E "mcp_(arango|d3|tool|kilocode|logger)" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    
    # Also kill any uv processes running MCP servers
    ps aux | grep "uv.*mcp_" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    
    # Wait a moment for processes to die
    sleep 1
    
    # Verify they're gone
    REMAINING=$(ps aux | grep -E "mcp_(arango|d3|tool|kilocode|logger)" | grep -v grep | wc -l)
    
    if [ $REMAINING -eq 0 ]; then
        echo "✅ Successfully cleaned up all zombie MCP processes"
    else
        echo "⚠️  Warning: $REMAINING processes still running"
        ps aux | grep -E "mcp_(arango|d3|tool|kilocode|logger)" | grep -v grep
    fi
else
    echo "✅ No zombie MCP processes found"
fi

# Also check for orphaned sentence-transformers processes (from tool-journey)
TRANSFORMER_COUNT=$(ps aux | grep "sentence-transformers" | grep -v grep | wc -l)
if [ $TRANSFORMER_COUNT -gt 0 ]; then
    echo "Found $TRANSFORMER_COUNT orphaned sentence-transformer processes"
    ps aux | grep "sentence-transformers" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    echo "✅ Cleaned up sentence-transformer processes"
fi

echo "🚀 Ready to start Claude with fresh MCP servers"