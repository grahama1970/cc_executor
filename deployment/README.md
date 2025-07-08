# CC Executor Docker Deployment

This directory contains everything needed to deploy CC Executor in a safe, containerized environment.

## Quick Start

1. **Ensure Claude is authenticated** (Claude CLI uses OAuth, not API keys):
   ```bash
   # On your host machine (not in Docker):
   claude --version  # Should show version if authenticated
   # If not authenticated, run: claude /login
   ```

2. **Start the services**:
   ```bash
   docker-compose up -d
   ```

3. **Check health**:
   ```bash
   curl http://localhost:8001/health  # REST API
   # WebSocket is on port 8004 (ws://localhost:8004/ws/mcp)
   ```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   REST API      │────▶│ WebSocket Server │────▶│    Redis    │
│  (Port 8001)    │     │   (Port 8004)    │     │ (Port 6380) │
└─────────────────┘     └──────────────────┘     └─────────────┘
        │                        │
        └────────────┬───────────┘
                     │
              ┌──────▼──────┐
              │ Claude CLI   │
              │ (OAuth Auth) │
              └─────────────┘
```

## Services

### 1. Redis
- Provides session state persistence
- Caches execution history
- Enables distributed deployments

### 2. WebSocket Server
- Core CC Executor service
- Handles Claude command execution
- Manages process lifecycle
- Provides streaming output

### 3. REST API (Optional)
- FastAPI wrapper for easier integration
- RESTful endpoints for task execution
- Suitable for webhook integrations

## Security Features

1. **Resource Limits**: Each container has CPU and memory limits
2. **Non-root Users**: Services run as unprivileged users
3. **Network Isolation**: Services communicate only through defined networks
4. **Volume Mounts**: Limited and read-only where possible

## Using the REST API

```python
import requests

# Execute a task list
response = requests.post("http://localhost:8000/execute", json={
    "tasks": [
        "Task 1: Create a Python web scraper",
        "Task 2: Add error handling to the scraper",
        "Task 3: Create unit tests"
    ],
    "timeout_per_task": 300
})

result = response.json()
print(f"Execution ID: {result['execution_id']}")
print(f"Completed: {result['completed_tasks']}/{result['total_tasks']}")
```

## Using WebSocket Directly

```python
from cc_executor import WebSocketClient
import asyncio

async def run_tasks():
    client = WebSocketClient(host="localhost", port=8004)
    await client.connect()
    
    result = await client.execute_command('claude -p "Create a function"')
    print(result)
    
    await client.disconnect()

asyncio.run(run_tasks())
```

## Environment Variables

### Authentication
- Claude CLI uses **OAuth authentication** from mounted `~/.claude` directory
- No `ANTHROPIC_API_KEY` needed - Claude uses browser-based authentication
- The `~/.claude` directory from your host is mounted in the container

### Optional
- `LOG_LEVEL`: Logging level (default: INFO)
- `MAX_SESSIONS`: Maximum concurrent sessions (default: 100)
- `SESSION_TIMEOUT`: Session timeout in seconds (default: 3600)
- `STREAM_TIMEOUT`: Stream timeout in seconds (default: 600)

## Monitoring

Check logs:
```bash
docker-compose logs -f websocket
docker-compose logs -f api
```

Check Redis:
```bash
docker exec -it cc_executor_redis redis-cli
> KEYS *
> INFO clients
```

## Scaling

For production deployments:

1. Use Docker Swarm or Kubernetes
2. Put a load balancer in front of multiple WebSocket instances
3. Use Redis Cluster for high availability
4. Add monitoring with Prometheus/Grafana

## Troubleshooting

### Service won't start
- Check logs: `docker-compose logs cc_execute`
- Verify Claude is authenticated on host: `claude --version`
- Check ~/.claude directory exists and is mounted

### Connection refused
- Check service health: `docker-compose ps`
- Verify ports aren't already in use
- Check firewall rules

### Out of memory
- Adjust resource limits in docker-compose.yml
- Monitor with `docker stats`