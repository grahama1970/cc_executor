#!/usr/bin/env python3
"""
Post-execution hook that verifies UUID4 was included in outputs.
This ensures the Claude instance actually executed the code.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def post_execute(task_data: Dict[str, Any], execution_result: Dict[str, Any]):
    """
    Verify that the expected UUID appears in the execution outputs.
    This proves the task actually ran and wasn't hallucinated.
    """
    # Get expected UUID from state
    state_file = Path("/tmp/cc_executor_uuid_state.json")
    if not state_file.exists():
        return {
            "status": "error",
            "message": "No UUID state file found - pre-hook may not have run"
        }
    
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    expected_uuid = state['execution_uuid']
    
    # Check if UUID appears in execution output
    output_str = str(execution_result)
    uuid_found = expected_uuid in output_str
    
    # Check for JSON files in tmp/responses/
    responses_dir = Path("tmp/responses")
    json_files_checked = []
    uuid_at_end_count = 0
    
    if responses_dir.exists():
        for json_file in responses_dir.glob("*.json"):
            json_files_checked.append(json_file.name)
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Check if UUID is present
                if isinstance(data, dict) and 'execution_uuid' in data:
                    # Check if it's the LAST key
                    keys = list(data.keys())
                    if keys[-1] == 'execution_uuid' and data['execution_uuid'] == expected_uuid:
                        uuid_at_end_count += 1
                        print(f"✅ UUID correctly placed at END in {json_file.name}")
                    else:
                        print(f"⚠️  UUID present but not at END in {json_file.name}")
            except json.JSONDecodeError:
                print(f"⚠️  Could not parse {json_file.name}")
    
    # Prepare verification report
    verification_report = {
        "expected_uuid": expected_uuid,
        "uuid_found_in_output": uuid_found,
        "json_files_checked": len(json_files_checked),
        "json_files_with_uuid_at_end": uuid_at_end_count,
        "task_number": state.get('task_number', 'unknown')
    }
    
    # Determine overall status
    if uuid_found and uuid_at_end_count > 0:
        status = "success"
        message = f"✅ UUID {expected_uuid} verified in {uuid_at_end_count} file(s)"
    elif uuid_found:
        status = "warning"
        message = f"⚠️  UUID {expected_uuid} found but not properly positioned"
    else:
        status = "error"
        message = f"❌ UUID {expected_uuid} NOT FOUND - possible hallucination!"
    
    print(f"\n🔍 Post-hook UUID Verification:")
    print(f"   Expected: {expected_uuid}")
    print(f"   Found in output: {uuid_found}")
    print(f"   JSON files checked: {len(json_files_checked)}")
    print(f"   Files with UUID at end: {uuid_at_end_count}")
    print(f"   Status: {status}")
    
    return {
        "status": status,
        "message": message,
        "verification_report": verification_report
    }

if __name__ == "__main__":
    # Test the hook
    import uuid
    
    # Setup test state
    test_uuid = str(uuid.uuid4())
    os.environ['EXECUTION_UUID'] = test_uuid
    
    state = {
        "execution_uuid": test_uuid,
        "task_number": 1
    }
    with open("/tmp/cc_executor_uuid_state.json", 'w') as f:
        json.dump(state, f)
    
    # Create test output directory and file
    test_dir = Path("tmp/responses")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_output = {
        "results": "test data",
        "timestamp": "2025-07-04T12:00:00",
        "execution_uuid": test_uuid  # Correctly at end
    }
    
    with open(test_dir / "test_output.json", 'w') as f:
        json.dump(test_output, f, indent=2)
    
    # Test the hook
    test_result = {
        "output": f"Task completed. UUID: {test_uuid}"
    }
    
    result = post_execute({"task_number": 1}, test_result)
    print(f"\nHook result: {json.dumps(result, indent=2)}")
    
    # Cleanup
    (test_dir / "test_output.json").unlink()
    
    assert result['status'] == 'success'
    print("\n✅ Hook test passed!")