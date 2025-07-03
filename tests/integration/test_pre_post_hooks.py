#!/usr/bin/env python3
"""Test that both pre and post execution hooks are working."""
import subprocess
import sys
import json
import time
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def check_redis_keys(pattern):
    """Check Redis for hook-related keys."""
    try:
        result = subprocess.run(
            ["redis-cli", "keys", pattern],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            keys = result.stdout.strip().split('\n')
            return [k for k in keys if k]
        return []
    except:
        return []

def main():
    print("=" * 60)
    print("TESTING PRE AND POST EXECUTION HOOKS")
    print("=" * 60)
    
    # Get initial state
    initial_hook_keys = check_redis_keys("hook:*")
    initial_metrics = check_redis_keys("metrics:*")
    print(f"Initial hook keys: {len(initial_hook_keys)}")
    print(f"Initial metrics keys: {len(initial_metrics)}")
    
    # Run a simple test command via websocket handler
    print("\nRunning test command...")
    start_time = time.time()
    
    # Use the websocket handler's test functionality
    result = subprocess.run([
        sys.executable,
        "src/cc_executor/core/websocket_handler.py",
        "--simple",
        "--no-server"
    ], capture_output=True, text=True)
    
    duration = time.time() - start_time
    print(f"Command completed in {duration:.1f}s with exit code: {result.returncode}")
    
    # Check for hook execution in output
    output = result.stderr  # Logs go to stderr
    
    # Check pre-execution hooks
    pre_hooks_ran = []
    if "[TEST] setup_environment.py completed" in output:
        pre_hooks_ran.append("setup_environment.py")
    if "[TEST] claude_instance_pre_check.py completed" in output:
        pre_hooks_ran.append("claude_instance_pre_check.py")
    if "[TEST] Virtual environment configured" in output:
        pre_hooks_ran.append("venv_configured")
    
    # Check post-execution hooks
    post_hooks_ran = []
    if "[HOOK POST-EXEC]" in output:
        post_hooks_ran.append("post_execution_hook")
    if "Post-execution hook completed" in result.stderr:
        post_hooks_ran.append("hook_integration_post")
    
    # Check Redis for new keys
    time.sleep(1)  # Give Redis time to update
    final_hook_keys = check_redis_keys("hook:*")
    final_metrics = check_redis_keys("metrics:*")
    
    new_hook_keys = len(final_hook_keys) - len(initial_hook_keys)
    new_metrics_keys = len(final_metrics) - len(initial_metrics)
    
    # Generate report
    print("\n" + "=" * 60)
    print("HOOK EXECUTION REPORT")
    print("=" * 60)
    
    print(f"\n✅ PRE-EXECUTION HOOKS ({len(pre_hooks_ran)} ran):")
    for hook in pre_hooks_ran:
        print(f"   - {hook}")
    
    print(f"\n{'✅' if post_hooks_ran else '❌'} POST-EXECUTION HOOKS ({len(post_hooks_ran)} ran):")
    for hook in post_hooks_ran:
        print(f"   - {hook}")
    
    print(f"\n📊 REDIS UPDATES:")
    print(f"   - New hook keys: {new_hook_keys}")
    print(f"   - New metrics keys: {new_metrics_keys}")
    
    # Check specific post-execution evidence
    if new_hook_keys > 0 or new_metrics_keys > 0:
        print("\n✅ Evidence of hook execution found in Redis")
    
    # Look for specific hook outputs
    if "record_execution_metrics" in output:
        print("✅ record_execution_metrics.py executed")
    
    # Overall result
    success = len(pre_hooks_ran) > 0 and (len(post_hooks_ran) > 0 or new_hook_keys > 0)
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: {'Both' if success else 'Not all'} pre and post hooks executed")
    
    # Show relevant log excerpts
    if not success:
        print("\nRelevant log excerpts:")
        for line in output.split('\n'):
            if any(keyword in line for keyword in ['hook', 'Hook', 'HOOK', 'POST', 'PRE']):
                print(f"   {line.strip()}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())