# Gemini Batch Processing Flow Guide

## Overview

This guide explains how the agent (Claude Code) processes multiple code files through Gemini in a loop, handles responses, extracts code, and manages failures. The system is designed to handle Gemini's 8K output token limit by processing files one at a time while maintaining full context.

## Complete Flow Diagram

```
1. Agent identifies broken files
   ↓
2. Create issue report with all context
   ↓
3. Send files to Gemini (one at a time)
   ↓
4. Extract code from responses
   ↓
5. Apply fixes or retry (max 2 attempts)
   ↓
6. If still failing, add to failure report
   ↓
7. Send failure report back to Gemini
```

## Step-by-Step Process

### 1. Identifying Broken Files

The agent searches for issues using various methods:

```bash
# Find mock implementations (forbidden in production)
grep -r "mock\|Mock" src/ --include="*.py"

# Find deprecated logger.bind() usage
grep -r "logger\.bind" src/ --include="*.py"

# Find missing asyncio.to_thread patterns
grep -r "def.*sync.*:" src/ | grep -v "async def"
```

### 2. Creating Issue Report

The agent creates a structured markdown report (`tmp/issues/fix_[issue_name].md`):

```markdown
# Issue Report: [Issue Name]

## Context
- **Project**: /path/to/project
- **Task**: Fix specific issues
- **Status**: BLOCKED - Issues need fixing

## Files to Fix
1. src/file1.py
2. src/file2.py

## Issue Details
[Specific details about what needs fixing]

## All Context Files (For Reference)

<!-- CODE_CONTEXT_START: src/file1.py -->
```python
[Complete file content]
```
<!-- CODE_CONTEXT_END: src/file1.py -->

[Additional context files...]
```

### 3. Batch Processing with Gemini

The agent uses `send_to_gemini_batch.py` to process files:

```python
# Agent executes:
uv run .claude/tools/send_to_gemini_batch.py '{
    "issue_report_file": "tmp/issues/fix_logger_bind.md",
    "files_to_fix": ["src/arango_log_sink.py", "src/agent_log_manager.py"],
    "max_tokens": 7500
}'
```

#### How the Batch Tool Works:

1. **Loads the issue report** and extracts sections
2. **For each file to fix**:
   - Creates a focused request with ALL context but emphasizes ONE file
   - Sends to Gemini with proper formatting requirements
   - Saves both request and response
   - Tracks costs and usage

3. **Output structure**:
```
tmp/gemini_batch_20250715_063222/
├── request_1_arango_log_sink.md      # What we sent
├── response_1_arango_log_sink.md     # What Gemini returned
├── request_2_agent_log_manager.md    
├── response_2_agent_log_manager.md   
└── BATCH_SUMMARY.json                # Processing summary
```

### 4. Extracting Code from Responses

The agent uses `extract_gemini_code.py`:

```python
# Agent executes:
uv run .claude/tools/extract_gemini_code.py '{
    "markdown_file": "tmp/gemini_batch_20250715_063222/response_1_arango_log_sink.md"
}'
```

This tool:
- Looks for code between `<!-- CODE_FILE_START -->` and `<!-- CODE_FILE_END -->` markers
- Extracts complete files to `tmp/gemini_extracted_[timestamp]/`
- Creates an extraction context file
- Returns a summary without loading full content

### 5. Applying Fixes

The agent typically:

```bash
# 1. Compare the changes
diff -u src/arango_log_sink.py tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py

# 2. If changes look good, copy the file
cp tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py src/arango_log_sink.py

# 3. Test the fix
python src/arango_log_sink.py
```

### 6. Handling Failures (2-Attempt Rule)

If a fix fails after application:

**First Attempt Failure:**
- Agent analyzes the error
- Creates a more detailed issue report including the error
- Retries with Gemini

**Second Attempt Failure:**
- Agent stops trying to fix automatically
- Adds the file and error details to a failure report
- Prepares for human intervention or advanced Gemini analysis

### 7. Failure Report for Gemini

After 2 failed attempts, the agent creates an enhanced report:

```markdown
# Failure Report: Persistent Issues After 2 Attempts

## Summary
The following files could not be fixed after 2 attempts with Gemini.

## Failed Files

### 1. src/problematic_file.py

**Original Issue**: Mock implementation needs real code
**Attempt 1 Error**: Missing import for 'real_module'
**Attempt 2 Error**: Type mismatch in function signature

**Error Details from Attempt 2**:
```
Traceback (most recent call last):
  File "src/problematic_file.py", line 45
  TypeError: Expected str, got int
