#!/usr/bin/env python3
"""
Launcher that runs all pre-hooks BEFORE launching Claude Code.
This ensures hooks execute deterministically outside of Claude's control.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_hook(hook_path: Path, description: str):
    """Run a hook and report results."""
    print(f"\n🪝 Running {description}...")
    try:
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()[:100]}...")
        else:
            print(f"❌ {description} failed with code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} exception: {e}")
        return False

def main():
    """Run all pre-hooks then launch Claude Code."""
    print("=" * 60)
    print("CC_EXECUTOR HOOK LAUNCHER")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    hooks_dir = project_root / "src" / "cc_executor" / "hooks"
    
    # Critical pre-execution hooks
    critical_hooks = [
        ("setup_environment.py", "Environment Setup"),
        ("claude_instance_pre_check.py", "Claude Instance Pre-Check"),
        ("check_cli_entry_points.py", "CLI Entry Points Check"),
        ("check_task_dependencies.py", "Task Dependencies Check"),
    ]
    
    all_passed = True
    for hook_file, description in critical_hooks:
        hook_path = hooks_dir / hook_file
        if hook_path.exists():
            if not run_hook(hook_path, description):
                all_passed = False
        else:
            print(f"⚠️  Hook not found: {hook_path}")
    
    if not all_passed:
        print("\n❌ Some hooks failed. Fix issues before proceeding.")
        return 1
    
    print("\n✅ All pre-hooks passed!")
    
    # Now launch the actual cc_execute prompt
    print("\n🚀 Launching cc_execute.md prompt...")
    prompt_path = project_root / "src" / "cc_executor" / "prompts" / "cc_execute.py"
    
    if prompt_path.exists():
        # Execute the prompt that creates the Claude instance
        subprocess.run([sys.executable, str(prompt_path)])
    else:
        print(f"❌ Prompt not found: {prompt_path}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())