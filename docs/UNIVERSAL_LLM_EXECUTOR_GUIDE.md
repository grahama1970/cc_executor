# Universal LLM Executor MCP Server Guide

## Overview

The Universal LLM Executor is a powerful MCP server that provides a unified interface for executing any LLM CLI tool (Claude, Gemini, GPT, Llama, etc.) with intelligent features like:

- **Smart file concatenation** with token-aware chunking
- **Automatic timeout learning** via Redis
- **JSON output parsing** with repair capabilities
- **Progress monitoring** for long-running tasks
- **Clean subprocess management** with process groups

## Installation

The server has been installed and is available in your MCP configuration as `universal-llm-executor`.

### Manual Installation

If you need to install it manually:

```bash
# Run the installation script
python install_universal_llm_mcp.py

# Or manually add to ~/.claude/claude_code/.mcp.json:
{
  "mcpServers": {
    "universal-llm-executor": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/graham/workspace/experiments/cc_executor",
        "run",
        "--script",
        "src/cc_executor/servers/mcp_universal_llm_executor.py"
      ],
      "env": {
        "PYTHONPATH": "/home/graham/workspace/experiments/cc_executor/src",
        "UV_PROJECT_ROOT": "/home/graham/workspace/experiments/cc_executor",
        "LLM_OUTPUT_DIR": "/tmp/llm_outputs",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
      }
    }
  }
}
```

## Available Tools

### 1. `execute_llm`

Execute any LLM CLI with a prompt.

**Parameters:**
- `llm` (required): LLM name (claude, gemini, gpt, llama, etc.)
- `prompt` (required): The prompt to send to the LLM
- `timeout` (optional): Timeout in seconds (auto-calculated if not provided)
- `stream` (optional): Enable streaming output if supported
- `output_dir` (optional): Directory for output files (default: /tmp/llm_outputs)
- `extra_args` (optional): Additional CLI arguments as JSON array
- `env_vars` (optional): Additional environment variables as JSON object

**Example:**
```python
# Basic usage
mcp__universal-llm-executor__execute_llm("claude", "Explain quantum computing")

# With streaming and custom timeout
mcp__universal-llm-executor__execute_llm(
    llm="gemini",
    prompt="Write a Python function for binary search",
    stream=True,
    timeout=120
)

# With extra arguments
mcp__universal-llm-executor__execute_llm(
    llm="claude",
    prompt="Analyze this code",
    extra_args='["--model", "claude-3-opus"]'
)
```

### 2. `concatenate_files`

Concatenate multiple files with intelligent chunking based on token limits.

**Parameters:**
- `file_paths` (required): JSON array of file paths to concatenate
- `output_path` (optional): Output file path (default: auto-generated)
- `chunk_size` (optional): Maximum tokens per chunk (default: model-specific)
- `model` (optional): Model name for token estimation

**Example:**
```python
# Concatenate Python files
mcp__universal-llm-executor__concatenate_files(
    file_paths='["src/main.py", "src/utils.py", "tests/test_main.py"]',
    chunk_size=50000
)

# Concatenate with specific output
mcp__universal-llm-executor__concatenate_files(
    file_paths='["README.md", "docs/guide.md"]',
    output_path="/tmp/combined_docs.txt"
)
```

### 3. `detect_llms`

Detect which LLM CLIs are available on the system.

**Example:**
```python
# Check available LLMs
mcp__universal-llm-executor__detect_llms()
# Returns: {"claude": "claude", "gemini": "gemini", "gpt": "gpt"}
```

### 4. `estimate_tokens`

Estimate token count for text or file content.

**Parameters:**
- `text` (optional): Text content to analyze
- `file_path` (optional): Path to file to analyze
- `model` (optional): Model name for specific tokenizer

**Example:**
```python
# Estimate tokens in text
mcp__universal-llm-executor__estimate_tokens(
    text="This is a sample text to analyze",
    model="claude"
)

# Estimate tokens in file
mcp__universal-llm-executor__estimate_tokens(
    file_path="/path/to/document.txt"
)
```

### 5. `parse_llm_output`

Parse JSON from LLM output, handling markdown code blocks and malformed JSON.

**Parameters:**
- `output_file` (optional): Path to LLM output file
- `content` (optional): Direct content to parse
- `extract_streaming` (optional): Extract newline-delimited JSON objects

**Example:**
```python
# Parse output file
mcp__universal-llm-executor__parse_llm_output(
    output_file="/tmp/llm_outputs/claude_output_20250119_123456.txt"
)

# Parse streaming JSON
mcp__universal-llm-executor__parse_llm_output(
    content='{"type": "message", "text": "Hello"}\n{"type": "done"}',
    extract_streaming=True
)
```

## Features

### Smart File Concatenation

