# CC Executor Quick Start - Claude Max Plan

## 🚀 Fastest Setup (2 minutes)

### Option 1: Local MCP (Recommended)
```bash
# 1. Add to ~/.claude/claude_desktop_config.json
{
  "mcpServers": {
    "cc-executor": {
      "command": "python",
      "args": ["-m", "cc_executor.servers.mcp_cc_execute"],
      "cwd": "/home/graham/workspace/experiments/cc_executor"
    }
  }
}

# 2. Restart Claude Desktop
# 3. Done! Use: /cc_execute <your command>
```

### Option 2: Docker (5 minutes)
```bash
cd deployment
./start_docker_claude_max.sh
# Done! WebSocket at ws://localhost:8004/ws
```

## 🧪 Quick Test
```bash
# In Claude Desktop:
/cc_execute echo "CC Executor is working!"
/cc_execute claude -p "What is 2+2? Return JSON: {\"answer\": 4}"
```

## 🔧 If Something Goes Wrong

### Claude hangs?
```bash
# You're probably not running as your user
cat docker-compose.override.yml
# Should show: user: "${UID}:${GID}"
```

### Permission denied?
```bash
# Re-run the start script
./start_docker_claude_max.sh
```

### Still not working?
```bash
# Check credentials are accessible
ls -la ~/.claude/.credentials.json
# Should be readable by your user
```

## 📚 Full Docs
- [Complete Deployment Guide](./DEPLOYMENT_GUIDE_CLAUDE_MAX.md)
- [Authentication Fix Guide](./CLAUDE_MAX_AUTHENTICATION_FIX.md)
- [Architecture Overview](./current/architecture/)

---
Remember: Claude Max Plan = No API keys needed! 🎉