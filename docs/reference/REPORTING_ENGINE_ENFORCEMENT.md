# Reporting Engine Enforcement Guidelines

## Mandatory Reporting Policy

**CRITICAL**: Every function that uses `cc_execute` or agent calls MUST generate a report using the Python reporting engine. This is enforced to prevent hallucination and ensure all executions are verifiable.

## Quick Reference

```python
# MANDATORY imports for any usage function
from cc_executor.client.cc_execute import cc_execute
from cc_executor.reporting.json_report_generator import JSONReportGenerator
from cc_executor.reporting import check_hallucination

# MANDATORY pattern
async def any_usage_function():
    # 1. Execute with JSON mode
    result = await cc_execute(task, json_mode=True)  # REQUIRED
    
    # 2. Verify execution
    check_hallucination(last_n=1, require_json=True)  # REQUIRED
    
    # 3. Generate report
    generator = JSONReportGenerator()
    report = generator.generate_latest_report()  # REQUIRED
```

## Enforcement Mechanisms

### 1. Code Review Checklist
- [ ] Does the function use `cc_execute`?
- [ ] Is `json_mode=True` set?
- [ ] Is a JSON schema defined in the prompt?
- [ ] Is `JSONReportGenerator` used?
- [ ] Is the report saved/returned?

### 2. Automated Validation
```python
def validate_usage_function(func_code: str) -> bool:
    """Validate a usage function follows reporting requirements."""
    checks = [
        "cc_execute" in func_code,
        "json_mode=True" in func_code,
        "JSONReportGenerator" in func_code,
        "generate_latest_report" in func_code or "generate_report" in func_code
    ]
    return all(checks)
```

### 3. Runtime Enforcement
```python
# Wrapper to enforce reporting
def enforce_reporting(func):
    async def wrapper(*args, **kwargs):
        # Track cc_execute calls
        initial_count = get_execution_count()
        
        # Run the function
        result = await func(*args, **kwargs)
        
        # Check if executions happened
        final_count = get_execution_count()
        if final_count > initial_count:
            # Verify report was generated
            if not report_exists_for_executions(initial_count, final_count):
                raise Exception(f"{func.__name__} used cc_execute but didn't generate a report!")
        
        return result
    return wrapper
```

## Examples of Enforcement

### ❌ WRONG - No Report Generated
```python
async def bad_usage_function():
    # This violates the policy!
    result = await cc_execute("Write code", json_mode=True)
    return result  # NO REPORT GENERATED!
```

### ✅ CORRECT - Report Generated
```python
async def good_usage_function():
    # Execute with JSON
    result = await cc_execute(
        "Write code. Return JSON: {'code': '...'}",
        json_mode=True
    )
    
    # Generate mandatory report
    generator = JSONReportGenerator()
    report = generator.generate_latest_report()
    
    return result, report  # Both result AND report
```

## Report Storage Convention

Reports should be saved with descriptive names:

```python
# Pattern: [function_name]_report_[timestamp].md
output_path = Path(f"{func.__name__}_report_{datetime.now():%Y%m%d_%H%M%S}.md")

generator = JSONReportGenerator()
report = generator.generate_latest_report(output_path=output_path)
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Validate Usage Functions
  run: |
    python -m cc_executor.validation.check_usage_functions
    # Ensures all usage functions generate reports
```

### Pre-commit Hook
```python
#!/usr/bin/env python3
# .git/hooks/pre-commit
import subprocess
import sys

# Check for usage functions without reports
result = subprocess.run([
    "python", "-m", "cc_executor.validation.check_usage_functions"
], capture_output=True)

if result.returncode != 0:
    print("ERROR: Usage functions must generate reports!")
    print(result.stdout.decode())
    sys.exit(1)
```

## Summary

The Python reporting engine is MANDATORY for:
- All `cc_execute` calls
- All agent calls
- Any function that generates code/content via AI

This ensures:
- No hallucinated results
- Full execution traceability
- Verifiable outputs with UUIDs
- Structured data for analysis

**Remember**: If you use `cc_execute`, you MUST generate a report!