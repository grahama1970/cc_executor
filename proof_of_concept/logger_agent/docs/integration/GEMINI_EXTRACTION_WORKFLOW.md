# Gemini Code Extraction Workflow

## Overview

This workflow enables Claude Code to efficiently process complete code solutions from Gemini without loading entire markdown files into context.

## Workflow Steps

### 1. Gemini Provides Complete Solution

Gemini generates a markdown file with all code in one shot using the required format:

```markdown
# Solution for [Issue Description]

## Summary
[Brief explanation of the solution]

## Code Files

<!-- CODE_FILE_START: src/utils/example.py -->
```python
#!/usr/bin/env python3
# Complete file content here
```
<!-- CODE_FILE_END: src/utils/example.py -->

<!-- CODE_FILE_START: src/utils/another_file.py -->
```python
#!/usr/bin/env python3
# Another complete file
```
<!-- CODE_FILE_END: src/utils/another_file.py -->
```

### 2. Claude Code Extracts Files

Using the ExtractGeminiCode tool:

```python
# Claude Code runs this tool
result = ExtractGeminiCode(
    markdown_file="docs/issues/gemini_solution.md"
)

# Result contains:
{
  "success": true,
  "output_directory": "tmp/gemini_extracted_20250714_123456",
  "files": [
    {"path": "src/utils/example.py", "lines": 150},
    {"path": "src/utils/another_file.py", "lines": 200}
  ],
  "context_file": "tmp/gemini_extracted_20250714_123456/EXTRACTION_CONTEXT.md"
}
```

### 3. Claude Code Analyzes Extracted Files

```bash
# Review extracted files
ls -la tmp/gemini_extracted_20250714_123456/

# Compare with existing
diff -u src/utils/example.py tmp/gemini_extracted_20250714_123456/src/utils/example.py

# Check syntax
python -m py_compile tmp/gemini_extracted_20250714_123456/src/utils/example.py
```

### 4. Claude Code Updates Code

```python
# Selectively apply changes
shutil.copy(
    "tmp/gemini_extracted_20250714_123456/src/utils/example.py",
    "src/utils/example.py"
)

# Or use the MultiEdit tool for partial updates
```

## Tool Usage Examples

### Basic Extraction

```json
{
  "tool": "ExtractGeminiCode",
  "inputs": {
    "markdown_file": "responses/gemini_fix.md"
  }
}
```

### With Custom Output Directory

```json
{
  "tool": "ExtractGeminiCode",
  "inputs": {
    "markdown_file": "responses/gemini_fix.md",
    "output_dir": "tmp/gemini_analysis_1"
  }
}
```

## Benefits

1. **Efficiency**: No need to load large markdown files into Claude's context
2. **Organization**: All extracted files go to tmp/ with clear timestamps
3. **Validation**: Automatic syntax checking for Python files
4. **Comparison**: Easy to diff against existing code
5. **Selective Updates**: Apply only the changes you need

## File Structure After Extraction

```
project/
├── tmp/
│   └── gemini_extracted_20250714_123456/
│       ├── EXTRACTION_CONTEXT.md     # Summary and commands
│       ├── src/
│       │   └── utils/
│       │       ├── example.py        # Extracted files
│       │       └── another_file.py
│       └── tests/
│           └── test_example.py
```

## Error Handling

The tool handles common issues:

1. **Missing markers**: Reports files with mismatched START/END tags
2. **Syntax errors**: Validates Python files and reports issues
3. **Path conflicts**: Creates directories as needed
4. **Large files**: Handles files of any size

## Integration with Vertex AI (Future)

```python
async def process_gemini_fix(issue_report: str):
    # 1. Send to Gemini via Vertex AI
    response = await vertex_ai.generate(
        model="gemini-1.5-flash",
        prompt=issue_report
    )
    
    # 2. Save response
    response_file = Path("tmp/gemini_response.md")
    response_file.write_text(response)
    
    # 3. Extract code using tool
    extraction = ExtractGeminiCode(
        markdown_file=str(response_file)
    )
    
    # 4. Process extracted files
    for file_info in extraction["files"]:
        # Analyze and apply changes
        pass
```

## Best Practices

1. **Always validate** extracted code before applying
2. **Use tmp/ directory** for all extractions
3. **Keep extraction logs** for debugging
4. **Review diffs** before overwriting files
5. **Test changes** with isolated test databases

---

This workflow ensures efficient, reliable code extraction from Gemini's responses without overwhelming Claude Code's context window.