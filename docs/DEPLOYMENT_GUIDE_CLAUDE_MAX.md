
# CC Executor Deployment Guide for Claude Max Plan Users

## Quick Start (5 minutes)

### 1. Local MCP Server (Fastest)

```bash
# Add to your Claude Desktop config (~/.claude/claude_desktop_config.json)
{
  "mcpServers": {
    "cc-executor": {
      "command": "python",
      "args": ["-m", "cc_executor.servers.mcp_cc_execute"],
      "cwd": "/home/graham/workspace/experiments/cc_executor"
    }
  }
}

# Restart Claude Desktop
# The cc_execute tool is now available!
```

### 2. Docker Deployment (More isolated)

```bash
cd deployment

# Use the Claude Max starter script
./start_docker_claude_max.sh

# Or manually:
export UID=$(id -u)
export GID=$(id -g)
docker compose up -d
```

## Understanding Authentication

### Claude Max Plan
- Authentication stored in `~/.claude/.credentials.json`
- No API key needed
- Docker needs permission to read credentials

### Why Docker Authentication Fails
1. Credentials file has 600 permissions (owner-only)
2. Docker runs as `appuser`, not your user
3. Solution: Run Docker as your user ID

## Testing Your Deployment

### Test MCP Server
```bash
# In Claude Desktop, test basic execution:
/cc_execute echo "Hello from CC Executor"

# Test with JSON output:
/cc_execute claude -p "What is 2+2? Return JSON: {\"answer\": 4}"

# Verify anti-hallucination UUID tracking:
/verify_execution <uuid-from-previous-command>
```

### Test Docker
```bash
# 1. Test WebSocket execution
python ../tests/test_docker_execution.py

# 2. Test Claude directly in container
docker exec -it cc_execute claude -p "Say hello"

# 3. Verify Redis connection
docker exec -it cc_execute python -c "import redis; r=redis.Redis(host='redis'); print('Redis:', r.ping())"

# 4. Check real-time logs
docker compose logs -f cc_execute

# 5. Test concurrent execution
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "echo test", "timeout": 30}'
```

## Troubleshooting

### "Claude hangs in Docker"
```bash
# 1. Check if credentials are mounted correctly
docker exec -it cc_execute ls -la /home/appuser/.claude/
# Should show .credentials.json with proper permissions

# 2. Test Claude CLI directly
docker exec -it cc_execute claude --version
# Should return version without hanging

# 3. Debug with verbose output
docker exec -it cc_execute claude -p "test" --verbose

# 4. If still hanging, check the override file:
cat docker-compose.override.yml
# Must have: user: "${UID}:${GID}"
```

### "Permission denied errors"
```bash
# 1. Verify your UID/GID
echo "UID=$UID GID=$GID"

# 2. Recreate override file
./start_docker_claude_max.sh

# 3. Rebuild with correct permissions
docker compose down
docker compose build --no-cache
docker compose up -d
```

### "WebSocket connection issues"
```bash
# 1. Check all services are healthy
docker compose ps
# All should be "running" with (healthy)

# 2. Test each endpoint
curl http://localhost:8001/health  # API health
curl http://localhost:8001/status  # Detailed status

# 3. Test WebSocket directly
websocat ws://localhost:8004/ws
# Type: {"jsonrpc":"2.0","method":"execute","params":{"command":"echo test"},"id":1}

# 4. Check for port conflicts
lsof -i :8001,8004
```

### "Redis connection failed"
```bash
# 1. Check Redis is running
docker exec -it cc_executor_redis redis-cli ping
# Should return: PONG

# 2. Test from cc_execute container
docker exec -it cc_execute redis-cli -h redis ping

# 3. Check Redis logs
docker compose logs redis
```

## Advanced Configuration

### Custom MCP Tools Integration
```json
{
  "mcpServers": {
    "cc-executor": {
      "command": "python",
      "args": ["-m", "cc_executor.servers.mcp_cc_execute"],
      "cwd": "/home/graham/workspace/experiments/cc_executor"
    },
    "perplexity-ask": {
      "command": "mcp-server-perplexity-ask"
    },
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "your-token"
      }
    }
  }
}
```

### Performance Optimization

#### 1. Redis Timeout Predictions
```bash
# Enable Redis-based timeout learning
docker exec -it cc_execute python -c "
import redis
r = redis.Redis(host='redis')
# CC Executor automatically learns from execution times
print('Redis memory usage:', r.info()['used_memory_human'])
"
```

#### 2. Concurrent Execution
```bash
# Docker supports multiple concurrent executions
# Each gets its own process group for isolation
for i in {1..5}; do
  curl -X POST http://localhost:8001/execute \
    -H "Content-Type: application/json" \
    -d "{\"command\": \"echo Task $i\", \"timeout\": 30}" &
done
wait
```

#### 3. Resource Limits
```yaml
# Add to docker-compose.override.yml
services:
  cc_execute:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Production Deployment

#### 1. Secure Setup
```bash
# Use Docker secrets for sensitive data
docker secret create claude_creds ~/.claude/.credentials.json

# Update compose file to use secrets
services:
  cc_execute:
    secrets:
      - claude_creds
    # Mount as: /run/secrets/claude_creds
```

#### 2. Monitoring
```bash
# Add health check monitoring
# CC Executor exposes health at /health

# Example docker-compose addition:
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    # Configure to scrape /health endpoint
```

#### 3. Load Balancing
```nginx
# Nginx config for WebSocket load balancing
upstream cc_executor {
    server localhost:8004;
    server localhost:8005;  # If running multiple instances
}

location /ws {
    proxy_pass http://cc_executor;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Integration Examples

#### With CI/CD
```yaml
# GitHub Actions example
- name: Execute Claude Task
  run: |
    curl -X POST http://cc-executor:8001/execute \
      -H "Content-Type: application/json" \
      -d '{
        "command": "claude -p \"Review this PR and suggest improvements\"",
        "timeout": 300
      }'
```

#### With Python Scripts
```python
import asyncio
import websockets
import json

async def execute_task(command):
    uri = "ws://localhost:8004/ws"
    async with websockets.connect(uri) as ws:
        # Send JSON-RPC request
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "execute",
            "params": {"command": command, "timeout": 120},
            "id": 1
        }))
        
        # Process streaming responses
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print(data)
            if "result" in data or "error" in data:
                break

# Run it
asyncio.run(execute_task('claude -p "Write a haiku"'))
```

## Common Use Cases

### 1. Automated Code Reviews
```bash
/cc_execute claude -p "Review this code for security issues: $(cat app.py)"
```

### 2. Documentation Generation
```bash
/cc_execute claude -p "Generate API documentation for all Python files in src/"
```

### 3. Test Generation
```bash
/cc_execute claude -p "Write comprehensive tests for the WebSocket handler"
```

### 4. Batch Processing
```bash
# Process multiple files
for file in *.md; do
  /cc_execute claude -p "Summarize: $(cat $file)" > summaries/$file.summary
done
```

## Summary

CC Executor provides flexible deployment options for Claude Max Plan users:

1. **Local MCP**: Zero-config integration with Claude Desktop
2. **Docker**: Scalable, isolated environment with WebSocket API

Key benefits:
- ✅ No API keys needed for Claude Max Plan
- ✅ Automatic authentication via ~/.claude/
- ✅ Redis-based timeout learning
- ✅ Anti-hallucination UUID tracking
- ✅ Concurrent execution support
- ✅ Production-ready with monitoring

Choose local MCP for simplicity, Docker for isolation and scalability!