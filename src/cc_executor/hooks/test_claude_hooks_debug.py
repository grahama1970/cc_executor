#!/usr/bin/env python3
"""
Proof of concept to test if Claude Code hooks work with --debug flag.

According to Anthropic's comment on issue #2891:
"For those of you trying hooks out, you can use --debug to see how they're triggering."

This script tests:
1. Whether hooks trigger at all
2. Whether --debug provides useful information
3. Whether our subprocess workaround is still needed
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def test_hook_with_debug():
    """Test if Claude Code hooks work with --debug flag."""
    print("=== Testing Claude Code Hooks with --debug ===\n")
    
    # Create a simple test command
    test_command = [
        "claude",
        "--debug",  # Enable debug mode as suggested
        "-p", 
        "Write a simple Python script that prints 'Hello from Claude'"
    ]
    
    print(f"Running command: {' '.join(test_command)}")
    print(f"Current directory: {os.getcwd()}")
    print(f"ANTHROPIC_API_KEY set: {'Yes' if os.environ.get('ANTHROPIC_API_KEY') else 'No'}")
    print(f"Virtual environment: {sys.prefix}")
    print("\n" + "="*60 + "\n")
    
    # Check if hooks exist
    hooks_dir = Path(__file__).parent
    print("Checking for hook files:")
    hook_files = [
        "setup_environment.py",
        "check_task_dependencies.py", 
        "analyze_task_complexity.py",
        "claude_instance_pre_check.py"
    ]
    
    for hook in hook_files:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            print(f"  ✅ {hook} exists")
            # Check if executable
            if os.access(hook_path, os.X_OK):
                print(f"     └─ Executable: Yes")
            else:
                print(f"     └─ Executable: No (may need chmod +x)")
        else:
            print(f"  ❌ {hook} NOT FOUND")
    
    print("\n" + "="*60 + "\n")
    
    # Test 1: Run Claude with --debug to see if hooks trigger
    print("Test 1: Running Claude with --debug flag...")
    start_time = time.time()
    found_indicators = []  # Initialize this before the try block
    
    try:
        # Run with environment that should trigger hooks
        env = os.environ.copy()
        env['CLAUDE_DEBUG'] = 'true'  # In case this helps
        
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        elapsed = time.time() - start_time
        
        print(f"Exit code: {result.returncode}")
        print(f"Elapsed time: {elapsed:.2f}s")
        print("\n--- STDOUT ---")
        print(result.stdout[:1000] + ("...[truncated]" if len(result.stdout) > 1000 else ""))
        print("\n--- STDERR ---")
        print(result.stderr[:1000] + ("...[truncated]" if len(result.stderr) > 1000 else ""))
        
        # Look for hook-related output
        combined_output = result.stdout + result.stderr
        hook_indicators = [
            "hook", "Hook", "HOOK",
            "setup_environment", 
            "check_task_dependencies",
            "pre-hook", "post-hook",
            "Running hook", "Executing hook",
            "debug", "Debug", "DEBUG"
        ]
        
        print("\n--- Hook Analysis ---")
        found_indicators = []
        for indicator in hook_indicators:
            if indicator in combined_output:
                found_indicators.append(indicator)
                # Find context around the indicator
                lines = combined_output.split('\n')
                for i, line in enumerate(lines):
                    if indicator in line:
                        print(f"\nFound '{indicator}' in line {i}:")
                        # Show 2 lines before and after
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        for j in range(start, end):
                            prefix = ">>> " if j == i else "    "
                            print(f"{prefix}{lines[j]}")
        
        if not found_indicators:
            print("❌ No hook-related output found in debug mode")
        else:
            print(f"\n✅ Found hook indicators: {', '.join(set(found_indicators))}")
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 30 seconds")
        print("This might indicate hooks are hanging...")
    except Exception as e:
        print(f"❌ Error running command: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Try our manual workaround for comparison
    print("Test 2: Testing our manual hook workaround...")
    
    # Run hooks manually before Claude command
    hooks_run = []
    for hook in ["setup_environment.py", "check_task_dependencies.py"]:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            print(f"\nManually running {hook}...")
            try:
                hook_result = subprocess.run(
                    [sys.executable, str(hook_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if hook_result.returncode == 0:
                    print(f"  ✅ {hook} completed successfully")
                    hooks_run.append(hook)
                else:
                    print(f"  ❌ {hook} failed with code {hook_result.returncode}")
                    if hook_result.stderr:
                        print(f"     Error: {hook_result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"  ❌ {hook} timed out")
            except Exception as e:
                print(f"  ❌ Error running {hook}: {e}")
    
    print(f"\nManual workaround result: {len(hooks_run)} hooks executed successfully")
    
    print("\n" + "="*60 + "\n")
    
    # Summary
    print("=== SUMMARY ===\n")
    print("1. Claude Code hooks with --debug:")
    if found_indicators:
        print("   ✅ Some hook-related output was found")
        print("   → Hooks might be partially working")
    else:
        print("   ❌ No hook-related output detected")
        print("   → Hooks appear to be completely broken")
    
    print("\n2. Manual hook workaround:")
    if hooks_run:
        print(f"   ✅ Successfully ran {len(hooks_run)} hooks manually")
        print("   → Workaround is functional")
    else:
        print("   ❌ No hooks could be run manually")
        print("   → Check hook file permissions and paths")
    
    print("\n3. Recommendation:")
    if not found_indicators and hooks_run:
        print("   → Continue using the subprocess workaround in websocket_handler.py")
        print("   → Claude Code hooks appear too broken to rely on")
    elif found_indicators:
        print("   → Investigate the debug output further")
        print("   → Hooks might be fixable with proper configuration")
    else:
        print("   → Check hook setup and permissions")
        print("   → Ensure .claude-hooks.json is properly configured")
    
    # Test 3: Check .claude-hooks.json
    print("\n" + "="*60 + "\n")
    print("Test 3: Checking .claude-hooks.json configuration...")
    
    config_path = Path.home() / "workspace" / "experiments" / "cc_executor" / ".claude-hooks.json"
    if config_path.exists():
        print(f"✅ Found .claude-hooks.json at: {config_path}")
        try:
            import json
            with open(config_path) as f:
                config = json.load(f)
            print(f"   Hooks configured: {len(config.get('hooks', {}))}")
            for hook_name in config.get('hooks', {}).keys():
                print(f"   - {hook_name}")
        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print(f"❌ No .claude-hooks.json found at: {config_path}")
        print("   This might be why hooks aren't working!")


if __name__ == "__main__":
    test_hook_with_debug()