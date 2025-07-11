# CC Execute Issues

This directory contains critical issues that need to be resolved for CC Execute to function properly.

## Current Issues

### 001 - Output Buffer Deadlock [HIGH PRIORITY]
- **File**: [001_output_buffer_deadlock.md](./001_output_buffer_deadlock.md)
- **Status**: UNRESOLVED
- **Impact**: Blocks all tasks that generate >64KB output
- **Affects**: PDF processing, code generation, detailed analysis
- **Root Cause**: Subprocess waits for exit before reading output, causing deadlock

### 002 - Excessive Execution Time [HIGH PRIORITY]
- **File**: [002_excessive_execution_time.md](./002_excessive_execution_time.md)
- **Status**: UNRESOLVED
- **Impact**: 60+ seconds for tasks that should take 10-20 seconds
- **Affects**: All complex tasks, iterative development, CI/CD
- **Root Cause**: Full CLI startup overhead, no context reuse, no caching

### 003 - No Partial Results on Timeout [HIGH PRIORITY]
- **File**: [003_no_partial_results_on_timeout.md](./003_no_partial_results_on_timeout.md)
- **Status**: UNRESOLVED
- **Impact**: Complete data loss when timeout occurs
- **Affects**: Long-running tasks, batch processing
- **Root Cause**: TimeoutError raised without capturing stdout

### 004 - JSON Mode Parsing Failures [HIGH PRIORITY]
- **File**: [004_json_mode_parsing_failures.md](./004_json_mode_parsing_failures.md)
- **Status**: UNRESOLVED
- **Impact**: json_mode=True frequently fails to parse valid JSON
- **Affects**: All JSON-based workflows
- **Root Cause**: Parser too strict, doesn't handle markdown blocks or extra text

## Issue Summary

| Issue | Severity | User Impact | Fix Complexity |
|-------|----------|-------------|----------------|
| Output Buffer Deadlock | Critical | Can't process large outputs | Medium |
| Excessive Execution Time | High | 10x slower than needed | High |
| No Partial Results | High | Data loss on timeout | Low |
| JSON Parsing Failures | High | Requires custom parsing | Low |

## Resolution Process

1. Issues in this directory MUST be resolved before CC Execute can be used in production
2. Each issue includes:
   - Root cause analysis
   - Proposed fix with code
   - Verification steps
   - Impact assessment

## Testing

After fixing an issue:
1. Run the verification test in the issue description
2. Test with real-world use cases (e.g., PDF processing)
3. Update issue status to RESOLVED
4. Add resolution notes with commit hash

## For CC Execute Maintainers

These issues are blocking production use of CC Execute. The ArXiv MCP Server team (and likely other users) need these resolved to adopt CC Execute for real workloads. We're happy to help test fixes!

Priority order for maximum impact:
1. Fix JSON parsing (easy win, affects everyone)
2. Fix partial results (prevents data loss)  
3. Fix buffer deadlock (enables large outputs)
4. Fix execution time (improves UX dramatically)