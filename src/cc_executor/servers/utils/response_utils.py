#!/usr/bin/env python3
"""
Standardized response utilities for MCP servers.

This module provides a consistent response format for all MCP tools:
{
    "success": bool,
    "data": {...},
    "error": str | null,
    "metadata": {
        "duration_ms": int,
        "tool": str,
        "version": str
    }
}
"""

import json
import time
from typing import Any, Dict, Optional
from datetime import datetime


MCP_VERSION = "2025-07-19"


def create_response(
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    tool_name: Optional[str] = None,
    start_time: Optional[float] = None
) -> str:
    """
    Create a standardized MCP response.
    
    Args:
        success: Whether the operation succeeded
        data: The response payload (only used if success=True)
        error: Error message (only used if success=False)
        tool_name: Name of the tool for metadata
        start_time: Start time for duration calculation (from time.time())
    
    Returns:
        JSON string with standardized response format
    """
    # Calculate duration if start_time provided
    duration_ms = None
    if start_time is not None:
        duration_ms = int((time.time() - start_time) * 1000)
    
    response = {
        "success": success,
        "data": data if success else None,
        "error": error if not success else None,
        "metadata": {
            "duration_ms": duration_ms,
            "tool": tool_name,
            "version": MCP_VERSION,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    return json.dumps(response, indent=2)


def create_success_response(
    data: Dict[str, Any],
    tool_name: Optional[str] = None,
    start_time: Optional[float] = None
) -> str:
    """Create a successful response."""
    return create_response(
        success=True,
        data=data,
        tool_name=tool_name,
        start_time=start_time
    )


def create_error_response(
    error: str,
    tool_name: Optional[str] = None,
    start_time: Optional[float] = None
) -> str:
    """Create an error response."""
    return create_response(
        success=False,
        error=error,
        tool_name=tool_name,
        start_time=start_time
    )


# For backward compatibility, some tools may need to parse the new format
def parse_response(response_str: str) -> Dict[str, Any]:
    """
    Parse a standardized response string.
    
    Returns:
        Dict with 'success', 'data', 'error', and 'metadata' keys
    """
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        # Handle non-standard responses
        return {
            "success": False,
            "data": None,
            "error": f"Invalid JSON response: {response_str[:100]}",
            "metadata": {
                "tool": "unknown",
                "version": MCP_VERSION
            }
        }