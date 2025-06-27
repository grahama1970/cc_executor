#!/usr/bin/env python3
"""Test script for VS Code debugging"""

import sys
import os

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"Script location: {__file__}")

# Test import from cc_executor
try:
    from cc_executor import __version__
    print(f"cc_executor version: {__version__}")
except ImportError as e:
    print(f"Failed to import cc_executor: {e}")

print("\nAll checks completed!")