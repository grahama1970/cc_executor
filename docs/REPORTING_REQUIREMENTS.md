# CC Executor Reporting Requirements

## Critical: JSON Mode is REQUIRED for Reporting

All `cc_execute` calls that need to be included in reports **MUST** use `json_mode=True`. This is not optional - it's a fundamental requirement for verification and anti-hallucination.

## Why JSON Mode is Required

### 1. **Anti-Hallucination Verification**
```python
# When json_mode=True, cc_execute automatically includes:
{
    "result": "...",
    "summary": "...",
    "execution_uuid": "a42ba88f-670a-45e6-bd75-b67efb50313c"  # MUST be last
}
```

The `execution_uuid` is generated BEFORE calling Claude and must be included in the response. This proves the execution actually happened.

### 2. **Structured Data Extraction**
Without JSON, we cannot reliably extract:
- Generated code
- Test results
- Function signatures
- Error messages
- Any structured output

### 3. **Report Generation**
Reports require structured data to:
- Display results in tables
- Extract specific fields
- Verify execution integrity
- Generate summaries

## How to Use JSON Mode

### Basic Example
```python
from cc_executor.client.cc_execute import cc_execute

# ❌ WRONG - No JSON structure
result = await cc_execute("Write a function to add numbers")

# ✅ CORRECT - JSON structure with schema
task = """Write a function to add numbers.
Return JSON: {
    "function_name": "add",
    "code": "def add(a, b): return a + b",
    "example": "add(2, 3) # Returns 5"
}"""
result = await cc_execute(task, json_mode=True)
```

### Complex Example with Schema
```python
task = """Analyze this code for security issues.
Return JSON with schema:
{
    "issues_found": [
        {"severity": "high|medium|low", "description": "...", "line": 0}
    ],
    "summary": "Overall security assessment",
    "recommendations": ["List of fixes"]
}"""

result = await cc_execute(task, json_mode=True)

# Extract structured data
from cc_executor.utils.json_utils import clean_json_string
parsed = clean_json_string(result["result"], return_dict=True)

# Now you can access fields directly
for issue in parsed.get("issues_found", []):
    print(f"{issue['severity']}: {issue['description']}")
```

## Report Generation

### From JSON Responses Only
```python
from cc_executor.reporting import generate_json_report

# Generate report from last 5 executions
# This will ONLY include executions that used json_mode=True
report_path = generate_json_report(last_n=5)
```

### Verification
```python
from cc_executor.reporting import check_hallucination

# Check with JSON requirement
verification = check_hallucination(last_n=5, require_json=True)

# Only JSON responses will pass verification
for v in verification['verifications']:
    if v.get('json_valid') and v.get('uuid_verified'):
        print(f"✅ Verified: {v['file']}")
    else:
        print(f"❌ Invalid: {v['file']} - Use json_mode=True")
```

## Best Practices

### 1. Always Define a Schema
```python
# Be explicit about what you want
schema = {
    "field1": "type and description",
    "field2": "type and description",
    # ... more fields
}

task = f"""Your task here.
Return JSON with this schema:
{json.dumps(schema, indent=2)}"""
```

### 2. Use clean_json_string for Parsing
```python
from cc_executor.utils.json_utils import clean_json_string

# This handles markdown code blocks and malformed JSON
parsed = clean_json_string(result["result"], return_dict=True)
```

### 3. Include Examples in Your Schema
```python
task = """Generate test data.
Return JSON like this example:
{
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
    ],
    "total": 2
}"""
```

## Common Mistakes

### ❌ Don't Do This
```python
# No structure - cannot generate reports
result = await cc_execute("Write some code")

# Trying to parse text as JSON
try:
    data = json.loads(result)  # Will fail
except:
    # Now what? No structured data!
```

### ✅ Do This Instead
```python
# Clear structure - perfect for reports
result = await cc_execute(
    "Write code. Return JSON: {'code': '...', 'language': 'python'}",
    json_mode=True
)

# Easy to extract
code = result["result"]["code"]
```

## Summary

1. **JSON mode is MANDATORY** for reporting - not optional
2. **Every execution** that needs reporting must use `json_mode=True`
3. **Define clear schemas** in your prompts
4. **Use clean_json_string** to parse responses
5. **Verify with UUIDs** to prevent hallucination

Without JSON mode, you cannot:
- Generate reports
- Verify executions
- Extract structured data
- Prove results are real

Make JSON mode your default!