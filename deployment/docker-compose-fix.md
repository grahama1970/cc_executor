# Self-Improving Docker Compose Configuration

## Objective
Iteratively improve the docker-compose.yml until it successfully runs cc_executor with proper port allocation and environment configuration.

## Current Issues to Fix
1. Port 8003 conflicts - need dynamic port allocation or conflict detection
2. ANTHROPIC_API_KEY passthrough working but shows warning
3. Redis connection issues in hooks

## Iteration Process

### Step 1: Port Conflict Detection
Instead of hardcoding ports, use dynamic allocation:

```yaml
services:
  cc_execute:
    ports:
      - "8001:8000"  # FastAPI - could also be dynamic
      - "8003-8010:8003"  # Try range of ports for WebSocket
```

### Step 2: Environment Variable Validation
Add healthcheck that validates required environment:

```yaml
healthcheck:
  test: |
    curl -f http://localhost:8000/health &&
    test -n "$${ANTHROPIC_API_KEY:-}" || echo "Warning: No API key"
```

### Step 3: Redis Connection Fix
Ensure Redis URL uses service name not localhost:

```yaml
environment:
  REDIS_URL: redis://redis:6379  # Use service name, not localhost
```

### Step 4: Add Port Discovery
Create a startup script that finds available ports:

```bash
#!/bin/bash
# find_free_port.sh
for port in {8003..8010}; do
  if ! nc -z localhost $port 2>/dev/null; then
    echo $port
    break
  fi
done
```

### Step 5: Complete Configuration Template
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: cc_executor_redis_${INSTANCE_ID:-default}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - cc_executor_net

  cc_execute:
    build:
      context: ..
      dockerfile: deployment/Dockerfile
    container_name: cc_execute_${INSTANCE_ID:-default}
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      PYTHONUNBUFFERED: "1"
      REDIS_URL: redis://redis:6379
      DISABLE_VENV_WRAPPING: "1"
      RUNNING_IN_DOCKER: "1"
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      # Dynamic port configuration
      WEBSOCKET_PORT: ${WEBSOCKET_PORT:-8003}
      API_PORT: ${API_PORT:-8000}
    ports:
      # Use environment variables for flexible port mapping
      - "${API_EXTERNAL_PORT:-8001}:8000"
      - "${WS_EXTERNAL_PORT:-8004}:8003"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ${CLAUDE_HOME:-~/.claude}:/home/appuser/.claude:ro
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: |
        curl -f http://localhost:8000/health || exit 1
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - cc_executor_net

networks:
  cc_executor_net:
    name: cc_executor_network_${INSTANCE_ID:-default}
    driver: bridge

volumes:
  redis_data:
    driver: local
```

### Step 6: Wrapper Script
Create `docker-run.sh`:

```bash
#!/bin/bash
# Auto-detect free ports and set environment

# Find free ports
find_free_port() {
  local start_port=$1
  for port in $(seq $start_port $((start_port + 10))); do
    if ! lsof -i:$port >/dev/null 2>&1; then
      echo $port
      return
    fi
  done
  echo "No free port found" >&2
  exit 1
}

# Set instance ID for multiple deployments
export INSTANCE_ID=${INSTANCE_ID:-$(date +%s)}

# Find free ports if not set
export API_EXTERNAL_PORT=${API_EXTERNAL_PORT:-$(find_free_port 8001)}
export WS_EXTERNAL_PORT=${WS_EXTERNAL_PORT:-$(find_free_port 8003)}

echo "Starting cc_executor:"
echo "  API Port: $API_EXTERNAL_PORT"
echo "  WebSocket Port: $WS_EXTERNAL_PORT"
echo "  Instance ID: $INSTANCE_ID"

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Warning: ANTHROPIC_API_KEY not set - Claude CLI features will be limited"
fi

# Start services
docker compose -p cc_executor_$INSTANCE_ID up -d

# Show connection info
echo ""
echo "Services started successfully!"
echo "API endpoint: http://localhost:$API_EXTERNAL_PORT"
echo "WebSocket endpoint: ws://localhost:$WS_EXTERNAL_PORT/ws/mcp"
```

## Testing Protocol

1. Run the wrapper script:
   ```bash
   ./docker-run.sh
   ```

2. Test WebSocket connection:
   ```bash
   wscat -c ws://localhost:$WS_EXTERNAL_PORT/ws/mcp
   ```

3. Test API endpoint:
   ```bash
   curl http://localhost:$API_EXTERNAL_PORT/health
   ```

4. If any test fails, check logs:
   ```bash
   docker logs cc_execute_$INSTANCE_ID
   ```

## Success Criteria
- [ ] No port conflicts on startup
- [ ] WebSocket streaming works
- [ ] API endpoint responds
- [ ] Redis connection established
- [ ] Multiple instances can run simultaneously
- [ ] Graceful handling of missing ANTHROPIC_API_KEY

## Iteration Notes
After each test, update this document with:
- What worked
- What failed  
- Next improvement to try

Continue iterating until all success criteria are met.