# MCP Tool Creation Guide: From Concept to Working Tool

This guide documents the complete process of creating MCP (Model Context Protocol) tools, based on lessons learned from building the ArangoDB MCP tools.

## ⚠️ Critical FastMCP Limitation

**FastMCP has validation issues with dictionary and list parameters.** Always use JSON strings instead:

```python
# ❌ WRONG - Will fail with validation errors
async def query(data: Dict[str, Any], items: List[str]) -> str:

# ✅ CORRECT - Use JSON strings
async def query(data: str, items: str) -> str:
    """Args:
        data: JSON string (e.g. '{"key": "value"}')
        items: JSON array string (e.g. '["item1", "item2"]')
    """
    parsed_data = json.loads(data)
    parsed_items = json.loads(items)
```

See the [FastMCP JSON Parameters Pattern](#fastmcp-json-parameters-pattern-important) section for complete examples.

## ⚠️ Additional Lessons Learned (2025-01-17)

### 1. **Security: Never use hard-coded credentials**
- Always use environment variables for passwords
- Raise clear errors if required env vars are missing
- Document required env vars in .env.example

### 2. **Performance: Avoid subprocess spawning in MCP tools**
- Direct function imports are ~300x faster than subprocess
- Use dynamic module loading with caching
- Handle both sync and async functions properly

### 3. **Architecture: Separate concerns in large classes**
- Break monolithic classes into focused managers
- Use composition over inheritance
- Each class should have a single responsibility

### 4. **HTML Templates: Keep them external**
- Store HTML in separate template files
- Use templating engines like Jinja2
- Keeps code clean and templates reusable

## Overview

MCP tools allow Claude to interact with external services and databases. This guide covers creating, configuring, debugging, and deploying MCP tools using the FastMCP framework.

## Quick Start Pattern

```bash
# 1. Create MCP server file
touch src/cc_executor/servers/mcp_your_tool.py

# 2. Add to MCP config
edit ~/.claude/claude_code/.mcp.json

# 3. Test with debug logging
MCP_DEBUG=true claude

# 4. Reload Claude after changes
# Use UI reload button or restart
```

## File Structure

```
project/
├── ~/.claude/claude_code/.mcp.json    # MCP configuration
├── src/project_name/
│   ├── servers/                      # MCP server implementations
│   │   ├── mcp_your_tool.py        # Individual MCP servers
│   │   ├── model.py                 # Shared Pydantic models
│   │   └── README.md               # Documentation for all servers
│   └── tools/                       # Core business logic
│       └── your_tool_logic.py      # Reusable logic
```

### Key Directory Organization:
- `servers/` - Contains all MCP server implementations
- `model.py` - Shared Pydantic models to avoid duplication
- `tools/` - Core logic that can be used by multiple servers

## Step 1: Create the MCP Server File

Use the FastMCP pattern (avoid standard MCP SDK due to initialization_options issues):

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "your-other-deps"
# ]
# ///

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# CRITICAL: Load environment and setup paths
# find_dotenv() searches up directory tree for .env file
load_dotenv(find_dotenv())

# Get project root from .env location
env_path = find_dotenv()
project_root = Path(env_path).parent if env_path else Path.cwd()
sys.path.insert(0, str(project_root))

# Import your tools AFTER path setup
from project_name.tools import your_tool_logic
# Import shared models if needed
from project_name.servers.model import SharedModel

# CRITICAL: Import logger agent for error tracking and knowledge building
LOGGER_AGENT_AVAILABLE = False
try:
    logger_agent_path = project_root / "proof_of_concept" / "logger_agent" / "src"
    sys.path.insert(0, str(logger_agent_path))
    
    from logger_agent.sinks.arango_sink import ArangoLogSink
    from logger_agent.managers.agent_log_manager import AgentLogManager
    
    LOGGER_AGENT_AVAILABLE = True
    logger.info("✓ Logger agent available for knowledge building")
except ImportError as e:
    logger.warning(f"Logger agent not available: {e}")

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Configure logger agent sink if available
if LOGGER_AGENT_AVAILABLE:
    db_config = {
        "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
        "database": os.getenv("ARANGO_DATABASE", "script_logs"),
        "username": os.getenv("ARANGO_USERNAME", "root"),
        "password": os.getenv("ARANGO_PASSWORD", "")
    }
    
    sink = ArangoLogSink(
        db_config=db_config,
        collection_name="log_events",
        batch_size=50,
        flush_interval=5.0
    )
    
    # Generate execution ID for this MCP session
    execution_id = f"mcp_{Path(__file__).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    sink.set_execution_context(execution_id, Path(__file__).stem)
    
    # Start sink
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(sink.start())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(sink.start())
        loop.close()
    
    # Filter for selective storage
    def should_store_in_db(record):
        # Always store errors
        if record["level"].no >= logger.level("ERROR").no:
            return True
        # Store MCP-specific categories
        if record.get("extra", {}).get("log_category", "") in [
            "MCP_ERROR", "MCP_RESOLVED", "MCP_STARTUP", "TOOL_FAILED"
        ]:
            return True
        return False
    
    logger.add(
        sink.write,
        level="DEBUG",
        enqueue=True,
        serialize=False,
        filter=should_store_in_db
    )

# Initialize FastMCP
mcp = FastMCP("your-tool-name")

@mcp.tool()
async def your_function(param1: str, param2: int = 10) -> str:
    """Tool description for Claude.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
    """
    try:
        result = your_tool_logic.do_something(param1, param2)
        return json.dumps(result, indent=2)
    except Exception as e:
        # Log error for knowledge building
        logger.error(
            f"Tool failed: {e}",
            extra={
                "log_category": "MCP_ERROR",
                "tool_name": "your_function",
                "params": {"param1": param1, "param2": param2},
                "error_type": type(e).__name__,
                "resolved": False  # Mark as unresolved
            }
        )
        return json.dumps({"error": str(e)}, indent=2)

# CRITICAL: This must be at the bottom
if __name__ == "__main__":
    mcp.run()
```

### Key Points:
- Use `#!/usr/bin/env -S uv run --script` shebang for standalone execution
- The uv script header allows direct execution without explicit Python interpreter
- FastMCP doesn't support `**kwargs` - use explicit parameters
- Always return JSON strings for complex data
- Add proper error handling
- Tools should be async functions
- **CRITICAL**: FastMCP has issues with dictionary/list parameters - use JSON strings instead (see Common Issues)

### Alternative: Standard Python Execution

If not using uv script pattern, adjust your .mcp.json:

```json
{
  "mcpServers": {
    "your-tool": {
      "command": "python",
      "args": [
        "/absolute/path/to/src/servers/mcp_your_tool.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/project/src"
      }
    }
  }
}
```

## Step 2: Configure MCP in ~/.claude/claude_code/.mcp.json

```json
{
  "mcpServers": {
    "your-tool-name": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/your/project",
        "run",
        "python",
        "src/project_name/servers/mcp_your_tool.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/your/project",
        "UV_PROJECT_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

### Configuration Tips:
- Use absolute paths everywhere
- Set both PYTHONPATH and UV_PROJECT_ROOT
- Tool name in config must match FastMCP initialization
- No trailing commas in JSON
- Add "/src" to PYTHONPATH if using src layout: `"PYTHONPATH": "/path/to/project/src"`

## Shared Models Pattern

When building multiple MCP servers, use a shared `model.py` file:

```python
# src/project_name/servers/model.py
"""Shared Pydantic models for MCP servers."""
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field

class RequestModel(BaseModel):
    """Shared request structure."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    messages: List[Dict[str, str]]
    
class ResultModel(BaseModel):
    """Shared result structure."""
    request_id: str
    status: Literal["success", "error"]
    data: Optional[Any] = None
    error: Optional[str] = None
```

## Server Composition Pattern

Build complex functionality by composing simpler servers:

```python
# mcp_complex_tool.py
from project_name.servers.mcp_simple_tool import simple_function
from project_name.servers.model import SharedModel

@mcp.tool()
async def complex_function(data: str) -> str:
    """Compose multiple tools."""
    # Reuse other MCP tools directly
    step1_result = await simple_function(data)
    # Process further...
    return final_result
```

## Step 3: Debugging MCP Issues

### Enable Debug Logging

```bash
# Method 1: Environment variable
export MCP_DEBUG=true
claude

# Method 2: Check Claude logs
tail -f ~/.claude/logs/mcp*.log

# Method 3: Add logging to your MCP server
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues and Solutions

1. **"Functions with **kwargs are not supported as tools"**
   - Solution: Replace `**kwargs` with explicit parameters
   ```python
   # Bad
   async def query(aql: str, **kwargs):
   
   # Good  
   async def query(aql: str, bind_vars: dict = None):
   ```

2. **FastMCP Dictionary/List Parameter Issues (CRITICAL)**
   - **Problem**: FastMCP fails to properly validate Dict[str, Any] or List[str] parameters
   - **Error**: `Input validation error: '{"key": "value"}' is not valid under any of the given schemas`
   - **Solution**: Convert all dict/list parameters to JSON strings
   
   ```python
   # WRONG - This will fail with validation errors
   @mcp.tool()
   async def query(aql: str, bind_vars: Optional[Dict[str, Any]] = None) -> str:
       result = execute_query(aql, bind_vars)
       return json.dumps(result)
   
   # CORRECT - Use JSON strings instead
   @mcp.tool()
   async def query(aql: str, bind_vars: Optional[str] = None) -> str:
       """Execute AQL query with optional bind variables.
       
       Args:
           aql: The AQL query string
           bind_vars: JSON string of bind variables (e.g. '{"@col": "users", "age": 25}')
       """
       # Parse JSON string to dict
       parsed_bind_vars = None
       if bind_vars:
           try:
               parsed_bind_vars = json.loads(bind_vars)
           except json.JSONDecodeError as e:
               return json.dumps({
                   "success": False,
                   "error": f"Invalid JSON in bind_vars: {str(e)}",
                   "suggestion": "Ensure bind_vars is a valid JSON string"
               })
       
       result = execute_query(aql, parsed_bind_vars)
       return json.dumps(result)
   ```
   
   **Usage from Claude:**
   ```python
   # Pass complex parameters as JSON strings
   await mcp__your-tool__query(
       "FOR doc IN @@col FILTER doc.age > @age RETURN doc",
       '{"@col": "users", "age": 25}'
   )
   ```
   
   **This affects all complex parameter types:**
   - `Dict[str, Any]` → Use `str` with JSON parsing
   - `List[str]` → Use `str` with JSON parsing  
   - `Optional[Dict]` → Use `Optional[str]` with JSON parsing
   
   **Important**: Always document in your tool's docstring that parameters expect JSON strings!

3. **"Server.run() missing 1 required positional argument: 'initialization_options'"**
   - Solution: Use FastMCP instead of standard MCP SDK
   - The standard SDK had breaking API changes

4. **Import errors (ModuleNotFoundError)**
   - Solution: Ensure PYTHONPATH is set in both:
     - The MCP config env section
     - The Python script sys.path
   - Common fixes:
     ```python
     # In your MCP server file
     sys.path.insert(0, str(project_root))
     sys.path.insert(0, str(project_root / "src"))  # If using src layout
     ```
   - Check import paths match your structure:
     ```python
     # Wrong: from servers.models import Model (plural)
     # Right: from servers.model import Model (singular)
     ```
   
5. **Tool not appearing in Claude**
   - Check exact name match between FastMCP("name") and config
   - **IMPORTANT**: Always reload Claude after ANY changes:
     - After modifying .mcp.json configuration
     - After changing tool parameters or signatures
     - After fixing bugs in your MCP server code
   - Use the `/mcp` command in Claude to reload
   - Verify no JSON syntax errors in .mcp.json
   - Check ~/.claude/logs/mcp*.log for startup errors

6. **Subprocess hangs or timeouts**
   - Add explicit error messages in your tools
   - Return early on errors rather than hanging
   - Use try/except blocks around all operations

### Better Error Visibility

Add this error wrapper to all MCP tools:

```python
def error_wrapped_tool(func):
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return json.dumps({"success": True, "data": result})
        except Exception as e:
            import traceback
            return json.dumps({
                "success": False,
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
    return wrapper

@mcp.tool()
@error_wrapped_tool
async def your_function():
    # Your code here
```

## FastMCP JSON Parameters Pattern (IMPORTANT)

Due to FastMCP's validation limitations with complex types, here's the recommended pattern for handling dictionaries and lists:

### Complete Working Example

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["fastmcp", "python-dotenv"]
# ///

from fastmcp import FastMCP
import json
from typing import Optional

mcp = FastMCP("database-tools")

# Internal function that uses proper Python types
def execute_database_query(query: str, params: dict = None, options: list = None):
    """Internal logic with normal Python types."""
    # Your actual implementation
    return {"results": [], "count": 0}

@mcp.tool()
async def query(
    query_string: str,
    parameters: Optional[str] = None,  # JSON string instead of dict
    options: Optional[str] = None      # JSON string instead of list
) -> str:
    """Execute database query with parameters.
    
    Args:
        query_string: The SQL/AQL query to execute
        parameters: JSON string of query parameters (e.g. '{"user_id": 123, "status": "active"}')
        options: JSON string of options array (e.g. '["include_metadata", "verbose"]')
        
    Examples:
        Basic query:
            query("SELECT * FROM users")
            
        With parameters:
            query(
                "SELECT * FROM users WHERE id = @id AND status = @status",
                '{"id": 123, "status": "active"}'
            )
            
        With options:
            query(
                "SELECT * FROM users",
                '{}',
                '["include_metadata", "limit_100"]'
            )
    """
    # Parse JSON parameters
    parsed_params = None
    parsed_options = None
    
    if parameters:
        try:
            parsed_params = json.loads(parameters)
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON in parameters: {str(e)}",
                "hint": "Ensure parameters is a valid JSON string"
            })
    
    if options:
        try:
            parsed_options = json.loads(options)
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON in options: {str(e)}",
                "hint": "Ensure options is a valid JSON array string"
            })
    
    # Call internal function with parsed types
    try:
        result = execute_database_query(query_string, parsed_params, parsed_options)
        return json.dumps({"success": True, "data": result})
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    mcp.run()
```

### Common Patterns for Different Parameter Types

```python
# 1. Simple dictionary parameter
@mcp.tool()
async def update_record(
    record_id: str,
    fields: str  # Instead of Dict[str, Any]
) -> str:
    """Update record fields.
    Args:
        record_id: The record ID
        fields: JSON string of fields to update (e.g. '{"name": "John", "age": 30}')
    """
    fields_dict = json.loads(fields)
    # ... implementation

# 2. List parameter
@mcp.tool()
async def batch_process(
    items: str  # Instead of List[str]
) -> str:
    """Process multiple items.
    Args:
        items: JSON array of items (e.g. '["item1", "item2", "item3"]')
    """
    items_list = json.loads(items)
    # ... implementation

# 3. Complex nested structures
@mcp.tool()
async def complex_operation(
    config: str  # Instead of complex Pydantic model
) -> str:
    """Perform complex operation.
    Args:
        config: JSON string of configuration (e.g. '{"mode": "fast", "options": {"retry": 3}}')
    """
    config_dict = json.loads(config)
    # ... implementation

# 4. Optional parameters with defaults
@mcp.tool()
async def search(
    query: str,
    filters: Optional[str] = None,  # Instead of Optional[Dict]
    sort_options: Optional[str] = None  # Instead of Optional[List]
) -> str:
    """Search with optional filters.
    Args:
        query: Search query
        filters: JSON string of filters (e.g. '{"category": "tech", "date": "2024"}')
        sort_options: JSON array of sort fields (e.g. '["date:desc", "score:asc"]')
    """
    filters_dict = json.loads(filters) if filters else {}
    sort_list = json.loads(sort_options) if sort_options else []
    # ... implementation
```

### Testing JSON Parameters

When testing your MCP tools, remember to pass JSON strings:

```python
# In Claude, calling your tools:

# ✅ CORRECT
await mcp__database-tools__query(
    "SELECT * FROM users WHERE age > @age",
    '{"age": 25}'
)

# ❌ WRONG - This will fail with validation error
await mcp__database-tools__query(
    "SELECT * FROM users WHERE age > @age",
    {"age": 25}  # Direct dict will fail!
)

# For nested structures
await mcp__database-tools__complex_operation(
    '{"mode": "fast", "retries": 3, "options": {"verbose": true, "timeout": 30}}'
)
```

## Step 4: Testing Your MCP Tool

Create a test script:

```python
# test_mcp_local.py
import subprocess
import json

def test_mcp_server():
    """Test MCP server can start and respond"""
    cmd = [
        "uv", "--directory", "/path/to/project",
        "run", "python", "src/servers/mcp_your_tool.py"
    ]
    
    # Test server starts
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send initialization
    proc.stdin.write('{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}\n')
    proc.stdin.flush()
    
    # Read response
    response = proc.stdout.readline()
    print(f"Response: {response}")
    
    proc.terminate()

if __name__ == "__main__":
    test_mcp_server()
```

## Step 5: Best Practices

### 1. Separate Concerns
- Keep MCP server thin - just parameter handling
- Put business logic in separate tool files
- This allows testing without MCP overhead

### 2. Consistent Return Format
```python
@mcp.tool()
async def my_tool() -> str:
    """Always return JSON strings with consistent structure"""
    try:
        data = do_work()
        return json.dumps({
            "success": True,
            "data": data,
            "count": len(data) if hasattr(data, '__len__') else 1
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, indent=2)
```

### 3. Parameter Documentation
```python
@mcp.tool()
async def complex_tool(
    query: str,
    limit: int = 10,
    options: dict = None
) -> str:
    """Brief description for Claude.
    
    Args:
        query: Natural language or technical query
        limit: Maximum results to return (default: 10)
        options: Optional dict with keys:
            - format: Output format ('json', 'text')
            - verbose: Include extra details
            
    Returns:
        JSON string with results or error
        
    Examples:
        - Basic: query="find errors", limit=5
        - Advanced: query="errors", options={"format": "text", "verbose": true}
    """
```

### 4. Handle Async Properly
```python
# If using synchronous libraries with FastMCP
import asyncio

@mcp.tool()
async def sync_tool_wrapper(param: str) -> str:
    """Wrap synchronous code for async MCP"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # default executor
        sync_function,
        param
    )
    return json.dumps(result)
