# MCP Logger Utils

A robust, shared logging and utility package for MCP (Model Context Protocol) servers, especially tailored for Claude Code environments.

## Features

- **Isolated Logging:** Prevents conflicts with other libraries using `loguru`.
- **Automatic Truncation:** Automatically shortens large strings, base64 data, and long lists (like embeddings) in logs to keep them clean and readable.
- **Universal Decorator:** The `@debug_tool` decorator works seamlessly with both `async` and `sync` functions.
- **Safe Serialization:** Handles non-serializable types (`datetime`, `Path`, etc.), preventing the logger from crashing.
- **Rich Context:** Logs function arguments, return values, execution time, and detailed error tracebacks.
- **Configurable:** Customize log directory, level, and truncation limits via constructor arguments or environment variables.
- **Robust JSON Repair:** Includes a powerful utility to parse malformed JSON commonly produced by LLMs.
- **Structured Error Response:** Returns a standardized JSON object on tool failure, including a unique error ID.

## Installation

```bash
pip install mcp-logger-utils
```

Or using `uv`:

```bash
uv pip install mcp-logger-utils
```

## Usage

### 1. Robust Logging with `@debug_tool`

Decorate your MCP tool functions to get automatic logging of inputs, outputs, performance, and errors.

#### a. Initialize the Logger

In your MCP server file, create an instance of `MCPLogger`. You can optionally configure truncation limits.

```python
from mcp_logger_utils import MCPLogger

# Default initialization
mcp_logger = MCPLogger("my-awesome-server")

# Customizing truncation limits
mcp_logger_custom = MCPLogger(
    "my-data-server",
    max_log_str_len=512,      # Allow longer strings in logs
    max_log_list_len=5       # Show fewer list items
)
```

#### b. Apply the Decorator

The same decorator works for both `async` and `sync` functions.

```python
from mcp_logger_utils import debug_tool

@mcp.tool()
@debug_tool(mcp_logger)
async def process_data(embedding: list, image_data: str) -> dict:
    # `embedding` (if long) and `image_data` (if long) will be
    # automatically truncated in the debug logs.
    return {"status": "processed"}
```

#### c. Configuration via Environment Variables

-   `MCP_LOG_DIR`: Overrides the default log directory (`~/.claude/mcp_logs`).
-   `MCP_LOG_LEVEL`: Sets the console log level (e.g., `DEBUG`, `INFO`).
-   `MCP_DEBUG`: Set to `true` or `1` for verbose `DEBUG` level logging.

### 2. JSON Repair Utility

When working with LLMs, you often get responses that are *almost* JSON but contain small errors or are wrapped in text. This utility provides a robust way to handle such cases.

#### `repair_and_parse_json(content, logger_instance=None)`

This function takes a string and does its best to return a valid Python `dict` or `list`.

-   It automatically extracts JSON from markdown code blocks (e.g., ` ```json ... ``` `).
-   It uses the `json-repair` library to fix common syntax errors.
-   If parsing fails, it safely returns the original string.

#### Example: Creating a Robust Tool

Here is how you can combine `@debug_tool` and `repair_and_parse_json` to build a tool that reliably processes LLM output.

```python
from mcp_logger_utils import MCPLogger, debug_tool, repair_and_parse_json
# from some_llm_library import get_llm_response

# Initialize logger
mcp_logger = MCPLogger("llm-processor-tool")

@mcp.tool()
@debug_tool(mcp_logger)
async def get_structured_data_from_llm(prompt: str) -> dict:
    """
    Calls an LLM to get structured data and robustly parses the response.
    """
    # 1. Get a response from an LLM. It might be messy.
    messy_response = "Here is the JSON you requested: ```json\n{\n  \"name\": \"Claude\",\n  \"version\": 3.0,\n  \"is_helpful\": true, // He is very helpful!\n}\n```"
    # messy_response = await get_llm_response(prompt)

    # 2. Use the utility to clean and parse it.
    # The logger passed to it will log the repair steps for easy debugging.
    parsed_data = repair_and_parse_json(messy_response, logger_instance=mcp_logger.logger)

    # 3. Check if parsing was successful before proceeding.
    if not isinstance(parsed_data, dict):
        raise ValueError(f"Failed to parse a valid dictionary from the LLM response. Got: {parsed_data}")

    # 4. Now you can safely work with the clean data.
    parsed_data["processed_at"] = "2024-07-19"
    return parsed_data
```

**Why this is a good pattern:**

1.  **Observability:** The `@debug_tool` logs the *raw, messy input* from the LLM, so you can always see exactly what your tool received.
2.  **Robustness:** Your tool doesn't crash on slightly malformed JSON.
3.  **Clarity:** The code explicitly shows the step where data is being cleaned, making the logic easy to follow.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.