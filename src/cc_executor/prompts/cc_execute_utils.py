#!/usr/bin/env python3
"""
CC_Execute utilities - Helper functions for spawning fresh Claude instances.

This module provides the implementation for executing tasks through the
WebSocket handler, ensuring each task gets a fresh Claude instance with
full 200K context.

Now includes automatic hook support for:
- Pre-execution hooks (e.g., UUID4 injection, environment setup)
- Post-execution hooks (e.g., UUID4 verification, result validation)
"""
import subprocess
import sys
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Try to import config, but use defaults if not available
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config import DEFAULT_EXECUTION_TIMEOUT
except ImportError:
    DEFAULT_EXECUTION_TIMEOUT = 600  # 10 minutes fallback

def apply_pre_hooks(task: str, hooks_config: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """
    Apply pre-execution hooks to modify the task.
    
    Currently implements automatic UUID4 injection for anti-hallucination.
    
    Args:
        task: Original task description
        hooks_config: Optional hooks configuration
        
    Returns:
        Tuple of (modified_task, execution_uuid)
    """
    # Generate UUID4 for this execution
    execution_uuid = str(uuid.uuid4())
    
    # Inject UUID4 requirements into the task
    # This happens automatically - task authors don't need to know about it!
    uuid_injection = f"""

IMPORTANT SYSTEM REQUIREMENT (automatically added by hook):
1. Import uuid at the start of your implementation if generating any JSON
2. Use this exact UUID in your output: {execution_uuid}
3. Print this at the start: "🔐 Execution UUID: {execution_uuid}"
4. Include "execution_uuid": "{execution_uuid}" as the LAST key in any JSON output you create
5. This is for anti-hallucination verification - the UUID proves execution actually occurred
"""
    
    # Modified task with UUID4 requirements
    modified_task = task + uuid_injection
    
    # Store UUID in environment for post-hook verification
    os.environ['EXECUTION_UUID'] = execution_uuid
    
    # Save hook state for post-verification
    state_file = Path("/tmp/cc_executor_hook_state.json")
    state = {
        "execution_uuid": execution_uuid,
        "task_original": task,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(state_file, 'w') as f:
        json.dump(state, f)
    
    print(f"🔐 Pre-hook: Generated execution UUID: {execution_uuid}")
    
    return modified_task, execution_uuid


def verify_post_hooks(result: Dict[str, Any], execution_uuid: str) -> Dict[str, Any]:
    """
    Apply post-execution hooks to verify the result.
    
    Currently implements UUID4 verification for anti-hallucination.
    
    Args:
        result: Execution result from websocket_handler
        execution_uuid: The UUID that should appear in output
        
    Returns:
        Enhanced result with hook verification status
    """
    verification_status = {
        "uuid_present": False,
        "uuid_at_end": False,
        "verification_passed": False,
        "messages": []
    }
    
    # Check if UUID appears in output
    output_text = '\n'.join(result.get('output_lines', []))
    
    if execution_uuid in output_text:
        verification_status["uuid_present"] = True
        verification_status["messages"].append(f"✅ UUID {execution_uuid} found in output")
        
        # Try to find JSON outputs and verify UUID is at end
        try:
            # Look for JSON blocks in output
            import re
            json_pattern = r'\{[^{}]*\}'
            json_matches = re.findall(json_pattern, output_text, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and 'execution_uuid' in data:
                        keys = list(data.keys())
                        if keys[-1] == 'execution_uuid':
                            verification_status["uuid_at_end"] = True
                            verification_status["messages"].append("✅ UUID found at END of JSON")
                        else:
                            verification_status["messages"].append(f"⚠️  UUID present but not at end. Last key: {keys[-1]}")
                except:
                    pass
        except Exception as e:
            verification_status["messages"].append(f"Could not parse JSON: {e}")
    else:
        verification_status["messages"].append(f"❌ UUID {execution_uuid} NOT found in output - possible hallucination!")
    
    # Overall verification status
    verification_status["verification_passed"] = verification_status["uuid_present"]
    
    # Add verification to result
    result["hook_verification"] = verification_status
    
    # Print verification summary
    print(f"\n🔍 Post-hook verification:")
    for msg in verification_status["messages"]:
        print(f"  {msg}")
    
    return result


def execute_task_via_websocket(
    task: str,
    timeout: Optional[int] = None,
    tools: Optional[List[str]] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Execute a task by calling websocket_handler.py to spawn a fresh Claude instance.
    
    Hooks are ALWAYS applied for anti-hallucination verification:
    1. Apply pre-hooks (UUID4 injection) to modify the task
    2. Build the Claude command with appropriate tools
    3. Call websocket_handler.py with the command
    4. Apply post-hooks (UUID4 verification) to verify results
    5. Return the enhanced results with verification status
    
    Args:
        task: The task description for Claude to execute
        timeout: Optional timeout in seconds (default: 600)
        tools: Optional list of tools to enable (default: Read, Write, Edit, Bash)
        max_retries: Maximum number of retry attempts for transient failures (default: 3)
    
    Returns:
        Dict containing success status, exit code, output lines, hook verification, and any errors
    """
    
    # ALWAYS apply pre-hooks for UUID4 anti-hallucination
    task, execution_uuid = apply_pre_hooks(task)
    print(f"[CC_EXECUTE] Task modified with UUID4 requirements")
    
    # Build the Claude command
    if tools is None:
        tools = ["Read", "Write", "Edit", "Bash"]  # Default tools
    
    # Use configured timeout if not specified
    if timeout is None:
        timeout = DEFAULT_EXECUTION_TIMEOUT
    
    # Build command following websocket_handler.py patterns
    # The prompt must come immediately after -p flag
    base_cmd = f'claude -p "{task}" --output-format stream-json --verbose'
    
    # Add tools if specified
    if tools:
        tools_str = " ".join(tools)
        base_cmd += f' --allowedTools {tools_str}'
    
    claude_cmd = base_cmd
    
    # Get paths
    current_dir = Path(__file__).parent
    websocket_handler_path = current_dir.parent / "core" / "websocket_handler.py"
    
    # Build the subprocess command
    cmd_args = [
        sys.executable,
        str(websocket_handler_path),
        "--execute", claude_cmd
    ]
    
    # Add timeout if specified
    if timeout:
        cmd_args.extend(["--timeout", str(timeout)])
    
    # Add no-server flag to prevent WebSocket server from starting
    cmd_args.append("--no-server")
    
    print(f"[CC_EXECUTE] Calling websocket_handler.py...")
    print(f"[CC_EXECUTE] Command: {claude_cmd[:100]}...")
    
    # Execute via subprocess with retry logic
    last_error = None
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse output
            output_lines = result.stdout.strip().split('\n') if result.stdout else []
            stderr = result.stderr if result.stderr else None
            
            # Check for transient failures and rate limits
            is_transient = False
            is_rate_limited = False
            retry_after = None
            
            if result.returncode != 0 and stderr:
                # Check for known transient errors
                transient_patterns = [
                    "Connection refused",
                    "Connection reset",
                    "Timeout expired",
                    "504 Gateway Timeout",
                    "502 Bad Gateway",
                    "ECONNRESET"
                ]
                is_transient = any(pattern in stderr for pattern in transient_patterns)
                
                # Check for rate limiting (429 Too Many Requests)
                if "429" in stderr or "Too Many Requests" in stderr or "rate limit" in stderr.lower():
                    is_rate_limited = True
                    is_transient = True
                    
                    # Try to extract Retry-After header value
                    import re
                    retry_match = re.search(r'Retry-After[:"]\s*(\d+)', stderr, re.IGNORECASE)
                    if retry_match:
                        retry_after = int(retry_match.group(1))
                    else:
                        # Default to 60 seconds if no Retry-After header
                        retry_after = 60
            
            # If successful or non-transient error, prepare result
            if result.returncode == 0 or not is_transient:
                final_result = {
                    'success': result.returncode == 0,
                    'exit_code': result.returncode,
                    'output_lines': output_lines,
                    'stderr': stderr,
                    'task': task,
                    'attempts': attempt + 1
                }
                
                # ALWAYS apply post-hooks for verification
                if execution_uuid and result.returncode == 0:
                    final_result = verify_post_hooks(final_result, execution_uuid)
                
                return final_result
            
            # If transient error and not last attempt, retry with appropriate backoff
            if attempt < max_retries - 1:
                if is_rate_limited and retry_after:
                    wait_time = retry_after
                    print(f"[CC_EXECUTE] Rate limit detected (429), waiting {wait_time}s as requested (attempt {attempt + 2}/{max_retries})...")
                else:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[CC_EXECUTE] Transient error detected, retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            
            last_error = stderr
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[CC_EXECUTE] Exception occurred, retrying in {wait_time}s (attempt {attempt + 2}/{max_retries}): {e}")
                time.sleep(wait_time)
            continue
    
    # All retries exhausted
    final_result = {
        'success': False,
        'exit_code': -1,
        'output_lines': [],
        'stderr': f"Failed after {max_retries} attempts. Last error: {last_error}",
        'task': task,
        'attempts': max_retries
    }
    
    # Still apply post-hooks even on failure to check for partial output
    if execution_uuid:
        final_result = verify_post_hooks(final_result, execution_uuid)
    
    return final_result


# Usage function for testing
if __name__ == "__main__":
    import asyncio
    
    def test_execution():
        """Test the execution function with automatic hook support."""
        print("=== CC_Execute Utils Test (Hooks Always Enabled) ===")
        
        # Test 1: Simple JSON generation task
        print("\n1. Testing automatic UUID4 hook injection:")
        test_task = "Create a simple JSON response with a greeting message and current timestamp"
        
        print(f"Original task: {test_task}")
        print("Executing with automatic hooks...")
        
        result = execute_task_via_websocket(
            task=test_task,
            timeout=60,
            tools=[]  # No tools needed
        )
        
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output lines: {len(result['output_lines'])}")
        
        # Check hook verification
        if 'hook_verification' in result:
            print("\nHook verification results:")
            for key, value in result['hook_verification'].items():
                if key != 'messages':
                    print(f"  {key}: {value}")
            
            # Show verification messages
            if result['hook_verification']['messages']:
                print("\nVerification details:")
                for msg in result['hook_verification']['messages']:
                    print(f"  {msg}")
        
        # Test 2: Demonstrate pre-hook modification
        print("\n\n2. Demonstrating automatic pre-hook task modification:")
        original_task = "Calculate the sum of 5 and 7"
        modified_task, test_uuid = apply_pre_hooks(original_task)
        
        print(f"Original task: '{original_task}'")
        print(f"UUID injected: {test_uuid}")
        print(f"\nTask expansion: {len(original_task)} → {len(modified_task)} chars")
        print("\nInjected requirements preview:")
        injection = modified_task[len(original_task):]
        print(injection[:200] + "..." if len(injection) > 200 else injection)
        
        # Save results for inspection
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(__file__).parent / "tmp" / "hook_test_responses"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save response with full details
        response_file = output_dir / f"hook_test_{timestamp}.json"
        with open(response_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Full response saved to: {response_file}")
        
        # Check if verification passed
        verification_passed = result.get('hook_verification', {}).get('verification_passed', False)
        
        if verification_passed:
            print("\n✅ UUID4 anti-hallucination verification PASSED!")
        else:
            print("\n❌ UUID4 verification failed - possible hallucination detected")
        
        return result['success'] and verification_passed
    
    # Run the test
    success = test_execution()
    exit(0 if success else 1)