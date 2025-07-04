# UUID Verification Hook Documentation

## Overview

The UUID verification hook is a critical anti-hallucination measure that ensures all prompt executions are real and verifiable. It consists of pre-execution UUID generation and post-execution verification.

## Implementation

### Pre-Execution Hook: `generate_execution_uuid.py`

```python
#!/usr/bin/env python3
"""
Pre-execution hook that generates a UUID4 for anti-hallucination verification.
This UUID must appear at the END of all JSON outputs.
"""

import uuid
import os
import json
from datetime import datetime
from pathlib import Path

def pre_execute(task_data):
    """Generate and inject UUID4 into task environment"""
    execution_uuid = str(uuid.uuid4())
    
    # Set in environment for task to access
    os.environ['EXECUTION_UUID'] = execution_uuid
    
    # Log for transcript verification
    print(f"🔐 Pre-hook: Generated execution UUID: {execution_uuid}")
    
    # Save to hook state for post-verification
    state_file = Path("/tmp/cc_executor_hook_state.json")
    state = {
        "execution_uuid": execution_uuid,
        "task_id": task_data.get("id", "unknown"),
        "timestamp": datetime.now().isoformat()
    }
    
    with open(state_file, 'w') as f:
        json.dump(state, f)
    
    return {
        "status": "success",
        "execution_uuid": execution_uuid,
        "message": f"UUID {execution_uuid} generated for verification"
    }

if __name__ == "__main__":
    # Test the hook
    test_result = pre_execute({"id": "test_task"})
    print(f"✅ Pre-hook test result: {test_result}")
    assert os.environ.get('EXECUTION_UUID') == test_result['execution_uuid']
    print("✅ UUID correctly set in environment")
```

### Post-Execution Hook: `verify_execution_uuid.py`

```python
#!/usr/bin/env python3
"""
Post-execution hook that verifies UUID4 appears in outputs.
Ensures execution actually occurred and wasn't hallucinated.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def post_execute(task_data: Dict[str, Any], execution_result: Dict[str, Any]):
    """Verify UUID appears in execution outputs"""
    # Get expected UUID from state
    state_file = Path("/tmp/cc_executor_hook_state.json")
    if not state_file.exists():
        return {
            "status": "error",
            "message": "No UUID state file found - pre-hook may not have run"
        }
    
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    expected_uuid = state['execution_uuid']
    
    # Check environment matches
    env_uuid = os.environ.get('EXECUTION_UUID')
    if env_uuid != expected_uuid:
        return {
            "status": "error",
            "message": f"Environment UUID mismatch: {env_uuid} != {expected_uuid}"
        }
    
    # Check execution result contains UUID
    result_str = json.dumps(execution_result)
    if expected_uuid not in result_str:
        return {
            "status": "error", 
            "message": f"UUID {expected_uuid} not found in execution result!"
        }
    
    # For JSON outputs, verify UUID is at END
    if isinstance(execution_result, dict):
        keys = list(execution_result.keys())
        if 'execution_uuid' in execution_result:
            if keys[-1] != 'execution_uuid':
                return {
                    "status": "warning",
                    "message": f"UUID present but not at end. Last key: {keys[-1]}"
                }
    
    # Check output files if specified
    output_files = execution_result.get('output_files', [])
    for file_path in output_files:
        if Path(file_path).exists() and file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, dict) and 'execution_uuid' in data:
                        if list(data.keys())[-1] != 'execution_uuid':
                            print(f"⚠️  UUID not at end in {file_path}")
                except json.JSONDecodeError:
                    print(f"⚠️  Could not parse JSON from {file_path}")
    
    return {
        "status": "success",
        "execution_uuid": expected_uuid,
        "message": f"✅ UUID {expected_uuid} verified in outputs"
    }

if __name__ == "__main__":
    # Test the hook
    # First simulate pre-hook
    test_uuid = "test-uuid-1234"
    os.environ['EXECUTION_UUID'] = test_uuid
    state = {"execution_uuid": test_uuid}
    with open("/tmp/cc_executor_hook_state.json", 'w') as f:
        json.dump(state, f)
    
    # Test successful verification
    test_result = {
        "data": "test",
        "execution_uuid": test_uuid
    }
    result = post_execute({}, test_result)
    print(f"✅ Post-hook test result: {result}")
    assert result['status'] == 'success'
    
    # Test failed verification
    bad_result = {"data": "test", "no_uuid": "here"}
    result = post_execute({}, bad_result)
    assert result['status'] == 'error'
    print("✅ Correctly detected missing UUID")
```

## Hook Configuration

Add to `.claude-hooks.json`:

```json
{
  "pre_execute": [
    {
      "name": "UUID Generation",
      "script": "hooks/generate_execution_uuid.py",
      "description": "Generates UUID4 for anti-hallucination verification"
    }
  ],
  "post_execute": [
    {
      "name": "UUID Verification", 
      "script": "hooks/verify_execution_uuid.py",
      "description": "Verifies UUID4 appears in execution outputs"
    }
  ]
}
```

## How It Works - Automatic and Transparent

### The Magic of Hooks

The UUID4 verification is **completely automatic**. Task authors don't need to:
- Know about UUID4s
- Modify their task descriptions  
- Include special instructions
- Change their code

The hooks handle everything transparently!

### What Actually Happens

1. **User writes normal task**: "Create a FastAPI TODO app"
2. **Pre-hook intercepts** and modifies the prompt to include:
   ```
   IMPORTANT SYSTEM REQUIREMENT (automatically added):
   - Import uuid and generate UUID4
   - Include it as last key in JSON outputs
   - This UUID (abc-123...) will be verified
   ```
3. **Claude sees modified prompt** with UUID4 requirements
4. **Post-hook verifies** the UUID appears in outputs

### In Assessment Reports

```markdown
## Anti-Hallucination Verification

**Report UUID**: `a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c`

This UUID was generated by pre-execution hook and verified by post-execution hook.

### Verification Commands
```bash
# Check hook state
cat /tmp/cc_executor_hook_state.json

# Verify in output files  
grep "a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c" output_*.json

# Check transcripts
rg "a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c" ~/.claude/projects/*/\*.jsonl
```
```

## Benefits

1. **Proof of Execution**: UUID in transcripts proves code actually ran
2. **Tamper Detection**: UUID at END of JSON prevents partial fabrication  
3. **Cross-Verification**: Same UUID in multiple locations for validation
4. **Audit Trail**: UUIDs can be traced through entire execution flow

## Testing

```bash
# Test pre-hook
python hooks/generate_execution_uuid.py

# Test post-hook
python hooks/verify_execution_uuid.py

# Full integration test
cc-execute --task "test_task" --hooks .claude-hooks.json
```

## Troubleshooting

### UUID Not Found
- Check pre-hook ran successfully
- Verify task reads EXECUTION_UUID environment variable
- Ensure UUID included in outputs

### UUID Not at End
- Review output generation code
- Make sure UUID is added as final step
- Check no modifications after UUID addition

### Environment Mismatch
- Verify hooks run in same environment as task
- Check for subprocess isolation issues
- Ensure environment variables are passed through

## Summary

The UUID verification hook provides a simple but effective anti-hallucination measure. By generating a cryptographically unique identifier before execution and verifying its presence (at the END) after execution, we can ensure that:

1. The execution actually occurred
2. The outputs are genuine
3. The results haven't been fabricated
4. There's an audit trail for verification

This pattern should be used for all prompts that claim to execute code or generate reports.