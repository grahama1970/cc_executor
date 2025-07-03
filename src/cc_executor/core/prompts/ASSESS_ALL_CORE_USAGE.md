# Core Components Usage Assessment — Self-Improving Prompt

## 🚨 CRITICAL: NO ARBITRARY TIMEOUTS - THIS IS THE ENTIRE POINT OF CC_EXECUTOR! 🚨
**THE WHOLE PROJECT EXISTS TO HANDLE LONG-RUNNING PROMPTS WITHOUT TIMEOUTS!**
- WebSocket + Redis = Intelligent timeout estimation
- NEVER impose arbitrary timeouts, especially on websocket_handler.py
- The --long test WILL take 3-5 minutes - THIS IS THE POINT!
- If websocket_handler.py fails, the project has 0% success rate
- Even the Bash tool has a 2-minute timeout - DON'T USE IT FOR LONG TESTS!

## 🚨 CRITICAL: USE THE GODDAMN HOOKS! 🚨
**HOOKS EXIST TO SET UP THE ENVIRONMENT AUTOMATICALLY!**
- Hooks are in `/home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/`
- `setup_environment.py` - Wraps commands to run in venv
- `check_task_dependencies.py` - Installs missing packages
- STOP trying to manually activate venv - THE HOOKS DO THIS!
- The hooks are EXECUTABLE SCRIPTS - RUN THEM!

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 8:1 (v8 failed - missing Claude's assessments)
- **Last Updated**: 2025-07-03
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial comprehensive usage function assessment | TBD    |
  | v2      | Added pre/post hooks and proper environment setup | TBD    |
  | v3      | Only tested --simple mode for websocket_handler.py | ❌ FAIL - Incomplete testing of core functionality |
  | v4      | Updated to test both --simple and --medium modes for websocket_handler.py | ❌ FAIL - Still missing --long test |
  | v5      | CRITICAL FIX: Removed ALL arbitrary timeouts for websocket_handler.py tests | ✅ SUCCESS - WebSocket handler completed --long test in 3.4 minutes! |
  | v6      | Manual testing with proper venv activation | ✅ SUCCESS - 19/20 components passed (95% success rate) |
  | v7      | Restructured core/ to contain only essential files | ✅ SUCCESS - 8/8 components passed (100% success rate) |
  | v8      | Failed to include MY reasonableness assessments in report | ❌ FAIL - Report missing Claude's analysis of outputs |

---
## 🏛️ ASSESSMENT PRINCIPLES (Immutable)

### 1. Purpose
Run ALL usage functions in the core/ directory WITH PROPER HOOKS, capture their raw outputs, assess reasonableness without regex/code matching, and generate a comprehensive markdown report in reports/.

**IMPORTANT**: The core/ directory now contains ONLY the essential WebSocket service files:
- main.py - FastAPI WebSocket service entry point
- config.py - Configuration and environment variables
- models.py - Pydantic models for JSON-RPC
- session_manager.py - WebSocket session lifecycle
- process_manager.py - Process execution/control
- stream_handler.py - Output streaming
- websocket_handler.py - WebSocket protocol/routing
- resource_monitor.py - System resource monitoring

All utility files have been moved to utils/, hook files to hooks/, client to client/, and examples to examples/.

### 2. CRITICAL: WebSocket Handler is THE CORE SCRIPT
- websocket_handler.py IS the main purpose of this project
- It provides WebSocket-based execution with intelligent timeout estimation
- Has THREE test modes: --simple (quick), --medium (moderate), --long (3-5 minutes)
- The --long test PROVES the system works for long-running commands

### 3. Reasonableness Assessment (No Code Execution)
For each usage function output, check if it's reasonable by looking for:
- Expected output format/structure
- Presence of relevant keywords/terms
- Appropriate data types (numbers, strings, etc.)
- Reasonable ranges for numeric values
- No obvious errors or stack traces (unless testing error handling)

## 🎯 EXECUTION TEMPLATE
**Execute this Python script to run the assessment:**

```python
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/prompts/scripts/assess_all_core_usage.py
```

This script:
1. Automatically finds all Python files in core/ with usage functions
2. Runs setup hooks before execution
3. Captures raw output without arbitrary timeouts
4. Assesses reasonableness of outputs
5. Generates a comprehensive report in prompts/reports/

## 📝 REPORT REQUIREMENTS
The generated report must include:
- Summary of pass/fail for each component
- Raw output samples for verification
- Specific indicators of reasonable output
- WebSocket handler status (CRITICAL component)
- Recommendations for any failures

## 🔄 CONTINUOUS IMPROVEMENT
After each run:
1. Update the success/failure ratio
2. Document any new issues discovered
3. Evolve the assessment based on lessons learned
4. NEVER introduce arbitrary timeouts

## 🔬 DIAGNOSTICS & RECOVERY

### Failure Report (2025-07-03) - v8
- **Failed Version:** v8
- **What Failed:** Generated report missing Claude's reasonableness assessments
- **Root Cause:** Misunderstood role - acted as passive script runner instead of active assessor
- **Evidence:** Report only contained automated script results, no Claude analysis

### Recovery Plan for v9
- **Action Required:** For EACH component output, add a section with:
  - MY assessment of why the output is reasonable (or not)
  - Specific analysis of numbers, formats, expected values
  - Judgment on whether it truly demonstrates the component works
  - Clear REASONABLE/UNREASONABLE verdict with reasoning
- **Report Format Change:** Add "Claude's Assessment" section for each component
- **Success Criteria:** Report must show MY thinking, not just script output