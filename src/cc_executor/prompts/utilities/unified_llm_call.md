# Unified LLM Call Command

Call different language models using the built-in LiteLLM integration.

## Usage

To call a specific model with a query:

```bash
# Basic usage
python -c "
import requests
import json

# Send request to Docker Claude API with model selection
response = requests.post(
    'http://localhost:8002/execute/json-stream',
    json={
        'question': 'Please call GPT-4 and ask: What is recursion?',
        'model': 'gpt-4'  # Optional - can specify model
    },
    stream=True
)

# Process streamed response
for line in response.iter_lines():
    if line:
        try:
            chunk = json.loads(line)
            if chunk.get('type') == 'output':
                print(chunk.get('line', ''))
        except:
            pass
"
```

## Using Multiple Models

To compare responses from different models:

```bash
# Ask Claude to use multiple models
curl -X POST http://localhost:8002/execute/json-stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Use the ask-gemini-flash and ask-perplexity commands to explain what a binary tree is. Compare their responses."
  }' \
  -N | jq -r 'select(.type=="output") | .line'
```

## Available Model Commands

These commands are available in ~/.claude/commands/:
- `ask-gemini-flash.md` - Google Gemini Flash model
- `ask-gemini-pro.md` - Google Gemini Pro model  
- `ask-perplexity.md` - Perplexity AI models
- `ask-ollama.md` - Local Ollama models
- `ask-claude-api.md` - Claude API (if configured)

## Example: Compare Multiple Models

```bash
# Tell Claude to compare responses
curl -X POST http://localhost:8002/execute/json-stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Use ask-gemini-flash to calculate the 20th Fibonacci number. Then use ask-perplexity to do the same. Show both results and note any differences. Include this marker in your response: FIBONACCI_TEST_123"
  }' \
  -N | jq -r 'select(.type=="output") | .line'
```

## For Stress Tests

The unified stress tests expect Claude to use its available commands to simulate calling different models. Since we don't have API keys configured, Claude should:

1. Try to use the requested model command
2. If it fails (no API key), document the error
3. Fall back to available commands or explain why it can't complete the task

## Notes

- Without API keys, most external model calls will fail
- Claude can still demonstrate the attempt and error handling
- The test verification looks for markers and patterns in the response
- Success is measured by Claude's ability to handle the request appropriately