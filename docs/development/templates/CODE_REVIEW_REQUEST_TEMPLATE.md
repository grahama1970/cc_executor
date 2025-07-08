# Code Review Request Template

## Overview

This template standardizes code review requests for the CC Executor project, ensuring all necessary information is provided and reviews focus on the most important aspects.

**Last Updated**: 2025-01-04 (Enhanced with project learnings)

## Template

```markdown
# Code Review Request: [Brief Title]

## Summary

[2-3 sentences describing the changes and their purpose]

**CRITICAL: Multi-Task Sequential Execution Status** (If Applicable)
- [ ] Changes maintain WebSocket blocking for sequential execution
- [ ] No parallel execution introduced
- [ ] Orchestrator pattern preserved

## Changes Made

### Files Modified/Created
- `path/to/file1.py` - [Brief description of changes]
- `path/to/file2.py` - [Brief description of changes]
- `path/to/new_file.py` - [New file: purpose]

### Key Changes

1. **[Category 1]**: [Description]
   - Specific change 1
   - Specific change 2

2. **[Category 2]**: [Description]
   - Specific change 1
   - Specific change 2

## Testing Performed

### Automated Tests
- [ ] All `if __name__ == "__main__"` blocks execute successfully
- [ ] Results saved to `tmp/responses/` and verified
- [ ] Assertions pass for expected behavior
- [ ] Exit codes correct (0 for success, 1 for failure)
- [ ] No circular imports or recursive loops
- [ ] Hook system doesn't cause server crashes

### Manual Testing
```bash
# Commands used for testing
python script_name.py
# Output: Success, results saved to tmp/responses/script_results_20250104_123456.json
```

### Test Results Summary
- **Success Rate**: X/Y tests passed
- **Performance**: Average execution time
- **Edge Cases**: Handled/tested

## Code Quality Checklist

### Structure
- [ ] Functions outside `__main__` block
- [ ] Single `asyncio.run()` call
- [ ] Proper import organization
- [ ] Type hints on all functions

### Documentation
- [ ] Clear docstrings with purpose
- [ ] Real-world examples provided
- [ ] Third-party documentation links
- [ ] Inline comments where needed

### Error Handling
- [ ] Try/except blocks with logging
- [ ] Graceful service degradation
- [ ] Meaningful error messages
- [ ] Proper exit codes

### Best Practices
- [ ] Loguru for all logging (no print statements)
- [ ] Redis for simple caching with availability check
- [ ] JSON output prettified with indent=2
- [ ] Results saved with timestamps in tmp/responses/
- [ ] Thread-safe singleton patterns where needed
- [ ] Subprocess streams properly drained (prevent deadlock)

## Potential Issues to Review

### 1. [Issue Title]
**File**: `path/to/file.py`
**Line**: 123-145
**Description**: [Explain the potential issue]
**Risk Level**: High/Medium/Low
**Suggested Fix**: [Optional suggestion]

### 2. [Issue Title]
[Same format as above]

## Performance Considerations

- **Memory Usage**: [Any concerns about memory usage]
- **Execution Time**: [Expected time for operations]
- **Scalability**: [How it handles larger inputs]
- **Resource Cleanup**: [Proper cleanup implemented?]

## Security Considerations

- [ ] No hardcoded credentials
- [ ] Input validation implemented
- [ ] No command injection vulnerabilities
- [ ] Safe file path handling

## Dependencies

### New Dependencies
- `package_name==1.2.3` - [Purpose]

### Updated Dependencies
- `existing_package` from 1.0.0 to 1.1.0 - [Reason]

## Backwards Compatibility

- [ ] Changes are backwards compatible
- [ ] Migration guide provided if needed
- [ ] Deprecation warnings added where appropriate

## Questions for Reviewer

1. [Specific question about implementation choice]
2. [Request for feedback on specific approach]
3. [Any areas of uncertainty]

**Common Questions to Consider:**
- Does this maintain sequential execution for the orchestrator pattern?
- Are subprocess streams properly drained to prevent deadlock?
- Is the hook initialization thread-safe?
- Should this functionality use cc_execute.md for isolation?

## Review Focus Areas

Please pay special attention to:
1. [Area 1 - e.g., error handling in websocket connections]
2. [Area 2 - e.g., Redis caching strategy]
3. [Area 3 - e.g., async operation efficiency]

## Definition of Done

- [ ] All tests pass
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Performance acceptable
- [ ] Security concerns addressed
- [ ] Code follows project patterns
```

## Example Code Review Request

