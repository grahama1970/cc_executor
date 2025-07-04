# Client Components Usage Assessment — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (New prompt)
- **Last Updated**: 2025-07-03
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial client usage assessment based on core learnings | TBD    |

---
## 🏛️ ASSESSMENT PRINCIPLES (Immutable)

### 1. Purpose
Run ALL usage functions in the client/ directory, capture their raw outputs using OutputCapture pattern, assess reasonableness without code execution, and generate a comprehensive markdown report in prompts/reports/.

**IMPORTANT**: The client/ directory contains:
- client.py - WebSocket client for connecting to CC Executor server

### 2. Key Learnings from Core Assessment
- Use OutputCapture pattern for consistent JSON output
- NO duplicate .txt files (JSON only with metadata)
- Check for functions that should be outside __main__ blocks
- Verify proper module naming (cc_executor.client.*)
- Client connects to existing server (doesn't manage its own)

### 3. Reasonableness Assessment (No Code Execution)
For each usage function output, check if it's reasonable by looking for:
- WebSocket connection attempts
- Proper error handling when server not running
- Command execution examples
- Connection status messages
- No obvious errors or stack traces (unless testing error cases)

## 🎯 EXECUTION PROCESS

### Step 1: Run the Automated Assessment
**Execute this Python script to generate the base report:**

```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/client/prompts/scripts/assess_all_client_usage.py
```

This script:
1. Automatically finds all Python files in client/ with usage functions
2. Runs setup hooks before execution
3. Captures raw output using OutputCapture pattern
4. Performs automated pass/fail assessment
5. Generates a base report in prompts/reports/

### Step 2: Add Claude's Analysis
**YOU must then:**
1. Read the generated report
2. Analyze each component's output
3. Add your reasonableness assessment following the template
4. Create a new report with your analysis included

## 📝 REPORT REQUIREMENTS

The generated report must include:
- Summary of pass/fail for each component
- **COMPLETE RAW JSON FILES with line numbers from Read tool**
- **CLAUDE'S REASONABLENESS ASSESSMENT for EACH component**
- Specific analysis of why each output is reasonable (or not)
- Code structure assessment (functions in __main__ blocks)
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
4. Apply learnings from core assessment

## 🔬 DIAGNOSTICS & RECOVERY

### Implementation Guide
1. Run the Python script: `assess_all_client_usage.py`
2. Read the generated report in `prompts/reports/`
3. **Use Read tool on EACH JSON file in tmp/responses/ to get FULL content with line numbers**
4. For each component:
   - Show the COMPLETE JSON file content (with line numbers)
   - Add Claude's Reasonableness Assessment based on the JSON data
   - Analyze the metadata (duration, success, line_count, etc.)
   - Check for misplaced functions in __main__ blocks
5. **NEVER extract just the "output" field - show the WHOLE JSON**
6. Save as new report with "-COMPLETE-JSON-WITH-CLAUDE-ANALYSIS" suffix