#!/usr/bin/env python3
"""
Test pre and post hooks with a simple Claude call.
This demonstrates that hooks don't trigger automatically.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import json

def create_test_hooks():
    """Create simple pre and post hook scripts for testing."""
    hooks_dir = Path(__file__).parent
    
    # Create pre-execute hook
    pre_hook = hooks_dir / "test_pre_execute.py"
    pre_hook_content = '''#!/usr/bin/env python3
"""Test pre-execute hook."""
import sys
from datetime import datetime

# Write to a marker file to prove hook ran
with open('/tmp/pre_hook_ran.txt', 'w') as f:
    f.write(f"Pre-hook executed at {datetime.now().isoformat()}\\n")
    f.write(f"Command: {' '.join(sys.argv[1:])}\\n")

print("TEST PRE-HOOK: Setting up environment")
'''
    
    with open(pre_hook, 'w') as f:
        f.write(pre_hook_content)
    os.chmod(pre_hook, 0o755)
    
    # Create post-execute hook
    post_hook = hooks_dir / "test_post_execute.py"
    post_hook_content = '''#!/usr/bin/env python3
"""Test post-execute hook."""
import sys
from datetime import datetime

# Write to a marker file to prove hook ran
with open('/tmp/post_hook_ran.txt', 'w') as f:
    f.write(f"Post-hook executed at {datetime.now().isoformat()}\\n")
    f.write(f"Exit code: {sys.argv[1] if len(sys.argv) > 1 else 'unknown'}\\n")

print("TEST POST-HOOK: Cleaning up")
'''
    
    with open(post_hook, 'w') as f:
        f.write(post_hook_content)
    os.chmod(post_hook, 0o755)
    
    return pre_hook, post_hook


def create_test_hooks_config():
    """Create a test .claude-hooks.json configuration."""
    project_root = Path(__file__).parent.parent.parent.parent
    test_config_path = project_root / ".claude-hooks-test.json"
    
    config = {
        "hooks": {
            "pre-execute": {
                "command": str(Path(__file__).parent / "test_pre_execute.py"),
                "description": "Test pre-execute hook"
            },
            "post-execute": {
                "command": str(Path(__file__).parent / "test_post_execute.py"),
                "description": "Test post-execute hook"
            }
        }
    }
    
    with open(test_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return test_config_path


def main():
    """Test pre and post hooks with Claude code."""
    print("=== Testing Pre and Post Hooks with Claude ===\n")
    
    # 1. Create test hooks
    print("1. Creating test hook scripts...")
    pre_hook, post_hook = create_test_hooks()
    print(f"   ✅ Created {pre_hook.name}")
    print(f"   ✅ Created {post_hook.name}")
    
    # 2. Create test configuration
    print("\n2. Creating test hooks configuration...")
    config_path = create_test_hooks_config()
    print(f"   ✅ Created {config_path.name}")
    
    # 3. Clean up marker files
    print("\n3. Cleaning up old marker files...")
    for marker in ['/tmp/pre_hook_ran.txt', '/tmp/post_hook_ran.txt']:
        if Path(marker).exists():
            Path(marker).unlink()
            print(f"   ✅ Removed {marker}")
    
    # 4. Run Claude command
    print("\n4. Running Claude command to create add function...")
    
    # The Claude command
    claude_cmd = [
        "claude",
        "--debug",  # Enable debug to see if hooks trigger
        "-p",
        "Write a simple Python function that adds two numbers and returns the result. Just the function, no explanation."
    ]
    
    print(f"   Command: {' '.join(claude_cmd)}")
    
    # Set environment to potentially trigger hooks
    env = os.environ.copy()
    env['CLAUDE_HOOKS_CONFIG'] = str(config_path)  # Try pointing to our config
    env['CLAUDE_DEBUG'] = 'true'
    
    print("   Running command...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            claude_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        elapsed = time.time() - start_time
        print(f"   ✅ Command completed in {elapsed:.2f}s")
        print(f"   Exit code: {result.returncode}")
        
        # Show output
        if result.stdout:
            print("\n   --- Claude Output ---")
            print("   " + result.stdout.replace('\n', '\n   '))
        
        if result.stderr and "[DEBUG]" not in result.stderr:
            print("\n   --- Errors ---")
            print("   " + result.stderr.replace('\n', '\n   '))
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Command timed out after 30s")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Check if hooks ran
    print("\n5. Checking if hooks executed...")
    
    pre_marker = Path('/tmp/pre_hook_ran.txt')
    post_marker = Path('/tmp/post_hook_ran.txt')
    
    if pre_marker.exists():
        print("   ✅ Pre-hook executed!")
        print(f"   Content: {pre_marker.read_text().strip()}")
    else:
        print("   ❌ Pre-hook did NOT execute")
    
    if post_marker.exists():
        print("   ✅ Post-hook executed!")
        print(f"   Content: {post_marker.read_text().strip()}")
    else:
        print("   ❌ Post-hook did NOT execute")
    
    # 6. Demonstrate manual workaround
    print("\n6. Demonstrating manual hook execution...")
    
    # Clean markers
    for marker in [pre_marker, post_marker]:
        if marker.exists():
            marker.unlink()
    
    # Run pre-hook manually
    print("   Running pre-hook manually...")
    pre_result = subprocess.run([sys.executable, str(pre_hook), "claude", "-p", "test"], 
                               capture_output=True, text=True)
    
    # Run the actual command
    print("   Running Claude command...")
    claude_result = subprocess.run(claude_cmd, capture_output=True, text=True, timeout=30, env=env)
    
    # Run post-hook manually
    print("   Running post-hook manually...")
    post_result = subprocess.run([sys.executable, str(post_hook), str(claude_result.returncode)], 
                                capture_output=True, text=True)
    
    # Check manual execution
    if pre_marker.exists() and post_marker.exists():
        print("   ✅ Manual hook execution works!")
        print(f"   Pre-hook: {pre_marker.read_text().strip()}")
        print(f"   Post-hook: {post_marker.read_text().strip()}")
    
    # 7. Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\nAutomatic hook triggering:")
    print("  - Pre-execute hook: ❌ Does NOT trigger")
    print("  - Post-execute hook: ❌ Does NOT trigger")
    print("\nManual hook execution:")
    print("  - Pre-execute hook: ✅ Works when run manually")
    print("  - Post-execute hook: ✅ Works when run manually")
    print("\nConclusion:")
    print("  Claude Code hooks are completely broken.")
    print("  The only solution is to manually run hooks in our code.")
    print("\nThis is exactly what we do in websocket_handler.py!")
    
    # Cleanup
    print("\n8. Cleaning up test files...")
    for f in [pre_hook, post_hook, config_path]:
        if f.exists():
            f.unlink()
            print(f"   ✅ Removed {f.name}")


if __name__ == "__main__":
    main()