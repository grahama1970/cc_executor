# KiloCode Human-in-the-Loop Code Review Workflow

## Overview

Since KiloCode's `execute_command` cannot programmatically trigger slash commands or access KiloCode's LLM, we've created an optimal human-in-the-loop workflow that leverages KiloCode's powerful review capabilities while maintaining automation where possible.

## The Solution

A structured workflow where:
1. **Claude Code** creates review requests with properly formatted prompts
2. **Human** manually triggers KiloCode's `/review-contextual` command
3. **Human** saves KiloCode's results back to the system
4. **Claude Code** parses results and implements the fixes automatically

## Directory Structure

```
/tmp/kilocode_reviews/
├── 01_ready_for_human/          # ⚡ Action required by human
│   └── 2025-07-19_1430_auth_security/
│       ├── COPY_THIS_PROMPT.md   # Ready to copy/paste
│       ├── metadata.json         # Review details
│       └── INSTRUCTIONS.txt      # Step-by-step guide
│
├── 02_awaiting_results/         # ⏳ In KiloCode processing
│   └── 2025-07-19_1430_auth_security/
│       └── PASTE_RESULTS_HERE.txt
│
├── 03_results_received/         # 📊 Results ready for parsing
│   └── 2025-07-19_1430_auth_security/
│       ├── kilocode_output.txt
│       └── parsed_issues.json
│
├── 04_fixes_in_progress/        # 🔧 Claude implementing fixes
│   └── 2025-07-19_1430_auth_security/
│       ├── FIX_001_HIGH_security.json
│       └── FIX_002_MEDIUM_performance.json
│
├── 05_completed/                # ✅ Done and archived
│   └── 2025-07-19_1430_auth_security/
│       └── COMPLETION_REPORT.json
│
└── DASHBOARD.json               # 📊 Current status overview
```

## Key Design Decisions

### 1. Clear Naming Conventions
- **Numbered directories** (01_, 02_, etc.) show workflow order
- **Action-oriented filenames** (COPY_THIS_PROMPT.md, PASTE_RESULTS_HERE.txt)
- **Descriptive folder names** include timestamp and description

### 2. Human-Friendly Design
- Clear instructions at each step
- Pre-formatted prompts ready for copy/paste
- Visual indicators of what needs attention

### 3. Status Tracking
- Directory location indicates status
- No ambiguity about what stage each review is in
- Dashboard provides quick overview

## MCP Server Tools

### `create_review`
Creates a new review request with formatted prompt for KiloCode.

```python
await create_review(
    files="src/auth.py src/db.py",
    description="authentication_security",
    context="Web app with strict security requirements",
    focus="security",
    severity="high"
)
```

### `save_review_results`
Saves KiloCode output and extracts actionable fixes.

```python
await save_review_results(
    review_name="2025-07-19_1430_auth_security",
    results="[KiloCode output here]"
)
```

### `get_pending_fixes`
Lists all fixes ready for implementation, sorted by severity.

### `start_fix` / `complete_fix`
Track fix implementation progress.

### `get_workflow_status`
Shows current state of all reviews in the system.

## Workflow Example

### 1. Claude Code Creates Review
```python
# Claude Code
result = await create_review(
    files="src/vulnerable.py",
    description="sql_injection_fix",
    context="Database module using SQLite",
    focus="security"
)
# Output: Review created in 01_ready_for_human/
```

### 2. Human Processes Review
1. Go to `01_ready_for_human/2025-07-19_1500_sql_injection_fix/`
2. Copy entire contents of `COPY_THIS_PROMPT.md`
3. In VS Code with KiloCode: `/review-contextual`
4. Paste the prompt
5. Wait for KiloCode to complete
6. Copy KiloCode's response
7. Move folder to `02_awaiting_results/`
8. Paste response into `PASTE_RESULTS_HERE.txt`

### 3. Claude Code Processes Results
```python
# Save and parse results
result = await save_review_results(
    review_name="2025-07-19_1500_sql_injection_fix",
    results="[pasted KiloCode output]"
)
# Automatically extracts fixes, moves to 03_results_received/

# Get pending fixes
fixes = await get_pending_fixes()
# Returns prioritized list of fixes

# Implement fixes
for fix in fixes:
    await start_fix(fix["review_name"], fix["fix_id"])
    # ... implement the fix ...
    await complete_fix(fix["review_name"], fix["fix_id"], "Fixed using parameterized queries")
```

## Benefits

1. **Uses KiloCode's LLM** - No external API calls needed
2. **Clear workflow** - Always know what needs human attention
3. **Automation where possible** - Parsing, tracking, and implementation automated
4. **Complete audit trail** - Every step documented
5. **Flexible** - Handles any format KiloCode outputs

## Implementation Files

- **Manager**: `/src/cc_executor/tools/kilocode_review_manager.py`
- **MCP Server**: `/src/cc_executor/servers/mcp_kilocode_workflow.py`
- **Test**: `/test_kilocode_workflow.py`

## Summary

This workflow elegantly solves the constraint that KiloCode's `execute_command` cannot trigger slash commands. By embracing human-in-the-loop for the KiloCode interaction while automating everything else, we get:

- The power of KiloCode's code review
- Clear tracking and organization
- Automated fix implementation
- No external dependencies

The human operator becomes the bridge between Claude Code's automation and KiloCode's AI capabilities, with minimal manual effort required.