```markdown
# Code Review Request: WebSocket Handler Improvements

## Summary

This PR improves the WebSocket handler's reliability by adding retry logic, better error handling, and comprehensive logging. It also ensures all functions follow the project's script template pattern.

## Changes Made

### Files Modified
- `src/cc_executor/core/websocket_handler.py` - Restructured to follow template pattern
- `src/cc_executor/core/models.py` - Added new status types
- `tests/integration/test_websocket.py` - New integration tests

### Key Changes

1. **Structure Improvements**:
   - Moved all functions outside `__main__` block
   - Consolidated to single `asyncio.run()` call
   - Added comprehensive docstring with examples

2. **Error Handling**:
   - Added exponential backoff for retries
   - Graceful degradation when Redis unavailable
   - Better timeout handling with configurable limits

3. **Logging Enhancements**:
   - Replaced all print() with logger calls
   - Added performance metrics logging
   - Structured logs for easier parsing

## Testing Performed

### Automated Tests
- [x] All `if __name__ == "__main__"` blocks execute successfully
- [x] Results saved to `tmp/responses/` and verified
- [x] Assertions pass for expected behavior
- [x] Exit codes correct (0 for success, 1 for failure)

### Manual Testing
```bash
# Test basic WebSocket connection
python websocket_handler.py
# Output: Success, results saved to tmp/responses/websocket_test_20250104_143022.json

# Test with timeout
python websocket_handler.py --timeout 30
# Output: Handled timeout gracefully with proper error message
```

### Test Results Summary
- **Success Rate**: 15/15 tests passed
- **Performance**: Average response time 250ms
- **Edge Cases**: Timeout, connection drops, invalid messages all handled

## Code Quality Checklist

### Structure
- [x] Functions outside `__main__` block
- [x] Single `asyncio.run()` call
- [x] Proper import organization
- [x] Type hints on all functions

### Documentation
- [x] Clear docstrings with purpose
- [x] Real-world examples provided
- [x] Third-party documentation links
- [x] Inline comments where needed

## Potential Issues to Review

### 1. Redis Connection Pool Size
**File**: `src/cc_executor/core/websocket_handler.py`
**Line**: 89-95
**Description**: Default pool size might be too small for high concurrency
**Risk Level**: Medium
**Suggested Fix**: Make pool size configurable via environment variable

### 2. Message Size Limit
**File**: `src/cc_executor/core/websocket_handler.py`
**Line**: 234
**Description**: No explicit limit on WebSocket message size
**Risk Level**: Low
**Suggested Fix**: Add configurable max message size (default 1MB)

## Performance Considerations

- **Memory Usage**: Stable at ~50MB under normal load
- **Execution Time**: 95th percentile response time under 500ms
- **Scalability**: Tested with 100 concurrent connections
- **Resource Cleanup**: All connections properly closed on shutdown

## Questions for Reviewer

1. Should we implement connection pooling for WebSocket clients?
2. Is the 30-second default timeout appropriate for all use cases?
3. Should we add Prometheus metrics for monitoring?

## Review Focus Areas

Please pay special attention to:
1. Error handling in the streaming message handler (lines 345-412)
2. Redis timeout calculation logic (lines 523-567)
3. Async task cancellation on connection drop (lines 234-256)

## Definition of Done

- [x] All tests pass
- [x] Documentation updated
- [x] No linting errors
- [x] Performance acceptable
- [x] Security concerns addressed
- [x] Code follows project patterns
```

## Code Review Response Template

```markdown
## Review Response

### Overall Assessment
[✅ Approved / 🔧 Needs Changes / ❌ Significant Issues]

### Strengths
- [Positive aspect 1]
- [Positive aspect 2]

### Required Changes
1. **[Critical Issue]**: [Description and required fix]
2. **[Important Issue]**: [Description and suggestion]

### Suggestions (Optional)
- [Nice-to-have improvement 1]
- [Performance optimization idea]

### Questions Answered
1. **Q**: Should we implement connection pooling?
   **A**: Yes, but in a separate PR. Current approach is acceptable.

2. **Q**: Is 30-second timeout appropriate?
   **A**: Consider making it configurable with 30s default.

### Specific Line Comments
- **Line 89**: Consider using `redis.connection.BlockingConnectionPool`
- **Line 234**: Add message size validation here
- **Line 523**: This calculation could be cached for performance

### Next Steps
1. Address required changes
2. Update tests for new edge cases
3. Re-request review when complete
```

## Best Practices for Code Reviews

### For Requesters
1. **Be Specific**: Point reviewers to areas of concern
2. **Test First**: Ensure all tests pass before requesting review
3. **Small PRs**: Keep changes focused and manageable
4. **Context**: Explain why changes were made, not just what

### For Reviewers
1. **Be Constructive**: Focus on improvements, not criticism
2. **Prioritize**: Distinguish between must-fix and nice-to-have
3. **Code Examples**: Provide examples for suggested changes
4. **Acknowledge Good Work**: Highlight what was done well

### Common Review Focuses

1. **Script Structure**
   - Functions in correct location (outside __main__)
   - Single asyncio.run() pattern enforced
   - Proper error handling with meaningful messages
   - No recursive imports or circular dependencies

2. **Project Patterns**
   - Logging with loguru (no print statements)
   - Redis for caching with graceful degradation
   - JSON output formatting (indent=2, sorted keys)
   - Results saved to tmp/responses/ with timestamps
   - OutputCapture pattern for consistent JSON output

