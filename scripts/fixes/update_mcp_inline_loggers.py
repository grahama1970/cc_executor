#!/usr/bin/env python3
"""Update MCP servers that have inline MCPLogger to use PyPI package."""

import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")

# Servers with inline MCPLogger
servers_with_inline = [
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py", 
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py"
]

updates_made = 0

for server in servers_with_inline:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        print(f"❌ {server} - File not found")
        continue
    
    with open(server_path, 'r') as f:
        content = f.read()
    
    # Pattern to match inline MCPLogger class definition
    inline_logger_pattern = r'class MCPLogger:.*?(?=\n(?:class|def|@|from|import|mcp_logger|if __name__|\Z))'
    
    # Pattern to match inline debug_tool decorator
    inline_debug_pattern = r'def debug_tool\(mcp_logger: MCPLogger\):.*?(?=\n(?:class|def|@|from|import|mcp_logger|if __name__|\Z))'
    
    # Remove inline implementations
    new_content = re.sub(inline_logger_pattern, '', content, flags=re.DOTALL)
    new_content = re.sub(inline_debug_pattern, '', new_content, flags=re.DOTALL)
    
    # Add PyPI import at the top (after other imports)
    if 'from mcp_logger_utils import' not in new_content:
        # Find a good place to insert the import
        import_lines = []
        for line in new_content.split('\n'):
            if line.startswith('from ') or line.startswith('import '):
                import_lines.append(line)
        
        if import_lines:
            last_import = import_lines[-1]
            new_content = new_content.replace(
                last_import,
                last_import + '\nfrom mcp_logger_utils import MCPLogger, debug_tool'
            )
        else:
            # No imports found, add after docstring
            lines = new_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('"""') and not line.startswith('#'):
                    lines.insert(i, 'from mcp_logger_utils import MCPLogger, debug_tool\n')
                    break
            new_content = '\n'.join(lines)
    
    # Clean up extra blank lines
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    
    if new_content != content:
        with open(server_path, 'w') as f:
            f.write(new_content)
        updates_made += 1
        print(f"✅ Updated: {server}")
    else:
        print(f"ℹ️  No changes needed: {server}")

# Also delete the temporary/debug versions
temp_files = [
    "src/cc_executor/servers/mcp_arango_tools_fixed.py",
    "src/cc_executor/servers/mcp_arango_tools_portable.py",
    "src/cc_executor/servers/mcp_arango_tools_debug.py",
    "src/cc_executor/servers/enhanced_mcp_startup.py",
    "src/cc_executor/servers/mcp_startup_wrapper.py"
]

print("\nCleaning up temporary files...")
for temp_file in temp_files:
    temp_path = PROJECT_ROOT / temp_file
    if temp_path.exists():
        temp_path.unlink()
        print(f"🗑️  Deleted: {temp_file}")

print(f"\n✅ Updated {updates_made} files")
print("\nNow running uv sync to ensure mcp-logger-utils is installed...")

import subprocess
subprocess.run(["uv", "sync"], cwd=PROJECT_ROOT)

print("\n✅ Complete! All MCP servers now use mcp-logger-utils from PyPI")
print("\nNext step: Reload Claude to test the MCP servers")