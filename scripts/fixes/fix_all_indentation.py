#!/usr/bin/env python3
"""Fix all indentation issues caused by sys.path removal."""

import os
import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")

def fix_file_indentation(filepath):
    """Fix indentation issues in a single file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for misaligned import sys
        if re.match(r'^\s+import sys\s*$', line) and i > 0:
            # Get indentation from previous line
            prev_line = lines[i-1]
            prev_indent = len(prev_line) - len(prev_line.lstrip())
            
            # If previous line ends with : or try:, increase indent by 4
            if prev_line.rstrip().endswith(':'):
                proper_indent = prev_indent + 4
            else:
                proper_indent = prev_indent
            
            # Fix the import sys line
            fixed_lines.append(' ' * proper_indent + 'import sys\n')
            i += 1
            
            # Check if next line is the problematic if statement
            if i < len(lines) and 'if str(Path(__file__)' in lines[i]:
                # Skip the if statement line
                i += 1
                
                # Check if next line is the problematic import
                if i < len(lines) and 'from cc_executor.' in lines[i]:
                    # Fix the import line with proper indentation
                    import_line = lines[i].strip()
                    fixed_lines.append(' ' * proper_indent + import_line + '\n')
                    i += 1
            continue
        
        # Check for standalone if str(Path(__file__)) lines that should be removed
        if 'if str(Path(__file__).parent' in line and 'sys.path' in line:
            # Skip this line entirely
            i += 1
            continue
            
        fixed_lines.append(line)
        i += 1
    
    return ''.join(fixed_lines)

# Fix cc_execute.py specifically
cc_execute_path = PROJECT_ROOT / "src/cc_executor/client/cc_execute.py"
if cc_execute_path.exists():
    print(f"\nFixing {cc_execute_path}...")
    fixed_content = fix_file_indentation(cc_execute_path)
    
    with open(cc_execute_path, 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed cc_execute.py")

# Now scan for any other files with similar issues
print("\nScanning for other files with indentation issues...")

for root, dirs, files in os.walk(PROJECT_ROOT / "src"):
    # Skip __pycache__ directories
    if '__pycache__' in root:
        continue
        
    for file in files:
        if file.endswith('.py'):
            filepath = Path(root) / file
            
            # Quick check if file has problematic patterns
            with open(filepath, 'r') as f:
                content = f.read()
            
            if 'if str(Path(__file__).parent' in content and 'sys.path' in content:
                print(f"Fixing: {filepath.relative_to(PROJECT_ROOT)}")
                fixed_content = fix_file_indentation(filepath)
                
                with open(filepath, 'w') as f:
                    f.write(fixed_content)

print("\n✅ Indentation fixes complete!")

# Now test the imports again
print("\nTesting MCP server imports...")
import subprocess
import sys

mcp_servers = [
    "src/cc_executor/servers/mcp_cc_execute.py",
    "src/cc_executor/servers/mcp_arango_tools.py",
    "src/cc_executor/servers/mcp_d3_visualizer.py",
    "src/cc_executor/servers/mcp_logger_tools.py",
    "src/cc_executor/servers/mcp_tool_journey.py",
    "src/cc_executor/servers/mcp_tool_sequence_optimizer.py",
    "src/cc_executor/servers/mcp_kilocode_review.py"
]

env = {
    **subprocess.os.environ,
    "PYTHONPATH": str(PROJECT_ROOT / "src")
}

success_count = 0
for server in mcp_servers:
    server_path = PROJECT_ROOT / server
    if not server_path.exists():
        continue
    
    cmd = [sys.executable, str(server_path), "test"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=5)
    
    if result.returncode == 0 and "ready" in result.stdout.lower():
        print(f"✅ {server}")
        success_count += 1
    else:
        print(f"❌ {server}")
        if result.stderr:
            # Show just the error type
            for line in result.stderr.split('\n'):
                if 'Error' in line:
                    print(f"   {line.strip()}")
                    break

print(f"\n{success_count}/{len(mcp_servers)} servers ready")