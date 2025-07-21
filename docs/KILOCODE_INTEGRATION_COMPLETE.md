# KiloCode Integration - Complete Working Solution

## Overview

This document describes the working integration between KiloCode and the cc_executor code review system. The solution works within KiloCode's limitations by providing a Python command that performs complete code reviews using LLMs directly.

## Key Insight

KiloCode's `execute_command` can only run system commands (like Python), NOT slash commands (like `/review-contextual`). Since we cannot programmatically trigger KiloCode's slash commands, we provide a standalone tool that performs the complete 2-level code review.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Post-Task Hook  │────▶│ MCP KiloCode     │────▶│ Python Command  │
│                 │     │ Review Server    │     │ Generation      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ JSON Results    │◀────│ 2-Level Review   │◀────│ Standalone Tool │
│ (Structured)    │     │ GPT-4 → Gemini   │     │ Execution       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Implementation Details

### 1. MCP Server (`mcp_kilocode_review.py`)

The server provides two main functions:

```python
@mcp.tool()
async def start_review(
    files: str,
    context: Optional[str] = None,
    focus: Optional[str] = None,
    severity: Optional[str] = None
) -> str:
    """
    Returns a Python command that performs complete 2-level code review.
    KiloCode executes this command via execute_command.
    """

@mcp.tool()
async def get_review_results(review_id: str) -> str:
    """
    Retrieves and parses JSON results from the completed review.
    """
```

### 2. Standalone Review Tool (`kilocode_review_standalone.py`)

The standalone tool performs:
- **Phase 1**: GPT-4 code review focusing on issues
- **Phase 2**: Gemini meta-review for validation
- Saves structured JSON results
- Returns appropriate exit codes

### 3. KiloCode Workflow

1. **Get Command**: Call `start_review()` to get the Python command
2. **Execute**: KiloCode runs: `python /path/to/kilocode_review_standalone.py [files] --options`
3. **LLM Processing**: The tool performs complete 2-level review
4. **Save Results**: Results saved as structured JSON
5. **Retrieve**: Call `get_review_results()` to get formatted results

## Usage Example

```python
# In post-task hook or direct usage
from cc_executor.servers.mcp_kilocode_review import KilocodeReviewTools

tools = KilocodeReviewTools()

# 1. Prepare review command
result = await tools.prepare_review_script(
    files=["src/example.py"],
    context="Project context here",
    focus="security",
    severity="medium"
)

# 2. KiloCode executes the command:
# execute_command(result["command"])
# Which runs: python /path/to/kilocode_review_standalone.py src/example.py --context-file /tmp/context.txt

# 3. Later, retrieve formatted results
review = await tools.parse_review_results(result["review_id"])
print(f"Issues found: {review['issues']['total']}")
print(f"Validated issues: {review['issues']['validated']}")
```

## File Structure

```
/tmp/kilocode_reviews/
└── review_20250719_131123_e46210aa/
    ├── context.txt                               # Saved context
    └── review_results_20250719_131123_e46210aa.json  # Complete results
```

## Result Structure

```json
{
  "timestamp": "2025-07-19T13:11:23",
  "files_reviewed": ["src/example.py"],
  "configuration": {
    "focus": "security",
    "severity": "medium",
    "context_provided": true
  },
  "phase1_review": {
    "issues": [...],
    "summary": {...}
  },
  "phase2_validation": {
    "validated_issues": [...],
    "false_positives": [...],
    "implementation_notes": "..."
  },
  "summary": "Found X issues | Y validated | Z false positives"
}
```

## Integration with Hooks

The post-task-list hook (`post_task_list_review.py`) automatically triggers reviews:

```python
# Detects modified files
modified_files = await self._get_modified_files()

# Triggers KiloCode review
if modified_files:
    result = await self.review_system.run_kilocode_review(
        files=modified_files,
        context=context
    )
```

## Advantages

1. **Complete Solution**: Performs full 2-level code review without needing slash commands
2. **Works Within Limitations**: Uses only `execute_command` with Python
3. **Direct LLM Access**: Uses GPT-4 and Gemini APIs directly
4. **Structured Results**: Returns JSON for easy parsing and display
5. **Extensible**: Easy to add more review phases or customize prompts

## Testing

Run the integration test to verify:

```bash
source .venv/bin/activate
python test_kilocode_complete_integration.py
```

This will:
1. Generate a Python command for review
2. Verify the standalone tool exists
3. Show expected output structure
4. Demonstrate result parsing

## Command Example

When KiloCode executes the command, it looks like:

```bash
/path/to/python /path/to/kilocode_review_standalone.py \
    src/file1.py src/file2.py \
    --context-file /tmp/kilocode_reviews/review_XXX/context.txt \
    --focus security \
    --severity medium \
    --output /tmp/kilocode_reviews/review_XXX/review_results_XXX.json
```

## Summary

The integration provides a complete code review solution that works within KiloCode's `execute_command` limitations. By creating a standalone Python tool that performs the full 2-level review using LLMs directly, we enable automated code reviews without requiring programmatic access to slash commands. The solution is seamless, returns structured results, and can be easily integrated into any workflow.