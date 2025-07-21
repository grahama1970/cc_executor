#!/usr/bin/env python3
"""Fix all syntax errors in mcp_arango_tools.py"""

import re
from pathlib import Path

def fix_syntax_errors():
    """Fix all positional argument follows keyword argument errors"""
    
    file_path = Path("src/cc_executor/servers/mcp_arango_tools.py")
    content = file_path.read_text()
    
    # Pattern to find create_error_response calls with mixed args
    # Replace "key": value with key=value
    pattern = r'create_error_response\(error=([^,]+),\s*"(\w+)":\s*([^)]+)\)'
    replacement = r'create_error_response(error=\1, \2=\3)'
    
    content = re.sub(pattern, replacement, content)
    
    # Pattern for create_success_response 
    pattern2 = r'create_success_response\(data=([^,]+),\s*"(\w+)":\s*([^)]+)\)'
    replacement2 = r'create_success_response(data=\1, \2=\3)'
    
    content = re.sub(pattern2, replacement2, content)
    
    # Save the fixed content
    file_path.write_text(content)
    print("Fixed syntax errors in mcp_arango_tools.py")

if __name__ == "__main__":
    fix_syntax_errors()