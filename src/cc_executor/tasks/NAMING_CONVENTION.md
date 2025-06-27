# Task Naming Convention

To maintain traceability between reviews and implementations, use this naming scheme:

## Format: `{SEQUENCE}_{FOCUS_AREA}_{TYPE}.{ext}`

### Components:
- **SEQUENCE**: 3-digit number (001, 002, etc.)
- **FOCUS_AREA**: Technical challenge being reviewed (e.g., websocket_reliability, process_control, backpressure_handling)
- **TYPE**: File purpose (review_request, review_feedback, implementation, fixes)
- **ext**: File extension (md, json, py)

## Examples:

### Orchestrator (O3) Files:
```
001_websocket_reliability_review_request.md    # Review request for WebSocket issues
001_websocket_reliability_review_feedback.md   # O3's findings
001_websocket_reliability_fixes.json           # Specific bugs to fix

002_backpressure_memory_review_request.md     # Review for memory management
002_backpressure_memory_review_feedback.md    # O3's analysis
002_backpressure_memory_fixes.json            # Memory leak fixes
```

### Executor (Claude) Files:
```
001_websocket_reliability_implementation.py    # Fix for connection issues
001_websocket_reliability_test_results.md     # Test verification
002_backpressure_memory_implementation.py     # Memory management fixes
```

## Focus Areas (Examples):
- `websocket_reliability` - Connection handling, disconnection cleanup
- `process_control` - SIGSTOP/SIGCONT, process groups, orphan prevention
- `backpressure_handling` - Buffer management, memory limits
- `concurrent_sessions` - Multi-connection isolation
- `error_recovery` - Graceful failure handling
- `state_consistency` - Session state management

## Workflow Example:

1. **Identify core challenge**:
   - "WebSocket connections drop and leave orphaned processes"

2. **Submit for review**:
   - `orchestrator/001_websocket_reliability_review_request.md`

3. **O3 reviews and finds bugs**:
   - `orchestrator/001_websocket_reliability_review_feedback.md`
   - `orchestrator/001_websocket_reliability_fixes.json`

4. **Claude implements fixes**:
   - `executor/001_websocket_reliability_implementation.py`
   - Tests fixes and documents results

5. **If more issues found**:
   - `orchestrator/002_websocket_reliability_review_request.md` (sequence increments)

## Benefits:
- Clear linkage between all related files
- Easy to sort chronologically
- Can track review iterations (001, 002, etc.)
- Component name stays consistent throughout