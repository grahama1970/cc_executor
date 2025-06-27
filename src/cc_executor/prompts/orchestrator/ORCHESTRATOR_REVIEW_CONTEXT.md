# O3 Review Context for CC-Executor MCP Implementation

## Project Overview

**CC-Executor** is a Model Context Protocol (MCP) WebSocket service that enables bidirectional communication with long-running Claude Code instances in Docker containers. The core problem it solves is reliable execution of complex tasks without timeouts, with real-time control over process execution.

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────┐     Subprocess     ┌─────────────┐
│   Client    │ ◄─────────────────► │  MCP Service │ ◄─────────────────► │   Claude    │
│  (Claude)   │    JSON-RPC 2.0     │   (Python)   │    OS Signals      │    Code     │
└─────────────┘                     └──────────────┘                     └─────────────┘
```

## Key Features Implemented

1. **Process Control**: Direct PAUSE/RESUME/CANCEL via OS signals (SIGSTOP/SIGCONT/SIGTERM)
2. **Back-Pressure Handling**: Buffer management prevents memory exhaustion from high-output processes
3. **Concurrent Sessions**: Support for multiple parallel executions
4. **Structured Logging**: JSON logs with request tracking
5. **Security**: Command allow-list configuration

## Implementation Files

### Core Implementation (Refactored as of 2025-06-25)
The original `core/implementation.py` (503 lines) has been refactored into 8 modular components:
- **`core/config.py`** (143 lines) - Configuration constants and environment variables
- **`core/models.py`** (245 lines) - Pydantic models for JSON-RPC and validation
- **`core/session_manager.py`** (362 lines) - WebSocket session lifecycle management
- **`core/process_manager.py`** (426 lines) - Process execution and control
- **`core/stream_handler.py`** (369 lines) - Stream handling with back-pressure
- **`core/websocket_handler.py`** (495 lines) - WebSocket protocol and routing
- **`core/main.py`** (283 lines) - FastAPI application and endpoints
- **`core/__init__.py`** (52 lines) - Package definition

Original implementation archived at: `archive/implementation.py.old`

### Task Implementations (To Review)
These are the graduated task implementations that should be reviewed:
- **`tasks/T00_read_understand.py`** - Context analysis tool
- **`tasks/T01_robust_logging.py`** - Structured logging implementation
- **`tasks/T02_backpressure_handling.py`** - Buffer management for high-output processes
- **`tasks/T03_websocket_stress_tests.py`** - Comprehensive stress test suite
- **`tasks/T05_security_pass.py`** - Command allow-list security

### Associated Prompts
Each task has a corresponding self-improving prompt in `prompts/`:
- `prompts/T00_read_understand.md`
- `prompts/T01_robust_logging.md`
- `prompts/T02_backpressure_handling.md`
- `prompts/T03_websocket_stress_tests.md`
- `prompts/T05_security_pass.md`

## Review Requirements

### 1. Self-Improving Prompt Template Compliance
All prompts must follow the template at `templates/SELF_IMPROVING_PROMPT_TEMPLATE.md`:
- Gamification metrics tracking (Success/Failure/Ratio)
- Evolution history
- Recovery tests (minimum 3)
- Usage functions that demonstrate real functionality

### 2. Code Quality Standards
- Each Python file must have usage functions in `if __name__ == "__main__"`
- Usage functions must test real functionality, not just imports
- All code must be executable and verifiable
- Structured logging throughout

### 3. Verification Requirements
- Every execution must be verifiable via transcript markers
- Usage functions must print unique markers (e.g., `MARKER_20250625_143022`)
- Results must be programmatically verified (assertions or checks)

## Testing Instructions

To run the MCP service:
```bash
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/core
python main.py --port 8003
# Or use Docker: docker compose up
```

To run stress tests:
```bash
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress
python unified_stress_test_executor.py
```

To run individual task implementations:
```bash
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks
python T01_robust_logging.py  # Example
```

## Critical Context for Review

1. **Bidirectional Communication**: The MCP protocol allows real-time control of subprocesses, not just fire-and-forget execution
2. **Reliability Focus**: The user prioritized reliability over security - the system must handle long-running processes without failure
3. **Back-Pressure is Critical**: High-output processes (like `yes | pv -qL 50000`) must not cause memory exhaustion
4. **Process Group Management**: Using `os.setsid()` ensures entire process trees can be controlled
5. **No Heartbeat Needed**: Continuous streaming serves as implicit heartbeat in bidirectional WebSocket

## Review Output Requirements

### File Naming Convention

O3 MUST create files following this exact naming pattern:

**Format**: `{SEQUENCE}_{COMPONENT}_{TYPE}.{ext}`

- **SEQUENCE**: Use the same 3-digit number from the review request (e.g., 001)
- **COMPONENT**: Use the exact component name from the review request (e.g., T01_robust_logging)
- **TYPE**: 
  - `review_feedback` for your markdown review
  - `fixes` for the JSON task list
- **ext**: `.md` for review, `.json` for fixes

### Required Output Files

For each review, O3 MUST create TWO files in the `executor/` directory:

1. **Review Feedback**: `{SEQUENCE}_{COMPONENT}_review_feedback.md`
   - Example: `001_T01_robust_logging_review_feedback.md`
   - Follow the format in REVIEW_PROMPT_AND_CODE_TEMPLATE.md
   - Include execution logs and specific line-referenced fixes

2. **Fix Tasks JSON**: `{SEQUENCE}_{COMPONENT}_fixes.json`
   - Example: `001_T01_robust_logging_fixes.json`
   - Structured task list for Claude to implement
   ```json
   {
     "review_id": "001_T01_robust_logging",
     "component": "T01_robust_logging",
     "date": "2025-06-25",
     "fixes": [
       {
         "id": 1,
         "severity": "critical|major|minor",
         "file": "implementation.py or prompt.md",
         "line": 45,
         "issue": "Clear description of the problem",
         "fix": "Specific fix to implement",
         "verification": "How to test the fix"
       }
     ]
   }
   ```

### Where to Save Files

**ALWAYS save both files in**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/executor/`

