"""Centralized MCP Logger for comprehensive debugging.

Based on MCP_DEBUGGING_GUIDE.md recommendations for better visibility.
"""

from pathlib import Path
from datetime import datetime
import json
import sys
import os
from typing import Optional, Dict, Any
from functools import wraps
import time
import traceback
from loguru import logger

class MCPLogger:
    """Centralized logger for MCP servers with comprehensive debugging features."""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.log_dir = Path.home() / ".claude" / "mcp_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Different log files for different purposes
        self.startup_log = self.log_dir / f"{tool_name}_startup.log"
        self.error_log = self.log_dir / f"{tool_name}_errors.log"
        self.calls_log = self.log_dir / f"{tool_name}_calls.jsonl"
        self.debug_log = self.log_dir / f"{tool_name}_debug.log"
        
        # Configure loguru
        logger.remove()  # Remove default handler
        
        # Console output (stderr for MCP compatibility)
        logger.add(
            sys.stderr, 
            level="DEBUG" if os.getenv("MCP_DEBUG") else "INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # File output with rotation
        logger.add(
            self.debug_log,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Log startup info
        self.log_startup_info()
    
    def log_startup_info(self):
        """Log comprehensive startup information."""
        startup_info = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": self.tool_name,
            "pid": os.getpid(),
            "python": sys.executable,
            "python_version": sys.version,
            "working_dir": os.getcwd(),
            "sys_path": sys.path,
            "env": {
                "MCP_DEBUG": os.getenv("MCP_DEBUG", "not set"),
                "ANTHROPIC_DEBUG": os.getenv("ANTHROPIC_DEBUG", "not set"),
                "PYTHONPATH": os.getenv("PYTHONPATH", "not set"),
                "UV_PROJECT_ROOT": os.getenv("UV_PROJECT_ROOT", "not set")
            }
        }
        
        with open(self.startup_log, 'a') as f:
            f.write(json.dumps(startup_info, indent=2) + "\n")
        
        logger.info(f"MCP Server '{self.tool_name}' starting - PID: {os.getpid()}")
        logger.debug(f"Python: {sys.executable}")
        logger.debug(f"Working dir: {os.getcwd()}")
        logger.debug(f"MCP_DEBUG: {os.getenv('MCP_DEBUG', 'not set')}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with full context."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        with open(self.error_log, 'a') as f:
            f.write(json.dumps(error_entry) + '\n')
        
        logger.error(f"{type(error).__name__}: {error}")
        if context:
            logger.error(f"Context: {json.dumps(context, indent=2)}")
    
    def log_call(self, function: str, args: Dict[str, Any], result: Any, duration: float):
        """Log tool calls with timing."""
        call_entry = {
            "timestamp": datetime.now().isoformat(),
            "function": function,
            "args": self._serialize_args(args),
            "success": not isinstance(result, Exception),
            "duration_ms": duration * 1000,
            "result_preview": self._preview_result(result)
        }
        
        if isinstance(result, Exception):
            call_entry["error"] = str(result)
            call_entry["error_type"] = type(result).__name__
        
        with open(self.calls_log, 'a') as f:
            f.write(json.dumps(call_entry) + '\n')
        
        status = "✓" if call_entry["success"] else "✗"
        logger.info(f"{status} {function} completed in {duration:.3f}s")
    
    def _serialize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Safely serialize arguments for logging."""
        serialized = {}
        for key, value in args.items():
            try:
                # Try to JSON serialize to ensure it's safe
                json.dumps(value)
                serialized[key] = value
            except:
                # Fall back to string representation
                serialized[key] = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        return serialized
    
    def _preview_result(self, result: Any) -> str:
        """Create a preview of the result for logging."""
        if isinstance(result, Exception):
            return f"Error: {type(result).__name__}"
        
        try:
            result_str = str(result)
            if len(result_str) > 200:
                return result_str[:200] + "..."
            return result_str
        except:
            return "<unprintable result>"


def debug_tool(mcp_logger: MCPLogger):
    """Decorator for comprehensive tool debugging."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Log the call
            logger.debug(f"Tool {func.__name__} called")
            logger.debug(f"Args: {args}")
            logger.debug(f"Kwargs: {kwargs}")
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log success
                mcp_logger.log_call(
                    func.__name__,
                    {"args": args, "kwargs": kwargs},
                    result,
                    duration
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                mcp_logger.log_error(e, {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs,
                    "duration": duration
                })
                
                # Log the call as failed
                mcp_logger.log_call(
                    func.__name__,
                    {"args": args, "kwargs": kwargs},
                    e,
                    duration
                )
                
                # Return error details instead of raising
                # This prevents the MCP server from crashing
                error_response = {
                    "error": str(e),
                    "type": type(e).__name__,
                    "tool": func.__name__,
                    "duration_ms": duration * 1000,
                    "traceback": traceback.format_exc()
                }
                
                return json.dumps(error_response, indent=2)
        
        return wrapper
    return decorator


def log_import_attempt(module_name: str, success: bool, error: Optional[Exception] = None):
    """Log import attempts for debugging import issues."""
    status = "✓" if success else "✗"
    if success:
        logger.info(f"{status} Import successful: {module_name}")
    else:
        logger.error(f"{status} Import failed: {module_name} - {error}")
        logger.debug(f"Python path: {sys.path}")
        logger.debug(f"Current dir: {os.getcwd()}")


# Example usage in MCP server:
if __name__ == "__main__":
    # Test the logger
    mcp_logger = MCPLogger("test-server")
    
    @debug_tool(mcp_logger)
    async def test_function(param: str) -> str:
        """Test function to demonstrate logging."""
        if param == "error":
            raise ValueError("Test error")
        return f"Success: {param}"
    
    # Test the function
    import asyncio
    
    async def main():
        # Test success
        result = await test_function("hello")
        print(f"Result: {result}")
        
        # Test error
        result = await test_function("error")
        print(f"Error result: {result}")
    
    asyncio.run(main())