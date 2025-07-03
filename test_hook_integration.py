#!/usr/bin/env python3
"""
Test script to verify cc_executor hook integration.

This script tests that:
1. Hook scripts in src/cc_executor/hooks/ are actually executed
2. The programmatic hook enforcement works correctly
3. Hook execution logs are properly captured
4. Redis integration stores hook data when available
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from cc_executor.core.hook_integration import HookIntegration, ProgrammaticHookEnforcement
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# Test marker for verification
TEST_MARKER = f"HOOK_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


async def test_hook_scripts_execution():
    """Test that hook scripts are actually executed."""
    print(f"\n{'='*60}")
    print(f"Testing Hook Scripts Execution - {TEST_MARKER}")
    print(f"{'='*60}\n")
    
    # Create enforcer instance
    enforcer = ProgrammaticHookEnforcement()
    
    # Test 1: Initialize and check venv setup
    print("1. Testing initialization and venv setup...")
    init_result = enforcer.initialize()
    print(f"   - Initialization: {'✓ Success' if init_result else '✗ Failed'}")
    print(f"   - Venv path: {enforcer.venv_path or 'Not detected'}")
    print(f"   - Redis available: {'✓ Yes' if enforcer.redis_client else '✗ No'}")
    
    # Test 2: Run pre-execute hook with a test command
    print("\n2. Testing pre-execute hook...")
    test_command = f"echo '{TEST_MARKER} - Testing pre-execute hook'"
    context = {
        'test_marker': TEST_MARKER,
        'run_all_hooks': True  # This triggers additional hooks
    }
    
    pre_result = enforcer.pre_execute_hook(test_command, context)
    print(f"   - Command: {test_command}")
    print(f"   - Wrapped command: {pre_result.get('wrapped_command', 'None')}")
    print(f"   - Session ID: {pre_result.get('session_id', 'None')}")
    
    # Test 3: Check if setup_environment.py was executed
    print("\n3. Checking hook script execution logs...")
    
    # Look for evidence that hooks ran
    hooks_dir = Path(__file__).parent / "src" / "cc_executor" / "hooks"
    log_files = list(hooks_dir.glob("*.log"))
    
    if log_files:
        print(f"   - Found {len(log_files)} log files in hooks directory")
        for log_file in log_files[:3]:  # Show first 3
            print(f"     • {log_file.name}")
    
    # Test 4: Run post-execute hook
    print("\n4. Testing post-execute hook...")
    enforcer.post_execute_hook(test_command, 0, f"Output with {TEST_MARKER}")
    
    # Test 5: Check metrics
    print("\n5. Checking hook metrics...")
    metrics = enforcer.get_metrics()
    if metrics:
        print("   - Metrics stored in Redis:")
        for key, value in metrics.items():
            print(f"     • {key}: {value}")
    else:
        print("   - No metrics available (Redis not connected)")
    
    # Test 6: Test async execution with HookIntegration
    print("\n6. Testing HookIntegration async execution...")
    hook_integration = HookIntegration()
    
    # Test pre-execution hook
    pre_hook_result = await hook_integration.pre_execution_hook(
        test_command, 
        f"test_session_{TEST_MARKER}"
    )
    
    if pre_hook_result:
        print("   - Pre-execution hook result:")
        for key, value in pre_hook_result.get('pre-execute', {}).items():
            if key != 'wrapped_command':  # Skip long command
                print(f"     • {key}: {value}")
    
    # Test post-execution hook
    post_hook_result = await hook_integration.post_execution_hook(
        test_command,
        0,
        1.23,
        f"Test output with {TEST_MARKER}"
    )
    
    if post_hook_result:
        print("   - Post-execution hook result:")
        for key, value in post_hook_result.get('post-execute', {}).items():
            if key != 'metrics':  # Handle metrics separately
                print(f"     • {key}: {value}")
    
    print(f"\n{'='*60}")
    print("Hook Integration Test Complete")
    print(f"{'='*60}\n")


def test_hook_script_direct_execution():
    """Test direct execution of hook scripts to ensure they work."""
    print(f"\n{'='*60}")
    print("Testing Direct Hook Script Execution")
    print(f"{'='*60}\n")
    
    hooks_dir = Path(__file__).parent / "src" / "cc_executor" / "hooks"
    
    # Test key hook scripts
    test_hooks = [
        "setup_environment.py",
        "claude_instance_pre_check.py",
        "analyze_task_complexity.py"
    ]
    
    for hook_name in test_hooks:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            print(f"\nTesting {hook_name}...")
            
            try:
                # Set up environment for hook
                env = os.environ.copy()
                env['PYTHONPATH'] = str(Path(__file__).parent / "src")
                env['CLAUDE_TEST_MARKER'] = TEST_MARKER
                
                # Run hook script
                result = subprocess.run(
                    [sys.executable, str(hook_path)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                print(f"   - Exit code: {result.returncode}")
                
                if result.stdout:
                    print(f"   - Stdout preview: {result.stdout[:200]}...")
                    
                if result.stderr and result.returncode != 0:
                    print(f"   - Stderr: {result.stderr[:200]}...")
                    
            except subprocess.TimeoutError:
                print(f"   - ✗ Timed out after 10 seconds")
            except Exception as e:
                print(f"   - ✗ Error: {e}")
        else:
            print(f"\n✗ Hook script not found: {hook_name}")


def verify_hook_execution_in_logs():
    """Verify hook execution by checking logs and Redis."""
    print(f"\n{'='*60}")
    print("Verifying Hook Execution Evidence")
    print(f"{'='*60}\n")
    
    # Check for log files that might contain evidence
    evidence_found = []
    
    # 1. Check hooks directory for any generated files
    hooks_dir = Path(__file__).parent / "src" / "cc_executor" / "hooks"
    tmp_dir = hooks_dir / "tmp"
    
    if tmp_dir.exists():
        recent_files = []
        for file in tmp_dir.rglob("*"):
            if file.is_file():
                # Check if file was created in last 5 minutes
                mtime = file.stat().st_mtime
                if time.time() - mtime < 300:  # 5 minutes
                    recent_files.append(file)
        
        if recent_files:
            print(f"1. Found {len(recent_files)} recent files in hooks/tmp/:")
            for file in recent_files[:5]:  # Show first 5
                print(f"   • {file.relative_to(hooks_dir)}")
            evidence_found.append("recent_tmp_files")
    
    # 2. Check Redis for hook data
    try:
        import redis
        r = redis.Redis(decode_responses=True)
        
        # Look for hook-related keys
        hook_keys = []
        for key in r.scan_iter("hook:*"):
            hook_keys.append(key)
        
        if hook_keys:
            print(f"\n2. Found {len(hook_keys)} hook-related keys in Redis:")
            for key in hook_keys[:5]:  # Show first 5
                print(f"   • {key}")
                # Try to get the value
                try:
                    value = r.get(key)
                    if value and TEST_MARKER in str(value):
                        print(f"     ✓ Contains our test marker!")
                        evidence_found.append("redis_marker")
                except:
                    pass
    except Exception as e:
        print(f"\n2. Could not check Redis: {e}")
    
    # 3. Check for any log files with our marker
    print(f"\n3. Searching for test marker '{TEST_MARKER}' in files...")
    
    # Search in hooks directory
    marker_files = []
    for ext in ['*.log', '*.txt', '*.json']:
        for file in hooks_dir.rglob(ext):
            try:
                if file.is_file() and TEST_MARKER in file.read_text():
                    marker_files.append(file)
            except:
                pass
    
    if marker_files:
        print(f"   ✓ Found marker in {len(marker_files)} files:")
        for file in marker_files[:3]:
            print(f"     • {file.relative_to(hooks_dir)}")
        evidence_found.append("marker_in_files")
    
    # Summary
    print(f"\n{'='*60}")
    print("Verification Summary:")
    print(f"{'='*60}")
    
    if evidence_found:
        print(f"\n✓ Hook execution verified! Evidence found:")
        for evidence in evidence_found:
            print(f"  • {evidence}")
    else:
        print("\n✗ No direct evidence of hook execution found")
        print("  This might mean:")
        print("  - Hooks are not writing logs/output")
        print("  - Redis is not available")
        print("  - Hooks are failing silently")
    
    return len(evidence_found) > 0


async def main():
    """Run all tests."""
    print(f"\n{'='*80}")
    print("CC_EXECUTOR HOOK INTEGRATION TEST")
    print(f"{'='*80}")
    print(f"Test marker: {TEST_MARKER}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run async tests
    await test_hook_scripts_execution()
    
    # Run sync tests
    test_hook_script_direct_execution()
    
    # Verify execution
    success = verify_hook_execution_in_logs()
    
    print(f"\n{'='*80}")
    print(f"FINAL RESULT: {'✓ HOOKS ARE WORKING' if success else '✗ HOOKS NOT VERIFIED'}")
    print(f"{'='*80}\n")
    
    return success


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(main())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)