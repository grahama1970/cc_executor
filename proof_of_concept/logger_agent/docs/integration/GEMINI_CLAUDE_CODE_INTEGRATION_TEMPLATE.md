# Gemini-Claude Code Integration Template

**PURPOSE**: Rock-solid templates for automated Gemini Flash API integration

## 1. Claude Code → Gemini Template

### Problem Report Format

When Claude Code encounters issues and needs Gemini's help, use this EXACT format:

```markdown
# Issue Report for Gemini

## Context
- **Project**: [Project name and path]
- **Task**: [What Claude Code was trying to accomplish]
- **Status**: BLOCKED

## Files Analyzed
[List all relevant files with their paths]

## Issue Details

### Error Type: [AsyncIO/Import/Database/etc]

**Error Message**:
```
[Exact error message and traceback]
```

**Location**: [file:line_number]

**What Was Attempted**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Why It Failed**:
[Technical explanation of the root cause]

## Code Context

<!-- CODE_CONTEXT_START: path/to/failing/file.py -->
```python
# Lines around the error (with line numbers)
```
<!-- CODE_CONTEXT_END: path/to/failing/file.py -->

## Required Solution Format

Please provide fixes using the standardized code block format:

<!-- CODE_FILE_START: path/to/file.py -->
```python
# Complete fixed file content
```
<!-- CODE_FILE_END: path/to/file.py -->

## Test Database Pattern Required

All database-interacting code MUST use test database isolation:

```python
from utils.test_db_utils import setup_test_database, teardown_test_database

async def main():
    test_db, test_db_name, test_db_config = await setup_test_database()
    try:
        # Your code here
        pass
    finally:
        await teardown_test_database(test_db_name)
```
```

## 2. Gemini Response Template

### Gemini MUST Follow This EXACT Format

```markdown
# Solution for [Issue Type]

## Summary
[2-3 sentences explaining the fix]

## Root Cause Analysis
[Technical explanation of why the error occurred]

## Code Fixes

### File Structure
```
project/
├── src/
│   ├── fixed_file1.py
│   └── fixed_file2.py
└── tests/
    └── test_fixed.py
```

### Fixed Code Files

<!-- CODE_FILE_START: src/utils/log_utils.py -->
```python
#!/usr/bin/env python3
"""
Complete file content with ALL fixes applied.
No placeholders, no ellipsis (...), no comments like "rest remains the same".
ENTIRE FILE MUST BE INCLUDED.
"""

# Complete working code here
```
<!-- CODE_FILE_END: src/utils/log_utils.py -->

<!-- CODE_FILE_START: src/utils/test_db_utils.py -->
```python
#!/usr/bin/env python3
"""
Test database utilities for isolated testing.
"""

# Complete working code here
```
<!-- CODE_FILE_END: src/utils/test_db_utils.py -->

## Validation

### Expected Behavior After Fix
1. [Specific test command]: Should output [expected result]
2. [Another test]: Should complete without errors

### Test Commands
```bash
python src/arango_init.py
python src/agent_log_manager.py
```

## Additional Notes
[Any warnings, caveats, or future considerations]
```

## 3. Automated Extraction Workflow

### Step 1: Claude Code Detects Issue
```python
try:
    # Attempt operation
    result = await some_async_operation()
except Exception as e:
    # Generate issue report
    issue_report = generate_issue_report(e, context)
    # Save for Gemini
    Path("issues/for_gemini.md").write_text(issue_report)
```

### Step 2: Send to Gemini (Future Vertex API)
```python
async def get_gemini_solution(issue_report: str) -> str:
    """Send issue to Gemini Flash via Vertex AI."""
    # Future implementation
    response = await vertex_ai.generate(
        model="gemini-flash",
        prompt=GEMINI_PROMPT_TEMPLATE.format(issue=issue_report),
        temperature=0.1,  # Low temp for consistent formatting
        max_tokens=8000
    )
    return response
```

### Step 3: Extract and Apply Fixes

Using Claude Code's ExtractGeminiCode tool:

```python
# Extract code without loading full markdown into context
result = ExtractGeminiCode(
    markdown_file="gemini_response.md"
)

# Result provides:
# - output_directory: "tmp/gemini_extracted_TIMESTAMP"
# - files: List of extracted files with paths and line counts
# - context_file: Summary of extraction

# Review and apply changes selectively
```

Or using the command line:
```bash
# Extract code from Gemini's response
python scripts/extract_code_from_markdown.py \
    gemini_response.md \
    tmp/gemini_extracted \
    --validate \
    --report extraction_report.json

# Test the fixes
python src/working_usage_verification.py
```

## 4. Critical Requirements for Gemini

