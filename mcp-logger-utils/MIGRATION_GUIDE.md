# MCP Logger Utils Migration Guide

This guide explains how to migrate existing MCP servers to use the shared `mcp-logger-utils` package.

## Installation

First, ensure the package is installed:

```bash
# For development (editable install)
cd /home/graham/workspace/experiments/cc_executor
uv pip install -e mcp-logger-utils/

# For production
uv pip install mcp-logger-utils
```

## Migration Steps

### 1. Update UV Script Dependencies

Replace any local MCPLogger imports in your UV script header:

```python
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils",  # Add this
#     # ... other dependencies
# ]
# ///
```

### 2. Update Imports

Replace the old import:
```python
# OLD - Remove this
from cc_executor.utils.mcp_logger import MCPLogger, debug_tool

# NEW - Use this
from mcp_logger_utils import MCPLogger, debug_tool
```

### 3. Remove Inline MCPLogger Code

If you have MCPLogger class defined inline in your MCP server file, remove it entirely. The package provides the same functionality.

### 4. Initialize Logger

Keep the initialization the same:
```python
# Initialize MCP logger
mcp_logger = MCPLogger("your-server-name")
```

### 5. Use Debug Decorator

Apply the debug decorator to your tools:
```python
@debug_tool(mcp_logger)
async def your_tool(param1: str, param2: int) -> dict:
    """Your tool description."""
    # Tool implementation
    return result
```

## Example Migration

Here's a complete example for an MCP server:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils",
#     "python-dotenv",
#     # ... your other dependencies
# ]
# ///

from fastmcp import FastMCP
from mcp_logger_utils import MCPLogger, debug_tool
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Initialize MCP logger
mcp_logger = MCPLogger("example-server")

# Create MCP server
mcp = FastMCP("example-server")

@mcp.tool()
@debug_tool(mcp_logger)
async def example_tool(input_text: str) -> str:
    """Example tool with debug logging."""
    return f"Processed: {input_text}"

if __name__ == "__main__":
    mcp.run()
```

## Benefits

1. **Consistent Logging**: All MCP servers use the same logging format
2. **Debug Information**: Automatic capture of tool inputs, outputs, and errors
3. **Centralized Updates**: Bug fixes and improvements to MCPLogger benefit all servers
4. **Reduced Code Duplication**: No need to maintain MCPLogger in 15+ files

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError: No module named 'mcp_logger_utils'`:

1. Ensure the package is installed:
   ```bash
   uv pip list | grep mcp-logger-utils
   ```

2. If using editable install, ensure you're in the correct directory:
   ```bash
   cd /home/graham/workspace/experiments/cc_executor
   uv pip install -e mcp-logger-utils/
   ```

### UV Script Issues

If UV can't find the package:

1. Ensure it's listed in the UV script dependencies
2. Try clearing UV's cache:
   ```bash
   rm -rf ~/.cache/uv
   ```

## Next Steps

After migrating to mcp-logger-utils:

1. Test the MCP server: `python your_mcp_server.py`
2. Check logs appear in `~/.claude/mcp_logs/`
3. Verify the server works in Claude Code
4. Remove any old inline MCPLogger code

## List of MCP Servers to Migrate

Based on the cc_executor project structure, these servers need migration:

1. ✅ mcp_arango_tools.py - COMPLETED
2. mcp_cc_execute.py
3. mcp_d3_visualizer.py
4. mcp_kilocode_review.py
5. mcp_logger_tools.py
6. mcp_tool_journey.py
7. mcp_tool_sequence_optimizer.py
8. graph_analytics_test.py
9. Any other MCP servers in the project

Each server should follow the same migration pattern shown above.