```

## Server Documentation Pattern

Create a comprehensive README.md in your servers directory:

```markdown
# MCP Servers Documentation

## Available Servers

### 1. Tool Name (`mcp_tool_name.py`)
**Purpose:** Brief description of what this tool does.

**Tools:**
- `function_name` - What this function does

**Key Features:**
- Feature 1
- Feature 2

**Example:**
```python
result = await function_name(param="value")
```

### 2. Another Tool (`mcp_another_tool.py`)
[Similar structure...]

## Typical Workflows

### Workflow Name
1. Use `tool_a` to do X
2. Use `tool_b` with the result
3. Process final output

## Dependencies
| Server | Key Dependencies | Purpose |
|--------|------------------|---------|
| tool_name | package1, package2 | What it's for |

## Debugging Tips
- Common issue 1 and fix
- Common issue 2 and fix
```

## Complete Working Example

Here's the pattern that works reliably:

### mcp_example.py
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru"
# ]
# ///

import json
import sys
from pathlib import Path
from fastmcp import FastMCP

# Path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Initialize
mcp = FastMCP("example-tool")

@mcp.tool()
async def hello(name: str = "World") -> str:
    """Say hello to someone.
    
    Args:
        name: Name to greet (default: World)
    """
    return f"Hello, {name}!"

@mcp.tool() 
async def calculate(expression: str) -> str:
    """Safely evaluate a math expression.
    
    Args:
        expression: Math expression like "2 + 2"
    """
    try:
        # Safe evaluation
        allowed = {
            'abs': abs, 'round': round, 
            'min': min, 'max': max
        }
        result = eval(expression, {"__builtins__": {}}, allowed)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
```

