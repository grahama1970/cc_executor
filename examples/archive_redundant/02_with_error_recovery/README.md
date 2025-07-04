# Error Recovery Helpers Example

This example demonstrates how to use cc_executor's error recovery features to build more resilient task lists.

## What You'll Learn

- How to anticipate and document common errors
- Using retry logic and timeout adjustments
- Learning from past failures
- Building self-improving task lists

## The Example

We'll build the same TODO API but with error recovery patterns:
1. Document common errors and their fixes
2. Track past failures and successes
3. Use appropriate timeouts and retries

## Files in This Example

- `task_list.md` - Task list with error recovery annotations
- `run_example.py` - Execution script with retry logic
- `.error_recovery.json` - Tracks errors and solutions
- After execution: `todo_api/` directory with generated code

## How to Run

```bash
cd examples/02_with_error_recovery
python run_example.py
```

## Key Concepts Demonstrated

1. **Error Documentation**: Each task lists common errors and fixes
2. **Retry Logic**: Automatic retries with backoff
3. **Learning System**: Errors are tracked and solutions saved
4. **Timeout Management**: Dynamic timeout adjustment based on complexity

## Error Recovery Features

- **Pre-emptive Fixes**: Common errors documented upfront
- **Automatic Retries**: Failed tasks retry with fixes applied
- **Knowledge Base**: `.error_recovery.json` grows over time
- **Self-Healing**: System learns from failures