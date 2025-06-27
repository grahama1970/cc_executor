#!/bin/bash
set -e

echo "--- Starting MCP Bridge E2E Capability Test Suite ---"

# --- Pre-flight Check for required Docker image ---
IMAGE_NAME="cc-executor/claude-code-docker:latest"
echo "--> Checking for required Docker image: $IMAGE_NAME"
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "❌ ERROR: The required Docker image '$IMAGE_NAME' was not found."
    echo "Please ensure it has been built and is available locally."
    exit 1
fi
echo "✅ Docker image found."

# --- Docker Compose for Test Orchestration ---
cat << EOF > docker-compose.e2e.yml
version: '3.8'
services:
  cc-executor-mcp:
    build: 
      # AMENDED: Correct context path from project root
      context: ./prompts/cc_executor_mcp
      dockerfile: Dockerfile
    ports: ["8003:8003"]
    environment:
      - CLAUDE_API_URL=http://claude-api:8000
    networks:
      - mcp-net
    depends_on:
      claude-api:
        condition: service_healthy

  claude-api:
    image: ${IMAGE_NAME}
    container_name: claude-api-e2e-test
    ports:
      - "8002:8000"
    networks:
      - mcp-net
    environment:
      # AMENDED: Ensure local execution by unsetting the API key
      ANTHROPIC_API_KEY: ""
    volumes:
      - ~/.claude:/home/claude-user/.claude:rw
      - ~/.config/claude:/home/claude-user/.config/claude:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      timeout: 10s
      retries: 5

networks:
  mcp-net:
    driver: bridge
EOF

# --- Start Services & Perform Health Check ---
# Cleanup previous runs to ensure a clean state
docker compose -f docker-compose.e2e.yml down --volumes > /dev/null 2>&1

echo "--> Starting services with docker-compose..."
docker compose -f docker-compose.e2e.yml up --build -d

echo "--> Waiting for bridge service to become healthy..."
TIMEOUT=90
INTERVAL=5
ELAPSED=0
BRIDGE_URL="http://localhost:8003/docs" 

while ! curl -s -f "$BRIDGE_URL" > /dev/null; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "❌ ERROR: Bridge service did not become healthy within $TIMEOUT seconds."
        echo "--- Bridge Service Logs ---"
        docker compose -f docker-compose.e2e.yml logs cc-executor-mcp
        exit 1
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo "    ... waiting, ${ELAPSED}s elapsed"
done
echo "✅ Bridge service is up and running."

# --- Run Test and Cleanup ---
TEST_RESULT=0

echo "--> Running basic E2E test..."
# AMENDED: Execute the external Python test client using the correct path from project root
python3 ./prompts/cc_executor_mcp/tests/test_e2e_client.py || TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "--> Running stress tests..."
    python3 ./prompts/cc_executor_mcp/tests/mcp_stress_test.py || TEST_RESULT=$?
fi

if [ $TEST_RESULT -eq 0 ]; then
    echo "--> Running concurrent connection tests..."
    python3 ./prompts/cc_executor_mcp/tests/mcp_concurrent_test.py || TEST_RESULT=$?
fi

if [ $TEST_RESULT -eq 0 ]; then
    echo "--> Running hallucination detection tests..."
    python3 ./prompts/cc_executor_mcp/tests/mcp_hallucination_test.py || TEST_RESULT=$?
fi

echo "--> Cleaning up services..."
docker compose -f docker-compose.e2e.yml down --volumes
rm -f docker-compose.e2e.yml

if [ $TEST_RESULT -eq 0 ]; then
    echo "--- E2E Test Suite Succeeded ---"
    exit 0
else
    echo "--- E2E Test Suite FAILED ---"
    exit 1
fi