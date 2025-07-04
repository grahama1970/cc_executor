#!/usr/bin/env python3
"""
Pre-execution hook that automatically injects UUID4 requirements into Claude prompts.
This ensures EVERY task execution includes anti-hallucination verification.
"""

import uuid
import os
import json
from datetime import datetime
from pathlib import Path

def pre_execute(task_data):
    """
    Automatically modify the Claude prompt to include UUID4 generation.
    This happens transparently - task authors don't need to know about it.
    """
    # Generate UUID for this execution
    execution_uuid = str(uuid.uuid4())
    
    # Set in environment for post-hook verification
    os.environ['EXECUTION_UUID'] = execution_uuid
    
    # Get the original task description
    original_task = task_data.get("task", "")
    
    # Inject UUID4 requirements into the prompt
    modified_task = f"""{original_task}

IMPORTANT SYSTEM REQUIREMENT (automatically added by hook):
1. Import uuid at the start of your implementation
2. Generate execution_uuid = str(uuid.uuid4()) immediately
3. Print: "🔐 Execution UUID: {{execution_uuid}}"
4. Include this UUID as the LAST key in any JSON output you create
5. Save any JSON results to tmp/responses/ with the UUID included

Example JSON structure (UUID must be last):
{{
    "results": "your actual results",
    "timestamp": "{datetime.now().isoformat()}",
    "execution_uuid": "{{the uuid you generated}}"
}}

This UUID ({execution_uuid}) will be verified after execution.
"""
    
    # Update the task data with modified prompt
    task_data["task"] = modified_task
    
    # Log what we're doing
    print(f"🔐 Pre-hook: Injected UUID4 requirement into prompt")
    print(f"   Expected UUID: {execution_uuid}")
    
    # Save hook state for post-verification
    state_file = Path("/tmp/cc_executor_uuid_state.json")
    state = {
        "execution_uuid": execution_uuid,
        "task_number": task_data.get("task_number", "unknown"),
        "original_task_length": len(original_task),
        "modified_task_length": len(modified_task),
        "timestamp": datetime.now().isoformat()
    }
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    return {
        "status": "success",
        "execution_uuid": execution_uuid,
        "message": f"UUID {execution_uuid} injected into prompt"
    }

if __name__ == "__main__":
    # Test the hook
    test_task = {
        "task": "Create a simple hello world script",
        "task_number": 1
    }
    
    print("Testing pre-execution hook...")
    print(f"Original task: {test_task['task']}")
    
    result = pre_execute(test_task)
    
    print(f"\nModified task preview (first 500 chars):")
    print(test_task['task'][:500] + "...")
    print(f"\nHook result: {result}")
    
    # Verify environment variable was set
    assert os.environ.get('EXECUTION_UUID') == result['execution_uuid']
    print("✅ Hook test passed!")