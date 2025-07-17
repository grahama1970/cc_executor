# Complete Gemini Integration Workflow

## Overview

This document describes the complete workflow for sending issues to Gemini Flash and processing the responses, all without overwhelming Claude Code's context window.

## Full Workflow

### Step 1: Create Issue Report

When Claude Code encounters a complex issue, create a comprehensive issue report:

```python
# Generate issue report programmatically
issue_content = f"""# Issue Report for Gemini

## Context
- **Project**: {project_path}
- **Task**: {task_description}
- **Status**: BLOCKED

## Files Analyzed
{file_list}

## Issue Details

### Error Type: {error_type}

**Error Message**:
```
{error_traceback}
```

**Location**: {file}:{line}

## Code Context

<!-- CODE_CONTEXT_START: {failing_file} -->
```python
{code_context_with_line_numbers}
```
<!-- CODE_CONTEXT_END: {failing_file} -->

## Required Solution Format

Please provide ALL fixes using this exact format:

<!-- CODE_FILE_START: path/to/file.py -->
```python
# Complete file content - no ellipsis or placeholders
```
<!-- CODE_FILE_END: path/to/file.py -->

## Test Database Pattern Required

All database operations MUST use test database isolation:
```python
from utils.test_db_utils import setup_test_database, teardown_test_database
```
"""

# Save issue report
issue_file = Path("tmp/issues/gemini_issue_001.md")
issue_file.parent.mkdir(parents=True, exist_ok=True)
issue_file.write_text(issue_content)
```

### Step 2: Send to Gemini

Use the SendToGemini tool to send the issue without loading it into context:

```json
{
  "tool": "SendToGemini",
  "inputs": {
    "issue_file": "tmp/issues/gemini_issue_001.md",
    "temperature": 0.1,
    "max_tokens": 16000
  }
}
```

Result:
```json
{
  "success": true,
  "issue_file": "tmp/issues/gemini_issue_001.md",
  "output_file": "tmp/gemini_response_20250714_123456.md",
  "response_length": 12543,
  "model": "vertex_ai/gemini-1.5-flash",
  "usage": {
    "prompt_tokens": 3456,
    "completion_tokens": 2890,
    "total_tokens": 6346
  },
  "cost": {
    "total_cost": 0.0022,
    "currency": "USD",
    "method": "litellm_completion_cost"
  },
  "has_code_markers": true,
  "code_files_count": 3,
  "code_files": [
    "src/agent_log_manager.py",
    "src/arango_log_sink.py",
    "src/utils/test_db_utils.py"
  ]
}
```

### Step 3: Extract Code from Response

Use the ExtractGeminiCode tool to extract files:

```json
{
  "tool": "ExtractGeminiCode",
  "inputs": {
    "markdown_file": "tmp/gemini_response_20250714_123456.md"
  }
}
```

Result:
```json
{
  "success": true,
  "output_directory": "tmp/gemini_extracted_20250714_124532",
  "files": [
    {"path": "src/agent_log_manager.py", "lines": 250},
    {"path": "src/arango_log_sink.py", "lines": 180},
    {"path": "src/utils/test_db_utils.py", "lines": 90}
  ],
  "context_file": "tmp/gemini_extracted_20250714_124532/EXTRACTION_CONTEXT.md"
}
```

### Step 4: Analyze and Apply Changes

```bash
# Review extracted files
cd tmp/gemini_extracted_20250714_124532
ls -la src/

# Compare with existing
diff -u ../../src/agent_log_manager.py src/agent_log_manager.py

# Test syntax
python -m py_compile src/agent_log_manager.py

# Apply changes selectively
cp src/agent_log_manager.py ../../src/agent_log_manager.py

# Run tests
python ../../src/agent_log_manager.py
```

## Cost Tracking

The Gemini response includes a cost summary section:

```markdown
<!-- GEMINI_API_COST_START -->
## API Call Cost Summary

- **Model**: vertex_ai/gemini-1.5-flash
- **Temperature**: 0.1
- **Max Tokens**: 16000
- **Input Tokens**: 3,456
- **Output Tokens**: 2,890
- **Total Tokens**: 6,346
- **Total Cost**: $0.0022 USD
- **Timestamp**: 2025-07-14T12:34:56
<!-- GEMINI_API_COST_END -->
```

