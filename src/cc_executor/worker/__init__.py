"""
Secure worker module for CC Executor.

This module provides isolated code execution in a restricted container environment.
"""

from .main import SecureWorker

__all__ = ["SecureWorker"]