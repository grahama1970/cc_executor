#!/usr/bin/env python3
"""Fix imports in MCP servers to use correct paths with PYTHONPATH."""

import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")

# MCP servers to fix
mcp_servers = [
    "src/cc_executor/servers/mcp_cc_execute.py",
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

# Import replacements
replacements = [
    # Fix utils imports
    (r'from utils\.mcp_logger import', 'from cc_executor.utils.mcp_logger import'),
    (r'from utils\.setup_arangodb_logging import', 'from cc_executor.utils.setup_arangodb_logging import'),
    
    # Fix other potential imports
    (r'from client\.cc_execute import', 'from cc_executor.client.cc_execute import'),
    (r'from services\.', 'from cc_executor.services.'),
    (r'from models\.', 'from cc_executor.models.'),
]

fixes_made = 0

for server in mcp_servers:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        print(f"❌ {server} - File not found")
        continue
    
    with open(server_path, 'r') as f:
        original = f.read()
    
    modified = original
    changes = False
    
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            changes = True
            modified = new_content
    
    if changes:
        with open(server_path, 'w') as f:
            f.write(modified)
        fixes_made += 1
        print(f"✅ Fixed imports in: {server}")
    else:
        print(f"ℹ️  No changes needed: {server}")

print(f"\n✅ Fixed {fixes_made} files")
print("\nNow testing imports again...")

# Re-run the import test
import subprocess
import sys

print("\n" + "=" * 60)
failures = []

for server in mcp_servers:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        continue
    
    env = {
        **subprocess.os.environ,
        "PYTHONPATH": str(PROJECT_ROOT / "src")
    }
    
    # Test import by running with test flag
    cmd = [sys.executable, str(server_path), "test"]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )
    
    if result.returncode == 0 and "ready to start" in result.stdout.lower():
        print(f"✅ {server} - Ready to start")
    else:
        print(f"❌ {server} - Still has issues")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()[:100]}...")
        failures.append(server)

print("\n" + "=" * 60)
print(f"Summary: {len(mcp_servers) - len(failures)}/{len(mcp_servers)} servers ready")