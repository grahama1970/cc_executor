#!/usr/bin/env python3
"""Update all MCP servers to use mcp-logger-utils from PyPI."""

import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")

# MCP servers to update
mcp_servers = [
    "src/cc_executor/servers/mcp_cc_execute.py",
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

# Patterns to replace
import_patterns = [
    (r'from cc_executor\.utils\.mcp_logger import MCPLogger, debug_tool', 
     'from mcp_logger_utils import MCPLogger, debug_tool'),
    (r'from cc_executor\.utils\.mcp_logger import MCPLogger',
     'from mcp_logger_utils import MCPLogger, debug_tool'),
    (r'import cc_executor\.utils\.mcp_logger as mcp_logger',
     'from mcp_logger_utils import MCPLogger, debug_tool'),
]

# Also need to remove the old SimpleMCPLogger class from mcp_arango_tools_fixed.py
simple_logger_pattern = r'class SimpleMCPLogger:.*?(?=\n(?:class|def|@|from|import|\Z))'

updates_made = 0

for server in mcp_servers:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        print(f"❌ {server} - File not found")
        continue
    
    with open(server_path, 'r') as f:
        content = f.read()
    
    # Replace all import patterns
    new_content = content
    for old_pattern, new_pattern in import_patterns:
        new_content = re.sub(old_pattern, new_pattern, new_content)
    
    # Remove SimpleMCPLogger class if present
    new_content = re.sub(simple_logger_pattern, '', new_content, flags=re.DOTALL)
    
    if new_content != content:
        with open(server_path, 'w') as f:
            f.write(new_content)
        updates_made += 1
        print(f"✅ Updated: {server}")
    else:
        print(f"ℹ️  No changes needed: {server}")

# Also update pyproject.toml to include mcp-logger-utils dependency
pyproject_path = PROJECT_ROOT / "pyproject.toml"
if pyproject_path.exists():
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Add mcp-logger-utils to dependencies if not already there
    if 'mcp-logger-utils' not in content:
        # Find the dependencies section
        pattern = r'(dependencies = \[)'
        replacement = r'\1\n    "mcp-logger-utils>=0.2.0",'
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(pyproject_path, 'w') as f:
                f.write(new_content)
            print(f"✅ Updated pyproject.toml with mcp-logger-utils dependency")

print(f"\n✅ Updated {updates_made} files")
print("\nNext steps:")
print("1. Run: uv sync")
print("2. Reload Claude to test the MCP servers")
print("3. Verify they work with the PyPI package")