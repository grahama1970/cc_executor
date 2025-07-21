#!/usr/bin/env python3
"""Update all MCP server shebangs to standard Python."""

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

print("Updating MCP server shebangs...")

for server_path in mcp_servers:
    filepath = PROJECT_ROOT / server_path
    if not filepath.exists():
        print(f"❌ {server_path} - Not found")
        continue
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Check if first line is the old shebang
    if lines[0].strip() == '#!/usr/bin/env -S uv run --script':
        # Replace with standard Python shebang
        lines[0] = '#!/usr/bin/env python3\n'
        
        with open(filepath, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Updated shebang in {server_path}")
    else:
        print(f"ℹ️  {server_path} - Shebang already correct or different")

print("\n✅ All shebangs updated!")
print("\nThe MCP servers now use standard Python shebangs.")
print("They'll be run with 'uv run python' as configured in .mcp.json")