This is the same directory where you found the review request.

### Example Workflow

1. O3 receives: `orchestrator/001_websocket_reliability_review_request.md` (review request still arrives in orchestrator folder)
2. O3 creates:
   - `executor/001_websocket_reliability_review_feedback.md`
   - `orchestrator/001_websocket_reliability_fixes.json`
3. Claude reads the fixes and works in `executor/` directory
   - Claude has context at `executor/EXECUTOR_CONTEXT.md` for handling fixes

## Expected Review Actions

O3 should:
1. Execute each task's usage function and verify it works
2. Check compliance with self-improving prompt template
3. Verify that prompts have accurate metrics and evolution history
4. Ensure code has proper error handling and logging
5. Identify any architectural issues or missing functionality
6. Provide specific, line-referenced fixes for Claude to implement
7. Save output files with correct names in the orchestrator directory

## Common Issues to Check

1. **Missing Recovery Tests**: Each prompt needs at least 3 recovery test scenarios
2. **Fake Metrics**: Ensure Success/Failure counts reflect actual executions
3. **Import-Only Tests**: Usage functions must test real functionality
4. **Missing Verification**: All outputs must be programmatically verified
5. **Template Deviations**: Prompts must follow the exact template structure

## File Paths for Review

Review these task implementation pairs:
1. `prompts/T01_robust_logging.md` + `tasks/T01_robust_logging.py`
2. `prompts/T02_backpressure_handling.md` + `tasks/T02_backpressure_handling.py`
3. `prompts/T03_websocket_stress_tests.md` + `tasks/T03_websocket_stress_tests.py`
4. `prompts/T05_security_pass.md` + `tasks/T05_security_pass.py`

The main implementation (now split across `core/*.py` modules) incorporates all these features and should be checked for proper integration. See review request 003 for details on the modularization.

## Review History

1. **001_websocket_reliability** - Initial review of WebSocket service reliability
   - Identified 6 critical fixes (race conditions, buffer management, etc.)
   - All fixes implemented by executor
   
2. **002_websocket_reliability** - Second round after fix implementation
   - Verified fixes were properly implemented
   - Identified additional edge cases
   
3. **003_modularization** - Post-refactoring review request (2025-06-25)
   - Refactored 503-line implementation.py into 8 modules
   - All modules follow file rules (<500 lines, documented)
   - Ready for architectural review