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
- **Success/Failure Ratio**: 9:2 (v8 & v9 failed - different issues)
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
  | v9      | Added Claude's assessments but TRUNCATED outputs in report | ❌ FAIL - Report contained "[truncated]" outputs instead of complete data |

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

## 🎯 EXECUTION PROCESS

### Step 1: Run the Automated Assessment
**Execute this Python script to generate the base report:**

```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/prompts/scripts/assess_all_core_usage.py
```

This script:
1. Automatically finds all Python files in core/ with usage functions
2. Runs setup hooks before execution
3. Captures raw output without arbitrary timeouts
4. Performs automated pass/fail assessment
5. Generates a base report in prompts/reports/

### Step 2: Add Claude's Analysis
**YOU must then:**
1. Read the generated report
2. Analyze each component's output
3. Add your reasonableness assessment following the template
4. Create a new report with your analysis included

## 📝 REPORT REQUIREMENTS
**CRITICAL**: Reports MUST follow the template at `/home/graham/workspace/experiments/cc_executor/docs/templates/CORE_ASSESSMENT_REPORT_TEMPLATE.md`

The generated report must include:
- Summary of pass/fail for each component
- **COMPLETE RAW JSON FILES with line numbers from Read tool**
- **CLAUDE'S REASONABLENESS ASSESSMENT for EACH component**
- Specific analysis of why each output is reasonable (or not)
- WebSocket handler status (CRITICAL component)
- Recommendations based on actual output analysis

**CRITICAL ANTI-HALLUCINATION REQUIREMENTS:**
1. MUST show complete JSON file content with line numbers using Read tool
2. MUST NOT show just extracted "output" field (too easy to fake)
3. MUST include ALL metadata (timestamp, duration, success, etc.)
4. Line numbers prove you actually read the file

## 🔄 CONTINUOUS IMPROVEMENT
After each run:
1. Update the success/failure ratio
2. Document any new issues discovered
3. Evolve the assessment based on lessons learned
4. NEVER introduce arbitrary timeouts

## 🔬 DIAGNOSTICS & RECOVERY

### Failure Report (2025-07-03) - v8 & v9

#### v8 Failure
- **What Failed:** Generated report missing Claude's reasonableness assessments
- **Root Cause:** Misunderstood role - acted as passive script runner instead of active assessor
- **Evidence:** Report only contained automated script results, no Claude analysis

#### v9 Failure  
- **What Failed:** Report contained TRUNCATED outputs with "[truncated]" text
- **Root Cause:** Used the assessment script's truncated output instead of reading actual JSON files
- **Evidence:** Output samples ended with "...[truncated]" instead of complete data
- **Critical Learning:** MUST read the JSON response files in tmp/responses/ for COMPLETE outputs

### Recovery Plan for v10
- **Action Required:** For EACH component output:
  - MY assessment of why the output is reasonable (or not)
  - Specific analysis of numbers, formats, expected values
  - Judgment on whether it truly demonstrates the component works
  - Clear REASONABLE/UNREASONABLE verdict with reasoning
  - **CRITICAL: Include COMPLETE outputs from JSON files - NO TRUNCATION!**
- **Report Format:** Follow `/home/graham/workspace/experiments/cc_executor/docs/templates/CORE_ASSESSMENT_REPORT_TEMPLATE.md`
- **Success Criteria:** 
  - Report must show MY thinking, not just script output
  - **MUST read actual JSON response files in tmp/responses/**
  - **MUST include COMPLETE outputs - no "[truncated]" text allowed**

### Implementation Guide
1. Run the Python script: `assess_all_core_usage.py`
2. Read the generated report in `prompts/reports/`
3. **Use Read tool on EACH JSON file in tmp/responses/ to get FULL content with line numbers**
4. For each component:
   - Show the COMPLETE JSON file content (with line numbers)
   - Add Claude's Reasonableness Assessment based on the JSON data
   - Analyze the metadata (duration, success, line_count, etc.)
5. **NEVER extract just the "output" field - show the WHOLE JSON**
6. Save as new report with "-COMPLETE-JSON-WITH-CLAUDE-ANALYSIS" suffix

## 🚨 CRITICAL: The Three-Step Assessment Process

### MANDATORY FOR EVERY PYTHON SCRIPT - NO EXCEPTIONS:

**FAILURE CONDITIONS - Script automatically FAILS if:**
1. ❌ No `if __name__ == "__main__"` block exists
2. ❌ The `__main__` block doesn't save output to `/tmp/responses/`
3. ❌ Output is not saved as proper JSON format
4. ❌ Agent doesn't Read and assess the output file

**When a script FAILS these requirements:**
- The agent MUST immediately fix the script
- Add the missing `__main__` block with output saving
- Re-run the script to generate output
- Then perform the assessment

### For EVERY Python Script Tested:

#### Step 1: Script Execution (Automated)
- The script's `if __name__ == "__main__"` block runs
- Output is captured and saved to `/tmp/responses/<component_name>_response.json`
- This happens automatically via the assessment script

#### Step 2: Load Raw Response (MANDATORY for Claude)
```bash
# You MUST do this for EACH component:
Read /tmp/responses/websocket_handler_response.json
Read /tmp/responses/session_manager_response.json
# ... etc for ALL components
```

#### Step 3: Assess Reasonableness (MANDATORY for Claude)
For each loaded response, provide:
- **Expected behavior**: What this component should do
- **Actual output analysis**: What the output shows
- **Key indicators**: Specific values/formats that matter
- **Verdict**: REASONABLE/UNREASONABLE
- **Reasoning**: Why you made this verdict

### Why This Process is MANDATORY
1. **Anti-hallucination**: Line numbers prove you actually read the file
2. **Complete verification**: Full JSON shows all metadata (duration, success, etc.)
3. **Real assessment**: Your analysis proves you understood the output
4. **Quality assurance**: Ensures every script actually works, not just compiles

### Report Format for Each Component
```markdown
### Component: [component_name.py]

#### Raw Response (from /tmp/responses/[component_name]_response.json):
```
[COMPLETE JSON content with line numbers from Read tool]
```

#### Claude's Reasonableness Assessment:
- **Expected behavior**: [What this component should do]
- **Actual output analysis**: [What the output shows]
- **Key indicators**: [Specific values/formats that matter]
- **Verdict**: [REASONABLE/UNREASONABLE]
- **Reasoning**: [Why you made this verdict]
```