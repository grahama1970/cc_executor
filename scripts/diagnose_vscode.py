#!/usr/bin/env python3
"""Diagnose VS Code Python interpreter issues."""

import json
import os
import subprocess
import sys
from pathlib import Path

def main():
    """Run diagnostics for VS Code Python setup."""
    print("=== VS Code Python Diagnostics ===\n")
    
    # Current Python info
    print(f"1. Current Python Information:")
    print(f"   Executable: {sys.executable}")
    print(f"   Version: {sys.version}")
    print(f"   Prefix: {sys.prefix}")
    print(f"   Virtual env: {hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)}")
    print()
    
    # Check PYTHONPATH
    print(f"2. PYTHONPATH:")
    print(f"   Environment: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"   sys.path: {json.dumps(sys.path, indent=6)}")
    print()
    
    # Check VS Code settings
    print(f"3. VS Code Settings:")
    vscode_dir = Path(".vscode")
    if vscode_dir.exists():
        settings_file = vscode_dir / "settings.json"
        if settings_file.exists():
            with open(settings_file) as f:
                settings = json.load(f)
                print(f"   Python interpreter: {settings.get('python.defaultInterpreterPath', 'Not set')}")
                print(f"   Extra paths: {settings.get('python.analysis.extraPaths', [])}")
        else:
            print("   No settings.json found")
    else:
        print("   No .vscode directory found")
    print()
    
    # Check if we can import project modules
    print(f"4. Import Test:")
    try:
        import cc_executor
        print(f"   ✓ Successfully imported cc_executor")
        print(f"   Version: {cc_executor.__version__}")
        print(f"   Location: {cc_executor.__file__}")
    except ImportError as e:
        print(f"   ✗ Failed to import cc_executor: {e}")
    print()
    
    # Check debugpy
    print(f"5. Debugpy Check:")
    try:
        import debugpy
        print(f"   ✓ debugpy installed")
        print(f"   Version: {debugpy.__version__}")
        print(f"   Location: {debugpy.__file__}")
    except ImportError as e:
        print(f"   ✗ debugpy not found: {e}")
    print()
    
    # Check if running in VS Code terminal
    print(f"6. VS Code Environment:")
    print(f"   TERM_PROGRAM: {os.environ.get('TERM_PROGRAM', 'Not set')}")
    print(f"   VSCODE_IPC_HOOK_CLI: {'Yes' if 'VSCODE_IPC_HOOK_CLI' in os.environ else 'No'}")
    print(f"   Running in VS Code: {'Yes' if 'VSCODE_IPC_HOOK_CLI' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode' else 'No'}")
    print()
    
    # Test python symlink resolution
    print(f"7. Python Binary Resolution:")
    python_bin = Path(sys.executable)
    print(f"   Binary: {python_bin}")
    print(f"   Is symlink: {python_bin.is_symlink()}")
    if python_bin.is_symlink():
        print(f"   Resolves to: {python_bin.resolve()}")
    print()
    
    # Check for potential issues
    print(f"8. Potential Issues:")
    issues = []
    
    if "PYTHONPATH" not in os.environ:
        issues.append("PYTHONPATH not set in environment")
    
    if not Path(".venv").exists():
        issues.append(".venv directory not found")
    
    if not Path(".venv/bin/python").exists():
        issues.append(".venv/bin/python not found")
    
    try:
        import cc_executor
    except ImportError:
        issues.append("Cannot import cc_executor - PYTHONPATH may be incorrect")
    
    if issues:
        for issue in issues:
            print(f"   ⚠ {issue}")
    else:
        print(f"   ✓ No issues detected")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())