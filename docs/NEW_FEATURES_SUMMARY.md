# New Features Added to cc_execute

## Summary

Five key features have been added to improve reliability and usability of the cc_execute Python API:

## 1. Token Limit Pre-Check & Auto-Truncation

**Function**: `check_token_limit(task: str, max_tokens: int = 190000) -> str`

- Automatically checks prompt length before sending to Claude
- Truncates prompts that exceed 190k tokens (leaving 10k for response)
- Prevents the #1 cause of execution failures
- Applied automatically within cc_execute

**Example**:
```python
# This happens automatically inside cc_execute
task = check_token_limit(very_long_prompt)
```

## 2. Rate Limit Retry with Tenacity

**Implementation**: `@retry` decorator on `_execute_claude_command`

- Uses tenacity library for clean, flexible retry logic
- Retries up to 3 times on rate limit errors
- Exponential backoff: 5 seconds → 10 seconds → 20 seconds (max 60s)
- Custom `RateLimitError` exception for specific handling
- Much cleaner than manual retry loops

**Configuration**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    retry=retry_if_exception_type(RateLimitError)
)
```

## 3. Ambiguous Prompt Detection

**Function**: `detect_ambiguous_prompt(task: str) -> Optional[str]`

- Complements the existing `amend_prompt` feature
- Provides quick heuristic checks for problematic patterns:
  - Command-style prompts ("Write", "Create", "Build")
  - Overly brief prompts (< 5 words)
  - Long unstructured prompts
  - Interactive language ("help me", "guide me")
- Returns warning message or None if prompt is good
- Applied automatically with warnings logged

**Example**:
```python
warning = detect_ambiguous_prompt("Write code")
# Returns: "Starts with 'Write' - consider question format: 'What is...'; Very brief prompt - may be too vague"
```

## 4. Execution History Export

**Function**: `export_execution_history(redis_client=None, format="json", limit=100) -> str`

- Exports task execution history from Redis
- Supports JSON and CSV formats
- Includes timing data, success rates, and last run times
- Useful for analyzing performance patterns
- Leverages existing Redis infrastructure

**Example**:
```python
# Export as JSON
history = await export_execution_history(format="json", limit=50)

# Export as CSV
history_csv = await export_execution_history(format="csv")
```

## 5. Progress Callback Support

**Parameter**: `progress_callback: Optional[Callable[[str], Any]]`

- Unidirectional progress reporting (not bidirectional like MCP)
- Called at key points during execution:
  - Start of execution
  - During streaming when progress indicators detected
  - On completion
  - On rate limit retries
- Enables better UX for long-running tasks

**Example**:
```python
async def my_callback(message: str):
    print(f"[PROGRESS] {message}")

result = await cc_execute(
    "Complex task...",
    progress_callback=my_callback
)
```

## Usage Example

```python
from cc_executor.client.cc_execute import cc_execute

# All features work together automatically
result = await cc_execute(
    "Create a comprehensive REST API with authentication",  # Will be checked for ambiguity
    json_mode=True,
    progress_callback=lambda msg: print(f"Progress: {msg}")  # Get updates
)
# Token limits checked ✓
# Rate limits handled ✓
# Progress reported ✓
# History saved to Redis ✓
```

## Benefits

1. **Increased Reliability**: Automatic handling of common failure modes
2. **Better Observability**: Progress callbacks and history export
3. **Cleaner Code**: Tenacity decorator instead of manual retry loops
4. **Proactive Warnings**: Detect issues before they cause failures
5. **No Breaking Changes**: All features integrate seamlessly

## Implementation Notes

- Token limit checking uses rough estimate (1 token ≈ 4 characters)
- Rate limit detection looks for patterns: 'rate limit', '429', 'too many requests'
- History export scans Redis keys with pattern `task:timing:*`
- Progress callbacks are async-compatible
- All features respect existing behavior and defaults