3. **Async & Subprocess Handling**
   - Subprocess streams properly drained (critical!)
   - Process groups used for cleanup (os.setsid)
   - WebSocket blocking maintains sequential execution
   - Proper task cancellation and cleanup

4. **Maintainability**
   - Clear documentation with real examples
   - Consistent naming (no duplicate .txt files)
   - Testable code with assertions
   - No code duplication
   - Hook system properly integrated

5. **Critical Patterns**
   - Sequential execution preserved (no parallel)
   - Thread-safe singleton initialization
   - Deferred hook initialization to prevent crashes
   - Question format for cc_execute.md tasks

## Known Anti-Patterns to Check

### From Project Experience
1. **Subprocess Deadlock**: Not draining stdout/stderr when using PIPE
2. **Hook Initialization**: Initializing in __init__ causes server crashes
3. **Circular Imports**: CLI main.py calling itself via subprocess
4. **Multiple asyncio.run()**: Causes event loop conflicts
5. **Redis Without Check**: Assuming Redis is always available
6. **Print Instead of Logger**: Using print() for output
7. **Functions in __main__**: Logic mixed with test code
8. **Missing Process Cleanup**: Zombie processes from poor cleanup

## Summary

This template ensures code reviews are:
- Comprehensive but focused
- Constructive and actionable
- Consistent across the project
- Efficient for both requester and reviewer
- Informed by real project learnings

Following this template helps maintain code quality while enabling fast, effective reviews and avoiding known pitfalls discovered during CC Executor development.

## COMPREHENSIVE CODE-REVIEW ASSESSMENT PROCESS

When performing a code review for CC Executor, follow this rigorous assessment process:

### Scope

1. **Read the specified review-request markdown file in full**
   - No skimming - read every section thoroughly
   - Note all referenced files and changes

2. **Open every file it references and inspect them line-by-line**
   - Use Read tool to examine complete files
   - Track specific line numbers for issues

3. **Evaluate against the four Review Focus Areas:**
   
   a. **Template compliance (PYTHON_SCRIPT_TEMPLATE.md)**
      - Verify shebang, docstring, imports organization
      - Check function placement (outside `__main__`)
      - Validate single `asyncio.run()` pattern
      - Ensure proper logging with loguru
      - Confirm results saved to `tmp/responses/`
   
   b. **Report structure (TASK_LIST_REPORT_TEMPLATE.md)**
      - Verify all required sections present
      - Check raw JSON inclusion for each task
      - Validate anti-hallucination measures
      - Ensure proper timestamp and session tracking
   
   c. **Hook integration (pre/post hooks & sequential guarantees)**
      - Verify pre-flight checks run before execution
      - Confirm post-execution reports generated
      - Validate sequential execution maintained
      - Check hook configuration in `.claude-hooks.json`
   
   d. **Error-recovery patterns (simple, non-brittle)**
      - Ensure retry logic is straightforward
      - Verify no over-engineering
      - Check error tracking mechanisms
      - Validate known fixes documentation

### Deliverables (write to tasks/executor/incoming)

#### A. `NNN_<slug>_assessment.md`
Create a comprehensive assessment containing:
- **Strengths & weaknesses per focus area**
  - What's done well
  - What needs improvement
  - Missing elements
- **Exact file + line references for each issue**
  - E.g., "websocket_handler.py:234 - Missing error handling"
- **Impact analysis and overall verdict**
  - Critical/High/Medium/Low impact ratings
  - APPROVED/NEEDS_CHANGES/REJECTED verdict

#### B. Update or create `NNN_<slug>_fixes.json`
Create a task list with:
- **ONE task per finding, numbered 00N_**
- **Priority levels**: critical, high, medium, low
- **Component tags**: hooks, core, cli, client, docs
- **Keep tasks minimal, iterative, non-brittle**

Example structure:
```json
{
  "review_id": "021_comprehensive_project_review",
  "tasks": [
    {
      "id": "001_fix_redis_timeout",
      "priority": "medium",
      "component": "hooks",
      "file": "task_list_completion_report.py",
      "line": 65,
      "issue": "Redis connection might hang",
      "fix": "Add connection timeout parameter"
    }
  ]
}
```

### Rules

- **No skimming**: Cite real line numbers and actual code
- **Provide both deliverables**: Narrative assessment AND task list
- **Do not add complexity**: Keep fixes simple and targeted
- **Be specific**: Vague feedback helps no one
- **Consider impact**: Focus on what matters most

### Example Review Command

```markdown
PLEASE PERFORM A COMPREHENSIVE CODE-REVIEW ASSESSMENT

Review: src/cc_executor/tasks/orchestrator/incoming/021_comprehensive_project_review_and_validation.md

Start the assessment immediately and produce:
1. 021_comprehensive_project_review_assessment.md
2. 021_comprehensive_project_review_fixes.json

Both in src/cc_executor/tasks/executor/incoming/
```