You can extract cost programmatically:
```python
import re

# Read response file
response_text = Path("tmp/gemini_response_20250714_123456.md").read_text()

# Extract cost section
cost_match = re.search(
    r'<!-- GEMINI_API_COST_START -->.*?Total Cost.*?\$([0-9.]+).*?<!-- GEMINI_API_COST_END -->',
    response_text,
    re.DOTALL
)

if cost_match:
    cost = float(cost_match.group(1))
    print(f"API call cost: ${cost:.4f}")
```

## Complete Example Script

```python
#!/usr/bin/env python3
"""Complete Gemini workflow example."""

import json
from pathlib import Path
import subprocess
import sys

def process_issue_with_gemini(issue_content: str):
    """Complete workflow to process an issue with Gemini."""
    
    # 1. Save issue report
    issue_file = Path("tmp/issues/current_issue.md")
    issue_file.parent.mkdir(parents=True, exist_ok=True)
    issue_file.write_text(issue_content)
    
    # 2. Send to Gemini
    send_result = subprocess.run([
        "uv", "run", ".claude/tools/send_to_gemini.py",
        json.dumps({"issue_file": str(issue_file)})
    ], capture_output=True, text=True)
    
    if send_result.returncode != 0:
        print(f"Failed to send to Gemini: {send_result.stderr}")
        return False
    
    send_data = json.loads(send_result.stdout)
    print(f"Gemini response saved to: {send_data['output_file']}")
    print(f"Cost: ${send_data['cost']['total_cost']:.4f}")
    
    # 3. Extract code
    extract_result = subprocess.run([
        "uv", "run", ".claude/tools/extract_gemini_code.py",
        json.dumps({"markdown_file": send_data['output_file']})
    ], capture_output=True, text=True)
    
    if extract_result.returncode != 0:
        print(f"Failed to extract code: {extract_result.stderr}")
        return False
    
    extract_data = json.loads(extract_result.stdout)
    print(f"Extracted {len(extract_data['files'])} files to: {extract_data['output_directory']}")
    
    # 4. Run tests on extracted code
    for file_info in extract_data['files']:
        if file_info['path'].endswith('.py'):
            test_result = subprocess.run([
                sys.executable, "-m", "py_compile",
                f"{extract_data['output_directory']}/{file_info['path']}"
            ], capture_output=True)
            
            if test_result.returncode == 0:
                print(f"✓ {file_info['path']} - syntax valid")
            else:
                print(f"✗ {file_info['path']} - syntax error")
    
    return True
```

## Benefits

1. **Efficiency**: No large files loaded into Claude's context
2. **Cost Tracking**: Automatic cost calculation and reporting
3. **Validation**: Syntax checking before applying changes
4. **Selective Updates**: Review diffs before overwriting
5. **Audit Trail**: All interactions saved with timestamps

## Error Handling

Both tools handle common errors:

- **Missing files**: Clear error messages
- **API failures**: Error details saved to .error.json files
- **Invalid responses**: Warns if CODE_FILE_START markers missing
- **Syntax errors**: Validates Python files automatically

## Future Vertex AI Integration

This workflow is designed to work seamlessly with automated Vertex AI pipelines:

```python
# Future automated pipeline
async def automated_issue_resolution(error: Exception, context: dict):
    # 1. Generate issue report
    issue_report = generate_issue_report(error, context)
    
    # 2. Send to Gemini via tool
    send_result = await run_tool("SendToGemini", {
        "issue_file": save_issue(issue_report)
    })
    
    # 3. Extract code via tool
    extract_result = await run_tool("ExtractGeminiCode", {
        "markdown_file": send_result["output_file"]
    })
    
    # 4. Apply and test
    return apply_and_test_changes(extract_result["output_directory"])
```

---

This complete workflow enables efficient, cost-effective issue resolution with Gemini Flash while maintaining full visibility and control over the process.