# MCP Server Development Checklist

This checklist ensures MCP servers work correctly with Claude Code's Model Context Protocol infrastructure. It's based on the reference implementation in `mcp_arango_tools.py` and lessons learned from debugging various MCP servers.

## 1. File Structure Requirements

### Shebang Line
- [ ] **MUST use**: `#!/usr/bin/env -S uv run --script`
- [ ] **NOT**: `#!/usr/bin/env python3` or `#!/usr/bin/env python`
- [ ] Must be the very first line of the file

### Script Dependencies Block
- [ ] **MUST include** immediately after shebang:
```python
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils>=0.1.5",
#     # other dependencies
# ]
# ///
```
- [ ] **mcp-logger-utils>=0.1.5** is REQUIRED for all MCP servers
- [ ] List all direct dependencies (not transitive ones)
- [ ] Use exact format with `# ///` markers

## 2. Import Requirements

### Forbidden Imports
- [ ] **NO sys.path manipulation**
  - ❌ `sys.path.insert(0, str(Path(__file__).parent))`
  - ❌ `sys.path.append(...)`
  - ❌ Any modification of sys.path

### Required Imports
- [ ] **MUST import from mcp-logger-utils**:
```python
from mcp_logger_utils import MCPLogger, debug_tool
```

### Import Order
1. Standard library imports
2. Third-party imports
3. MCP-specific imports (fastmcp, mcp_logger_utils)
4. NO local module imports (define utilities inline instead)

## 3. MCP Server Initialization

### Required Setup
```python
# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("server-name")
mcp_logger = MCPLogger("server-name")
```

### Naming Convention
- [ ] Server name in FastMCP should match file name pattern
  - File: `mcp_arango_tools.py` → Server: `"arango-tools"`
  - File: `mcp_d3_visualizer.py` → Server: `"d3-visualizer"`

### Service Class Pattern (for complex servers)
- [ ] Create a service class to encapsulate functionality
- [ ] Initialize as singleton AFTER MCP setup
```python
class ArangoTools:
    """Service class for database operations."""
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def get_schema(self) -> Dict[str, Any]:
        # Implementation
        pass

# Create singleton after imports
tools = ArangoTools()

# Tools use the service instance
@mcp.tool()
@debug_tool(mcp_logger)
async def schema() -> str:
    result = tools.get_schema()
    return json.dumps(result, indent=2, default=str)
```

## 4. Tool Decorator Pattern

### MUST Use Both Decorators
```python
@mcp.tool()
@debug_tool(mcp_logger)
async def tool_name(...) -> str:
    """Tool documentation."""
    # implementation
```

### Critical Rules
- [ ] **Order matters**: `@mcp.tool()` first, `@debug_tool(mcp_logger)` second
- [ ] All tools MUST be async functions
- [ ] All tools MUST return a string (JSON formatted)
- [ ] Never use just `@mcp.tool()` alone

## 5. Tool Implementation

### Return Format
- [ ] **MUST return JSON string**, not dict or other types
- [ ] Use `indent=2` for readability
- [ ] Use `default=str` for non-serializable objects (like datetime)
```python
# ✅ Correct
return json.dumps({"success": True, "data": result}, indent=2, default=str)

# ❌ Wrong
return {"success": True, "data": result}
```

### Error Handling Pattern
- [ ] Use consistent error response structure
- [ ] Include error type for debugging
- [ ] Provide helpful suggestions when possible
```python
try:
    # operation
    return json.dumps({"success": True, "data": result}, indent=2, default=str)
except SpecificError as e:
    return json.dumps({
        "success": False,
        "error": str(e),
        "type": type(e).__name__,
        "suggestions": ["Check X", "Try Y"]
    }, indent=2)
except Exception as e:
    return json.dumps({"error": str(e), "type": type(e).__name__}, indent=2)
```

### Parameter Handling
- [ ] JSON string parameters must be parsed with error handling:
```python
# Parse JSON parameters safely
if bind_vars:
    try:
        vars = json.loads(bind_vars)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON in bind_vars: {e}",
            "suggestion": "Ensure bind_vars is valid JSON string"
        }, indent=2)
```

### Collection/Resource Validation
- [ ] Check if resources exist before operations
```python
# Check collection exists
if not tools.db.has_collection(collection):
    return json.dumps({"error": f"Collection '{collection}' not found"})
```

### Standardized Response Format (REQUIRED)
- [ ] **ALL MCP servers MUST use consistent response format**
- [ ] Return structure must include success/error status and metadata

#### Required Response Structure:
```json
{
    "success": bool,
    "data": {...} | null,    // Only present when success=true
    "error": str | null,     // Only present when success=false
    "metadata": {
        "duration_ms": int,
        "tool": str,
        "version": str,
        "timestamp": str
    }
}
```

#### Implementation Options:

