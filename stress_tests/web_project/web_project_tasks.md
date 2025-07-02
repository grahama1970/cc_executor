# Web Project Tasks Using cc_execute

This task list demonstrates using cc_execute.md to execute tasks with Claude Code instances.

## Task 1: Initialize Project Structure

Use cc_execute.md to create a basic web project structure:

```bash
# Execute via WebSocket
python -c "
from cc_executor.client.websocket_client_standalone import WebSocketClient
import asyncio

async def run():
    client = WebSocketClient()
    result = await client.execute_command(
        'claude -p \"What is a Python script that creates directories: templates, static, src? Show complete code.\" --output-format stream-json --allowedTools none'
    )
    print('\\n'.join(result.get('output_data', [])))

asyncio.run(run())
" > task1_output.txt
```

**Success Criteria:**
- Contains Python code with os.makedirs
- Creates the specified directories

## Task 2: Create Simple API

Use cc_execute.md prompt pattern:

```
What is a FastAPI app with a /health endpoint returning {status: ok}? 

After providing your answer, evaluate it against these criteria:
1. Must have FastAPI import
2. Must have /health endpoint
3. Must return JSON response

If missing any criteria, improve your response.
```

## Task 3: Create Todo Model

```
What is a SQLAlchemy Todo model with id, title, completed fields?

Evaluate against:
1. SQLAlchemy imports present
2. Todo class defined
3. All fields specified

Improve if needed.
```

## Task 4: Create Docker Config

```
What is a Dockerfile for Python FastAPI using port 8000?

Check for:
1. FROM python:3.10-slim
2. EXPOSE 8000
3. CMD with uvicorn

Self-improve if missing.
```

## Task 5: Create Unit Test

```
What is a pytest test for a FastAPI /health endpoint?

Verify:
1. TestClient import
2. Test function defined
3. Proper assertions

Refine if incomplete.
```

---

## Execution Pattern

Each task follows the cc_execute pattern:
1. Ask with "What is..." format (per CLAUDE_CODE_PROMPT_RULES.md)
2. Include self-evaluation criteria
3. Allow self-improvement
4. Execute via WebSocket with appropriate timeout

## Quick Test Script

```bash
#!/bin/bash
# test_web_tasks.sh

echo "Testing Task 1..."
claude -p "What is a Python script that creates directories: templates, static, src? Show complete code." \
  --output-format stream-json \
  --allowedTools none \
  --dangerously-skip-permissions

echo -e "\n\nTesting Task 2..."
claude -p "What is a FastAPI app with a /health endpoint returning {status: ok}? 

After providing your answer, evaluate it against these criteria:
1. Must have FastAPI import
2. Must have /health endpoint  
3. Must return JSON response

If missing any criteria, improve your response." \
  --output-format stream-json \
  --allowedTools none \
  --dangerously-skip-permissions
```

## Simplified WebSocket Execution

```python
# simple_executor.py
import asyncio
from cc_executor.client.websocket_client_standalone import WebSocketClient

async def execute_task(prompt):
    client = WebSocketClient()
    cmd = f'claude -p "{prompt}" --output-format stream-json --allowedTools none'
    result = await client.execute_command(cmd)
    return '\n'.join(result.get('output_data', []))

# Run tasks
prompts = [
    "What is a Python script creating templates, static, src directories?",
    "What is a FastAPI /health endpoint example?",
    "What is a SQLAlchemy Todo model?"
]

async def main():
    for i, prompt in enumerate(prompts):
        print(f"\nTask {i+1}:")
        output = await execute_task(prompt)
        print(output[:200] + "..." if len(output) > 200 else output)

asyncio.run(main())
```