#!/usr/bin/env python3
"""
Debug utilities for testing individual hooks.
Provides functions to test each hook in isolation with sample data.
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOKS_DIR))

def set_env_context(context: Dict[str, Any]) -> Dict[str, str]:
    """Convert context dict to CLAUDE_* environment variables."""
    env = os.environ.copy()
    for key, value in context.items():
        env_key = f"CLAUDE_{key.upper()}"
        if isinstance(value, (dict, list)):
            env[env_key] = json.dumps(value)
        else:
            env[env_key] = str(value)
    return env

def run_hook(hook_name: str, context: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """Run a hook with given context and return results."""
    hook_path = HOOKS_DIR / f"{hook_name}.py"
    
    if not hook_path.exists():
        return {"error": f"Hook not found: {hook_path}"}
    
    env = set_env_context(context)
    
    try:
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Hook timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}

# Debug functions for each hook

def debug_setup_environment():
    """Debug setup_environment.py hook."""
    print("=== Testing setup_environment.py ===\n")
    
    test_cases = [
        {
            "name": "Python command",
            "context": {
                "command": "python script.py",
                "session_id": "test_123"
            }
        },
        {
            "name": "Pytest command",
            "context": {
                "command": "pytest tests/",
                "session_id": "test_456"
            }
        },
        {
            "name": "Non-Python command",
            "context": {
                "command": "ls -la",
                "session_id": "test_789"
            }
        },
        {
            "name": "Complex Python path",
            "context": {
                "command": "/usr/bin/python3 -m pip install requests",
                "session_id": "test_abc"
            }
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Command: {test['context']['command']}")
        
        result = run_hook("setup_environment", test['context'])
        
        if result.get('success'):
            # Try to get wrapped command from Redis
            import redis
            try:
                r = redis.Redis(decode_responses=True)
                wrapped = r.get(f"cmd:wrapped:{test['context']['session_id']}")
                print(f"Wrapped: {wrapped}")
            except:
                print("Redis not available - check stdout for wrapped command")
                if result['stdout']:
                    print(f"Output: {result['stdout'][:200]}")
        else:
            print(f"Error: {result.get('error', result.get('stderr'))}")

def debug_check_task_dependencies():
    """Debug check_task_dependencies.py hook."""
    print("\n=== Testing check_task_dependencies.py ===\n")
    
    test_contexts = [
        {
            "name": "Import detection",
            "context": {
                "context": "Task 1: Create a script that uses pandas\nimport pandas as pd\nimport numpy as np",
                "session_id": "dep_test_1"
            }
        },
        {
            "name": "Install detection", 
            "context": {
                "context": "First run: uv pip install fastapi websockets\nThen create the endpoint",
                "session_id": "dep_test_2"
            }
        }
    ]
    
    for test in test_contexts:
        print(f"\nTest: {test['name']}")
        result = run_hook("check_task_dependencies", test['context'])
        
        if result['success']:
            print("✓ Dependencies checked")
            # Check if packages were stored
            import redis
            try:
                r = redis.Redis(decode_responses=True)
                pkgs = r.get(f"hook:req_pkgs:{test['context']['session_id']}")
                if pkgs:
                    print(f"Required packages: {pkgs}")
            except:
                pass
        else:
            print(f"✗ Error: {result.get('stderr')}")

def debug_claude_instance_pre_check():
    """Debug claude_instance_pre_check.py hook."""
    print("\n=== Testing claude_instance_pre_check.py ===\n")
    
    context = {
        "command": "claude -p 'Create a test function'",
        "session_id": "claude_test_1"
    }
    
    print("Running comprehensive environment validation...")
    result = run_hook("claude_instance_pre_check", context, timeout=60)
    
    if result['success']:
        print("✓ All checks passed")
        if result['stdout']:
            # Parse validation results
            lines = result['stdout'].split('\n')
            for line in lines:
                if '✓' in line or '✗' in line:
                    print(f"  {line}")
    else:
        print(f"✗ Validation failed: {result.get('stderr')}")

def debug_analyze_task_complexity():
    """Debug analyze_task_complexity.py hook."""
    print("\n=== Testing analyze_task_complexity.py ===\n")
    
    test_commands = [
        "echo 'Hello World'",
        "python simple_script.py",
        "Create a FastAPI endpoint with WebSocket support for real-time notifications",
        "Implement async functions for concurrent API calls then create comprehensive tests"
    ]
    
    for cmd in test_commands:
        print(f"\nCommand: {cmd[:50]}...")
        
        # Create a temp file with the command
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(f"Task: {cmd}")
            temp_file = f.name
        
        context = {"file": temp_file}
        result = run_hook("analyze_task_complexity", context)
        
        if result['success'] and result['stdout']:
            try:
                data = json.loads(result['stdout'])
                print(f"Complexity: {data.get('complexity_score', 'N/A')}")
                print(f"Timeout: {data.get('estimated_timeout', 'N/A')}s")
            except:
                print("Could not parse complexity data")
        
        os.unlink(temp_file)

def debug_claude_response_validator():
    """Debug claude_response_validator.py hook."""
    print("\n=== Testing claude_response_validator.py ===\n")
    
    test_responses = [
        {
            "name": "Complete response",
            "output": """# Task Execution Report
## Status: completed

## Steps Completed:
1. Created function
   File: /tmp/test.py
   
