#!/usr/bin/env python3
"""
Task List Environment Setup Template

This template is customized by each task list to set up its execution environment.
It follows the patterns from PYTHON_SCRIPT_TEMPLATE.md for dynamic paths.

Placeholders to be replaced:
- TODO API Example: Human-readable name
- PLACEHOLDER_RELATIVE_PATH: Path relative to where this runs
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Dynamic path detection (no hardcoding)
CURRENT_FILE = Path(__file__)
TASK_LIST_NAME = "TODO API Example"

# Find project root by looking for markers
def find_project_root():
    """Find project root by looking for pyproject.toml or .git."""
    current = CURRENT_FILE.parent
    while current.parent != current:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    # Fallback to current directory
    return Path.cwd()

# Set up paths dynamically
PROJECT_ROOT = find_project_root()
TASK_LIST_DIR = CURRENT_FILE.parent  # Directory where this setup script is saved

def setup_environment():
    """Set up the execution environment following cc_executor patterns."""
    
    # Ensure we're in project root for consistent execution
    os.chdir(PROJECT_ROOT)
    
    # Set PYTHONPATH
    os.environ['PYTHONPATH'] = str(PROJECT_ROOT / 'src')
    if str(PROJECT_ROOT / 'src') not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT / 'src'))
    
    # Create directory structure (relative to where setup script is)
    directories = {
        "tmp": TASK_LIST_DIR / "tmp",
        "responses": TASK_LIST_DIR / "tmp" / "responses",
        "scripts": TASK_LIST_DIR / "tmp" / "scripts",
        "reports": TASK_LIST_DIR / "reports"
    }
    
    for name, path in directories.items():
        path.mkdir(parents=True, exist_ok=True)
    
    # Log setup completion
    print(f"✓ Environment setup complete for {TASK_LIST_NAME}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Working directory: {os.getcwd()}")
    print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"  Task list directory: {TASK_LIST_DIR}")
    print(f"\n📁 Created directories:")
    for name, path in directories.items():
        print(f"   {name}: {path.relative_to(PROJECT_ROOT)}")
    
    # Save setup info for verification
    setup_info = {
        "timestamp": datetime.now().isoformat(),
        "task_list_name": TASK_LIST_NAME,
        "project_root": str(PROJECT_ROOT),
        "task_list_dir": str(TASK_LIST_DIR),
        "python_path": os.environ.get('PYTHONPATH'),
        "directories": {name: str(path) for name, path in directories.items()}
    }
    
    # Save to responses directory
    import json
    setup_log = directories["responses"] / f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(setup_log, 'w') as f:
        json.dump(setup_info, f, indent=2)
    
    return directories

if __name__ == "__main__":
    """Run setup when executed directly."""
    
    # Check virtual environment
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  WARNING: Virtual environment not activated!")
        print("   Run: source .venv/bin/activate")
        print("   Continuing anyway...\n")
    
    # Run setup
    try:
        directories = setup_environment()
        print(f"\n✅ Setup completed successfully!")
        print(f"💾 Setup log saved to: {directories['responses']}")
        exit(0)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)