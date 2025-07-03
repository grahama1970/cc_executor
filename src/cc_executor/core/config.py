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

# Shell configuration
PREFERRED_SHELL = os.environ.get('CC_EXECUTOR_SHELL', 'zsh')  # 'zsh', 'bash', or 'default'
SHELL_PATHS = {
    'zsh': ['/bin/zsh', '/usr/bin/zsh', '/usr/local/bin/zsh'],
    'bash': ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash']
}

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
    import json
    from pathlib import Path
    from datetime import datetime
    import io
    import sys
    
    # Create tmp/responses directory for saving output
    responses_dir = Path(__file__).parent / "tmp" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    
    # Capture all output
    output_buffer = io.StringIO()
    
    # Create a custom print that writes to both stdout and buffer
    def print_and_capture(*args, **kwargs):
        # Print to stdout as normal
        print(*args, **kwargs)
        # Also print to buffer
        print(*args, **kwargs, file=output_buffer)
    
    # Replace print for this block
    _print = print
    print = print_and_capture
    
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
    
    # Restore original print
    print = _print
    
    # Save raw response as prettified JSON to prevent hallucination
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = Path(__file__).stem  # "config"
    
    # Get captured output
    output_content = output_buffer.getvalue()
    
    # Save as prettified JSON for easy verification
    response_file = responses_dir / f"{filename}_{timestamp}.json"
    with open(response_file, 'w') as f:
        json.dump({
            'filename': filename,
            'timestamp': timestamp,
            'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'module': 'cc_executor.core.config',
            'output': output_content,
            'line_count': len(output_content.strip().split('\n')),
            'success': '✅' in output_content
        }, f, indent=4)
    
    print(f"\n💾 Raw response saved to: {response_file.relative_to(Path.cwd())}")