## Verification:
Performed: Yes
Output: Function works correctly""",
            "exit_code": 0
        },
        {
            "name": "Hallucinated response",
            "output": "I've successfully created the function for you in utils.py",
            "exit_code": 0
        },
        {
            "name": "Acknowledged only",
            "output": "I'll create that function for you...",
            "exit_code": 0
        }
    ]
    
    for test in test_responses:
        print(f"\nTest: {test['name']}")
        
        context = {
            "command": "claude -p 'Create function'",
            "output": test['output'],
            "exit_code": test['exit_code'],
            "duration": "5.2",
            "session_id": f"val_test_{test['name']}"
        }
        
        result = run_hook("claude_response_validator", context)
        
        if result['stdout']:
            try:
                validation = json.loads(result['stdout'])
                print(f"Quality: {validation.get('quality', 'unknown')}")
                print(f"Hallucination score: {validation.get('hallucination_score', 'N/A')}")
            except:
                print("Could not parse validation result")

def debug_truncate_logs():
    """Debug truncate_logs.py hook."""
    print("\n=== Testing truncate_logs.py ===\n")
    
    test_outputs = [
        {
            "name": "Small output",
            "output": "Simple test output\nJust two lines"
        },
        {
            "name": "Large text",
            "output": "\n".join([f"Line {i}: " + "x" * 100 for i in range(200)])
        },
        {
            "name": "Binary data",
            "output": "data:image/png;base64," + "A" * 10000
        }
    ]
    
    for test in test_outputs:
        print(f"\nTest: {test['name']}")
        
        context = {
            "output": test['output'],
            "duration": "1.5",
            "session_id": "truncate_test"
        }
        
        result = run_hook("truncate_logs", context)
        
        if result['success'] and result['stdout']:
            try:
                data = json.loads(result['stdout'])
                print(f"Original: {data['original_size']} bytes")
                print(f"Truncated: {data['truncated_size']} bytes")
                reduction = (1 - data['truncated_size'] / data['original_size']) * 100
                print(f"Reduction: {reduction:.1f}%")
            except:
                print("Could not parse truncation data")

def debug_all_hooks():
    """Run all hook debug functions."""
    debug_setup_environment()
    debug_check_task_dependencies()
    debug_claude_instance_pre_check()
    debug_analyze_task_complexity()
    debug_claude_response_validator()
    debug_truncate_logs()

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Hook Debug Utilities Test ===\n")
        
        # Test environment context setting
        print("1. Testing environment context conversion:\n")
        
        test_context = {
            "command": "python test.py",
            "session_id": "test_123",
            "duration": 5.5,
            "complex_data": {"key": "value", "list": [1, 2, 3]}
        }
        
        env = set_env_context(test_context)
        print("Context converted to environment variables:")
        for key, value in env.items():
            if key.startswith("CLAUDE_"):
                print(f"  {key} = {value[:50]}...")
        
        # Test hook runner
        print("\n\n2. Testing hook runner mechanism:\n")
        
        # Create a simple test hook
        test_hook_content = '''#!/usr/bin/env python3
import os
import sys
import json

# Simple test hook
session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
command = os.environ.get('CLAUDE_COMMAND', 'unknown')

result = {
    "session_id": session_id,
    "command": command,
    "processed": True
}

print(json.dumps(result))
sys.exit(0)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', dir=HOOKS_DIR, delete=False) as f:
            f.write(test_hook_content)
            test_hook_name = Path(f.name).stem
        
        # Make it executable
        os.chmod(f.name, 0o755)
        
        print(f"Created test hook: {test_hook_name}")
        
        result = run_hook(test_hook_name, test_context)
        print(f"Exit code: {result['exit_code']}")
        print(f"Success: {result['success']}")
        
        if result['stdout']:
            try:
                data = json.loads(result['stdout'])
                print(f"Hook output: {json.dumps(data, indent=2)}")
            except:
                print(f"Raw output: {result['stdout']}")
        
        # Cleanup
        os.unlink(f.name)
        
        # Test specific hook debugging
        print("\n\n3. Testing specific hook debug functions:\n")
        
        print("Available debug functions:")
        debug_funcs = [name for name in globals() if name.startswith('debug_') and callable(globals()[name])]
        for func in debug_funcs:
            print(f"  - {func}")
        
        # Test one specific debug function
        print("\n\nRunning debug_setup_environment():")
        print("-" * 60)
        debug_setup_environment()
        
        # Demonstrate custom hook testing
        print("\n\n4. Custom hook testing example:\n")
        
        custom_context = {
            "command": "pytest tests/ -v",
            "session_id": "custom_test",
            "output": "5 passed in 0.5s",
            "exit_code": 0
        }
        
        print("Testing a hook with custom context:")
        print(f"Context: {json.dumps(custom_context, indent=2)}")
        
        # Would run the hook here
        # result = run_hook("some_hook", custom_context)
        
        print("\n=== Test Complete ===")
        
    elif len(sys.argv) > 1:
        hook_name = sys.argv[1]
        if hook_name == "all":
            debug_all_hooks()
        else:
            debug_func = f"debug_{hook_name}"
            if debug_func in globals():
                globals()[debug_func]()
            else:
                print(f"Unknown hook: {hook_name}")
                print("Available: setup_environment, check_task_dependencies, ")
                print("          claude_instance_pre_check, analyze_task_complexity,")
                print("          claude_response_validator, truncate_logs, all")
    else:
        print("Usage: python debug_hooks.py <hook_name|all>")
        print("\nExample: python debug_hooks.py setup_environment")
        print("         python debug_hooks.py all")
        print("         python debug_hooks.py --test")