**MANDATORY: Use response_utils (ALL MCP servers MUST use this)**
```python
# REQUIRED imports in every MCP server
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Success case (ONLY use this format)
return create_success_response(
    data={"result": value, "count": 10},
    tool_name="your_tool_name",
    start_time=start_time  # from time.time()
)

# Error case (ONLY use this format)
return create_error_response(
    error="Detailed error message here",
    tool_name="your_tool_name", 
    start_time=start_time
)
```

**❌ FORBIDDEN: Manual JSON formatting (DO NOT USE THESE PATTERNS)**
These patterns are now forbidden and will fail code review:

```python
# ❌ Manual json.dumps
return json.dumps({"success": True, "data": result})

# ❌ Raw dict returns  
return {"success": False, "error": "Something failed"}

# ❌ Inconsistent field names
return {"status": "ok", "result": data}  # Wrong field names
```

**Why response_utils is mandatory:**
- Ensures consistent response format across ALL MCP servers
- Automatic metadata generation (duration, timestamps, version)
- Centralized format updates
- Prevents inconsistency bugs
- Required for proper MCP tool integration
```python
# Success response
return json.dumps({
    "success": True,
    "data": {"result": value},
    "error": None,
    "metadata": {
        "duration_ms": int((time.time() - start_time) * 1000),
        "tool": "your_tool_name",
        "version": "2025-07-19",
        "timestamp": datetime.now().isoformat()
    }
}, indent=2, default=str)

# Error response
return json.dumps({
    "success": False,
    "data": None,
    "error": "Error message here",
    "metadata": {
        "duration_ms": int((time.time() - start_time) * 1000),
        "tool": "your_tool_name",
        "version": "2025-07-19",
        "timestamp": datetime.now().isoformat()
    }
}, indent=2)
```

**Benefits of consistent response format:**
- Easier error handling for clients
- Consistent performance tracking with duration_ms
- Clear success/failure indication
- Standardized metadata for debugging

## 6. Variable Initialization

### Prevent UnboundLocalError
- [ ] Initialize all variables at function start:
```python
# ✅ Correct
def analyze_data(data):
    nodes = []
    links = []
    # rest of function

# ❌ Wrong - might reference before assignment
def analyze_data(data):
    if condition:
        nodes = []
    # nodes might be undefined here
```

## 7. Conditional Logic

### Complete Coverage
- [ ] All if/elif chains must handle all cases
- [ ] Use else clause for remaining cases
- [ ] Don't let valid data fall through to error/unknown

Example from ADVISOR_BUG_FIXES_SUMMARY:
```python
# ✅ Correct - handles all cases
if isinstance(data, list) and all(isinstance(item, dict) for item in data):
    if all({"_from", "_to"}.issubset(item.keys()) for item in data[:5]):
        # ArangoDB edge format
    elif any("vertices" in item for item in data[:5]):
        # ArangoDB path format  
    else:
        # Regular tabular data (was falling through before)
```

## 8. Main Entry Point

### Required Structure
```python
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            print(f"✓ {Path(__file__).name} can start successfully!")
            sys.exit(0)
        elif sys.argv[1] == "debug":
            asyncio.run(debug_function())
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
    else:
        # Run the MCP server
        try:
            logger.info("Starting MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)
```

### Test Functions (Optional but Recommended)
- [ ] Include `working_usage()` - stable examples
- [ ] Include `debug_function()` - experimental code (if needed)
- [ ] Document usage in docstrings
- [ ] These are NOT required for basic MCP servers

Example working_usage():
```python
async def working_usage():
    """Demonstrate working usage of the tools."""
    logger.info("=== Working Usage Demo ===")
    
    # Example tool usage
    result = await your_tool("parameter")
    logger.info(f"Result: {result}")
    
    logger.success("✅ Demo completed!")
    return True
```

## 9. Documentation

### Module Docstring
- [ ] Include comprehensive module docstring
- [ ] Add detailed debugging notes section
- [ ] Document common pitfalls with specific solutions
- [ ] Include environment variables
- [ ] Add "HOW TO DEBUG THIS MCP SERVER" section

Example (from mcp_arango_tools.py):
```python
"""
MCP Server for X - Brief description.

=== MCP DEBUGGING NOTES (YYYY-MM-DD) ===

COMMON MCP USAGE PITFALLS (learned from testing):
1. Boolean parameters often fail validation - use metadata JSON instead
2. The 'metadata' parameter must be a valid JSON string
3. Empty query results are SUCCESS: {"success": true, "count": 0, "results": []}
4. Always check resource exists before querying

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start
   python src/cc_executor/servers/mcp_server.py test
   
   # Check imports work
   python -c "from cc_executor.servers.mcp_server import ServiceClass"
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/server-name_startup.log
   - Debug log: ~/.claude/mcp_logs/server-name_debug.log
   - Calls log: ~/.claude/mcp_logs/server-name_calls.jsonl

3. COMMON ISSUES & FIXES:
   
   a) Connection refused:
      - Error: "Connection refused"
      - Fix: Start the service
      - Check: sudo systemctl status service-name
   
   b) Module not found:
      - Error: "ModuleNotFoundError: No module named 'x'"
      - Fix: uv add package-name
      - Check: python -c "import package"

4. ENVIRONMENT VARIABLES:
   - PYTHONPATH=/path/to/project/src
   - SERVICE_HOST=localhost (default)
   - SERVICE_PORT=8080 (default)

5. CURRENT STATUS:
   - ✅ All imports working
   - ❌ Known issue X
   - ⚠️ Warning about Y

=== END DEBUGGING NOTES ===
"""
```

