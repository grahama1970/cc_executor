"""MCP Logger implementation."""

import asyncio
import json
import os
import re
import sys
import time
import traceback
import uuid
from datetime import datetime
from functools import wraps
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from loguru import logger as loguru_logger

# Regex to identify common data URI patterns for images, moved to module level
BASE64_IMAGE_PATTERN = re.compile(r"^(data:image/[a-zA-Z+.-]+;base64,)")


class MCPLogger:
    """
    Centralized logger for MCP servers with comprehensive, automated debugging features.
    - Each instance is isolated to prevent conflicts with global loguru settings.
    - Automatically truncates large strings, lists (embeddings), and base64 data.
    """

    def __init__(
        self,
        tool_name: str,
        log_level: Optional[str] = None,
        max_log_str_len: int = 256,
        max_log_list_len: int = 10,
    ):
        """
        Initializes the MCPLogger.

        Args:
            tool_name: The name of the tool or server.
            log_level: The console logging level (overrides environment variables).
            max_log_str_len: Max length for strings before truncation in logs.
            max_log_list_len: Max number of elements for lists before summarizing.
        """
        self.tool_name = tool_name
        self.logger = loguru_logger.bind(tool_name=tool_name)
        
        # Store truncation configuration
        self.max_log_str_len = max_log_str_len
        self.max_log_list_len = max_log_list_len

        # Allow overriding log directory via environment variable
        log_dir_str = os.getenv("MCP_LOG_DIR", str(Path.home() / ".claude" / "mcp_logs"))
        self.log_dir = Path(log_dir_str)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Determine log level from param, env var, or default
        level = log_level or os.getenv("MCP_LOG_LEVEL", "INFO")
        if os.getenv("MCP_DEBUG", "false").lower() in ("true", "1"):
            level = "DEBUG"

        # Use a fresh logger configuration for this instance
        self.logger.remove()
        self.logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[tool_name]}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
            )
        )

        self.debug_log = self.log_dir / f"{self.tool_name}_debug.log"
        self.logger.add(
            self.debug_log,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[tool_name]}:{name}:{function}:{line} - {message}"
        )

        self.log_startup_info()

    def _truncate_for_log(self, value: Any) -> Any:
        """
        Recursively truncate large strings, lists, or dicts to make them log-friendly.
        This is an internal method that uses the instance's configuration.
        """
        if isinstance(value, str):
            match = BASE64_IMAGE_PATTERN.match(value)
            if match:
                header = match.group(1)
                data = value[len(header):]
                if len(data) > self.max_log_str_len:
                    half_len = self.max_log_str_len // 2
                    truncated_data = f"{data[:half_len]}...[truncated]...{data[-half_len:]}"
                    return header + truncated_data
                return value
            elif len(value) > self.max_log_str_len:
                half_len = self.max_log_str_len // 2
                return f"{value[:half_len]}...[truncated]...{value[-half_len:]}"
            return value

        elif isinstance(value, list):
            if len(value) > self.max_log_list_len:
                element_type = type(value[0]).__name__ if value else "element"
                return f"[<{len(value)} {element_type}s>]"
            return [self._truncate_for_log(item) for item in value]

        elif isinstance(value, dict):
            return {k: self._truncate_for_log(v) for k, v in value.items()}

        return value

    def _safe_json_dumps(self, data: Any, **kwargs) -> str:
        """
        Safely dump data to a JSON string, automatically truncating large values and
        handling common non-serializable types.
        """
        # First, truncate the data to make it log-friendly
        truncated_data = self._truncate_for_log(data)

        def default_serializer(o: Any) -> Any:
            if isinstance(o, (datetime, Path)):
                return str(o)
            if hasattr(o, '__dict__'):
                return self._truncate_for_log(o.__dict__)
            try:
                return f"<<non-serializable: {type(o).__name__}>>"
            except Exception:
                return "<<non-serializable>>"

        return json.dumps(truncated_data, default=default_serializer, **kwargs)

    def log_startup_info(self):
        """Log startup information."""
        self.logger.info(f"Logger initialized for '{self.tool_name}'. PID: {os.getpid()}")
        self.logger.debug(f"Log directory: {self.log_dir}")

    def log_call(self, function: str, duration: float, result: Optional[Any] = None):
        """Log a successful tool call."""
        self.logger.info(f"✓ {function} completed in {duration:.3f}s")
        self.logger.debug(f"Result: {self._safe_json_dumps(result)}")

    def log_error(self, function: str, duration: float, error: Exception, context: Dict[str, Any]) -> str:
        """Log an error with context and return a unique error ID."""
        error_id = str(uuid.uuid4())
        self.logger.error(f"✗ {function} failed in {duration:.3f}s. Error ID: {error_id}")
        self.logger.error(f"{type(error).__name__}: {error}")
        self.logger.debug(f"Error Context: {self._safe_json_dumps(context, indent=2)}")
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
        return error_id


def debug_tool(mcp_logger: MCPLogger, catch_exceptions: bool = True) -> Callable:
    """
    Decorator for comprehensive tool debugging. Handles both sync and async functions.

    Args:
        mcp_logger: An instance of MCPLogger.
        catch_exceptions: If True, catches exceptions and returns a JSON error.
                          If False, re-raises the exception.
    """
    def decorator(func: Callable) -> Callable:
        is_async = iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            log_context = {"args": args, "kwargs": kwargs}
            mcp_logger.logger.debug(f"Calling tool '{func_name}' with context: {mcp_logger._safe_json_dumps(log_context)}")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                mcp_logger.log_call(func_name, duration, result)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_id = mcp_logger.log_error(func_name, duration, e, log_context)
                if catch_exceptions:
                    return mcp_logger._safe_json_dumps({
                        "error": {
                            "id": error_id,
                            "type": type(e).__name__,
                            "message": str(e),
                            "tool": func_name,
                            "traceback": traceback.format_exc()
                        }
                    }, indent=2)
                else:
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            log_context = {"args": args, "kwargs": kwargs}
            mcp_logger.logger.debug(f"Calling tool '{func_name}' with context: {mcp_logger._safe_json_dumps(log_context)}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                mcp_logger.log_call(func_name, duration, result)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_id = mcp_logger.log_error(func_name, duration, e, log_context)
                if catch_exceptions:
                    return mcp_logger._safe_json_dumps({
                        "error": {
                            "id": error_id,
                            "type": type(e).__name__,
                            "message": str(e),
                            "tool": func_name,
                            "traceback": traceback.format_exc()
                        }
                    }, indent=2)
                else:
                    raise

        return async_wrapper if is_async else sync_wrapper
    return decorator