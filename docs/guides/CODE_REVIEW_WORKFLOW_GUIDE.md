# Complete Code Review Workflow

## Overview
The code review process follows a specific directory-based workflow where:
1. Review requests go to: `docs/tasks/reviewer/incoming/`
2. Reviewer (o3 model) places fixes in: `docs/tasks/executor/incoming/`
3. Executor implements fixes and continues the cycle

## Directory Structure
```
docs/tasks/
├── reviewer/
│   └── incoming/
│       ├── code_review_round1_request.md
│       ├── code_review_round2_request.md
│       └── code_review_round3_request.md
└── executor/
    └── incoming/
        ├── round1_fixes.json
        ├── round1_fixes.md
        ├── round2_fixes.json
        ├── round2_fixes.md
        ├── round3_assessment.json
        └── round3_assessment.md
```

## Workflow Steps

### Step 1: Create Review Request
Place in `docs/tasks/reviewer/incoming/`:

```markdown
# Code Review Request - Round N

## Pre-conditions
- All Python scripts have UUID4 anti-hallucination pattern ✓
- All outputs saved to tmp/responses/ ✓
- All outputs assessed as reasonable ✓

## Scope of Review
[Specific files and areas to review]

## Questions for Reviewer
[Specific technical questions]
```

### Step 2: Reviewer (o3) Creates Fix Documents
o3 places TWO files in `docs/tasks/executor/incoming/`:

#### A. Markdown Assessment File
`roundN_fixes.md`:
```markdown
# Code Review Round N - Fixes Required

## Critical Issues (Must Fix)
1. **Memory Leak in Bulk Operations**
   - File: `tools/bulk_operations.py`
   - Lines: 245-267
   - Issue: Processing 100+ papers causes memory overflow
   - Fix: Implement chunking with max 50 papers per batch

2. **SQL Injection Risk**
   - File: `storage/search_engine.py`
   - Lines: 156-178
   - Issue: User input directly concatenated to SQL
   - Fix: Use parameterized queries

## High Priority Issues
[List of high priority fixes]

## Medium Priority Issues
[List of medium priority fixes]

## Low Priority Suggestions
[Optional improvements]
```

#### B. JSON Task File
`roundN_fixes.json`:
```json
{
  "round": 1,
  "total_issues": 15,
  "tasks": [
    {
      "id": "001_fix_memory_leak",
      "priority": "critical",
      "file": "tools/bulk_operations.py",
      "lines": [245, 267],
      "issue": "Memory leak with large batches",
      "fix": "Implement chunking with max 50 papers",
      "verification": "Test with 200 papers, monitor memory"
    },
    {
      "id": "002_fix_sql_injection",
      "priority": "critical",
      "file": "storage/search_engine.py",
      "lines": [156, 178],
      "issue": "SQL injection vulnerability",
      "fix": "Use parameterized queries",
      "verification": "Test with malicious input"
    }
  ]
}
```

### Step 3: Executor Implements Fixes

The executor:
1. Reads files from `docs/tasks/executor/incoming/`
2. Implements each fix
3. Verifies UUID4 patterns still work
4. Creates next review request

### Step 4: Cycle Continues

This process repeats for 3 rounds:
- Round 1: Comprehensive review
- Round 2: Fix verification + remaining issues
- Round 3: Final approval

## Best Practices for Reviewers (o3 Model)

1. **Full-File Analysis Required**: Use static tools (`ruff`, `mypy`, `bandit`) and/or read every referenced file. Skimming is disallowed.
2. **Blockers-First Reporting**: Surface only stop-ship issues in initial fix list. Additional findings may be included as context but must not bloat executor scope.
3. **Concrete References**: Cite exact line numbers and code excerpts for each issue.
4. **Minimal-Complexity Fixes**: Prefer small, targeted patches over architectural rewrites unless unavoidable.
5. **Deliverables**: Always provide **both** `roundN_fixes.md` and `roundN_fixes.json`.
6. **Numbered Prefix**: Name reviewer output files with three-digit ordering prefix (e.g., `001_`).

These guidelines align with the updated template and ensure consistent, high-quality reviews.

## Template for Review Request

```markdown
# Code Review Request - Round [N]

## Metadata
- Date: [timestamp]
- Round: [1/2/3]
- Requester: Executor
- Reviewer: o3 Model

## Status Since Last Round
[Only for rounds 2 and 3]
- Issues fixed: [count]
- Files modified: [list]
- Tests re-run: [results]

## Current State
### Anti-Hallucination Validation
- Python scripts with UUID4: [count]/[total]
- Valid outputs: [count]/[total]
- Reasonable outputs: [count]/[total]

### MCP Tools Status
- Tools tested: [count]/[total]
- Integration tests: [PASS/FAIL]
- Performance: [metrics]

## Scope of This Review
### Files to Review
1. [file path] - [reason for review]
2. [file path] - [specific concern]

### Specific Areas
1. **[Area Name]**
   - File: [path]
   - Lines: [range]
   - Concern: [description]
   - Question: [specific question]

## Questions for Reviewer
1. [Specific technical question]
2. [Security concern]
3. [Performance question]
4. [Architecture decision]

## Expected Deliverables
Please create in `docs/tasks/executor/incoming/`:
1. `round[N]_fixes.md` - Detailed assessment
2. `round[N]_fixes.json` - Structured task list
```

## Template for Fix Response

