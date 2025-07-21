# MCP LLM Instance Server

## Overview

The `mcp_llm_instance.py` server provides a simplified, unified interface for executing LLM commands via their CLI tools. It replaces the complex WebSocket-based `cc_executor` with direct subprocess execution, avoiding unnecessary complexity while maintaining reliability.

## Key Features

- **Direct subprocess execution** - No WebSocket overhead, just simple process management
- **Multiple LLM support** - Claude, Gemini, GPT-4, Llama, and extensible for others
- **Smart retry logic** - Automatic retries for rate limits with exponential backoff
- **Streaming support** - Real-time output streaming for long-running generations
- **Fixed timeout categories** - Predictable timeouts based on task complexity
- **Clean error handling** - Clear error messages and proper process cleanup
- **JSON mode support** - Structured output with schema validation and robust extraction

## Architecture Comparison

### Old (WebSocket-based cc_executor):
```
Client → WebSocket → Session Manager → Process Manager → Stream Handler → Subprocess
         ↓                ↓                 ↓                ↓
      JSON-RPC       Heartbeat         Redis Timing    Complex Chunking
```

### New (Direct subprocess):
```
MCP Tool → execute_llm() → subprocess → Result
            ↓                  ↓
         Retry Logic     Simple Streaming
```

## Tools

### 1. execute_llm
Execute an LLM command and return the complete output.

```python
result = await execute_llm(
    model="claude",
    prompt="What is 2+2?",
    timeout=60,  # Optional, auto-selected if not provided
    json_mode=False,
    stream=True,
    json_schema=None  # Optional JSON schema
)
```

**JSON Mode Support:**
When `json_mode=True`, the tool will:
1. Add JSON instructions to the prompt
2. Use default schema if none provided: `{question: string, answer: string}`
3. Extract JSON from LLM output using multiple methods
4. Return parsed JSON in `result["parsed_json"]`

```python
# With default schema
result = await execute_llm(
    model="claude",
    prompt="What is the capital of France?",
    json_mode=True
)
print(result["parsed_json"])
# Output: {"question": "What is the capital of France?", "answer": "Paris"}

# With custom schema
schema = json.dumps({
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "country": {"type": "string"},
        "population": {"type": "number"}
    }
})
result = await execute_llm(
    model="claude",
    prompt="Tell me about Paris",
    json_mode=True,
    json_schema=schema
)
```

### 2. stream_llm
Stream output from an LLM in real-time.

```python
async for chunk in stream_llm(
    model="gemini",
    prompt="Write a story about AI",
    timeout=300
):
    print(chunk, end='', flush=True)
```

### 3. get_llm_status
Check which LLMs are available and configured.

```python
status = await get_llm_status()
# Returns availability and configuration for each model
```

### 4. estimate_tokens
Simple token estimation for text.

```python
result = await estimate_tokens(
    text="Your text here",
    model="claude"
)
```

### 5. configure_llm
Add or update LLM configuration at runtime.

```python
result = await configure_llm(
    model="custom-llm",
    command=["custom-llm", "-p"],
    timeout_category="normal",
    rate_limit_patterns=["rate limit", "429"]
)
```

## Configuration

### Supported Models

1. **Claude** (Default)
   - Uses browser authentication via `claude login`
   - Supports JSON mode and streaming
   - Command: `claude -p --dangerously-skip-permissions`
   - JSON mode: Fully supported with streaming JSON wrapper

2. **Gemini**
   - Requires authentication (run `gemini` once to authenticate)
   - Command: `gemini -y -p`
   - Note: May timeout on first run during auth
   - JSON mode: Works with prompt instructions

3. **GPT-4**
   - Requires `OPENAI_API_KEY` environment variable
   - Command: `openai api completions.create -m gpt-4`
   - JSON mode: Native support available

4. **Llama**
   - Local model via Ollama
   - Command: `ollama run llama2`
   - JSON mode: Works with prompt instructions

### Timeout Categories

- **QUICK**: 60 seconds - Simple queries, short responses
- **NORMAL**: 300 seconds (5 min) - Standard tasks
- **LONG**: 600 seconds (10 min) - Complex generation
- **EXTENDED**: 1800 seconds (30 min) - Very long tasks

The system automatically selects timeout based on prompt analysis.

## Usage Examples

### Basic Execution
```python
# Simple query
result = await execute_llm(
    model="claude",
    prompt="Explain quantum computing in one sentence"
)
print(result["output"])
```

### Streaming Long Content
```python
# Stream a long generation
async for chunk in stream_llm(
    model="claude",
    prompt="Write a comprehensive guide to Python async programming",
    timeout=600
):
    print(chunk, end='', flush=True)
```

### Multi-Model Comparison
```python
# Compare responses from different models
models = ["claude", "gemini"]
prompt = "What is the meaning of life?"

for model in models:
    try:
        result = await execute_llm(model=model, prompt=prompt)
        print(f"\n{model}: {result['output']}")
    except Exception as e:
        print(f"\n{model}: Error - {e}")
```

## Error Handling

The server handles several types of errors gracefully:

1. **Rate Limits** - Automatic retry with exponential backoff
2. **Timeouts** - Clean process termination and error reporting
3. **Authentication** - Clear messages about missing credentials
4. **Process Failures** - Detailed error output from stderr

## Testing

Run the test suite:
```bash
# Basic functionality test
python mcp_llm_instance.py test

# Manual testing with actual LLMs
python test_llm_instance_manual.py
```

## Environment Variables

- `ANTHROPIC_API_KEY` - For Claude API (not needed with browser auth)
- `OPENAI_API_KEY` - For GPT-4
- `GEMINI_API_KEY` - For Gemini (if using API instead of CLI)

## Migration from cc_executor

If migrating from the old WebSocket-based system:

1. Replace `cc_execute()` calls with `execute_llm()`
2. Remove WebSocket connection setup
3. Remove session management code
4. Simplify error handling (no more connection errors)
5. Update timeout logic (use categories instead of Redis prediction)

## Performance Comparison

| Metric | WebSocket cc_executor | Direct mcp_llm_instance |
|--------|----------------------|-------------------------|
| Startup overhead | ~500ms (WebSocket) | ~10ms (direct) |
| Memory usage | ~150MB (server+client) | ~30MB (single process) |
| Complexity | High (1000+ LOC) | Low (~600 LOC) |
| Failure modes | Many (connection, session, etc) | Few (just subprocess) |
| Maintenance | Complex | Simple |

## Known Issues

1. **Gemini Authentication** - First run may timeout during browser auth
2. **Claude Browser Auth** - Requires `claude login` to be run once
3. **Logger Errors** - mcp-logger-utils may show KeyError for 'tool_name' (cosmetic)
4. **JSON Extraction** - Complex nested JSON may require custom parsing logic

## Future Enhancements

1. Add support for more LLMs (Anthropic API, Cohere, etc.)
2. Implement response caching
3. Add cost tracking for API-based models
4. Support for function calling/tool use
5. Better streaming format parsing

## Contributing

When adding new LLM support:
1. Add configuration to `LLM_CONFIGS`
2. Update `build_command()` for model-specific flags
3. Add rate limit patterns
4. Test with `test_llm_instance_manual.py`
5. Update this documentation