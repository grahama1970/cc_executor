# Gemini Prompt Examples

## 1. Initial System Prompt for Gemini

```
You are an expert Python developer helping fix issues in an ArangoDB-based logging system.

CRITICAL REQUIREMENTS:
1. Always provide COMPLETE files - never use ellipsis (...) or "rest unchanged"
2. Use EXACT format: <!-- CODE_FILE_START: path --> and <!-- CODE_FILE_END: path -->
3. All database code MUST use test database isolation pattern
4. Include ALL imports, no placeholders
5. Code must be immediately executable

When providing solutions:
- Analyze the root cause first
- Provide complete working code
- Include test commands
- Follow the exact template format provided
```

## 2. Claude Code Issue Report Prompt

```python
ISSUE_REPORT_TEMPLATE = """
# Issue Report for Gemini

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

**What Was Attempted**:
{attempts}

**Why It Failed**:
{failure_reason}

## Code Context

<!-- CODE_CONTEXT_START: {failing_file} -->
```python
{code_context}
```
<!-- CODE_CONTEXT_END: {failing_file} -->

## Required Solution Format

Please provide fixes using the standardized code block format with <!-- CODE_FILE_START --> markers.
Include test database isolation for any database operations.
"""
```

## 3. Example Claude Code → Gemini Request

```python
# When Claude Code encounters an error
def generate_gemini_request(exception: Exception, context: dict) -> str:
    """Generate a properly formatted request for Gemini."""
    
    return f"""
{GEMINI_SYSTEM_PROMPT}

Please fix the following issue:

{ISSUE_REPORT_TEMPLATE.format(
    project_path=context['project_path'],
    task_description=context['task'],
    file_list='\n'.join(f"- {f}" for f in context['files']),
    error_type=type(exception).__name__,
    error_traceback=traceback.format_exc(),
    file=context['error_file'],
    line=context['error_line'],
    attempts='\n'.join(f"{i+1}. {a}" for i, a in enumerate(context['attempts'])),
    failure_reason=context['analysis'],
    failing_file=context['error_file'],
    code_context=context['code_snippet']
)}

Remember to provide COMPLETE files with the exact CODE_FILE_START/END format.
"""
```

## 4. Vertex AI API Call (Future Implementation)

```python
import vertexai
from vertexai.generative_models import GenerativeModel

async def get_gemini_fix(issue_report: str) -> str:
    """Get fix from Gemini Flash via Vertex AI."""
    
    # Initialize Vertex AI
    vertexai.init(project="your-project-id", location="us-central1")
    
    # Configure model
    model = GenerativeModel(
        "gemini-1.5-flash-001",
        system_instruction=GEMINI_SYSTEM_PROMPT
    )
    
    # Generate with specific parameters for consistency
    response = await model.generate_content_async(
        issue_report,
        generation_config={
            "temperature": 0.1,  # Low for consistent formatting
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
    )
    
    return response.text
```

## 5. Validation Prompt

After receiving Gemini's response, validate format:

```python
def validate_gemini_response(response: str) -> List[str]:
    """Validate that Gemini used correct format."""
    issues = []
    
    # Check for correct markers
    if "<!-- CODE_FILE_START:" not in response:
        issues.append("Missing CODE_FILE_START markers")
    
    # Check for complete files
    if "..." in response or "# rest unchanged" in response:
        issues.append("Contains incomplete code sections")
    
    # Check for test database pattern
    if "setup_test_database" not in response and "database" in response.lower():
        issues.append("Database code missing test isolation pattern")
    
    # Extract and validate each file
    pattern = r'<!-- CODE_FILE_START: (.*?) -->.*?<!-- CODE_FILE_END: \1 -->'
    matches = re.findall(pattern, response, re.DOTALL)
    
    if not matches:
        issues.append("No valid code blocks found")
    
    return issues
```

## 6. Success Criteria Checklist

Before considering a Gemini response successful:

- [ ] All CODE_FILE_START markers have matching CODE_FILE_END
- [ ] No ellipsis (...) or partial code
- [ ] All imports are present
- [ ] Test database pattern used for DB operations
- [ ] Code compiles without syntax errors
- [ ] Original error is resolved
- [ ] No new errors introduced

## 7. Example Full Workflow

```python
async def automated_fix_workflow(error: Exception, context: dict):
    """Complete automated fix workflow."""
    
    # 1. Generate issue report
    issue_report = generate_gemini_request(error, context)
    
    # 2. Get fix from Gemini
    gemini_response = await get_gemini_fix(issue_report)
    
    # 3. Validate response format
    validation_issues = validate_gemini_response(gemini_response)
    if validation_issues:
        raise ValueError(f"Invalid Gemini response: {validation_issues}")
    
    # 4. Extract code
    extracted_files = extract_code_from_markdown(gemini_response)
    
    # 5. Apply fixes
    for file_path, content in extracted_files.items():
        Path(file_path).write_text(content)
    
    # 6. Test fixes
    test_result = await run_tests()
    
    return {
        "fixed": test_result.success,
        "files_changed": list(extracted_files.keys()),
        "test_output": test_result.output
    }
```

## 8. Common Issue Types and Prompts

### AsyncIO Issues
```
The error "no running event loop" means async operations are being called outside async context.
Move the initialization into an async function and use asyncio.run().
```

### Import Issues
```
The error "No module named X" requires checking if the import path is correct.
Use absolute imports from the project root.
```

### Database Issues
```
All database operations MUST use the test database pattern.
Never connect directly to production database in tests.
```

---

These prompts and examples ensure consistent, high-quality responses from Gemini that can be automatically processed without manual intervention.