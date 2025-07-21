#!/usr/bin/env python3
"""Fix MCP server shebangs to use uv run --script since they have inline dependencies."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# MCP servers to fix
mcp_servers = [
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

print("Fixing MCP server shebangs to use uv run --script...")

for server_path in mcp_servers:
    filepath = PROJECT_ROOT / server_path
    if not filepath.exists():
        print(f"❌ {server_path} - Not found")
        continue
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Check if it has the script section and wrong shebang
    has_script_section = any('# /// script' in line for line in lines[:20])
    
    if has_script_section and lines[0].strip() == '#!/usr/bin/env python3':
        # Fix the shebang to use uv run --script
        lines[0] = '#!/usr/bin/env -S uv run --script\n'
        
        with open(filepath, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Fixed shebang in {server_path}")
    else:
        print(f"ℹ️  {server_path} - Shebang already correct or no script section")

print("\n✅ Shebangs fixed!")
print("\nMCP servers with inline dependencies now use 'uv run --script' shebang.")