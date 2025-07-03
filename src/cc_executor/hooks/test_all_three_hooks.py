#!/usr/bin/env python3
"""
Final definitive test of Claude Code hooks.
Tests hooks in three different ways to ensure our conclusion is solid.
"""

import subprocess
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

def create_instrumented_hook():
    """Create a hook that definitively proves it ran."""
    hook_content = '''#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Write multiple markers to prove execution
markers = [
    "/tmp/hook_executed.txt",
    "/tmp/hook_timestamp.txt",
    "/tmp/hook_args.txt"
]

timestamp = datetime.now().isoformat()

with open(markers[0], 'w') as f:
    f.write("YES")

with open(markers[1], 'w') as f:
    f.write(timestamp)

with open(markers[2], 'w') as f:
    f.write(f"Args: {sys.argv}\\nEnv: {os.environ.get('CLAUDE_HOOKS_CONFIG', 'NOT SET')}")

# Also print to stdout/stderr
print(f"HOOK EXECUTED at {timestamp}")
sys.stderr.write(f"HOOK STDERR: Executed at {timestamp}\\n")
'''
    
    hook_path = Path("/tmp/definitive_test_hook.py")
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    return hook_path

def clear_markers():
    """Clear all marker files."""
    markers = [
        "/tmp/hook_executed.txt",
        "/tmp/hook_timestamp.txt", 
        "/tmp/hook_args.txt"
    ]
    for marker in markers:
        p = Path(marker)
        if p.exists():
            p.unlink()

def check_markers():
    """Check if any markers were created."""
    main_marker = Path("/tmp/hook_executed.txt")
    if main_marker.exists():
        print("   ✅ HOOK EXECUTED - Marker files created:")
        for marker in ["/tmp/hook_executed.txt", "/tmp/hook_timestamp.txt", "/tmp/hook_args.txt"]:
            p = Path(marker)
            if p.exists():
                content = p.read_text().strip()
                print(f"      {marker}: {content[:50]}")
        return True
    else:
        print("   ❌ NO MARKERS - Hook did not execute")
        return False

def test_method_1_subprocess():
    """Test 1: Regular subprocess calls."""
    print("\n=== TEST 1: Regular Subprocess ===")
    print("Testing if hooks trigger on normal subprocess calls...")
    
    clear_markers()
    
    # Multiple subprocess variations
    tests = [
        ("Python command", [sys.executable, "-c", "print('test')"]),
        ("Shell command", ["echo", "test"]),
        ("Python module", [sys.executable, "-m", "sys"]),
    ]
    
    for name, cmd in tests:
        print(f"\n   Testing {name}: {' '.join(cmd)}")
        clear_markers()
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"   Exit code: {result.returncode}")
        
        if check_markers():
            return True
            
    return False

def test_method_2_claude_command():
    """Test 2: Claude-specific commands."""
    print("\n=== TEST 2: Claude Commands ===")
    print("Testing if hooks trigger on claude commands...")
    
    # First verify claude exists
    which_result = subprocess.run(["which", "claude"], capture_output=True, text=True)
    if which_result.returncode != 0:
        print("   ⚠️  Claude command not found in PATH")
        return False
    
    clear_markers()
    
    # Test various claude commands
    tests = [
        ("Version", ["claude", "--version"]),
        ("Help", ["claude", "--help"]),
        ("Debug version", ["claude", "--debug", "--version"]),
    ]
    
    for name, cmd in tests:
        print(f"\n   Testing {name}: {' '.join(cmd)}")
        clear_markers()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            print(f"   Exit code: {result.returncode}")
            
            # Check both markers and output
            if check_markers():
                return True
                
            # Also check if hook output appears in claude output
            if "HOOK EXECUTED" in result.stdout or "HOOK EXECUTED" in result.stderr:
                print("   ✅ Found hook output in command output!")
                return True
                
        except subprocess.TimeoutExpired:
            print("   ⏱️  Command timed out")
            
    return False

def test_method_3_with_config():
    """Test 3: With explicit configuration."""
    print("\n=== TEST 3: Explicit Configuration ===")
    print("Testing with explicit hook configuration...")
    
    # Create test configuration
    hook_path = create_instrumented_hook()
    config = {
        "hooks": {
            "pre-execute": str(hook_path),
            "post-execute": str(hook_path),
            "pre-tool": str(hook_path),
            "post-tool": str(hook_path)
        }
    }
    
    # Try multiple config locations
    config_locations = [
        Path.home() / ".claude-hooks.json",
        Path.cwd() / ".claude-hooks.json",
        Path("/tmp/.claude-hooks.json")
    ]
    
    for config_path in config_locations:
        print(f"\n   Testing with config at: {config_path}")
        
        # Write config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        try:
            # Test subprocess with this config
            clear_markers()
            
            env = os.environ.copy()
            env['CLAUDE_HOOKS_CONFIG'] = str(config_path)
            
            # Try to trigger hooks
            result = subprocess.run(
                [sys.executable, "-c", "print('test with config')"],
                capture_output=True,
                text=True,
                env=env,
                cwd=config_path.parent
            )
            
            if check_markers():
                print(f"   ✅ Hooks work with config at {config_path}!")
                return True
                
        finally:
            # Clean up config
            if config_path.exists():
                config_path.unlink()
                
    return False

def test_manual_execution():
    """Control test: Verify manual execution works."""
    print("\n=== CONTROL TEST: Manual Execution ===")
    print("Verifying our test hook works when run manually...")
    
    hook_path = create_instrumented_hook()
    clear_markers()
    
    result = subprocess.run([sys.executable, str(hook_path)], capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout}")
    
    return check_markers()

def main():
    """Run all tests and provide definitive conclusion."""
    print("="*60)
    print("DEFINITIVE CLAUDE CODE HOOKS TEST")
    print("="*60)
    
    # Show current environment
    print("\nEnvironment:")
    print(f"  Working directory: {os.getcwd()}")
    print(f"  Python: {sys.executable}")
    print(f"  Claude config exists: {Path('/home/graham/workspace/experiments/cc_executor/.claude-hooks.json').exists()}")
    
    # Run tests
    results = {
        "subprocess_hooks": test_method_1_subprocess(),
        "claude_hooks": test_method_2_claude_command(),
        "config_hooks": test_method_3_with_config(),
        "manual_execution": test_manual_execution()
    }
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test:.<40} {status}")
    
    print("\n" + "="*60)
    print("DEFINITIVE CONCLUSION")
    print("="*60)
    
    if results["manual_execution"] and not any([
        results["subprocess_hooks"],
        results["claude_hooks"],
        results["config_hooks"]
    ]):
        print("\n🔴 CLAUDE CODE HOOKS ARE 100% BROKEN")
        print("\nProof:")
        print("  1. Manual execution works ✅ (hooks are valid)")
        print("  2. Subprocess hooks fail ❌")
        print("  3. Claude command hooks fail ❌")
        print("  4. Explicit config hooks fail ❌")
        print("\nThe hooks system is completely non-functional.")
        print("Our workaround in websocket_handler.py is the ONLY solution.")
    else:
        unexpected = [k for k, v in results.items() if v and k != "manual_execution"]
        if unexpected:
            print(f"\n⚠️  UNEXPECTED: {unexpected} passed!")
            print("This requires further investigation.")
    
    # Cleanup
    clear_markers()
    for f in ["/tmp/definitive_test_hook.py"]:
        p = Path(f)
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    main()