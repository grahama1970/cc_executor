#!/usr/bin/env python3
"""Fix all MCP servers to be self-contained by inlining MCPLogger."""

import re
from pathlib import Path

# The minimal MCPLogger to inline
INLINE_MCP_LOGGER = '''
class MCPLogger:
    """Minimal logger for MCP servers."""
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.log_dir = Path.home() / ".claude" / "mcp_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure loguru
        logger.remove()
        logger.add(
            sys.stderr,
            level="DEBUG" if os.getenv("MCP_DEBUG") else "INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    def log_error(self, error: Exception, context: dict = None):
        """Log errors."""
        logger.error(f"{type(error).__name__}: {error}")
        if context:
            logger.debug(f"Context: {context}")
    
    def log_call(self, function: str, args: dict, result: Any, duration: float):
        """Log tool calls."""
        status = "✓" if not isinstance(result, Exception) else "✗"
        logger.info(f"{status} {function} completed in {duration:.3f}s")


def debug_tool(mcp_logger: MCPLogger):
    """Decorator for tool debugging."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                mcp_logger.log_call(
                    func.__name__,
                    {"args": args, "kwargs": kwargs},
                    result,
                    duration
                )
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                mcp_logger.log_error(e, {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                })
                return json.dumps({
                    "error": str(e),
                    "type": type(e).__name__,
                    "tool": func.__name__
                }, indent=2)
        
        return wrapper
    return decorator
'''

def fix_mcp_server(filepath: Path):
    """Fix a single MCP server file."""
    print(f"Processing {filepath.name}...")
    
    content = filepath.read_text()
    
    # Check if it has UV script header and imports from cc_executor
    if not content.startswith("#!/usr/bin/env -S uv run --script"):
        print(f"  Skipping - not a UV script")
        return
    
    if "from cc_executor.utils.mcp_logger import MCPLogger" not in content:
        print(f"  Skipping - doesn't import MCPLogger")
        return
    
    # Remove the import
    content = re.sub(
        r'from cc_executor\.utils\.mcp_logger import MCPLogger, debug_tool\n',
        '',
        content
    )
    
    # Find where to insert the inline code (after other imports)
    import_section_end = 0
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith(('import ', 'from ', '#')) and i > 10:
            import_section_end = i
            break
    
    # Insert the inline MCPLogger
    lines.insert(import_section_end, INLINE_MCP_LOGGER)
    
    # Also need to add missing imports
    additional_imports = []
    if 'from pathlib import Path' not in content:
        additional_imports.append('from pathlib import Path')
    if 'from typing import' not in content or 'Any' not in content:
        additional_imports.append('from typing import Any')
    if 'from functools import wraps' not in content:
        additional_imports.append('from functools import wraps')
    if 'import json' not in content:
        additional_imports.append('import json')
    
    # Find where to add these imports
    for i, line in enumerate(lines):
        if line.startswith('from loguru import logger'):
            for imp in reversed(additional_imports):
                lines.insert(i, imp)
            break
    
    # Write back
    new_content = '\n'.join(lines)
    filepath.write_text(new_content)
    print(f"  ✓ Fixed {filepath.name}")

def main():
    """Fix all MCP servers."""
    servers_dir = Path("src/cc_executor/servers")
    
    # List of files to fix
    files_to_fix = [
        "mcp_d3_visualizer.py",
        "mcp_kilocode_review.py", 
        "mcp_logger_tools.py",
        "mcp_tool_journey.py",
        "mcp_tool_sequence_optimizer.py"
    ]
    
    for filename in files_to_fix:
        filepath = servers_dir / filename
        if filepath.exists():
            fix_mcp_server(filepath)
        else:
            print(f"Warning: {filename} not found")

if __name__ == "__main__":
    main()