### Markdown Format (`roundN_fixes.md`)
```markdown
# Code Review Round [N] - Assessment

## Summary
- Total issues found: [count]
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

## Critical Issues - MUST FIX

### Issue 1: [Title]
**File**: `path/to/file.py`
**Lines**: 123-145
**Problem**: [Detailed description]
**Risk**: [Security/Performance/Reliability]
**Fix**: [Specific solution]
**Verification**: [How to test the fix]

### Issue 2: [Title]
[Same format]

## High Priority Issues - SHOULD FIX
[Similar format, less critical]

## Medium Priority Issues - NICE TO FIX
[Similar format, improvements]

## Low Priority Suggestions - OPTIONAL
[Similar format, optimizations]

## Security Assessment
- SQL Injection: [PASS/FAIL]
- Path Traversal: [PASS/FAIL]
- Input Validation: [PASS/FAIL]
- Rate Limiting: [PASS/FAIL]

## Performance Assessment
- Memory Usage: [Acceptable/Concern]
- Response Time: [Metrics]
- Scalability: [Assessment]

## Anti-Hallucination Pattern
- Implementation: [Correct/Issues]
- Coverage: [Percentage]
- Suggestions: [Any improvements]

## Overall Recommendation
[READY/NOT READY for next phase]
```

### JSON Format (`roundN_fixes.json`)
```json
{
  "metadata": {
    "round": 1,
    "date": "2025-01-06T15:30:00Z",
    "reviewer": "o3",
    "total_issues": 15
  },
  "summary": {
    "critical": 2,
    "high": 5,
    "medium": 6,
    "low": 2
  },
  "tasks": [
    {
      "id": "001_fix_memory_leak",
      "priority": "critical",
      "category": "performance",
      "file": "tools/bulk_operations.py",
      "lines": [245, 267],
      "issue": "Memory leak when processing >100 papers",
      "details": "Current implementation loads all papers into memory",
      "fix": "Implement streaming with 50-paper chunks",
      "code_snippet": "# Example fix\nfor chunk in chunks(papers, 50):\n    process_chunk(chunk)",
      "verification": {
        "test": "Run with 200 papers",
        "expected": "Memory stays under 500MB",
        "command": "python test_bulk_memory.py"
      }
    }
  ],
  "security": {
    "sql_injection": "FOUND - 1 instance",
    "path_traversal": "FOUND - 2 instances",
    "input_validation": "PARTIAL - needs improvement",
    "rate_limiting": "PASS"
  },
  "performance": {
    "current_metrics": {
      "avg_response_ms": 245,
      "memory_mb": 280,
      "max_concurrent": 10
    },
    "concerns": [
      "Memory usage scales linearly with paper count",
      "No connection pooling for API calls"
    ]
  },
  "recommendation": "NOT READY - Fix critical issues first"
}
```

## Final Round Template

For Round 3, the reviewer provides final assessment:

### `round3_assessment.md`
```markdown
# Code Review Round 3 - Final Assessment

## Review Summary
- Round 1: Fixed 15 issues
- Round 2: Fixed 5 issues  
- Round 3: 0 critical issues found

## Final Status
### Security
- ✓ No SQL injection vulnerabilities
- ✓ Path traversal protected
- ✓ Input validation comprehensive
- ✓ Rate limiting implemented

### Performance
- ✓ Memory usage optimized
- ✓ Response time < 500ms
- ✓ Scales to 1000+ papers

### Code Quality
- ✓ Anti-hallucination pattern complete
- ✓ Error handling comprehensive
- ✓ Documentation adequate
- ✓ Type hints complete

## Deployment Recommendation
**APPROVED FOR DEPLOYMENT**

No critical issues remaining. Code is production-ready.

## Post-Deployment Monitoring
Recommend monitoring:
1. Memory usage under load
2. API rate limit compliance
3. Error rates
4. Response times
```

### `round3_assessment.json`
```json
{
  "metadata": {
    "round": 3,
    "date": "2025-01-06T18:00:00Z",
    "reviewer": "o3"
  },
  "final_status": {
    "ready_for_deployment": true,
    "blocking_issues": 0,
    "total_issues_fixed": 20
  },
  "checklist": {
    "security": "PASS",
    "performance": "PASS",
    "reliability": "PASS",
    "maintainability": "PASS",
    "documentation": "PASS"
  },
  "deployment": {
    "recommendation": "APPROVED",
    "conditions": [],
    "monitoring": [
      "Watch memory usage",
      "Monitor API rates",
      "Track error rates"
    ]
  }
}
```

## Complete Workflow Example

1. **Executor** creates:
   - `docs/tasks/reviewer/incoming/code_review_round1_request.md`

2. **o3 Reviewer** creates:
   - `docs/tasks/executor/incoming/round1_fixes.md`
   - `docs/tasks/executor/incoming/round1_fixes.json`

3. **Executor** implements fixes, then creates:
   - `docs/tasks/reviewer/incoming/code_review_round2_request.md`

4. **o3 Reviewer** creates:
   - `docs/tasks/executor/incoming/round2_fixes.md`
   - `docs/tasks/executor/incoming/round2_fixes.json`

5. **Executor** implements fixes, then creates:
   - `docs/tasks/reviewer/incoming/code_review_round3_request.md`

6. **o3 Reviewer** creates:
   - `docs/tasks/executor/incoming/round3_assessment.md`
   - `docs/tasks/executor/incoming/round3_assessment.json`

7. **Executor** proceeds with deployment if approved

This workflow ensures clear communication and tracking throughout the review process.