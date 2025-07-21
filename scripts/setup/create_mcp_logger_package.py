#!/usr/bin/env python3
"""Create a minimal mcp-logger-utils package for shared MCP utilities."""

import os
from pathlib import Path

def create_package_structure():
    """Create the package structure for mcp-logger-utils."""
    
    # Create package directory
    package_dir = Path("mcp-logger-utils")
    package_dir.mkdir(exist_ok=True)
    
    # Create pyproject.toml
    pyproject_content = '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-logger-utils"
version = "0.1.0"
description = "Shared utilities for MCP servers"
authors = [{name = "Graham Anderson", email = "graham@grahama.co"}]
dependencies = [
    "loguru>=0.7.0",
]
requires-python = ">=3.8"
readme = "README.md"
license = {text = "MIT"}

[project.urls]
Homepage = "https://github.com/yourusername/mcp-logger-utils"
'''
    
    (package_dir / "pyproject.toml").write_text(pyproject_content)
    
    # Create README.md
    readme_content = '''# MCP Logger Utils

Shared utilities for MCP (Model Context Protocol) servers.

## Installation

```bash
pip install mcp-logger-utils
```

## Usage

```python
from mcp_logger_utils import MCPLogger, debug_tool

# Initialize logger
mcp_logger = MCPLogger("my-server")

# Use debug decorator
@debug_tool(mcp_logger)
async def my_tool():
    pass
```
'''
    
    (package_dir / "README.md").write_text(readme_content)
    
    # Create package source directory
    src_dir = package_dir / "src" / "mcp_logger_utils"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py
    init_content = '''"""MCP Logger Utils - Shared utilities for MCP servers."""

from .logger import MCPLogger, debug_tool

__version__ = "0.1.0"
__all__ = ["MCPLogger", "debug_tool"]
'''
    
    (src_dir / "__init__.py").write_text(init_content)
    
    # Create logger.py with the actual implementation
    logger_content = '''"""MCP Logger implementation."""

import json
import os
import sys
import time
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class MCPLogger:
    """Centralized logger for MCP servers with comprehensive debugging features."""
    
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
        
        # File logging
        self.debug_log = self.log_dir / f"{tool_name}_debug.log"
        logger.add(
            self.debug_log,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        self.log_startup_info()
    
    def log_startup_info(self):
        """Log startup information."""
        logger.info(f"MCP Server \'{self.tool_name}\' starting - PID: {os.getpid()}")
        logger.debug(f"Python: {sys.executable}")
        logger.debug(f"Working dir: {os.getcwd()}")
        
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log errors with context."""
        logger.error(f"{type(error).__name__}: {error}")
        if context:
            logger.debug(f"Context: {json.dumps(context, indent=2)}")
            
    def log_call(self, function: str, args: Dict[str, Any], result: Any, duration: float):
        """Log tool calls with timing."""
        status = "✓" if not isinstance(result, Exception) else "✗"
        logger.info(f"{status} {function} completed in {duration:.3f}s")


def debug_tool(mcp_logger: MCPLogger):
    """Decorator for comprehensive tool debugging."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            logger.debug(f"Tool {func.__name__} called")
            
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
                    "kwargs": kwargs,
                    "duration": duration
                })
                
                # Return error response instead of raising
                return json.dumps({
                    "error": str(e),
                    "type": type(e).__name__,
                    "tool": func.__name__,
                    "traceback": traceback.format_exc()
                }, indent=2)
        
        return wrapper
    return decorator
'''
    
    (src_dir / "logger.py").write_text(logger_content)
    
    # Create .gitignore
    gitignore_content = '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
'''
    
    (package_dir / ".gitignore").write_text(gitignore_content)
    
    print("✅ Package structure created in ./mcp-logger-utils/")
    print("\nNext steps:")
    print("1. cd mcp-logger-utils")
    print("2. pip install -e .  # For local development")
    print("3. pip install build twine  # For publishing")
    print("4. python -m build")
    print("5. python -m twine upload dist/*  # Upload to PyPI")
    print("\nOr for testing without PyPI:")
    print("pip install git+file:///path/to/mcp-logger-utils")

if __name__ == "__main__":
    create_package_structure()