The concatenator automatically:
- Detects file encoding (UTF-8, UTF-16, etc.)
- Adds clear file separators with paths
- Splits large content into token-limited chunks
- Preserves file structure and readability

### Timeout Learning

The executor learns optimal timeouts based on:
- LLM type (Claude, Gemini, etc.)
- Prompt size (in 10k token buckets)
- Historical execution times
- Stored in Redis with 7-day TTL

### JSON Output Parsing

Handles common LLM output formats:
- Direct JSON objects
- Markdown code blocks (```json)
- Mixed content with embedded JSON
- Streaming newline-delimited JSON
- Automatic repair of malformed JSON

### Process Management

- Uses process groups for clean termination
- Handles timeouts gracefully
- Captures both stdout and stderr
- Monitors output file growth for progress

## Configuration

### Environment Variables

- `LLM_OUTPUT_DIR`: Directory for output files (default: /tmp/llm_outputs)
- `REDIS_HOST`: Redis host for timeout learning (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `LOG_LEVEL`: Logging level (default: INFO)

### Supported LLMs

Default configurations for:
- **Claude**: Uses stdin for prompts, supports streaming
- **Gemini**: Command-line prompts, no streaming
- **GPT**: Command-line prompts, supports streaming
- **Llama**: Command-line prompts, supports streaming
- **Mistral**: Command-line prompts, supports streaming

### Token Limits

Default token limits by model:
- Claude: 100,000 tokens
- Gemini: 100,000 tokens
- GPT: 100,000 tokens
- Llama: 32,000 tokens
- Mistral: 32,000 tokens
- Default: 50,000 tokens

## Troubleshooting

### Common Issues

1. **LLM not found**
   ```
   Error: LLM 'claude' not found in PATH
   ```
   Solution: Ensure the LLM CLI is installed and in your PATH

2. **Token limit exceeded**
   ```
   Message: Content split into 3 chunks due to token limit
   ```
   Solution: This is normal - files are automatically chunked

3. **Process timeout**
   ```
   Error: Process timed out after 60 seconds
   ```
   Solution: Increase timeout or check if LLM is responding

4. **JSON parsing failed**
   ```
   Type: str (original content returned)
   ```
   Solution: Content wasn't valid JSON - original text is returned

### Debug Mode

Run the server in debug mode:
```bash
python src/cc_executor/servers/mcp_universal_llm_executor.py debug
```

### Test Mode

Quick validation test:
```bash
python src/cc_executor/servers/mcp_universal_llm_executor.py test
```

## Usage Examples

### Example 1: Compare LLM Responses

```python
# Get responses from multiple LLMs
for llm in ["claude", "gemini"]:
    result = mcp__universal-llm-executor__execute_llm(
        llm=llm,
        prompt="Explain the concept of recursion with a simple example"
    )
    print(f"{llm}: {result}")
```

### Example 2: Process Large Codebase

```python
# Concatenate all Python files
files = glob("src/**/*.py", recursive=True)
result = mcp__universal-llm-executor__concatenate_files(
    file_paths=json.dumps(files),
    chunk_size=80000,
    model="claude"
)

# Process each chunk
for chunk_path in result['output_paths']:
    mcp__universal-llm-executor__execute_llm(
        llm="claude",
        prompt=f"Analyze this code: {chunk_path}"
    )
```

### Example 3: Parse Streaming Output

```python
# Execute with streaming
result = mcp__universal-llm-executor__execute_llm(
    llm="claude",
    prompt="Generate a JSON API response",
    stream=True
)

# Parse streaming output
parsed = mcp__universal-llm-executor__parse_llm_output(
    output_file=result['output_file'],
    extract_streaming=True
)

# Process each JSON object
for obj in parsed['parsed']:
    if obj.get('type') == 'data':
        process_data(obj['content'])
```

## Best Practices

1. **Use appropriate timeouts**: Let the system learn optimal timeouts via Redis
2. **Check LLM availability**: Use `detect_llms()` before executing
3. **Handle chunked files**: When concatenating large files, process chunks separately
4. **Parse JSON carefully**: Use `parse_llm_output()` for robust JSON extraction
5. **Monitor progress**: Check output files for long-running tasks

## Integration with Other MCP Servers

The Universal LLM Executor works well with:
- **arango-tools**: Store LLM outputs in ArangoDB
- **logger-tools**: Log LLM interactions for learning
- **tool-journey**: Track LLM usage patterns
- **d3-visualizer**: Visualize LLM response comparisons

## Future Enhancements

Planned features:
- Support for more LLM CLIs (Ollama, Anthropic API, etc.)
- Batch processing of multiple prompts
- Response caching and deduplication
- Cost tracking and optimization
- Automatic prompt engineering