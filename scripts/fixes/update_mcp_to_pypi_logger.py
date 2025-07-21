#!/usr/bin/env python3
"""Update all MCP servers to use mcp-logger-utils from PyPI instead of local path."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# MCP servers to update
mcp_servers = [
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_cc_execute.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

print("Updating MCP servers to use mcp-logger-utils from PyPI...")

old_dependency = '"mcp-logger-utils @ file:///home/graham/workspace/experiments/cc_executor/mcp-logger-utils"'
new_dependency = '"mcp-logger-utils>=0.1.5"'

updated_count = 0

for server_path in mcp_servers:
    filepath = PROJECT_ROOT / server_path
    if not filepath.exists():
        print(f"❌ {server_path} - Not found")
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    if old_dependency in content:
        # Replace the local path with PyPI version
        updated_content = content.replace(old_dependency, new_dependency)
        
        with open(filepath, 'w') as f:
            f.write(updated_content)
        
        updated_count += 1
        print(f"✅ Updated {server_path}")
    else:
        print(f"ℹ️  {server_path} - Already using PyPI version or no dependency")

print(f"\n✅ Updated {updated_count} files!")
print("\nAll MCP servers now use mcp-logger-utils from PyPI instead of local path.")
print("This makes the project more portable and professional.")