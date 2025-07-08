"""
CC Executor - Simple async interface for complex Claude tasks.

Usage:
    from cc_executor import cc_execute
    
    result = await cc_execute("Create a full FastAPI application with auth")
"""

from .executor import cc_execute, cc_execute_list, CCExecutorConfig

__all__ = ["cc_execute", "cc_execute_list", "CCExecutorConfig"]
__version__ = "0.1.0"