### ~/.claude/claude_code/.mcp.json
```json
{
  "mcpServers": {
    "example-tool": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/user/project",
        "run", 
        "python",
        "src/servers/mcp_example.py"
      ]
    }
  }
}
```

## Debugging Workflow

1. **Start with minimal tool** - Just return "Hello"
2. **Check server starts** - `python mcp_tool.py` should not error
3. **Add to config** - Update .mcp.json
4. **Reload Claude** - Use UI reload button
5. **Test in Claude** - Try calling the tool
6. **Check logs if fails** - `~/.claude/logs/`
7. **Add complexity gradually** - One feature at a time

## Migration from Standard MCP to FastMCP

If you have existing MCP tools using the standard SDK:

```python
# Old (standard MCP SDK)
from mcp.server import Server, stdio_server
from mcp.server.models import InitializationOptions
import mcp.types as types

async def main():
    server = Server("tool-name")
    
    @server.call_tool
    async def handle_tool(name: str, arguments: dict):
        if name == "function":
            return types.TextContent(text="result")
    
    options = InitializationOptions()
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], options)

# New (FastMCP)
from fastmcp import FastMCP

mcp = FastMCP("tool-name")

@mcp.tool()
async def function(param: str) -> str:
    return "result"

if __name__ == "__main__":
    mcp.run()
```

