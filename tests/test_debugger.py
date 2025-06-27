#!/usr/bin/env python3
"""Test debugger functionality"""

import sys
import os

def test_function():
    x = 10
    y = 20
    result = x + y  # Set a breakpoint here
    return result

if __name__ == "__main__":
    print(f"Python: {sys.executable}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Test import
    try:
        from cc_executor import __version__
        print(f"cc_executor imported successfully, version: {__version__}")
    except ImportError as e:
        print(f"Import error: {e}")
    
    # Call function
    result = test_function()
    print(f"Result: {result}")