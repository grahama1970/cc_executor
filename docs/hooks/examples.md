# Hook Usage Examples Documentation

This document provides a comprehensive guide to testing and using all hooks in the cc_executor system. Each hook now includes built-in usage examples that can be run with the `--test` flag.

## Overview

All hooks in `/src/cc_executor/hooks/` have been updated with:
1. Comprehensive usage examples accessible via `--test` flag
2. Self-contained test cases demonstrating functionality
3. Redis integration tests (when available)
4. Edge case handling demonstrations
5. Full workflow examples

## Running Hook Tests

To test any hook independently:

```bash
# Test individual hooks
python src/cc_executor/hooks/analyze_task_complexity.py --test
python src/cc_executor/hooks/check_task_dependencies.py --test
python src/cc_executor/hooks/claude_instance_pre_check.py --test
python src/cc_executor/hooks/claude_response_validator.py --test
python src/cc_executor/hooks/claude_structured_response.py --test
python src/cc_executor/hooks/record_execution_metrics.py --test
python src/cc_executor/hooks/review_code_changes.py --test
python src/cc_executor/hooks/setup_environment.py --test
python src/cc_executor/hooks/task_list_preflight_check.py --test
python src/cc_executor/hooks/truncate_logs.py --test
python src/cc_executor/hooks/update_task_status.py --test

# Test hook debugging utilities
python src/cc_executor/hooks/debug_hooks.py --test
python src/cc_executor/hooks/debug_hooks.py all  # Run all hook tests
```

## Hook Descriptions and Test Coverage

### 1. analyze_task_complexity.py
**Purpose**: Analyzes task complexity using BM25 similarity search against historical tasks.

**Test Coverage**:
- Complexity estimation for various task types
- File extraction from .md and .py files
- BM25 similarity scoring
- Timeout prediction based on complexity
- Redis storage and retrieval

### 2. check_task_dependencies.py
**Purpose**: Ensures previous tasks completed and WebSocket is ready before execution.

**Test Coverage**:
- Task extraction from various formats
- Package requirement detection
- WebSocket readiness checks
- System resource validation
- Dependency chain verification

### 3. claude_instance_pre_check.py
**Purpose**: Comprehensive pre-execution environment validation for Claude instances.

**Test Coverage**:
- Virtual environment detection and validation
- MCP configuration checking
- Python path setup
- Dependency verification
- Environment variable configuration
- Command enhancement for Claude

### 4. claude_response_validator.py
**Purpose**: Validates Claude responses to detect hallucinations and incomplete work.

**Test Coverage**:
- Response quality analysis (complete, partial, hallucinated, etc.)
- Evidence extraction from responses
- Hallucination detection patterns
- Complexity scoring
- Self-reflection prompt generation
- Redis metrics storage

### 5. claude_structured_response.py
**Purpose**: Enforces structured response format similar to LiteLLM/OpenAI structured outputs.

**Test Coverage**:
- Response template generation
- Response parsing and validation
- Task status determination
- Retry prompt creation
- Workflow demonstration

### 6. debug_hooks.py
**Purpose**: Provides utilities for testing individual hooks in isolation.

**Test Coverage**:
- Environment context conversion
- Hook runner mechanism
- Individual hook debugging functions
- Custom context testing

### 7. record_execution_metrics.py
**Purpose**: Records execution metrics and triggers self-reflection when needed.

**Test Coverage**:
- Output quality analysis
- Performance metrics calculation
- Reflection trigger conditions
- Redis metrics storage
- Full workflow demonstration

### 8. review_code_changes.py
**Purpose**: Reviews code changes using static analysis and optionally perplexity-ask.

**Test Coverage**:
- Diff parsing and function extraction
- Review decision logic
- Static security analysis
- Risk level assessment
- Review report formatting

### 9. setup_environment.py
**Purpose**: Ensures proper Python virtual environment activation before commands.

**Test Coverage**:
- Virtual environment detection
- Command wrapping logic
- Environment variable setup
- Path resolution
- Redis storage of environment data

### 10. task_list_preflight_check.py
**Purpose**: Pre-flight validation for task lists to predict failure risks.

**Test Coverage**:
- Task extraction from markdown
- Complexity calculation
- Failure rate prediction
- Risk assessment
- Report generation
- Blocking issue detection

### 11. truncate_logs.py
**Purpose**: Truncates large logs to prevent bloat while preserving essential information.

**Test Coverage**:
- Binary content detection
- Smart truncation strategies
- Line and size limits
- Different output types
- Redis metrics storage

### 12. update_task_status.py
**Purpose**: Updates task status after execution and triggers self-improvement.

**Test Coverage**:
- Task info parsing
- Exit code interpretation
- Improvement strategy determination
- Metrics update
- Self-improvement triggering

## Common Test Patterns

All hooks follow these common patterns:

1. **Standalone Testing**: Each hook can be tested independently without the full system
2. **Redis Optional**: Tests gracefully handle Redis unavailability
3. **Edge Cases**: Each test includes edge cases and error conditions
4. **Real Examples**: Tests use realistic data and scenarios
5. **Visual Output**: Clear, formatted output showing test results

## Integration with Main System

These hooks integrate with the cc_executor system at various stages:

- **Pre-execution**: setup_environment, check_task_dependencies, claude_instance_pre_check
- **Task Analysis**: analyze_task_complexity, task_list_preflight_check
- **Response Validation**: claude_response_validator, claude_structured_response
- **Post-execution**: record_execution_metrics, update_task_status, truncate_logs
- **Code Review**: review_code_changes

## Best Practices

1. **Test Before Production**: Always run `--test` to verify hook functionality
2. **Check Redis**: Ensure Redis is running for full functionality
3. **Review Logs**: Check hook-specific logs in the logs directory
4. **Monitor Metrics**: Use Redis metrics to track hook performance
5. **Customize Thresholds**: Adjust complexity scores and thresholds based on your needs

## Troubleshooting

If a hook isn't working as expected:

1. Run with `--test` to verify basic functionality
2. Check Redis connectivity if metrics aren't being stored
3. Review the hook's log output for specific errors
4. Use debug_hooks.py to test in isolation
5. Verify environment variables are set correctly

## Contributing

When adding new hooks or modifying existing ones:

1. Always include a `--test` mode with comprehensive examples
2. Follow the existing pattern for usage demonstrations
3. Include edge case handling
4. Make Redis optional but beneficial
5. Document the hook's purpose and integration points