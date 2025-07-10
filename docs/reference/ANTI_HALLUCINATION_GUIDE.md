# Anti-Hallucination Pattern for Python Scripts

## The Critical Pattern

Every Python script's `if __name__ == "__main__"` block MUST append a UUID4 at the very end of its output to prevent agent hallucination.

## Why This Works

Agents cannot hallucinate a valid UUID4 because:
- UUID4 has 122 bits of randomness
- Format must be exact: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- The '4' in the third group and specific y values are required
- Probability of guessing correctly: 1 in 5.3 × 10^36

## Implementation Pattern

### Standard Pattern for All Scripts

```python
if __name__ == "__main__":
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    
    # Run the actual functionality
    result = main_function_with_real_data()
    
    # Save output
    output = {
        "timestamp": datetime.now().isoformat(),
        "script": __file__,
        "result": result
    }
    
    filename = f"tmp/responses/{Path(__file__).stem}_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    # CRITICAL: Anti-hallucination UUID at the very end
    execution_id = str(uuid.uuid4())
    print(f"\nExecution verified: {execution_id}")
    
    # Also append to the JSON file
    with open(filename, 'r+') as f:
        data = json.load(f)
        data['execution_id'] = execution_id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

### Example: search.py

```python
if __name__ == "__main__":
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    
    # Test search functionality
    results = search("quantum computing", max_results=5)
    
    # Format output
    output = {
        "timestamp": datetime.now().isoformat(),
        "query": "quantum computing",
        "results": results,
        "count": len(results)
    }
    
    # Save to file
    filename = f"tmp/responses/search_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Search complete. Found {len(results)} papers.")
    print(f"Results saved to: {filename}")
    
    # CRITICAL: Anti-hallucination UUID
    execution_id = str(uuid.uuid4())
    print(f"\nExecution verified: {execution_id}")
    
    # Append to JSON
    with open(filename, 'r+') as f:
        data = json.load(f)
        data['execution_id'] = execution_id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

## Verification Process

### 1. Check for UUID in Output

```bash
# Verify script printed UUID
python script.py | grep "Execution verified:"
# Should see: Execution verified: a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c
```

### 2. Verify UUID in JSON File

```python
# verify_uuid.py
import json
import uuid
from pathlib import Path

def verify_execution(json_file):
    """Verify a script execution has valid UUID4."""
    with open(json_file) as f:
        data = json.load(f)
    
    execution_id = data.get('execution_id')
    if not execution_id:
        return False, "No execution_id found"
    
    try:
        # Parse as UUID4
        uuid_obj = uuid.UUID(execution_id, version=4)
        if str(uuid_obj) != execution_id:
            return False, "Invalid UUID4 format"
        return True, f"Valid execution: {execution_id}"
    except:
        return False, "Not a valid UUID4"

# Check all recent outputs
for output_file in Path("tmp/responses").glob("*_response_*.json"):
    valid, msg = verify_execution(output_file)
    print(f"{output_file.name}: {'✓' if valid else '✗'} {msg}")
```

### 3. Automated Verification in Assessment

```python
def assess_script_output(script_name, output_file):
    """Assess if script output is reasonable and verified."""
    with open(output_file) as f:
        data = json.load(f)
    
    # FIRST: Check for valid UUID4
    execution_id = data.get('execution_id')
    if not execution_id:
        return False, "FAIL: No execution_id (possible hallucination)"
    
    try:
        uuid_obj = uuid.UUID(execution_id, version=4)
        if str(uuid_obj) != execution_id:
            return False, "FAIL: Invalid UUID4 (possible hallucination)"
    except:
        return False, "FAIL: Malformed UUID4 (possible hallucination)"
    
    # THEN: Check reasonableness
    # ... rest of assessment ...
    
    return True, f"PASS: Verified execution {execution_id}"
```

## Common Mistakes to Avoid

### ❌ Wrong: UUID at Top Only
```python
if __name__ == "__main__":
    execution_id = str(uuid.uuid4())  # Too early!
    # ... rest of code ...
    # Agent could hallucinate everything after this
```

### ❌ Wrong: No UUID in JSON
```python
if __name__ == "__main__":
    # ... code ...
    print(f"Execution verified: {uuid.uuid4()}")
    # But didn't save to JSON file - can't verify later
```

### ✅ Right: UUID at Bottom + in JSON
```python
if __name__ == "__main__":
    # ... all execution ...
    
    # At the very end:
    execution_id = str(uuid.uuid4())
    print(f"\nExecution verified: {execution_id}")
    
    # And save to JSON
    with open(filename, 'r+') as f:
        data = json.load(f)
        data['execution_id'] = execution_id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

## Pre-Hook Pattern for Automation

Create a pre-hook that automatically adds UUID verification:

```python
# add_uuid_verification.py
import ast
import astor

def add_uuid_to_main_block(filename):
    """Add UUID verification to __main__ block if missing."""
    with open(filename) as f:
        tree = ast.parse(f.read())
    
    # Find if __name__ == "__main__" block
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if (isinstance(node.test, ast.Compare) and 
                isinstance(node.test.left, ast.Name) and
                node.test.left.id == "__name__"):
                
                # Check if UUID already added
                has_uuid = any(
                    "execution_id" in ast.dump(n) 
                    for n in node.body
                )
                
                if not has_uuid:
                    # Add UUID code at end
                    uuid_code = ast.parse('''
execution_id = str(uuid.uuid4())
print(f"\\nExecution verified: {execution_id}")
''')
                    node.body.extend(uuid_code.body)
    
    # Write back
    with open(filename, 'w') as f:
        f.write(astor.to_source(tree))
```

## Summary

The anti-hallucination pattern requires:
1. **UUID4 at the very END** of `__main__` execution
2. **Print to console** for immediate verification  
3. **Save to JSON** for later verification
4. **Check in assessment** before accepting output

This makes it impossible for agents to hallucinate successful execution because they cannot generate valid UUID4s.