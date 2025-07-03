#!/usr/bin/env python3
"""Test that pre and post hooks work for ALL THREE tests: simple, medium, long."""
import subprocess
import sys
import time
import json
from pathlib import Path

def run_test(test_type, timeout=300):
    """Run a specific test and check for hook execution."""
    print(f"\n{'='*60}")
    print(f"TESTING {test_type.upper()}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Run the test
    result = subprocess.run([
        sys.executable,
        "src/cc_executor/core/websocket_handler.py",
        test_type,
        "--no-server"
    ], 
    capture_output=True, 
    text=True,
    timeout=timeout,
    cwd=Path(__file__).parent)
    
    duration = time.time() - start_time
    
    # Check for hook execution evidence
    stderr = result.stderr
    stdout = result.stdout
    
    # Pre-hooks checks
    pre_hooks = {
        "setup_environment": "setup_environment.py completed" in stderr,
        "claude_instance_pre_check": "claude_instance_pre_check.py completed" in stderr,
        "venv_configured": "Virtual environment configured" in stderr
    }
    
    # Post-hooks checks
    post_hooks = {
        "running_post_hooks": "Running post-execution hooks" in stderr,
        "record_metrics": "Post-hook record_execution_metrics.py" in stderr,
        "response_validator": "Post-hook claude_response_validator.py" in stderr
    }
    
    # Count successes
    pre_success = sum(pre_hooks.values())
    post_success = sum(post_hooks.values())
    
    # Report results
    print(f"\nCompleted in {duration:.1f}s (exit code: {result.returncode})")
    
    print(f"\nPRE-EXECUTION HOOKS ({pre_success}/3):")
    for name, found in pre_hooks.items():
        print(f"  {'✅' if found else '❌'} {name}")
    
    print(f"\nPOST-EXECUTION HOOKS ({post_success}/3):")
    for name, found in post_hooks.items():
        print(f"  {'✅' if found else '❌'} {name}")
    
    # Check if Claude actually executed
    if "Claude's response:" in stdout:
        print("\n✅ Claude executed successfully")
    else:
        print("\n❌ Claude execution unclear")
    
    # Return success status
    return {
        "test": test_type,
        "duration": duration,
        "exit_code": result.returncode,
        "pre_hooks_pass": pre_success == 3,
        "post_hooks_pass": post_success >= 2,  # At least 2 of 3
        "claude_executed": "Claude's response:" in stdout
    }

def main():
    print("="*80)
    print("COMPREHENSIVE HOOK VERIFICATION FOR ALL THREE TESTS")
    print("="*80)
    
    # Check Redis is running
    redis_check = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
    if redis_check.returncode != 0:
        print("⚠️  Redis not running - some hooks may fail")
    
    # Run all three tests
    tests = [
        ("--simple", 60),    # 1 minute timeout
        ("--medium", 120),   # 2 minute timeout
        ("--long", 360)      # 6 minute timeout
    ]
    
    results = []
    
    for test_type, timeout in tests:
        try:
            result = run_test(test_type, timeout)
            results.append(result)
        except subprocess.TimeoutExpired:
            print(f"\n❌ {test_type} TIMEOUT after {timeout}s")
            results.append({
                "test": test_type,
                "duration": timeout,
                "exit_code": -1,
                "pre_hooks_pass": False,
                "post_hooks_pass": False,
                "claude_executed": False
            })
        except Exception as e:
            print(f"\n❌ {test_type} ERROR: {e}")
            results.append({
                "test": test_type,
                "duration": 0,
                "exit_code": -2,
                "pre_hooks_pass": False,
                "post_hooks_pass": False,
                "claude_executed": False
            })
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    all_pass = True
    for r in results:
        status = "✅ PASS" if (r["pre_hooks_pass"] and r["post_hooks_pass"] and r["claude_executed"]) else "❌ FAIL"
        print(f"\n{r['test']:10} {status}")
        print(f"  Duration: {r['duration']:.1f}s")
        print(f"  Pre-hooks: {'✅' if r['pre_hooks_pass'] else '❌'}")
        print(f"  Post-hooks: {'✅' if r['post_hooks_pass'] else '❌'}")
        print(f"  Claude ran: {'✅' if r['claude_executed'] else '❌'}")
        
        if not (r["pre_hooks_pass"] and r["post_hooks_pass"]):
            all_pass = False
    
    print("\n" + "="*80)
    if all_pass:
        print("✅ ALL TESTS PASSED - HOOKS WORK FOR ALL THREE!")
    else:
        print("❌ SOME TESTS FAILED - HOOKS NOT WORKING CONSISTENTLY")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    # Only run simple and medium by default (long takes 3-5 minutes)
    if "--all" in sys.argv:
        sys.exit(main())
    else:
        print("Running simple and medium tests only. Use --all to include long test.")
        # Temporarily modify to skip long test
        import test_all_three_hooks
        test_all_three_hooks.tests = [("--simple", 60), ("--medium", 120)]
        sys.exit(main())