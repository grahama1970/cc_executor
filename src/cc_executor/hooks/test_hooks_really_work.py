#!/usr/bin/env python3
"""
Comprehensive test to verify if Claude Code hooks work or not.
This test checks multiple potential issues to ensure our conclusion is solid.
"""

import subprocess
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

def log(msg, level="INFO"):
    """Timestamped logging."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {level}: {msg}")

def test_hook_configuration():
    """Verify hook configuration is valid."""
    log("=== Testing Hook Configuration ===")
    
    # Check multiple possible locations for .claude-hooks.json
    possible_locations = [
        Path.home() / ".claude-hooks.json",  # Global
        Path.cwd() / ".claude-hooks.json",   # Current dir
        Path("/home/graham/workspace/experiments/cc_executor/.claude-hooks.json"),  # Project
    ]
    
    config_found = None
    for loc in possible_locations:
        if loc.exists():
            log(f"✅ Found config at: {loc}")
            config_found = loc
            try:
                with open(loc) as f:
                    config = json.load(f)
                log(f"   Hooks defined: {list(config.get('hooks', {}).keys())}")
            except Exception as e:
                log(f"❌ Error reading config: {e}", "ERROR")
        else:
            log(f"   Not found at: {loc}")
    
    if not config_found:
        log("❌ No .claude-hooks.json found!", "ERROR")
        return False
    
    return True

def test_hook_files_exist():
    """Verify hook files actually exist and are executable."""
    log("\n=== Testing Hook Files ===")
    
    hooks_dir = Path(__file__).parent
    hook_files = list(hooks_dir.glob("*.py"))
    
    log(f"Found {len(hook_files)} Python files in hooks directory")
    
    # Check specific hooks we care about
    important_hooks = [
        "setup_environment.py",
        "check_task_dependencies.py",
        "analyze_task_complexity.py"
    ]
    
    all_good = True
    for hook_name in important_hooks:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            executable = os.access(hook_path, os.X_OK)
            log(f"✅ {hook_name}: exists {'(executable)' if executable else '(not executable)'}")
            
            # Try to import it to check for syntax errors
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(hook_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    log(f"   Syntax: valid")
                else:
                    log(f"   Syntax error: {result.stderr}", "ERROR")
                    all_good = False
            except Exception as e:
                log(f"   Error checking syntax: {e}", "ERROR")
                all_good = False
        else:
            log(f"❌ {hook_name}: NOT FOUND", "ERROR")
            all_good = False
    
    return all_good

def create_test_marker_hook():
    """Create a minimal hook that just creates a marker file."""
    log("\n=== Creating Test Marker Hook ===")
    
    test_hook = Path("/tmp/test_marker_hook.py")
    content = '''#!/usr/bin/env python3
import os
from datetime import datetime

# Create marker with timestamp
marker_path = "/tmp/claude_hook_triggered.txt"
with open(marker_path, "w") as f:
    f.write(f"Hook triggered at: {datetime.now().isoformat()}\\n")
    f.write(f"PID: {os.getpid()}\\n")
    f.write(f"Args: {sys.argv}\\n")

print(f"HOOK EXECUTED: Marker created at {marker_path}")
'''
    
    test_hook.write_text(content)
    os.chmod(test_hook, 0o755)
    log(f"Created test hook at: {test_hook}")
    
    # Create a test config that uses this hook
    test_config = Path("/tmp/test-claude-hooks.json")
    config = {
        "hooks": {
            "pre-execute": str(test_hook),
            "post-execute": str(test_hook)
        }
    }
    
    with open(test_config, "w") as f:
        json.dump(config, f, indent=2)
    
    log(f"Created test config at: {test_config}")
    return test_hook, test_config

def test_subprocess_with_hooks(config_path=None):
    """Test if hooks trigger with subprocess."""
    log("\n=== Testing Subprocess Hook Triggering ===")
    
    # Clear marker
    marker = Path("/tmp/claude_hook_triggered.txt")
    if marker.exists():
        marker.unlink()
        log("Cleared old marker file")
    
    # Test different subprocess methods
    test_cases = [
        {
            "name": "Simple Python print",
            "cmd": [sys.executable, "-c", "print('Test')"],
            "shell": False
        },
        {
            "name": "Shell command",
            "cmd": "echo 'Shell test'",
            "shell": True
        },
        {
            "name": "Python script execution",
            "cmd": [sys.executable, "-c", "import sys; print(sys.version)"],
            "shell": False
        }
    ]
    
    for test in test_cases:
        log(f"\nTesting: {test['name']}")
        log(f"Command: {test['cmd'] if not test['shell'] else test['cmd']}")
        
        # Set up environment
        env = os.environ.copy()
        
        # Try various environment variables that might trigger hooks
        env['CLAUDE_HOOKS_ENABLED'] = 'true'
        env['CLAUDE_DEBUG'] = 'true'
        env['DEBUG'] = '1'
        
        if config_path:
            env['CLAUDE_HOOKS_CONFIG'] = str(config_path)
        
        # Also try changing to directory with .claude-hooks.json
        original_cwd = os.getcwd()
        try:
            # Change to project directory
            os.chdir("/home/graham/workspace/experiments/cc_executor")
            
            # Run command
            if test['shell']:
                result = subprocess.run(
                    test['cmd'],
                    shell=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
            else:
                result = subprocess.run(
                    test['cmd'],
                    capture_output=True,
                    text=True,
                    env=env
                )
            
            log(f"Exit code: {result.returncode}")
            log(f"Output: {result.stdout.strip()}")
            
            # Check if marker was created
            if marker.exists():
                log("✅ HOOK TRIGGERED! Marker file created", "SUCCESS")
                log(f"Marker content: {marker.read_text().strip()}")
                return True
            else:
                log("❌ Hook did NOT trigger")
                
        except Exception as e:
            log(f"Error: {e}", "ERROR")
        finally:
            os.chdir(original_cwd)
    
    return False

def test_manual_hook_execution():
    """Test manual hook execution as a control."""
    log("\n=== Testing Manual Hook Execution ===")
    
    marker = Path("/tmp/claude_hook_triggered.txt")
    if marker.exists():
        marker.unlink()
    
    test_hook = Path("/tmp/test_marker_hook.py")
    if test_hook.exists():
        log(f"Running {test_hook} manually...")
        
        result = subprocess.run(
            [sys.executable, str(test_hook)],
            capture_output=True,
            text=True
        )
        
        log(f"Exit code: {result.returncode}")
        log(f"Output: {result.stdout.strip()}")
        
        if marker.exists():
            log("✅ Manual execution works!", "SUCCESS")
            return True
        else:
            log("❌ Manual execution failed", "ERROR")
            return False
    
    return False

def test_claude_command_specifically():
    """Test if hooks trigger specifically for claude command."""
    log("\n=== Testing Claude Command Specifically ===")
    
    marker = Path("/tmp/claude_hook_triggered.txt")
    if marker.exists():
        marker.unlink()
    
    # Test claude command with various flags
    test_commands = [
        ["claude", "--version"],
        ["claude", "--help"],
        ["claude", "--debug", "--version"],
    ]
    
    for cmd in test_commands:
        log(f"\nTesting: {' '.join(cmd)}")
        
        try:
            # Run with timeout to avoid hanging
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                env=os.environ.copy()
            )
            
            log(f"Exit code: {result.returncode}")
            
            if marker.exists():
                log("✅ Hook triggered for claude command!", "SUCCESS")
                return True
            else:
                log("❌ No hook trigger")
                
        except subprocess.TimeoutExpired:
            log("Command timed out", "WARN")
        except FileNotFoundError:
            log("Claude command not found", "ERROR")
            break
        except Exception as e:
            log(f"Error: {e}", "ERROR")
    
    return False

def main():
    """Run comprehensive hook tests."""
    print("=" * 70)
    print("COMPREHENSIVE CLAUDE CODE HOOK TEST")
    print("=" * 70)
    
    results = {
        "config_valid": test_hook_configuration(),
        "files_exist": test_hook_files_exist(),
    }
    
    # Create test hook for controlled testing
    test_hook, test_config = create_test_marker_hook()
    
    # Test with project config
    results["project_hooks_trigger"] = test_subprocess_with_hooks()
    
    # Test with our test config
    results["test_hooks_trigger"] = test_subprocess_with_hooks(test_config)
    
    # Test manual execution
    results["manual_execution"] = test_manual_hook_execution()
    
    # Test claude command specifically
    results["claude_hooks_trigger"] = test_claude_command_specifically()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test:.<40} {status}")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    
    if results["manual_execution"] and not any([
        results["project_hooks_trigger"],
        results["test_hooks_trigger"],
        results["claude_hooks_trigger"]
    ]):
        print("Claude Code hooks are CONFIRMED BROKEN:")
        print("- Hooks exist and are valid ✅")
        print("- Manual execution works ✅")
        print("- Automatic triggering fails ❌")
        print("\nThe workaround in websocket_handler.py is necessary.")
    elif any([results["project_hooks_trigger"], results["test_hooks_trigger"]]):
        print("SURPRISING: Hooks might be working!")
        print("Further investigation needed.")
    else:
        print("Test results inconclusive.")
        print("Check test output for errors.")
    
    # Cleanup
    for f in [test_hook, test_config, Path("/tmp/claude_hook_triggered.txt")]:
        if f.exists():
            f.unlink()


if __name__ == "__main__":
    main()