### MUST Requirements
1. **Complete Files Only**: Never use ellipsis (...) or "rest remains unchanged"
2. **Exact Marker Format**: Use `<!-- CODE_FILE_START: path -->` and `<!-- CODE_FILE_END: path -->`
3. **Test Database Pattern**: All DB code must use test database isolation
4. **Working Code**: All code must be executable, no pseudocode
5. **Import Order**: Correct Python import order (stdlib, third-party, local)

### MUST NOT Requirements
1. **No Partial Files**: Every file must be complete
2. **No Placeholders**: No TODO, FIXME, or placeholder comments
3. **No Mixed Formats**: Don't mix old --- markers with new <!-- markers
4. **No Assumptions**: Include all necessary imports and error handling

## 5. Example: AsyncIO Event Loop Fix

### Claude Code Issue Report
```markdown
# Issue Report for Gemini

## Context
- **Project**: /home/user/logger_agent
- **Task**: Running agent_log_manager.py working_usage function
- **Status**: BLOCKED

## Files Analyzed
- src/agent_log_manager.py
- src/arango_log_sink.py

## Issue Details

### Error Type: AsyncIO Event Loop

**Error Message**:
```
RuntimeError: no running event loop
  File "agent_log_manager.py", line 661
    sink = get_arango_sink()
```

**Location**: agent_log_manager.py:661

**What Was Attempted**:
1. Running working_usage() function
2. Initializing ArangoDB sink
3. Starting async operations

**Why It Failed**:
The get_arango_sink() function tries to create async tasks outside of an async context.

## Code Context

<!-- CODE_CONTEXT_START: src/agent_log_manager.py -->
```python
659: # Configure logger with ArangoDB sink
660: from arango_log_sink import get_arango_sink
661: sink = get_arango_sink()  # ERROR HERE
662: logger.add(sink.write, enqueue=True, level="DEBUG")
```
<!-- CODE_CONTEXT_END: src/agent_log_manager.py -->

## Required Solution Format

Please provide the complete fixed agent_log_manager.py file using CODE_FILE_START/END markers.
```

### Gemini Response (Correct Format)
```markdown
# Solution for AsyncIO Event Loop Error

## Summary
The error occurs because sink initialization happens outside async context. The fix moves sink creation into the async main() function.

## Root Cause Analysis
The get_arango_sink() function calls asyncio.create_task() which requires a running event loop. This must be called from within an async function.

## Code Fixes

### Fixed Code Files

<!-- CODE_FILE_START: src/agent_log_manager.py -->
```python
#!/usr/bin/env python3
"""
agent_log_manager.py - Complete fixed file
"""

import asyncio
import sys
from pathlib import Path
# ... all imports ...

# ... all code before main ...

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        sink = None
        sink_handler_id = None
        try:
            # Initialize sink within async context
            sink = get_arango_sink()
            await sink.start()
            sink_handler_id = logger.add(sink.write, enqueue=True, level="DEBUG")
            
            if mode == "debug":
                success = await debug_function()
            else:
                success = await working_usage()
            return success
        finally:
            if sink_handler_id:
                logger.remove(sink_handler_id)
            if sink:
                await sink.stop()
    
    asyncio.run(main())
```
<!-- CODE_FILE_END: src/agent_log_manager.py -->

## Validation

### Expected Behavior After Fix
1. `python src/agent_log_manager.py`: Should run without event loop errors
2. Should create test database and run tests successfully

### Test Commands
```bash
python src/agent_log_manager.py
```
```

## 6. Vertex AI Integration (Future)

```python
# Future implementation for automated workflow
class GeminiIntegration:
    def __init__(self, project_id: str):
        self.vertex_ai = vertexai.init(project=project_id)
        self.model = "gemini-1.5-flash-latest"
    
    async def fix_issue(self, issue_report: str) -> Dict[str, str]:
        """Get fix from Gemini and extract code."""
        # Generate solution
        response = await self.generate_solution(issue_report)
        
        # Extract code files
        extracted_files = self.extract_code_files(response)
        
        # Validate syntax
        validation_results = self.validate_code(extracted_files)
        
        return {
            "files": extracted_files,
            "validation": validation_results,
            "response": response
        }
```

## 7. Success Metrics

A successful integration will:
1. Generate properly formatted issue reports 100% of the time
2. Receive correctly formatted responses from Gemini 95%+ of the time
3. Extract code without manual intervention 100% of the time
4. Pass syntax validation 100% of the time
5. Fix the reported issue 90%+ of the time

## 8. Template Version

**Version**: 1.0.0
**Last Updated**: 2025-07-14
**Status**: PRODUCTION READY

---

This template is designed for direct integration with Vertex AI Gemini Flash API. No modifications should be needed for automated workflows.