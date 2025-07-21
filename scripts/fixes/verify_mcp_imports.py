#!/usr/bin/env python3
"""Verify all MCP servers can import their dependencies after sys.path removal."""

import subprocess
import sys
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")
print(f"PYTHONPATH should be: {PROJECT_ROOT}/src")

# MCP servers to test
mcp_servers = [
    "src/cc_executor/servers/poc_mcp.py",
    "src/cc_executor/servers/mcp_cc_execute.py",
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

print("\nTesting MCP server imports...")
print("=" * 60)

failures = []

for server in mcp_servers:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        print(f"❌ {server} - File not found")
        continue
    
    # Test with proper PYTHONPATH
    env = {
        **subprocess.os.environ,
        "PYTHONPATH": str(PROJECT_ROOT / "src")
    }
    
    # Quick import test - just check if it can load without running
    cmd = [sys.executable, "-c", f"import sys; sys.path.insert(0, '{PROJECT_ROOT}/src'); exec(open('{server_path}').read().split('if __name__')[0])"]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    
    if result.returncode == 0:
        print(f"✅ {server} - Imports OK")
    else:
        print(f"❌ {server} - Import failed")
        print(f"   Error: {result.stderr.strip()}")
        failures.append((server, result.stderr))

print("\n" + "=" * 60)
print(f"Summary: {len(mcp_servers) - len(failures)}/{len(mcp_servers)} servers passed")

if failures:
    print("\nFailed servers:")
    for server, error in failures:
        print(f"\n{server}:")
        # Show just the relevant error line
        for line in error.split('\n'):
            if 'Error' in line or 'import' in line:
                print(f"  {line.strip()}")

# Now update the MCP config to use the original arango-tools
print("\n\nUpdating MCP config to use original mcp_arango_tools.py...")
config_path = Path.home() / ".claude" / "claude_code" / ".mcp.json"

if config_path.exists():
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace the fixed version with original
    updated = content.replace(
        '"src/cc_executor/servers/mcp_arango_tools_fixed.py"',
        '"src/cc_executor/servers/mcp_arango_tools.py"'
    )
    
    if updated != content:
        with open(config_path, 'w') as f:
            f.write(updated)
        print("✅ Updated MCP config to use original mcp_arango_tools.py")
    else:
        print("ℹ️  MCP config already using original or not found")