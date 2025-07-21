#!/usr/bin/env python3
"""Fix ALL remaining sys.path and import issues comprehensively."""

import os
import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")
print(f"PYTHONPATH should be: {PROJECT_ROOT}/src")

def fix_indentation_comprehensive(content):
    """Fix all indentation issues in a file."""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Pattern 1: Misaligned import statements after sys.path removal
        if re.match(r'^\s+from cc_executor\.|^\s+import ', line):
            # Check if previous line suggests this should be less indented
            if i > 0:
                prev_line = lines[i-1]
                # If previous line is a comment or project_root assignment, reduce indent
                if 'project_root' in prev_line.lower() or prev_line.strip().startswith('#'):
                    # Find the base indentation level
                    j = i - 1
                    while j >= 0 and (lines[j].strip() == '' or lines[j].strip().startswith('#')):
                        j -= 1
                    if j >= 0:
                        base_indent = len(lines[j]) - len(lines[j].lstrip())
                        # If in a function/class, add 4 spaces
                        if lines[j].rstrip().endswith(':'):
                            base_indent += 4
                        fixed_line = ' ' * base_indent + line.strip()
                        fixed_lines.append(fixed_line)
                        i += 1
                        continue
        
        # Pattern 2: Remove orphaned sys.path checks
        if 'if str(Path(__file__).parent' in line and 'sys.path' in line:
            # Skip this line
            i += 1
            continue
            
        # Pattern 3: Fix misaligned 'import sys' statements
        if line.strip() == 'import sys' and i > 0:
            prev_line = lines[i-1] if i > 0 else ''
            if prev_line.rstrip().endswith(':'):
                # Should be indented after a colon
                indent = len(prev_line) - len(prev_line.lstrip()) + 4
                fixed_lines.append(' ' * indent + 'import sys')
                i += 1
                continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def fix_imports_comprehensive(content):
    """Fix all import issues."""
    # Replace relative imports with absolute imports
    replacements = [
        # Hook imports
        (r'from setup_environment import', 'from cc_executor.hooks.setup_environment import'),
        (r'from claude_instance_pre_check import', 'from cc_executor.hooks.claude_instance_pre_check import'),
        
        # Utils imports
        (r'from utils\.', 'from cc_executor.utils.'),
        (r'import utils\.', 'import cc_executor.utils.'),
        
        # Core imports
        (r'from core\.', 'from cc_executor.core.'),
        (r'import core\.', 'import cc_executor.core.'),
        
        # Services imports
        (r'from services\.', 'from cc_executor.services.'),
        (r'import services\.', 'import cc_executor.services.'),
        
        # Client imports
        (r'from client\.', 'from cc_executor.client.'),
        (r'import client\.', 'import cc_executor.client.'),
        
        # Models imports
        (r'from models\.', 'from cc_executor.models.'),
        (r'import models\.', 'import cc_executor.models.'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    return content

# Process all Python files
print("\nProcessing all Python files...")
files_processed = 0
files_with_issues = []

for root, dirs, files in os.walk(PROJECT_ROOT / "src"):
    # Skip __pycache__
    if '__pycache__' in root:
        continue
        
    for file in files:
        if file.endswith('.py'):
            filepath = Path(root) / file
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    original = f.read()
                
                # Apply fixes
                fixed = original
                fixed = fix_imports_comprehensive(fixed)
                fixed = fix_indentation_comprehensive(fixed)
                
                if fixed != original:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(fixed)
                    files_processed += 1
                    print(f"✅ Fixed: {filepath.relative_to(PROJECT_ROOT)}")
                    
            except Exception as e:
                files_with_issues.append((filepath, str(e)))
                print(f"❌ Error processing {filepath.relative_to(PROJECT_ROOT)}: {e}")

print(f"\n✅ Processed {files_processed} files")

if files_with_issues:
    print(f"\n⚠️  {len(files_with_issues)} files had issues:")
    for filepath, error in files_with_issues[:5]:  # Show first 5
        print(f"  - {filepath.relative_to(PROJECT_ROOT)}: {error}")

# Test MCP servers
print("\n" + "="*60)
print("Testing MCP servers...")

import subprocess
import sys

mcp_servers = [
    "mcp_cc_execute.py",
    "mcp_arango_tools.py", 
    "mcp_d3_visualizer.py",
    "mcp_logger_tools.py",
    "mcp_tool_journey.py",
    "mcp_tool_sequence_optimizer.py",
    "mcp_kilocode_review.py"
]

env = {
    **os.environ,
    "PYTHONPATH": str(PROJECT_ROOT / "src")
}

working_servers = []
failed_servers = []

for server in mcp_servers:
    server_path = PROJECT_ROOT / "src" / "cc_executor" / "servers" / server
    if not server_path.exists():
        print(f"⚠️  {server} - Not found")
        continue
    
    cmd = [sys.executable, str(server_path), "test"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=5)
    
    if result.returncode == 0:
        if "ready" in result.stdout.lower() or "test" in result.stdout.lower():
            print(f"✅ {server} - Working")
            working_servers.append(server)
        else:
            print(f"⚠️  {server} - Runs but unclear status")
            failed_servers.append((server, "No clear ready status"))
    else:
        print(f"❌ {server} - Failed")
        # Extract key error
        error_msg = "Unknown error"
        for line in result.stderr.split('\n'):
            if 'Error:' in line or 'error' in line.lower():
                error_msg = line.strip()
                break
        failed_servers.append((server, error_msg))

print(f"\n" + "="*60)
print(f"Summary: {len(working_servers)}/{len(mcp_servers)} servers working")

if failed_servers:
    print("\nFailed servers:")
    for server, error in failed_servers:
        print(f"  - {server}: {error}")

print("\n✅ Fix script complete!")
print("\nNext steps:")
print("1. Reload Claude to pick up the MCP config changes")
print("2. Test that MCP tools are available")
print("3. Run: mcp__arango-tools__schema() to verify")