```

**Gemini's Last Attempt**:
[Include the code that Gemini generated]

**Context That May Be Missing**:
- The real_module is defined in src/utils/
- The function signature changed in commit abc123

## Recommended Approach
[Agent's analysis of why it's failing]
```

## Cost Tracking

The system tracks costs for each operation:

```json
{
  "success": true,
  "files_processed": 3,
  "files_succeeded": 2,
  "total_cost": 0.0048,
  "average_cost_per_file": 0.0016,
  "results": [
    {
      "file_to_fix": "src/arango_log_sink.py",
      "success": true,
      "cost": 0.0016,
      "usage": {
        "prompt_tokens": 10065,
        "completion_tokens": 4558,
        "total_tokens": 14623
      }
    }
  ]
}
```

## Example: Complete Flow in Action

```bash
# 1. Agent finds deprecated logger.bind() usage
$ grep -n "logger\.bind" src/arango_log_sink.py
386:    logger.bind(skip_sink=True).error(...)
517:    logger.bind(execution_id=execution_id).info(...)

# 2. Agent creates issue report
$ cat tmp/issues/fix_logger_bind.md
[Issue report with all context]

# 3. Agent sends to Gemini
$ uv run .claude/tools/send_to_gemini_batch.py '{"issue_report_file": "tmp/issues/fix_logger_bind.md", "files_to_fix": ["src/arango_log_sink.py"]}'
Processing 1 files through Gemini...
[1/1] Processing src/arango_log_sink.py
  ✓ Success - Cost: $0.0016

# 4. Agent extracts code
$ uv run .claude/tools/extract_gemini_code.py '{"markdown_file": "tmp/gemini_batch_20250715_063222/response_1_arango_log_sink.md"}'
Extracted 1 file(s) to tmp/gemini_extracted_20250715_063317/

# 5. Agent applies fix
$ cp tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py src/arango_log_sink.py

# 6. Agent tests
$ python src/arango_log_sink.py
[No deprecation warnings - success!]
```

## Key Features

### 1. Context Preservation
- ALL files are sent as context for EACH file fix
- Gemini can see the entire codebase structure
- References between files are maintained

### 2. Token Limit Management
- Each file gets its own API call (8K output limit)
- Input can be large (1M tokens) but output is limited
- Batching prevents token overflow

### 3. Error Recovery
- Requests and responses are saved for debugging
- Failed files can be retried with more context
- 2-attempt limit prevents infinite loops

### 4. Cost Efficiency
- Average cost: ~$0.0016 per file
- Gemini Flash is used for speed and cost
- Progress tracking shows real-time costs

## Advanced Usage

### Custom Temperature
```python
# For more creative solutions (higher temperature)
{
    "issue_report_file": "tmp/issues/complex_refactor.md",
    "files_to_fix": ["src/complex_module.py"],
    "temperature": 0.7,
    "max_tokens": 8000
}
```

### Specific Output Directory
```python
# For organizing multiple fix attempts
{
    "issue_report_file": "tmp/issues/fix_mocks.md", 
    "files_to_fix": ["src/module1.py", "src/module2.py"],
    "output_dir": "tmp/gemini_attempts/attempt_1"
}
```

## Troubleshooting

### Common Issues

1. **"Object of type datetime is not JSON serializable"**
   - Not related to logger.bind() fix
   - Indicates serialization issue in the code logic

2. **"Code markers not found in response"**
   - Gemini didn't follow the format requirements
   - Check response file manually
   - May need to adjust prompt

3. **"Token limit exceeded"**
   - Too much context or file too large
   - Split into smaller files
   - Reduce context files

### Debug Commands

```bash
# Check what Gemini received
cat tmp/gemini_batch_*/request_*.md

# Check what Gemini returned  
cat tmp/gemini_batch_*/response_*.md

# Check extraction results
ls -la tmp/gemini_extracted_*/

# Compare all changes at once
for f in tmp/gemini_extracted_*/src/*.py; do
    diff -u src/$(basename $f) $f
done
```

## Best Practices

1. **Always verify changes** before applying
2. **Test immediately** after applying fixes
3. **Keep issue reports focused** on specific problems
4. **Include error messages** in retry attempts
5. **Save successful patterns** for future use

## Integration with Agent Workflow

The agent integrates this flow naturally:

1. **Discovery Phase**: Agent finds issues through search
2. **Analysis Phase**: Agent creates detailed issue reports
3. **Execution Phase**: Agent runs batch processing
4. **Verification Phase**: Agent tests and validates fixes
5. **Iteration Phase**: Agent retries or escalates failures

This systematic approach ensures reliable, cost-effective code fixes while maintaining full context and traceability.