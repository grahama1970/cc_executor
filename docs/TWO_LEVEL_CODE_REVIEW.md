# Two-Level Code Review System

## Overview

The Two-Level Code Review System provides automated, comprehensive code review after task list completion. It uses two AI models in sequence to provide different perspectives and catch more issues:

1. **Level 1**: o3 model (or GPT-4 fallback) performs initial comprehensive review
2. **Level 2**: Gemini provides meta-analysis of the first review and adds additional insights

## Architecture

```
Task List Completion
        ↓
Post-Task-List Hook
        ↓
File Detection (Git + Redis)
        ↓
┌─────────────────┐
│ Level 1: o3/GPT4│
│ - Code Quality  │
│ - Security      │
│ - Performance   │
│ - Architecture  │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Level 2: Gemini │
│ - Meta Review   │
│ - Missing Issues│
│ - Priority Adj. │
│ - Summary       │
└────────┬────────┘
         ↓
Formatted Review Report
         ↓
Saved to /tmp/code_reviews/
```

## Components

### 1. **post_task_list_review.py**
- Detects when all tasks in a list are complete
- Identifies modified files through Git and Redis tracking
- Triggers the 2-level review process

### 2. **two_level_code_review.py**
- Orchestrates the review process
- Prepares prompts for each model
- Formats and saves the final report

### 3. **hook_integration.py**
- Integrates with existing hook system
- Handles the `post-task-list` event

### 4. **mcp_client.py**
- Provides interface to call MCP tools
- Handles model communication

## Usage

### Automatic Triggering

The review automatically triggers when:
1. All tasks in a task list are marked complete
2. Modified files are detected
3. `DISABLE_CODE_REVIEW` is not set to '1'

### Manual Testing

```bash
# Run the test script
python test_two_level_review.py

# Test individual components
python src/cc_executor/hooks/post_task_list_review.py --test
python src/cc_executor/hooks/two_level_code_review.py
```

### Environment Variables

```bash
# Disable code review
export DISABLE_CODE_REVIEW=1

# Set session ID (usually automatic)
export CLAUDE_SESSION_ID=my_session_123

# Set context (for task list detection)
export CLAUDE_CONTEXT="Working on task_list.md"
```

## Review Output Format

The system generates a comprehensive markdown report:

```markdown
# 🔍 Two-Level Code Review Report

**Generated**: 2024-01-15 10:30:00
**Session**: session_123
**Files Reviewed**: 5

## 📊 Review Summary
- Task Completion: 5/5 tasks completed
- Success Rate: 100.0%

## 🤖 Level 1: Initial Code Review
[Detailed code review from o3/GPT-4]

## 🧠 Level 2: Meta Review Analysis
[Gemini's analysis of the first review]

## 📝 Files Reviewed
- file1.py
- file2.py
...

## 🎯 Action Items
### 🔴 Critical Issues
### 🟡 Important Improvements
### 🟢 Suggestions
```

## Integration with Task System

The review system integrates with the existing task tracking:

1. **Task Completion Tracking**: Uses Redis to track task status
2. **File Modification Detection**: Combines Git diff and Redis file edit tracking
3. **Session Management**: Links reviews to specific Claude sessions

## Model Configuration

### Primary Models
- **Level 1**: o3-mini (via LiteLLM)
- **Level 2**: Gemini (via llm_instance)

### Fallback Models
- **Level 1 Fallback**: GPT-4 (if o3 unavailable)
- **Level 2 Fallback**: Gemini CLI direct call

## Customization

### Adding Review Criteria

Edit `_prepare_o3_prompt()` in `two_level_code_review.py`:

```python
def _prepare_o3_prompt(self, files: List[str], context: Dict) -> str:
    # Add custom review criteria
    prompt += """
## Additional Review Criteria
6. **Your Custom Criteria**
   - Specific checks
   - Custom standards
"""
```

### Changing Severity Levels

Modify the emoji indicators in the prompt:
- 🔴 Critical (must fix)
- 🟡 Important (should fix)
- 🟢 Suggestion (nice to have)
- 🔵 Custom level

### Output Location

Reviews are saved to `/tmp/code_reviews/` by default. Change in `TwoLevelCodeReview.__init__()`:

```python
self.output_dir = Path("/your/custom/path")
```

## Troubleshooting

### Review Not Triggering

1. Check all tasks are marked complete:
   ```bash
   redis-cli hgetall task:status
   ```

2. Verify session ID is set:
   ```bash
   echo $CLAUDE_SESSION_ID
   ```

3. Ensure task list context:
   ```bash
   echo $CLAUDE_CONTEXT  # Should contain "task_list"
   ```

### Model Errors

1. **o3 not available**: System falls back to GPT-4
2. **API keys missing**: Set appropriate environment variables
3. **Timeout errors**: Increase timeout in `mcp_client.py`

### No Files Detected

1. Check Git status: `git status`
2. Verify Redis tracking: `redis-cli keys "hook:file_edit:*"`
3. Ensure files were actually modified during session

## Performance Considerations

- **File Limit**: Reviews up to 10 files to avoid token limits
- **Timeout**: 5 minutes per model call
- **Caching**: Results cached in Redis for 24 hours

## Future Enhancements

1. **Incremental Reviews**: Review only changed portions
2. **Custom Model Selection**: Configure which models to use
3. **Integration with CI/CD**: Trigger on git hooks
4. **Team Collaboration**: Share reviews with team
5. **Historical Analysis**: Track code quality over time

## Example Integration

```python
# In your task completion handler
async def on_task_list_complete(session_id: str):
    """Called when all tasks are done."""
    
    # Trigger code review
    context = {
        "session_id": session_id,
        "trigger": "task_completion"
    }
    
    from cc_executor.hooks.hook_integration import get_hook_integration
    hooks = get_hook_integration()
    
    result = await hooks.execute_hook('post-task-list', context)
    
    if result and result.get('success'):
        print(f"Code review completed: {result.get('review_result', {}).get('output_file')}")
```

## Security Considerations

1. **File Access**: Only reviews files accessible to the process
2. **API Keys**: Stored in environment, not in code
3. **Output Sanitization**: Review outputs are text-only
4. **Rate Limiting**: Respects API rate limits with retries

## Contributing

To add new review models or criteria:

1. Add model configuration in `two_level_code_review.py`
2. Update prompts for specific focus areas
3. Test with `test_two_level_review.py`
4. Submit PR with example outputs