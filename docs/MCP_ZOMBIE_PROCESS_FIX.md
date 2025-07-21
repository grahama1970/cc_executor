# MCP Zombie Process Fix

## Problem
MCP servers create zombie processes that prevent proper registration with Claude. This was discovered when 47 zombie processes were found running since July 16th, preventing the servers from being available as `mcp__*` tools.

## Solution
Added a StartUp hook that automatically kills zombie MCP processes before Claude starts.

### Hook Configuration

1. **Script Location**: `.claude/hooks/kill_zombie_mcp.py`
   - Kills all MCP server processes (arango, d3, tool, kilocode, logger)
   - Cleans up orphaned sentence-transformer processes
   - Removes large MCP log files (>100MB)
   - Sets MCP_DEBUG environment variables

2. **Registration**: Added to `.claude/settings.json`
   ```json
   "StartUp": {
     "command": "python",
     "args": [
       "/home/graham/workspace/experiments/cc_executor/.claude/hooks/kill_zombie_mcp.py"
     ]
   }
   ```

### Manual Cleanup
If needed, run manually:
```bash
# Kill all zombie MCP processes
/home/graham/workspace/experiments/cc_executor/scripts/kill_zombie_mcp_servers.sh

# Or use the Python script
python /home/graham/workspace/experiments/cc_executor/.claude/hooks/kill_zombie_mcp.py
```

### What This Fixes
- MCP servers not appearing as `mcp__*` tools
- "Tool not available" errors despite correct configuration
- Multiple instances of the same server running
- Port/resource conflicts preventing registration

### Prevention
The StartUp hook runs automatically when Claude starts, ensuring:
- Clean slate for MCP servers
- No port conflicts
- Proper tool registration
- Available as `mcp__server-name__tool-name`

## Verification
After reloading Claude, these should be available:
- `mcp__arango-tools__*`
- `mcp__d3-visualizer__*`
- `mcp__tool-journey__*`
- `mcp__tool-sequence-optimizer__*`
- `mcp__kilocode-review__*`