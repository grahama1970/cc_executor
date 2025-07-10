"""Constants for CC Executor core functionality."""

# Completion markers for detecting when Claude has finished
COMPLETION_MARKERS = [
    "Task completed successfully",
    "I've completed",
    "I have completed",
    "The task is complete",
    "Process complete",
    "Done!",
    "Finished!",
    "Operation complete",
    "All done"
]

# Pattern for detecting file creation
FILE_CREATION_PATTERN = r'(?:Created?|Wrote|Generated?|Saved?)\s+(?:file|script|program):\s*([^\s]+(?:\.[a-zA-Z]+)?)'

# Patterns for detecting token limit issues
TOKEN_LIMIT_PATTERNS = [
    r"token.*limit",
    r"context.*window",
    r"maximum.*length",
    r"too.*long",
    r"truncated"
]

# JSON-RPC error codes
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL_ERROR = -32603

# Custom error codes
ERROR_COMMAND_NOT_ALLOWED = -32001
ERROR_PROCESS_NOT_FOUND = -32002
ERROR_SESSION_LIMIT = -32003
ERROR_TOKEN_LIMIT = -32004

# Session limits
MAX_SESSIONS = 100

# Logging configuration
LOG_ROTATION_SIZE = 10 * 1024 * 1024  # 10MB
LOG_RETENTION_COUNT = 5