## Advanced Patterns and Lessons Learned

### Separation of Concerns Pattern

When building MCP tools, follow the principle of **single responsibility**:

```python
# ❌ WRONG: Mixing data management with visualization
class ArangoTools:
    def query_data(self): ...
    def insert_data(self): ...
    def generate_d3_visualization(self): ...  # Don't mix concerns!

# ✅ CORRECT: Separate tools for separate responsibilities
# mcp_arango_tools.py - Data management only
class ArangoTools:
    def query_data(self): ...
    def insert_data(self): ...
    def analyze_graph(self): ...  # Graph analytics, not visualization

# mcp_d3_visualizer.py - Visualization only
class D3Visualizer:
    def generate_visualization(self): ...
    def list_visualizations(self): ...
```

Benefits:
- Cleaner dependencies (D3 tools don't need database drivers)
- Easier testing and maintenance
- Tools can evolve independently
- Better composability

### Learning System Pattern

When building tools that need to learn and evolve, implement these key features:

```python
# 1. Solution Tracking with Key Reasons
def track_solution_outcome(self, solution_id: str, outcome: str, 
                         key_reason: str, category: str, 
                         gotchas: List[str] = None):
    """Track WHY solutions work/fail, not just that they do."""
    # Store only the KEY reason, not exhaustive data
    # Categories enable filtering: 'async_fix', 'import_error', etc.

# 2. Pattern Discovery
def discover_patterns(self, problem_id: str):
    """Find similar problems through multiple methods:
    - Same error type
    - Text similarity (BM25)
    - Graph connections
    - Successful solution categories
    """

# 3. Lesson Extraction
def extract_lesson(self, solution_ids: List[str], lesson: str, 
                  category: str, applies_to: List[str]):
    """Extract general principles from specific solutions."""
    # Links multiple solutions to derive patterns

# 4. Multi-dimensional Search
def advanced_search(self, category: str = None, 
                   error_type: str = None,
                   time_range: str = None,
                   min_success_rate: float = None):
    """Search with multiple filters for precise results."""
```

Key principles:
- Store key reasons/gotchas, not exhaustive data
- Use categories for easy filtering
- Build relationships between problems and solutions
- Extract general lessons from specific cases

### Graph Analytics Pattern

For tools managing graph data, provide analytics capabilities:

```python
def analyze_graph(self, graph_name: str, algorithm: str, 
                 params: Dict = None):
    """Essential graph algorithms for problem-solving."""
    
    algorithms = {
        "shortest_path": "Find path between error and solution",
        "connected_components": "Identify problem clusters", 
        "neighbors": "Find related items within N hops",
        "centrality": "Identify most important nodes"
    }
```

This enables agents to understand the structure of their knowledge graph.

### Integration with External Services

When your MCP tool can optionally use external services:

```python
class D3Visualizer:
    def __init__(self):
        # Check if optional service is available
        self.viz_server_url = os.getenv("VIZ_SERVER_URL", "http://localhost:8000")
        self.use_server = self._check_server_availability()
    
    def generate_visualization(self, data):
        if self.use_server:
            try:
                # Use advanced server features
                return self._server_generate(data)
            except:
                # Graceful fallback
                logger.warning("Server unavailable, using local generation")
        
        # Always have local fallback
        return self._local_generate(data)
```

Benefits:
- Works standalone (no hard dependencies)
- Can leverage advanced features when available
- Graceful degradation

### Collection Auto-Creation Pattern

For database tools, ensure collections exist before use:

```python
def track_solution_outcome(self, ...):
    # Ensure collection exists (in case not created on startup)
    if not self.db.has_collection("solution_outcomes"):
        self.db.create_collection("solution_outcomes")
    
    # Now safe to insert
    result = self.db.collection("solution_outcomes").insert(doc)
```

This prevents errors when collections are added after initial setup.

### Environment Variable Configuration

Use environment variables for deployment flexibility:

```python
# In MCP server
output_dir = Path(os.getenv("D3_OUTPUT_DIR", "/tmp/visualizations"))
server_url = os.getenv("VIZ_SERVER_URL", "http://localhost:8000")

# In .mcp.json
"d3-visualizer": {
    "command": "uv",
    "args": [...],
    "env": {
        "D3_OUTPUT_DIR": "/tmp/visualizations",
        "VIZ_SERVER_URL": "http://localhost:8000"
    }
}
```

This allows users to customize behavior without code changes.

### Research Integration Pattern

When tools encounter errors, provide explicit research suggestions:

```python
def research_database_issue(self, error_info: Dict) -> Dict:
    """Prepare research context and tool suggestions."""
    
    return {
        "tool_suggestions": {
            "context7": {
                "action": "Use context7 for official docs",
                "steps": [
                    "await mcp__context7__resolve-library-id('arangodb')",
                    "await mcp__context7__get-library-docs(id, topic='aql')"
                ],
                "when": "For syntax errors or unknown functions"
            },
            "perplexity": {
                "action": "Research specific error",
                "prompt": f"ArangoDB {error_info['error']}...",
                "when": "For error codes or unusual behaviors"
            },
            "glossary": {
                "action": "Check internal glossary",
                "aql": "FOR term IN glossary_terms...",
                "when": "To understand technical terms"
            }
        },
        "recovery_workflow": [
            "1. Check glossary for unfamiliar terms",
            "2. Use context7 for official documentation",
            "3. Use perplexity-ask for specific errors",
            "4. Update glossary with new terms",
            "5. Link solution to error for future"
        ]
    }
```

This empowers agents to self-recover from errors.

## Error Resolution and Knowledge Building

### CRITICAL: Log Problems and Solutions

The most important aspect of MCP tools is building a knowledge base of problems and their solutions. This enables learning from errors and finding fixes faster.

#### 1. When Errors Occur - Log as Unresolved

```python
@mcp.tool()
async def process_data(file_path: str) -> str:
    """Process data from file."""
    try:
        result = await complex_processing(file_path)
        return json.dumps({"success": True, "data": result})
    except Exception as e:
        # CRITICAL: Log unresolved error
        error_id = f"error_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
        
        logger.error(
            f"Processing failed: {e}",
            extra={
                "log_category": "MCP_ERROR",
                "error_id": error_id,
                "tool_name": "process_data",
                "file_path": file_path,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "stack_trace": traceback.format_exc(),
                "resolved": False,  # IMPORTANT: Mark as unresolved
                "resolution": None,
                "fix_rationale": None
            }
        )
        
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_id": error_id,  # Return ID for tracking
            "hint": "Error logged for analysis"
        })
```

#### 2. When You Fix an Error - Update with Resolution

```python
# After fixing an error, ALWAYS update the log entry
async def log_resolution(error_id: str, fix_description: str, rationale: str):
    """Log how an error was resolved for future reference."""
    
    if not LOGGER_AGENT_AVAILABLE:
        logger.warning("Cannot log resolution - logger agent not available")
        return
    
    # Use ArangoDB to update the error log
    update_query = """
    FOR doc IN log_events
        FILTER doc.error_id == @error_id
        UPDATE doc WITH {
            resolved: true,
            resolution: @fix_description,
            fix_rationale: @rationale,
            resolved_at: DATE_ISO8601(DATE_NOW()),
            resolution_execution_id: @execution_id
        } IN log_events
        RETURN NEW
    """
    
    # Execute through MCP or direct connection
    logger.info(
        "Error resolved",
        extra={
            "log_category": "MCP_RESOLVED",
            "error_id": error_id,
            "resolution": fix_description,
            "rationale": rationale
        }
    )
```

#### 3. Create Edge Relationships

```python
async def link_error_to_helpful_resources(error_id: str, helpful_ids: list, relationship_type: str):
    """Create edges linking errors to helpful fixes/scripts/resources."""
    
    # Create edges in error_relationships collection
    for helpful_id in helpful_ids:
        edge_data = {
            "_from": f"log_events/{error_id}",
            "_to": f"log_events/{helpful_id}",
            "relationship_type": relationship_type,
            "created_at": datetime.now().isoformat(),
            "helpfulness_score": 0.9,  # How helpful was this reference
            "context": "This script's fix pattern solved my issue"
        }
        
        # Insert edge
        logger.info(
            "Creating error relationship edge",
            extra={
                "log_category": "MCP_EDGE_CREATED",
                "from_error": error_id,
                "to_resource": helpful_id,
                "relationship": relationship_type
            }
        )

# Example relationships:
# - "inspired_by" - Another error's fix inspired this solution
# - "similar_pattern" - Same error pattern but different context  
# - "uses_technique" - Borrowed technique from another fix
# - "references_script" - Script that helped solve this
# - "depends_on_fix" - This fix requires another fix first
```

#### 4. Query Past Solutions with Graph Traversal

```python
async def find_related_fixes(error_type: str, error_message: str, max_depth: int = 2) -> list:
    """Find related fixes using graph traversal."""
    
    # Direct matches first
    direct_query = """
    FOR doc IN log_events
        FILTER doc.error_type == @error_type
        FILTER doc.resolved == true
        RETURN doc
    """
    
    # Graph traversal for related fixes
    graph_query = """
    // Start from similar errors
    FOR error IN log_events
        FILTER error.error_type == @error_type OR 
               CONTAINS(LOWER(error.error_message), LOWER(@keyword))
        FILTER error.resolved == true
        
        // Traverse relationships up to max_depth
        FOR v, e, p IN 1..@max_depth OUTBOUND error 
            GRAPH 'error_resolution_graph'
            OPTIONS {uniqueVertices: 'global'}
            
            // Only follow helpful relationships
            FILTER e.helpfulness_score > 0.7
            FILTER v.resolved == true
            
            RETURN DISTINCT {
                error: v.error_message,
                resolution: v.resolution,
                rationale: v.fix_rationale,
                relationship_path: p.edges[*].relationship_type,
                distance: LENGTH(p.edges),
                relevance_score: (2 - LENGTH(p.edges)) / 2 * e.helpfulness_score
            }
    """
    
    # This finds fixes that helped solve similar problems
```

### Best Practices for Knowledge Building

1. **Always Log Errors with Context**
   ```python
   extra={
       "log_category": "MCP_ERROR",
       "tool_name": "your_tool",
       "parameters": params,
       "error_type": type(e).__name__,
       "resolved": False
   }
   ```

2. **Update When Fixed**
   - Never leave errors as unresolved if you fixed them
   - Include detailed rationale for future reference
   - Link to relevant documentation or issues

3. **Categories for MCP Logs**
   - `MCP_ERROR` - Tool execution errors
   - `MCP_RESOLVED` - Fixed errors with solutions
   - `MCP_STARTUP` - Initialization issues
   - `MCP_CONNECTION` - External service failures
   - `TOOL_TIMEOUT` - Performance issues

4. **Query Patterns for Learning**
   ```aql
   // Find all unresolved MCP errors
   FOR doc IN log_events
       FILTER doc.log_category == "MCP_ERROR"
       FILTER doc.resolved == false
       RETURN doc
   
   // Find successful resolutions for specific error type
   FOR doc IN log_events
       FILTER doc.error_type == "FileNotFoundError"
       FILTER doc.resolved == true
       RETURN {
           fix: doc.resolution,
           why: doc.fix_rationale
       }
   ```

### Example: Complete Error Lifecycle with Relationships

```python
# 1. Error occurs and is logged
try:
    result = await process_data("./data.csv")
except FileNotFoundError as e:
    error_id = "err_1234_abcd"
    log_unresolved_error(e, {"file": "./data.csv", "cwd": os.getcwd()})
    
    # Search for similar errors
    similar_fixes = await find_related_fixes("FileNotFoundError", "data.csv")
    return error_response(error_id, hints=similar_fixes)

# 2. You find that error_789_xyz had a similar issue with config files
# Their fix used Path.resolve() - you try it and it works!

# 3. Log the resolution AND create edges
await log_resolution(
    error_id=error_id,
    fix_description="Changed to use absolute paths with Path.resolve()",
    rationale="MCP tools run from different working directories, so relative paths fail. Always use absolute paths or find_dotenv() pattern."
)

# 4. Create edges to helpful resources
await mcp_arango_tools.edge(
    from_id=f"log_events/{error_id}",
    to_id="log_events/err_789_xyz",  # The error that helped
    collection="error_relationships",
    relationship_type="inspired_by",
    helpfulness_score=0.95,
    notes="Their Path.resolve() solution worked perfectly for my CSV issue"
)

# Also link to the script that had the working pattern
await mcp_arango_tools.edge(
    from_id=f"log_events/{error_id}",
    to_id="scripts/data_processor.py",
    collection="error_relationships", 
    relationship_type="references_script",
    helpfulness_score=0.8,
    notes="This script shows proper path handling patterns"
)

# 5. Next time: Graph traversal finds related fixes even if not exact match!
# Query: "FileNotFoundError with JSON files"
# Finds: Your CSV fix → inspired_by → config file fix → similar_pattern → JSON fix
# Returns entire solution chain with relevance scores!
```

### Graph Traversal Benefits

1. **Discover Non-Obvious Solutions**
   - Error A → inspired_by → Error B → uses_technique → Error C
   - Find fixes that worked for seemingly unrelated problems

2. **Build Solution Chains**
   - ModuleNotFoundError → depends_on_fix → PYTHONPATH issue → references_script → setup.py

3. **Track Knowledge Sources**
   - Which scripts/errors were most helpful for solving problems
   - Build a "most valuable fixes" leaderboard

4. **Pattern Recognition**
   - Identify clusters of related errors
   - Find common root causes across different symptoms

### Managing Evolving Knowledge

#### 5. Deprecate Outdated Solutions

```python
async def deprecate_solution(error_id: str, reason: str, replacement_id: str = None):
    """Mark a solution as deprecated when better approach is found."""
    
    # Multi-document transaction to update solution and relationships
    update_operations = [
        # 1. Mark original solution as deprecated
        {
            "collection": "log_events",
            "filter": {"_key": error_id},
            "update": {
                "deprecated": True,
                "deprecated_at": datetime.now().isoformat(),
                "deprecation_reason": reason,
                "replaced_by": replacement_id,
                "resolved": False  # No longer considered resolved
            }
        },
        
        # 2. Update all edges pointing to this solution
        {
            "collection": "error_relationships",
            "filter": {"_to": f"log_events/{error_id}"},
            "update": {
                "deprecated": True,
                "helpfulness_score": 0.1,  # Dramatically reduce score
                "deprecation_note": f"Deprecated: {reason}"
            }
        }
    ]
    
    # Log the deprecation
    logger.warning(
        f"Solution deprecated: {error_id}",
        extra={
            "log_category": "MCP_KNOWLEDGE_UPDATED",
            "action": "deprecate_solution",
            "error_id": error_id,
            "reason": reason,
            "replacement": replacement_id
        }
    )

# Example usage
await deprecate_solution(
    error_id="err_old_123",
    reason="subprocess.run() with shell=True is insecure, use shlex.split() instead",
    replacement_id="err_new_456"
)
```

#### 6. Handle Contradicting Solutions

```python
async def resolve_contradiction(solutions: list, test_results: dict):
    """When multiple solutions contradict, test and update based on results."""
    
    winning_solution = None
    failed_solutions = []
    
    # Test each solution
    for solution in solutions:
        if test_results[solution["_key"]]["success"]:
            winning_solution = solution
        else:
            failed_solutions.append(solution)
    
    if not winning_solution:
        logger.error("All solutions failed!", extra={"solutions": solutions})
        return
    
    # Bulk update to resolve contradiction
    bulk_updates = []
    
    # 1. Confirm winning solution
    bulk_updates.append({
        "collection": "log_events",
        "key": winning_solution["_key"],
        "update": {
            "confirmed_at": datetime.now().isoformat(),
            "confirmation_count": {"$inc": 1},
            "test_results": test_results[winning_solution["_key"]]
        }
    })
    
    # 2. Deprecate failed solutions
    for failed in failed_solutions:
        bulk_updates.append({
            "collection": "log_events",
            "key": failed["_key"],
            "update": {
                "deprecated": True,
                "deprecation_reason": "Failed when tested",
                "replaced_by": winning_solution["_key"],
                "failed_test": test_results[failed["_key"]]
            }
        })
    
    # 3. Create "contradicts" edges
    for failed in failed_solutions:
        bulk_updates.append({
            "collection": "error_relationships",
            "insert": {
                "_from": f"log_events/{winning_solution['_key']}",
                "_to": f"log_events/{failed['_key']}",
                "relationship_type": "contradicts",
                "test_date": datetime.now().isoformat(),
                "reason": "Tested and proven superior"
            }
        })
    
    # Execute bulk update
    await execute_bulk_updates(bulk_updates)
```

#### 7. Knowledge Evolution Patterns

```python
async def evolve_knowledge(error_type: str, new_insight: str):
    """Update all related solutions with new understanding."""
    
    # Find all solutions for this error type
    find_query = """
    FOR doc IN log_events
        FILTER doc.error_type == @error_type
        FILTER doc.resolved == true
        FILTER doc.deprecated != true
        RETURN doc
    """
    
    solutions = await execute_query(find_query, {"error_type": error_type})
    
    # Categorize based on new insight
    still_valid = []
    needs_update = []
    now_deprecated = []
    
    for solution in solutions:
        if "shell=True" in solution.get("resolution", ""):
            now_deprecated.append(solution)
        elif "subprocess" in solution.get("resolution", ""):
            needs_update.append(solution)
        else:
            still_valid.append(solution)
    
    # Bulk update based on categorization
    updates = []
    
    # Deprecate dangerous solutions
    for sol in now_deprecated:
        updates.append({
            "key": sol["_key"],
            "update": {
                "deprecated": True,
                "deprecation_reason": new_insight,
                "security_risk": True
            }
        })
    
    # Update solutions that need modification
    for sol in needs_update:
        updates.append({
            "key": sol["_key"],
            "update": {
                "needs_review": True,
                "review_reason": new_insight,
                "last_reviewed": datetime.now().isoformat()
            }
        })
    
    # Confirm still valid solutions
    for sol in still_valid:
        updates.append({
            "key": sol["_key"],
            "update": {
                "reconfirmed_at": datetime.now().isoformat(),
                "still_valid_because": "Uses secure subprocess pattern"
            }
        })
    
    logger.info(
        f"Knowledge evolved for {error_type}",
        extra={
            "deprecated_count": len(now_deprecated),
            "updated_count": len(needs_update),
            "valid_count": len(still_valid),
            "insight": new_insight
        }
    )
```

#### 8. Query Updated Knowledge

```aql
// Find non-deprecated solutions
FOR doc IN log_events
    FILTER doc.error_type == @error_type
    FILTER doc.resolved == true
    FILTER doc.deprecated != true
    SORT doc.confirmed_at DESC, doc.resolved_at DESC
    RETURN doc

// Find contradiction chains
FOR v, e, p IN 1..3 OUTBOUND @start_error error_relationships
    FILTER e.relationship_type == "contradicts"
    RETURN {
        original: p.vertices[0].resolution,
        contradicted_by: v.resolution,
        reason: e.reason,
        test_date: e.test_date
    }

// Find solutions that need review
FOR doc IN log_events
    FILTER doc.needs_review == true
    FILTER doc.deprecated != true
    RETURN {
        solution: doc.resolution,
        review_reason: doc.review_reason,
        last_reviewed: doc.last_reviewed
    }
```

## Summary

1. Use FastMCP, not standard MCP SDK
2. Handle imports and paths carefully  
3. Always return JSON strings from tools
4. Add comprehensive error handling
5. Enable debug logging when troubleshooting
6. Test locally before integrating with Claude
7. Reload Claude after any config changes
8. **CRITICAL: Always log errors with `resolved: False`**
9. **CRITICAL: Update logs with resolution and rationale when fixed**
10. **CRITICAL: ALWAYS create edges to helpful resources when resolving**
11. **Build a navigable knowledge graph, not just a flat log**

### The Golden Rule: No Orphan Solutions

**EVERY time you resolve an error, you MUST create edges to:**
- The error/solution that inspired your fix (`inspired_by`)
- Scripts that showed the working pattern (`references_script`)  
- Techniques you borrowed (`uses_technique`)
- Other errors with similar patterns (`similar_pattern`)

**NO EXCEPTIONS!** A solution without edges is worthless for future learning.

```python
# ❌ BAD - Orphan solution
logger.info("Fixed the error", extra={
    "resolved": True,
    "resolution": "Used absolute paths"
})

# ✅ GOOD - Connected solution
await mcp__arango-tools__insert(
    # ... error details ...
    resolved=True,
    resolution="Used Path.resolve() for absolute paths"
)

# MUST be followed by:
await mcp__arango-tools__edge(
    from_id=f"log_events/{error_id}",
    to_id="log_events/similar_error_that_helped",
    collection="error_relationships",
    relationship_type="inspired_by",
    helpfulness_score=0.95
)
```

The combination of FastMCP pattern, logger agent integration, and **mandatory edge creation** builds a self-improving knowledge graph where every solution contributes to future problem-solving. Following this guide ensures your MCP tools don't just work - they learn and get smarter with every fix.