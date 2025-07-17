# Kilocode Review MCP Integration Guide

## Overview

The kilocode-review MCP server provides an automated code review system that understands project-specific constraints and applies contextual fixes. It integrates with Claude Code through the MCP (Model Context Protocol) to enable self-correction workflows.

## Key Features

1. **Context-Aware Reviews**: Understands project-specific patterns and constraints
2. **Actionable Fixes**: Provides pre-validated fixes that are safe to apply
3. **Asynchronous Processing**: Reviews run in background, allowing other work to continue
4. **Two-Phase Validation**: Uses multiple models for comprehensive analysis

## Architecture

```
Claude Code Agent
    ↓
mcp_kilocode_review.py (MCP Server)
    ↓
kilocode CLI tool (review-contextual command)
    ↓
Two-Phase Review Process:
  - Phase 1: O3 model with context analysis
  - Phase 2: Gemini 2.5 Pro validation
    ↓
Structured Output Files:
  - review_summary.md
  - actionable_fixes.md
  - incompatible_suggestions.md
  - context_applied.md
```

## Setup

### 1. MCP Configuration

The server is already configured in `~/.claude/claude_code/.mcp.json`:

```json
"kilocode-review": {
  "command": "uv",
  "args": [
    "--directory",
    "/home/graham/workspace/experiments/cc_executor",
    "run",
    "--script",
    "src/cc_executor/servers/mcp_kilocode_review.py"
  ],
  "env": {
    "PYTHONPATH": "/home/graham/workspace/experiments/cc_executor/src",
    "UV_PROJECT_ROOT": "/home/graham/workspace/experiments/cc_executor"
  }
}
```

### 2. Available Tools

The server provides two MCP tools:

- `mcp__kilocode-review__start_review`: Initiates an asynchronous review
- `mcp__kilocode-review__get_review_results`: Retrieves completed review results

## Usage Workflow

### Step 1: Start Review

```python
# Agent calls start_review with files to review
result = await mcp__kilocode-review__start_review(
    files="src/server1.py src/server2.py",
    focus="security",       # Optional: security, performance, maintainability, architecture
    severity="medium"       # Optional: low, medium, high, critical
)

# Returns:
{
    "success": true,
    "review_id": "docs/code_review/20250117_120000_abc123",
    "message": "Review started successfully..."
}
```

### Step 2: Wait for Completion

The review process typically takes 2-3 minutes. The agent should wait before checking results.

### Step 3: Get Results

```python
# Agent retrieves results using the review_id
results = await mcp__kilocode-review__get_review_results(
    review_id="docs/code_review/20250117_120000_abc123"
)

# Returns:
{
    "success": true,
    "results": {
        "summary": "Review summary...",
        "actionable_fixes": "Markdown with specific fixes...",
        "incompatible_suggestions": "Standard fixes not applicable...",
        "context_applied": "Project constraints considered..."
    }
}
```

### Step 4: Apply Fixes

The agent parses `actionable_fixes` and applies changes using Edit/MultiEdit tools.

## Context Management

The system uses multiple context sources:

1. **Auto-detection**: First .md file with "context" in name
2. **Project Context**: `.kilocode/CONTEXT.md` (fallback)
3. **Inline Context**: Via `--context` parameter
4. **Context File**: Via `--context-file` parameter

## Example Context File

```markdown
# CC Executor MCP Context

## Project Type
MCP servers using FastMCP framework for Claude Code integration

## Critical Constraints
1. **FastMCP Return Values**: All @mcp.tool functions MUST return JSON strings
2. **Lazy Loading**: Heavy resources (models, connections) load on first use
3. **Thread Safety**: Use locks for shared state in concurrent environments

## Patterns to Follow
- Single-file MCP servers with embedded usage examples
- Graceful error handling with MCP logger integration
- Double-checked locking for singleton resources
```

## Integration with Claude Code

### Mandatory Self-Correction Prompt

Add this to your task instructions:

```markdown
### **Mandatory Final Step: Self-Correction and Verification**

Once you believe you have completed the primary coding task, you **MUST** perform a final quality check using the `kilocode-review` tool. This is a non-negotiable step to ensure your work adheres to all project constraints.

Follow this procedure exactly:

1. **Identify Changed Files**: List all files you created or modified
2. **Initiate Review**: Call `mcp__kilocode-review__start_review` with file paths
3. **Wait for Completion**: Wait 2-3 minutes for review to complete
4. **Retrieve Results**: Call `mcp__kilocode-review__get_review_results`
5. **Apply Fixes**: If `actionable_fixes` contains suggestions, apply them exactly
6. **Conclude**: Confirm the task is complete and has passed review
```

## Benefits

1. **Consistency**: Ensures all code follows project patterns
2. **Quality**: Catches common mistakes before human review
3. **Learning**: Incompatible suggestions teach project-specific rules
4. **Efficiency**: Automated fixes save manual correction time

## Troubleshooting

### Review Not Starting
- Check if kilocode CLI is installed and accessible
- Verify file paths are correct and files exist
- Check server logs for detailed error messages

### Results Not Found
- Ensure sufficient wait time (2-3 minutes minimum)
- Verify review_id matches the one returned by start_review
- Check if review output directory exists

### Fixes Not Applying
- Parse markdown carefully to extract file paths and changes
- Ensure exact string matching when using Edit tool
- Use MultiEdit for multiple changes to same file

## Advanced Features

### Focus Areas
- `security`: SQL injection, XSS, authentication issues
- `performance`: N+1 queries, inefficient algorithms
- `maintainability`: Code complexity, duplication
- `architecture`: Design patterns, modularity

### Severity Levels
- `low`: Style and minor improvements
- `medium`: Important but not critical issues
- `high`: Significant problems affecting functionality
- `critical`: Security vulnerabilities or major bugs

## Best Practices

1. **Always Review Before Committing**: Make it part of your workflow
2. **Use Appropriate Focus**: Target specific concerns when needed
3. **Apply All Actionable Fixes**: They're pre-validated for your project
4. **Learn from Incompatible Suggestions**: Understand why they don't apply
5. **Maintain Context Files**: Keep project constraints documented

## Example Implementation

See `examples/demo_kilocode_review.py` for a complete demonstration of the workflow.

## Future Enhancements

1. **Streaming Progress**: Real-time updates during review
2. **Batch Reviews**: Review multiple PRs or branches
3. **Custom Rules**: Project-specific linting rules
4. **Integration Tests**: Verify fixes don't break functionality