"""
Configuration module for CC Executor MCP WebSocket Service.

This module centralizes all configuration constants and environment variable
loading for the service. All configuration values are defined here to make
them easy to modify and test.

Third-party Documentation:
- FastAPI Configuration: https://fastapi.tiangolo.com/advanced/settings/
- Pydantic Settings: https://docs.pydantic.dev/latest/usage/settings/
- JSON-RPC 2.0 Spec: https://www.jsonrpc.org/specification
- WebSocket Protocol: https://datatracker.ietf.org/doc/html/rfc6455
- Loguru Configuration: https://loguru.readthedocs.io/en/stable/api/logger.html

Example Input:
    Environment variables:
    - ALLOWED_COMMANDS="echo,ls,cat"
    - LOG_LEVEL="DEBUG"
    - DEBUG="true"

Expected Output:
    Configuration loaded with:
    - ALLOWED_COMMANDS = ["echo", "ls", "cat"]
    - LOG_LEVEL = "DEBUG"
    - DEBUG_MODE = True
"""

import os
from typing import Optional, List

# Service configuration
SERVICE_NAME = "cc_executor_mcp"
SERVICE_VERSION = "1.0.0"

# WebSocket configuration
WS_PATH = "/ws/mcp"
DEFAULT_PORT = int(os.getenv("DEFAULT_PORT", "8003"))

# Session management
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "100"))  # Maximum concurrent WebSocket sessions
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # Session timeout in seconds (default 1 hour)

# Process execution
MAX_BUFFER_SIZE = int(os.getenv("MAX_BUFFER_SIZE", "8388608"))  # Maximum line size for stdout/stderr (8MB for large Claude JSON events)
STREAM_TIMEOUT = int(os.getenv("STREAM_TIMEOUT", "600"))  # Stream read timeout in seconds (default 10 minutes)
PROCESS_CLEANUP_TIMEOUT = int(os.getenv("PROCESS_CLEANUP_TIMEOUT", "10"))  # Timeout for process cleanup operations

# Security configuration
ALLOWED_COMMANDS: Optional[List[str]] = None
if os.getenv("ALLOWED_COMMANDS"):
    ALLOWED_COMMANDS = [cmd.strip() for cmd in os.getenv("ALLOWED_COMMANDS").split(",")]

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Health check configuration
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # Seconds between health checks

# JSON-RPC configuration
JSONRPC_VERSION = "2.0"

# Error codes (JSON-RPC 2.0 standard)
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL_ERROR = -32603
ERROR_SERVER_ERROR = -32000

# Custom error codes
ERROR_SESSION_LIMIT = -32001
ERROR_COMMAND_NOT_ALLOWED = -32002
ERROR_PROCESS_NOT_FOUND = -32003
ERROR_STREAM_TIMEOUT = -32004

# Development/Testing
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"


if __name__ == "__main__":
    """Usage example demonstrating configuration loading and validation."""
    
    print("=== CC Executor Configuration ===")
    print(f"Service: {SERVICE_NAME} v{SERVICE_VERSION}")
    print(f"Default Port: {DEFAULT_PORT}")
    print(f"WebSocket Path: {WS_PATH}")
    print()
    
    print("=== Session Configuration ===")
    print(f"Max Sessions: {MAX_SESSIONS}")
    print(f"Session Timeout: {SESSION_TIMEOUT}s")
    print()
    
    print("=== Process Configuration ===")
    print(f"Max Buffer Size: {MAX_BUFFER_SIZE} bytes")
    print(f"Stream Timeout: {STREAM_TIMEOUT}s")
    print(f"Cleanup Timeout: {PROCESS_CLEANUP_TIMEOUT}s")
    print()
    
    print("=== Security Configuration ===")
    if ALLOWED_COMMANDS:
        print(f"Allowed Commands: {', '.join(ALLOWED_COMMANDS)}")
    else:
        print("Allowed Commands: ALL (no restrictions)")
    print()
    
    print("=== Logging Configuration ===")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print()
    
    # Test environment variable parsing
    print("=== Testing Environment Variable Parsing ===")
    
    # Simulate environment variables
    test_commands = "echo,ls,cat,grep"
    parsed_commands = [cmd.strip() for cmd in test_commands.split(",")]
    print(f"Input: ALLOWED_COMMANDS='{test_commands}'")
    print(f"Parsed: {parsed_commands}")
    
    # Test log level parsing
    test_level = "WARNING"
    print(f"Input: LOG_LEVEL='{test_level}'")
    print(f"Parsed: {test_level}")
    
    # Test boolean parsing
    test_debug = "true"
    parsed_debug = test_debug.lower() == "true"
    print(f"Input: DEBUG='{test_debug}'")
    print(f"Parsed: {parsed_debug}")
    
    # Verify error codes are unique
    error_codes = {
        ERROR_PARSE_ERROR, ERROR_INVALID_REQUEST, ERROR_METHOD_NOT_FOUND,
        ERROR_INVALID_PARAMS, ERROR_INTERNAL_ERROR, ERROR_SERVER_ERROR,
        ERROR_SESSION_LIMIT, ERROR_COMMAND_NOT_ALLOWED, ERROR_PROCESS_NOT_FOUND,
        ERROR_STREAM_TIMEOUT
    }
    assert len(error_codes) == 10, "Error codes must be unique"
    
    print("\n✅ Configuration validation passed!")