### Tool Docstrings
- [ ] Document purpose
- [ ] Document all parameters
- [ ] Document return format
- [ ] Include examples

## 10. Advanced Patterns (from mcp_arango_tools.py)

### Retry Logic for External Services
- [ ] Use tenacity for connection retries
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True
)
def _connect(self):
    """Connect to service with retry logic."""
    # Connection code
```

### Conditional Tool Decorators
- [ ] Handle missing optional dependencies gracefully
```python
# When mcp_logger might not be available
@mcp.tool
@debug_tool(mcp_logger) if mcp_logger else lambda f: f
async def tool_name():
    pass
```

### Import Error Handling
- [ ] Gracefully handle missing optional dependencies
```python
try:
    from optional_package import Feature
    FEATURE_AVAILABLE = True
except ImportError:
    FEATURE_AVAILABLE = False
    logger.warning("Optional feature not available")
```

## 11. Common Pitfalls to Avoid

### From mcp_arango_tools.py Experience
1. **Boolean parameters often fail MCP validation**
   - Use JSON metadata parameter instead
   
2. **Different parameter formats for different operations**
   - `insert()`: Direct params + optional metadata JSON
   - `upsert()`: ALL parameters must be JSON strings
   - Check each tool's specific requirements

3. **Empty results are SUCCESS**
   - `{"success": true, "count": 0, "results": []}` is valid
   - Don't treat empty results as errors

4. **Lazy Loading for Heavy Dependencies**
   - Use singleton pattern for ML/heavy libraries
   - Load only when first used, not at import time

## 11. Testing Checklist

### Local Testing
- [ ] `python mcp_server.py test` runs without errors
- [ ] No import errors at startup
- [ ] Heavy dependencies lazy-loaded (not imported at startup)

### MCP Integration Testing
- [ ] Server starts via MCP config
- [ ] Tools appear in Claude Code
- [ ] Tools execute successfully
- [ ] Errors return proper JSON format

## 12. Performance Considerations

### Lazy Loading for Heavy Dependencies

**CRITICAL**: For detailed implementation guidance, see [`docs/supplementary/LAZY_LOADING_STATE.md`](./supplementary/LAZY_LOADING_STATE.md)

#### Why Lazy Loading is Essential
- [ ] Heavy ML libraries (sklearn, faiss, sentence-transformers, marker-pdf) can take 10-30 seconds to load
- [ ] MCP servers have startup timeouts - loading heavy dependencies at import time causes server failures
- [ ] Memory efficiency - only load what's actually used

#### Implementation Pattern (from mcp_arango_tools.py)
- [ ] Use thread-safe singleton pattern
- [ ] Double-checked locking for thread safety
- [ ] Encapsulate all related state and behavior

```python
class MLProcessor:
    """Thread-safe, lazy-loading singleton for ML operations."""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MLProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.models = None
            self.models_loaded = False
            self.load_lock = threading.Lock()
            self.initialized = True
    
    def _ensure_models_loaded(self):
        """Load models on first use with double-checked locking."""
        if not self.models_loaded:
            with self.load_lock:
                if not self.models_loaded:
                    logger.info("Loading models (first use)...")
                    # Import and load here, not at module level
                    from sklearn.cluster import KMeans
                    self.KMeans = KMeans
                    self.models_loaded = True
```

#### Key Points from LAZY_LOADING_STATE.md
- [ ] **Instant Server Startup**: Server starts immediately, models load on first request
- [ ] **Thread Safety**: Prevents race conditions when multiple requests arrive simultaneously
- [ ] **Encapsulation**: All state and behavior contained in one class, not scattered globals
- [ ] **Testability**: Easy to mock for testing, no global state manipulation

#### Anti-Patterns to Avoid
- [ ] ❌ Global variables with loading functions
- [ ] ❌ Module-level imports of heavy libraries
- [ ] ❌ Unprotected lazy loading (race conditions)

```python
# ❌ WRONG - Brittle and not thread-safe
MODELS = None
_loaded = False

def _ensure_loaded():
    global MODELS, _loaded
    if not _loaded:
        import heavy_library  # Race condition!
        MODELS = heavy_library.load()
        _loaded = True

# ✅ CORRECT - Use the singleton pattern shown above
```

## Summary

Following this checklist ensures your MCP server:
1. Starts reliably without import errors
2. Integrates properly with Claude Code
3. Handles errors gracefully
4. Performs efficiently with lazy loading
5. Provides good debugging information

Always test with `python your_server.py test` before deploying!