"""
CC-Executor: MCP WebSocket Service for remote command execution.

A secure WebSocket service that implements the Model Context Protocol (MCP)
for executing commands remotely with proper session management, process control,
and output streaming.
"""

__version__ = "1.0.0"
__author__ = "Graham Anderson"
__email__ = "graham@grahama.co"

# Public API
__all__ = [
    "__version__",
    "cc_execute_task_list",
    "WebSocketHandler",
    "SessionManager", 
    "ProcessManager",
    "StreamHandler",
    "WebSocketClient",
]

# Import main components for easier access
from .core.websocket_handler import WebSocketHandler
from .core.session_manager import SessionManager
from .core.process_manager import ProcessManager
from .core.stream_handler import StreamHandler
from .client.client import WebSocketClient
from .simple import cc_execute_task_list