#!/usr/bin/env python3
"""
Setup script for TODO API task list.
Finds and customizes the setup template from the project root.
"""

from pathlib import Path

# Find project root by looking for pyproject.toml
def find_project_root():
    """Find project root by looking for pyproject.toml or .git."""
    current = Path.cwd()
    while current.parent != current:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()

# Find and read the setup template
project_root = find_project_root()
template_path = project_root / 'src/cc_executor/prompts/setup_template.py'

if not template_path.exists():
    print(f"❌ Setup template not found at: {template_path}")
    print(f"   Project root detected as: {project_root}")
    exit(1)

print(f"✓ Found setup template at: {template_path}")

with open(template_path, 'r') as f:
    setup_code = f.read()

# Customize for this task list
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_NAME', 'TODO API Example')

# Write to current directory (will find project root dynamically)
with open('setup_env.py', 'w') as f:
    f.write(setup_code)

print("✓ Created customized setup_env.py")

# Run the setup
exec(open('setup_env.py').read())