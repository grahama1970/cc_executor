#!/bin/bash
set -e

echo "--- Starting True MCP Service Test Suite ---"

# Cleanup previous runs
docker ps -a | grep -E "cc-executor-mcp" | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1 || true

# Build the Docker image
echo "--> Building Docker image..."
docker build -t cc-executor-mcp:latest ./prompts/cc_executor_mcp

# Run the container
echo "--> Running Docker container..."
docker run -d --name cc-executor-mcp-test -p 8003:8003 cc-executor-mcp:latest

# Health check
echo "--> Waiting for service to become healthy..."
TIMEOUT=60
INTERVAL=3
ELAPSED=0
while ! curl -s -f http://localhost:8003/docs > /dev/null; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "❌ ERROR: Service did not become healthy within $TIMEOUT seconds."
        docker logs cc-executor-mcp-test
        docker rm -f cc-executor-mcp-test
        exit 1
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done
echo "✅ Service is up and running."

# Run tests
TEST_RESULT=0

echo "--> Running bidirectional control test..."
python3 ./prompts/cc_executor_mcp/tests/test_bidirectional_control.py || TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "--> Running basic E2E test (updated for direct execution)..."
    python3 ./prompts/cc_executor_mcp/tests/test_e2e_client.py || TEST_RESULT=$?
fi

if [ $TEST_RESULT -eq 0 ]; then
    echo "--> Running stress tests..."
    python3 ./prompts/cc_executor_mcp/tests/mcp_stress_test.py || TEST_RESULT=$?
fi

# Cleanup
echo "--> Cleaning up..."
docker rm -f cc-executor-mcp-test > /dev/null 2>&1 || true

if [ $TEST_RESULT -eq 0 ]; then
    echo "--- Test Suite Succeeded ---"
else
    echo "--- Test Suite FAILED ---"
fi
exit $TEST_RESULT