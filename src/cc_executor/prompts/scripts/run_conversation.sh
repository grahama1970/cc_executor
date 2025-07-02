#!/bin/bash

# This script provides the full, correct environment to run the conversational task.

# Ensure we are in the project root
cd "/home/graham/workspace/experiments/cc_executor" || exit

# 1. Set the environment variables
export PATH="$HOME/.claude/commands:$PATH"
export PYTHONPATH="$(pwd)/src"

echo "--- Environment Setup ---"
echo "PATH: $PATH"
echo "PYTHONPATH: $PYTHONPATH"
echo "-----------------------"

# 2. Start the server in the background
echo "Starting WebSocket server..."
uv run python -m cc_executor.core.websocket_handler & 
SERVER_PID=$!

# 3. Use a trap to ensure the server is killed on script exit
trap 'echo "Cleaning up server PID $SERVER_PID..."; kill $SERVER_PID' EXIT

# 4. Wait for the server to be ready
echo "Waiting for server to initialize (5 seconds)..."
sleep 5

# 5. Define the single, complex prompt for Claude
CLAUDE_PROMPT="With a maximum of 3 conversation turns, perform the following task:\n\n**Turn 1: Concurrent Research**\nConcurrently execute the following two tasks:\n1. Use the \`mcp__perplexity-ask\` tool to research the question: 'What is the fastest, most optimized method in Python for multiplying two matrices?'.\n2. Use the \`Bash\` tool to execute the prompt at \`@src/cc_executor/prompts/commands/ask-gemini-cli.md\` with the same question.\n\nAfter both tools return their results, synthesize their findings into a single, comprehensive answer.\n\n**Turn 2: Code and Benchmark**\nBased on the synthesized findings from Turn 1, write a Python script to /tmp/benchmark_matmul.py that benchmarks the top recommended methods against a naive pure Python implementation. After writing the file, use the \`Bash\` tool to execute it with \`uv run python /tmp/benchmark_matmul.py\` and capture the output.\n\n**Turn 3: Final Report**\nProvide a final report for the researchers. The report must include:\n1. The synthesized research from Turn 1.\n2. The full output from the benchmark execution in Turn 2.\n3. A final conclusion based on all the gathered evidence."

# 6. Construct the full claude command
CLAUDE_COMMAND="claude -p \"$CLAUDE_PROMPT\" --output-format stream-json --verbose --mcp-config .mcp.json --allowedTools mcp__perplexity-ask,Bash,Write --dangerously-skip-permissions"

# 7. Create a temporary python script to execute the command via the websocket client
CLIENT_SCRIPT_PATH="/tmp/temp_client.py"
cat << EOF > $CLIENT_SCRIPT_PATH
import asyncio
import json
import sys
import websockets

WEBSOCKET_URL = "ws://localhost:8004/ws"

async def execute_command(command):
    print(f'--- Executing Claude Command ---\n{command}\n--------------------------------\n')
    try:
        async with websockets.connect(WEBSOCKET_URL, ping_timeout=None) as websocket:
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"command": command},
                "id": "1"
            }))
            while True:
                response = await websocket.recv()
                print(response)
                data = json.loads(response)
                if data.get("method") == "process.completed":
                    break
    except Exception as e:
        print(f"Client Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Corrected import path is not needed here as this is a self-contained script
    asyncio.run(execute_command("""$CLAUDE_COMMAND"""))
EOF

# 8. Execute the client script
echo "Executing research task..."
uv run python $CLIENT_SCRIPT_PATH

# The trap will handle cleanup
echo "Task finished."
