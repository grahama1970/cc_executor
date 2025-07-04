# Code Review Request: CC_Execute and WebSocket Handler Integration

## Overview
This code review request covers the integration between cc_execute.md (the orchestrator entry point) and websocket_handler.py, along with supporting utilities. The system enables orchestrators to spawn fresh Claude instances with full 200K context for individual tasks.

## Key Components for Review

### 1. **cc_execute.md** (Entry Point)
- Location: `/src/cc_executor/prompts/cc_execute.md`
- Purpose: Documentation and API contract for orchestrators
- Status: Graduated prompt (10:1 success ratio)
- Describes how to use cc_execute_utils.py

### 2. **cc_execute_utils.py** (Implementation)
- Location: `/src/cc_executor/prompts/cc_execute_utils.py`
- Key function: `execute_task_via_websocket()`
- Builds Claude commands and calls websocket_handler.py via subprocess
- Returns JSON response with execution results

### 3. **websocket_handler.py** (Execution Engine)
- Location: `/src/cc_executor/core/websocket_handler.py`
- New features:
  - `--execute` flag for direct command execution
  - `execute_claude_command()` utility function at module level
  - Reorganized code structure for better accessibility
- Manages process execution, streaming, and output collection

### 4. **Supporting Files**
- `process_manager.py`: Process lifecycle management with zsh support
- `stream_handler.py`: Async streaming with chunking and timeout handling
- `models.py`: Data models for JSON-RPC protocol
- `config.py`: Configuration constants

## How It Should Work

1. **Orchestrator needs Task N executed**:
   ```python
   from cc_execute_utils import execute_task_via_websocket
   
   result = execute_task_via_websocket(
       task="Analyze this code and suggest improvements",
       timeout=120,
       tools=["Read", "Edit"]
   )
   ```

2. **cc_execute_utils.py**:
   - Builds Claude command with proper flag order: `claude -p "task" --output-format stream-json --verbose`
   - Calls websocket_handler.py with `--execute` flag
   - Captures JSON output and returns structured result

3. **websocket_handler.py**:
   - Receives command via `--execute` flag
   - Sets up environment (venv, hooks)
   - Executes command with ProcessManager
   - Streams output with StreamHandler
   - Returns JSON response with Claude's output

4. **Result**:
   - Fresh Claude instance with 200K context
   - No context pollution between tasks
   - Structured JSON response with all output
   - Sequential execution guaranteed

## Review Focus Areas

### ✅ What Works Well
- Clean separation of concerns
- Module-level functions for reusability
- JSON-based communication
- Proper error handling and logging

### 🔍 Areas for Review

1. **Error Handling**:
   - Should we add retry logic for transient failures?
   - How to handle Claude API rate limits?

2. **Performance**:
   - Is subprocess overhead acceptable?
   - Should we consider connection pooling for multiple tasks?

3. **Configuration**:
   - Should timeout be configurable at a higher level?
   - Tool selection strategy - defaults vs explicit?

4. **Logging**:
   - Current warnings about missing imports when run directly
   - Should we clean up or suppress these warnings?

5. **Testing**:
   - Need integration tests for the full flow?
   - Mock vs real Claude calls for testing?

## Request for Feedback

Looking for **iterative, helpful changes** that:
- ✅ Improve reliability without adding brittleness
- ✅ Enhance clarity without needless complexity
- ✅ Follow existing patterns in the codebase
- ✅ Make the system more maintainable

**NOT looking for**:
- ❌ Over-engineering or "enterprise" patterns
- ❌ Thread safety concerns (single-threaded by design)
- ❌ Edge cases that haven't occurred
- ❌ Performance optimizations for non-bottlenecks

## Questions for Reviewers

1. Is the subprocess approach the right choice for isolation?
2. Should we add more structured error types?
3. Any concerns with the JSON streaming approach?
4. Is the API surface clean enough for orchestrators?

## Next Steps
After review, we can iterate on specific improvements while maintaining the system's simplicity and effectiveness.