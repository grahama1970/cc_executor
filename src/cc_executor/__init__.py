"""
CC Executor: Sequential task execution for Claude Code.

Two ways to use:
1. Python API: from cc_executor.client import cc_execute  
2. MCP Server: cc-executor start (for AI agents)

A secure service that enables orchestration of complex AI workflows 
with fresh context for each task.
"""

__version__ = "1.0.0"
__author__ = "Graham Anderson"
__email__ = "graham@grahama.co"

# Public API
__all__ = [
    "__version__",
    # Python API
    "cc_execute",
    "cc_execute_task_list", 
    "CCExecutorConfig",
    # MCP Server components
    "WebSocketHandler",
    "SessionManager", 
    "ProcessManager",
    "StreamHandler",
]

# Python API imports (for direct usage)
from .client import cc_execute, cc_execute_task_list, CCExecutorConfig

# MCP Server imports (for server mode)
from .core.websocket_handler import WebSocketHandler
from .core.session_manager import SessionManager
from .core.process_manager import ProcessManager
from .core.stream_handler import StreamHandler