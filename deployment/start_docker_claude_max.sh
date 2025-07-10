#!/bin/bash
# Start Docker with Claude Max Plan authentication

echo "🚀 Starting CC Executor Docker for Claude Max Plan users..."

# Export user ID for proper permissions
export UID=$(id -u)
export GID=$(id -g)

# Check if credentials exist
if [ ! -f ~/.claude/.credentials.json ]; then
    echo "❌ Error: Claude credentials not found at ~/.claude/.credentials.json"
    echo "Please ensure you're logged into Claude Code first."
    exit 1
fi

# Create docker-compose override for Claude Max users
cat > docker-compose.override.yml << EOF
services:
  cc_execute:
    user: "${UID}:${GID}"
    environment:
      # Claude Max Plan - no API key needed
      ANTHROPIC_API_KEY: ""
EOF

echo "✅ Created docker-compose.override.yml with user permissions"

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check health
echo "🏥 Checking service health..."
curl -s http://localhost:8001/health | jq . || echo "API not ready yet"

echo ""
echo "✅ Docker services started!"
echo ""
echo "Test WebSocket with:"
echo "  python ../tests/test_docker_execution.py"
echo ""
echo "Or test Claude directly:"
echo "  docker exec -it cc_execute claude -p 'Say hello'"
echo ""
echo "View logs:"
echo "  docker compose logs -f"