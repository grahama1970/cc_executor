#!/usr/bin/env python3
"""Fix all sys.path manipulations in the project."""

import os
import re
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Load .env to get project root
env_path = find_dotenv()
load_dotenv(env_path)
PROJECT_ROOT = Path(env_path).parent if env_path else Path.cwd()

print(f"Project root: {PROJECT_ROOT}")
print(f"Will set PYTHONPATH={PROJECT_ROOT}/src")

# Find all Python files with sys.path manipulation
files_to_fix = []
for root, dirs, files in os.walk(PROJECT_ROOT / "src"):
    for file in files:
        if file.endswith(".py"):
            filepath = Path(root) / file
            with open(filepath, 'r') as f:
                content = f.read()
                if 'sys.path.insert' in content or 'sys.path.append' in content:
                    files_to_fix.append(filepath)

print(f"\nFound {len(files_to_fix)} files to fix")

# Patterns to remove
patterns = [
    # Remove sys.path manipulations and the imports that depend on them
    (r'sys\.path\.insert\(.*?\)\n', ''),
    (r'sys\.path\.append\(.*?\)\n', ''),
    # Common patterns that follow sys.path manipulation
    (r'# Add.*?to.*?path.*?\n', ''),
    (r'# Add MCP logger utility\n', ''),
]

fixes_made = 0

for filepath in files_to_fix:
    with open(filepath, 'r') as f:
        original = f.read()
    
    modified = original
    for pattern, replacement in patterns:
        modified = re.sub(pattern, replacement, modified)
    
    if modified != original:
        with open(filepath, 'w') as f:
            f.write(modified)
        fixes_made += 1
        print(f"✓ Fixed: {filepath.relative_to(PROJECT_ROOT)}")

print(f"\n✅ Fixed {fixes_made} files")

# Create a proper .env file with PYTHONPATH
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    if 'PYTHONPATH' not in env_content:
        with open(env_file, 'a') as f:
            f.write(f"\n# Python path for proper imports\nPYTHONPATH={PROJECT_ROOT}/src\n")
        print(f"✓ Added PYTHONPATH to .env")
else:
    with open(env_file, 'w') as f:
        f.write(f"# Python path for proper imports\nPYTHONPATH={PROJECT_ROOT}/src\n")
    print(f"✓ Created .env with PYTHONPATH")

print(f"\n🎯 Next steps:")
print(f"1. Review the changes")
print(f"2. Update MCP config to set PYTHONPATH env var")
print(f"3. Reload Claude to test")