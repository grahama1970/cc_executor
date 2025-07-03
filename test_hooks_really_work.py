#!/usr/bin/env python3
"""Actually verify hooks are working, not hallucinating."""
import subprocess
import json
import time
from pathlib import Path

def check_redis_for_evidence():
    """Look for actual evidence in Redis."""
    # Get recent hook executions
    result = subprocess.run(
        ["redis-cli", "--scan", "--pattern", "hook:*"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return None
        
    keys = [k for k in result.stdout.strip().split('\n') if k]
    
    # Get the most recent hook data
    recent_hooks = []
    for key in keys[-5:]:  # Last 5 hooks
        data = subprocess.run(
            ["redis-cli", "get", key],
            capture_output=True,
            text=True
        )
        if data.returncode == 0 and data.stdout:
            try:
                hook_data = json.loads(data.stdout)
                recent_hooks.append({
                    'key': key,
                    'command': hook_data.get('command', '')[:50],
                    'timestamp': hook_data.get('timestamp', 0)
                })
            except:
                pass
                
    return recent_hooks

def main():
    print("=== REAL HOOK VERIFICATION ===\n")
    
    # Check initial Redis state
    initial_hooks = check_redis_for_evidence()
    print(f"Found {len(initial_hooks) if initial_hooks else 0} existing hook records in Redis")
    
    # Run a test that SHOULD trigger hooks
    print("\nRunning Claude command through websocket handler...")
    start_time = time.time()
    
    result = subprocess.run([
        "python3",
        "src/cc_executor/core/websocket_handler.py",
        "--simple",
        "--no-server"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    duration = time.time() - start_time
    
    # Check for hook execution evidence
    print(f"\nCommand completed in {duration:.1f}s")
    
    # Give Redis a moment to update
    time.sleep(0.5)
    
    # Check final Redis state
    final_hooks = check_redis_for_evidence()
    
    if initial_hooks and final_hooks:
        new_hooks = len(final_hooks) - len(initial_hooks)
        print(f"\nNEW REDIS HOOK RECORDS: {new_hooks}")
        
        if new_hooks > 0:
            print("\nMost recent hook executions:")
            for hook in final_hooks[-new_hooks:]:
                print(f"  - {hook['key']}: {hook['command']}")
    
    # Check stderr for hook messages
    hook_messages = []
    for line in result.stderr.split('\n'):
        if '[TEST]' in line and 'hook' in line.lower():
            hook_messages.append(line.strip())
    
    if hook_messages:
        print(f"\nHOOK EXECUTION MESSAGES ({len(hook_messages)}):")
        for msg in hook_messages[:10]:  # First 10
            print(f"  {msg}")
    
    # Check if Claude actually used the right Python
    if "VIRTUAL_ENV" in result.stderr or ".venv" in result.stderr:
        print("\n✅ Virtual environment references found in output")
    else:
        print("\n❌ No virtual environment references found")
    
    # Final verdict - check stderr directly since hook_messages might miss some
    has_pre_hooks = ("setup_environment.py completed" in result.stderr or 
                     "claude_instance_pre_check.py completed" in result.stderr)
    has_post_hooks = ("Post-hook" in result.stderr or 
                      "post-execution hooks" in result.stderr)
    has_redis_evidence = final_hooks and initial_hooks and len(final_hooks) > len(initial_hooks)
    
    print(f"\nVERDICT:")
    print(f"  Pre-hooks executed: {'✅' if has_pre_hooks else '❌'}")
    print(f"  Post-hooks executed: {'✅' if has_post_hooks else '❌'}")
    print(f"  Redis evidence: {'✅' if has_redis_evidence else '❌'}")
    
    if has_pre_hooks and has_post_hooks:
        print("\n✅ HOOKS ARE ACTUALLY WORKING")
    else:
        print("\n❌ HOOKS ARE NOT WORKING AS EXPECTED")

if __name__ == "__main__":
    main()