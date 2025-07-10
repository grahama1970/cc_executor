# Usage Examples Report Template

## Purpose
This template ensures ALL usage functions that call `cc_execute` or agent calls MUST generate reports using the Python reporting engine. This is mandatory to prevent hallucination and ensure verifiable results.

## Requirements

### 1. MANDATORY JSON Mode
```python
# ❌ WRONG - No JSON mode, cannot generate report
result = await cc_execute("Write a function")

# ✅ CORRECT - JSON mode required for reporting
result = await cc_execute(task, json_mode=True)
```

### 2. Report Generation Pattern

Every usage function MUST follow this pattern:

```python
async def usage_function():
    """Your usage function that calls cc_execute."""
    
    # 1. Import the reporting engine
    from cc_executor.reporting import generate_json_report, check_hallucination
    from cc_executor.reporting.json_report_generator import JSONReportGenerator
    
    # 2. Execute your tasks with JSON mode
    executions = []
    
    task1 = """Your task here.
    Return JSON: {"field1": "value", "field2": "value"}"""
    result1 = await cc_execute(task1, json_mode=True)
    executions.append(("task1_name", result1))
    
    # 3. Verify executions are not hallucinated
    verification = check_hallucination(last_n=len(executions), require_json=True)
    
    # 4. Generate report using Python engine
    generator = JSONReportGenerator()
    report_path = generator.generate_latest_report(
        last_n=len(executions),
        output_path=Path("USAGE_REPORT.md")
    )
    
    return report_path
```

## Report Structure

The Python reporting engine generates reports with this structure:

```markdown
# [Report Title]

**Generated**: [Timestamp]
**Total Executions**: [Count]

## Verification Summary

All executions in this report:
- ✅ Have valid JSON responses
- ✅ Include execution UUID for verification
- ✅ Are saved as physical files on disk
- ✅ Can be independently verified

## Execution Details

### Execution 1

**Metadata**:
- File: `cc_execute_[session]_[timestamp].json`
- UUID: `[execution_uuid]`
- Duration: [time]s
- Exit Code: [code]

**Task**:
```
[The actual task/prompt sent]
```

**JSON Response**:
```json
{
    "result": "...",
    "files_created": [...],
    "summary": "...",
    "execution_uuid": "[uuid]"
}
```

**Result**:
[Parsed JSON content from result field]
```

## Example: Complete Usage Function with Reporting

```python
#!/usr/bin/env python3
"""
Example usage function with mandatory reporting.
"""

import asyncio
from pathlib import Path
from cc_executor.client.cc_execute import cc_execute
from cc_executor.reporting.json_report_generator import JSONReportGenerator
from cc_executor.reporting import check_hallucination


async def analyze_code_with_report():
    """Analyze code and generate mandatory report."""
    
    print("🔍 Analyzing code with JSON reporting...")
    
    # Define task with JSON schema
    task = """Analyze this Python code:
    ```python
    def process_data(items):
        return [x * 2 for x in items if x > 0]
    ```
    
    Return JSON with this schema:
    {
        "function_name": "process_data",
        "complexity": "O(n)",
        "issues": [
            {"type": "warning", "description": "No type hints"}
        ],
        "improved_code": "def process_data(items: List[int]) -> List[int]:",
        "test_cases": [
            {"input": "[1, -2, 3]", "expected": "[2, 6]"}
        ]
    }"""
    
    # Execute with JSON mode (MANDATORY)
    result = await cc_execute(task, json_mode=True)
    
    # Verify execution
    verification = check_hallucination(last_n=1, require_json=True)
    
    if verification['status'] != 'success':
        raise Exception("Execution verification failed!")
    
    # Generate report (MANDATORY)
    generator = JSONReportGenerator()
    report_path = generator.generate_latest_report(
        last_n=1,
        output_path=Path("code_analysis_report.md")
    )
    
    print(f"✅ Report generated: {report_path}")
    
    # Extract and use the results
    from cc_executor.utils.json_utils import clean_json_string
    parsed = clean_json_string(result["result"], return_dict=True)
    
    # Save improved code
    if "improved_code" in parsed:
        with open("improved_function.py", "w") as f:
            f.write(parsed["improved_code"])
    
    return report_path


if __name__ == "__main__":
    # Run and generate report
    report = asyncio.run(analyze_code_with_report())
    print(f"📄 View report: {report}")
```

## Enforcement Rules

### 1. No JSON Mode = No Report
If `json_mode=False`, the reporting engine will reject the execution:
```python
# This will fail report generation
result = await cc_execute("task", json_mode=False)
generator.generate_latest_report()  # ERROR: No JSON responses found
```

### 2. UUID Verification Required
Every JSON response must include the execution UUID as the last field:
```json
{
    "result": "...",
    "summary": "...",
    "execution_uuid": "must-be-last-field"
}
```

### 3. Physical File Verification
The reporting engine checks for physical response files:
```python
# Files saved to: src/cc_executor/client/tmp/responses/
# Format: cc_execute_[session]_[timestamp].json
```

## Common Patterns

### Pattern 1: Multiple Tasks Report
```python
async def multi_task_with_report():
    tasks = []
    
    # Task 1
    result1 = await cc_execute("Task 1 with JSON schema", json_mode=True)
    tasks.append(("task1", result1))
    
    # Task 2
    result2 = await cc_execute("Task 2 with JSON schema", json_mode=True)
    tasks.append(("task2", result2))
    
    # Generate combined report
    generator = JSONReportGenerator()
    report = generator.generate_latest_report(last_n=len(tasks))
    return report
```

### Pattern 2: Concurrent Tasks Report
```python
async def concurrent_with_report():
    from asyncio import gather
    
    tasks = [
        cc_execute("Task 1: Return JSON: {...}", json_mode=True),
        cc_execute("Task 2: Return JSON: {...}", json_mode=True),
        cc_execute("Task 3: Return JSON: {...}", json_mode=True)
    ]
    
    results = await gather(*tasks)
    
    # All executions included in report
    generator = JSONReportGenerator()
    report = generator.generate_latest_report(last_n=len(results))
    return report
```

### Pattern 3: Agent Call Report
```python
async def agent_call_with_report():
    # Agent calls should also request JSON responses
    task = """Research Python async patterns.
    Return findings as JSON:
    {
        "patterns": ["pattern1", "pattern2"],
        "best_practices": ["practice1", "practice2"],
        "examples": {"pattern1": "code example"}
    }"""
    
    result = await cc_execute(task, json_mode=True, agent=True)
    
    # Generate report for agent execution
    generator = JSONReportGenerator()
    report = generator.generate_latest_report(last_n=1)
    return report
```

## Checklist for Usage Functions

- [ ] Import reporting modules at the top
- [ ] Use `json_mode=True` for ALL cc_execute calls
- [ ] Define clear JSON schemas in prompts
- [ ] Call `check_hallucination()` to verify
- [ ] Generate report with `JSONReportGenerator`
- [ ] Save report to meaningful filename
- [ ] Handle report generation errors
- [ ] Return or display report path

## Summary

**EVERY** usage function that calls `cc_execute` or agent calls MUST:

1. Use `json_mode=True`
2. Define JSON schemas in prompts
3. Generate reports using the Python reporting engine
4. Verify executions are not hallucinated
5. Save reports with descriptive filenames

This is not optional - it's required for verification and anti-hallucination.