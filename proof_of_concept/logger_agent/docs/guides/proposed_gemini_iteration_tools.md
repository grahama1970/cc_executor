# Proposed Tools for Gemini Iteration Workflow

## Current Situation

We have these tools in `tools.json`:
1. **SendToGemini** - Send single issue report
2. **SendToGeminiBatch** - Send multiple files  
3. **ExtractGeminiCode** - Extract code from response

## Missing Tools for Complete Iteration

### 1. ApplyGeminiFixWithRetry
```json
{
    "tool_name": "ApplyGeminiFixWithRetry",
    "description": "Applies extracted Gemini code fix, tests it, and retries up to 2 times if it fails. Handles the complete iteration loop including error analysis and retry logic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "extracted_file": {
                "type": "string",
                "description": "Path to the extracted file from Gemini (e.g., tmp/gemini_extracted_*/src/file.py)"
            },
            "target_file": {
                "type": "string", 
                "description": "Path where the file should be applied (e.g., src/file.py)"
            },
            "test_command": {
                "type": "string",
                "description": "Command to test if the fix works (e.g., 'python src/file.py')"
            },
            "original_issue_file": {
                "type": "string",
                "description": "Path to the original issue report for context in retries"
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum retry attempts (default: 2)"
            }
        },
        "required": ["extracted_file", "target_file", "test_command", "original_issue_file"]
    }
}
```

### 2. CreateGeminiFailureReport
```json
{
    "tool_name": "CreateGeminiFailureReport",
    "description": "Creates a comprehensive failure report after 2 failed attempts, ready to send back to Gemini with all error context and attempted solutions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "failed_file": {
                "type": "string",
                "description": "Path to the file that failed to fix"
            },
            "attempts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "attempt_number": {"type": "integer"},
                        "error_message": {"type": "string"},
                        "gemini_response_file": {"type": "string"},
                        "test_output": {"type": "string"}
                    }
                },
                "description": "Array of attempt details including errors and responses"
            },
            "original_issue": {
                "type": "string",
                "description": "Description of the original issue"
            },
            "output_file": {
                "type": "string",
                "description": "Where to save the failure report"
            }
        },
        "required": ["failed_file", "attempts", "original_issue"]
    }
}
```

### 3. GeminiIterativeFixWorkflow
```json
{
    "tool_name": "GeminiIterativeFixWorkflow", 
    "description": "Orchestrates the complete Gemini fix workflow: send issue, extract code, apply fix, test, retry on failure, create failure report. This is the all-in-one tool.",
    "input_schema": {
        "type": "object",
        "properties": {
            "issue_report_file": {
                "type": "string",
                "description": "Path to the issue report markdown file"
            },
            "files_to_fix": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of files that need fixing"
            },
            "test_commands": {
                "type": "object",
                "description": "Map of file paths to their test commands"
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum retries per file (default: 2)"
            },
            "continue_on_failure": {
                "type": "boolean",
                "description": "Continue with other files if one fails (default: true)"
            }
        },
        "required": ["issue_report_file", "files_to_fix"]
    }
}
```

## Implementation Example for ApplyGeminiFixWithRetry

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["loguru"]
# ///

import json
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

def apply_and_test(extracted_file: str, target_file: str, test_command: str) -> dict:
    """Apply fix and test it."""
    # Backup original
    backup_file = f"{target_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(target_file, backup_file)
    
    try:
        # Apply fix
        shutil.copy(extracted_file, target_file)
        
        # Test
        result = subprocess.run(
            test_command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "returncode": result.returncode
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if not result.get("success"):
            # Restore backup on failure
            shutil.copy(backup_file, target_file)

def create_retry_issue_report(original_issue: str, error_info: dict, attempt: int) -> str:
    """Create enhanced issue report for retry."""
    return f"""# Retry Attempt {attempt + 1}: Fix Failed

## Previous Error
```
{error_info['error']}
```

## Original Issue Report
{original_issue}

## Additional Context for Retry
- The previous fix compiled but failed at runtime
- Error occurred during: {error_info.get('phase', 'testing')}
- Please ensure the fix handles this specific error case

## Required: Complete Working Solution
Provide the COMPLETE fixed file that addresses the above error.
"""

def main():
    input_data = json.loads(sys.argv[1])
    
    extracted_file = input_data["extracted_file"]
    target_file = input_data["target_file"]
    test_command = input_data["test_command"]
    original_issue_file = input_data["original_issue_file"]
    max_retries = input_data.get("max_retries", 2)
    
    attempts = []
    
    for attempt in range(max_retries):
        # Apply and test
        result = apply_and_test(extracted_file, target_file, test_command)
        
        attempts.append({
            "attempt": attempt + 1,
            "result": result,
            "extracted_file": extracted_file
        })
        
        if result["success"]:
            print(json.dumps({
                "success": True,
                "attempts": attempts,
                "final_status": "fixed"
            }))
            return
        
        # If failed and more retries available
        if attempt < max_retries - 1:
            # Create retry issue report
            original_issue = Path(original_issue_file).read_text()
            retry_issue = create_retry_issue_report(
                original_issue,
                result,
                attempt
            )
            
            # Save retry issue
            retry_file = f"tmp/retry_issue_{attempt + 1}.md"
            Path(retry_file).write_text(retry_issue)
            
            # Call Gemini again (this would use SendToGemini tool)
            # For now, we'll just note that we need to retry
            attempts[-1]["retry_issue_file"] = retry_file
    
    # All attempts failed
    print(json.dumps({
        "success": False,
        "attempts": attempts,
        "final_status": "failed_after_retries"
    }))
```

## How This Improves the Workflow

### Current Process (Manual Steps):
1. I use SendToGeminiBatch
2. I use ExtractGeminiCode  
3. I manually copy files
4. I manually test
5. I manually analyze errors
6. I manually create retry reports
7. I manually track attempts

### With Integrated Tools:
```python
# One tool call handles everything:
result = GeminiIterativeFixWorkflow({
    "issue_report_file": "tmp/issues/fix_mocks.md",
    "files_to_fix": ["src/module1.py", "src/module2.py"],
    "test_commands": {
        "src/module1.py": "python -m pytest tests/test_module1.py",
        "src/module2.py": "python src/module2.py"
    }
})

# Result includes:
# - Which files succeeded
# - Which files failed after retries  
# - Failure reports ready for Gemini
# - All attempt history
```

## Benefits of Tool Integration

1. **Atomic Operations** - Each tool completes a full workflow step
2. **Error Handling** - Built-in retry logic and error analysis
3. **Progress Tracking** - Tools return structured progress data
4. **Context Preservation** - Tools maintain context between attempts
5. **Reduced Manual Work** - I don't need to orchestrate multiple bash commands

## Next Steps

1. Implement these tools in `.claude/tools/`
2. Add them to `tools.json`
3. Test with real fix scenarios
4. Refine based on common failure patterns

This would make the Gemini integration much more powerful and autonomous!