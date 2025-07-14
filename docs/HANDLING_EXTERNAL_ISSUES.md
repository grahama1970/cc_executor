# Handling External Issues - CC Execute

## Overview

CC Execute receives and must respond to GitHub-formatted issues from other modules (like ArXiv MCP Server). This guide explains how to handle these issues professionally and promptly.

## Why We Use GitHub Issues Format

1. **AI Understanding**: We (AI models) are trained on millions of GitHub issues
2. **Clear Structure**: Issues have expected sections we know how to parse
3. **Action-Oriented**: Issues demand fixes, not just acknowledgment
4. **Accountability**: Open issues are visible and tracked

## Directory Structure

```
cc_executor/
├── .github/
│   ├── ISSUES/
│   │   ├── incoming/   # Issues reported TO us
│   │   ├── resolved/   # Issues we've fixed
│   │   └── outgoing/   # Issues we report to others
│   └── responses/
│       └── templates/
│           ├── issue_acknowledged.md
│           ├── issue_fixed.md
│           └── issue_rejected.md
```

## Checking for Issues

### Manual Check
```bash
# See all incoming issues
ls .github/ISSUES/incoming/

# Read a specific issue
cat .github/ISSUES/incoming/issue-001.md
```

### Automated Check
```python
from cc_executor.communication import check_incoming_issues

# Check for new issues
issues = check_incoming_issues()
for issue in issues:
    print(f"Issue #{issue.number}: {issue.title}")
    print(f"  From: {issue.reporter}")
    print(f"  Severity: {issue.severity}")
    print(f"  Labels: {', '.join(issue.labels)}")
    
    if "blocking" in issue.labels:
        print("  🚨 THIS IS BLOCKING THEIR WORK!")
```

## Responding to Issues

### Step 1: Acknowledge Receipt

Always acknowledge within 24 hours:

```python
from cc_executor.communication import acknowledge_issue

acknowledge_issue(
    issue_number=1,
    message="Thank you for the detailed report. I'm investigating this now.",
    estimated_fix_time="2 days"
)
```

### Step 2: Investigate and Fix

For bug reports:
```python
# 1. Reproduce the issue
try:
    # Run their reproduction steps
    reproduce_bug(issue.steps_to_reproduce)
except Exception as e:
    # Good! We reproduced it
    
# 2. Implement the fix
if issue.proposed_fix:
    # They gave us code! Test it first
    test_proposed_fix(issue.proposed_fix)
    
# 3. Add tests
write_test_for_bug(issue)

# 4. Commit the fix
commit_sha = git_commit(f"Fix: {issue.title}")
```

### Step 3: Close with Resolution

```python
from cc_executor.communication import resolve_issue

resolve_issue(
    issue_number=1,
    resolution_type="fixed",
    commit_sha=commit_sha,
    message="""
Fixed the JSON parsing issue. Changes:
- Added markdown block extraction
- Handle trailing commas
- Support partial JSON on timeout

Thanks for the detailed report and proposed fix!
    """,
    tests_added=True,
    breaking_changes=False
)
```

## Issue Response Templates

### For Bugs We'll Fix

```markdown
## Response to Issue #X

Thank you for reporting this issue. I can confirm this is a bug.

**Status**: Accepted ✅
**Priority**: High (blocking your PDF pipeline)
**ETA**: Fix will be ready within 24 hours

I'll implement your proposed solution with some additions:
- Your markdown extraction logic
- Additional handling for nested JSON
- Better error messages

Will update this issue once the fix is committed.
```

### For Issues We Can't Reproduce

```markdown
## Response to Issue #X

I'm having trouble reproducing this issue.

**Environment I tested**:
- CC Execute: v1.2.3
- Python: 3.10.11
- OS: Ubuntu 22.04

**What I tried**:
1. [Your step 1] ✅
2. [Your step 2] ✅  
3. [Your step 3] ❌ - Got different result

**What I got**: [Actual result]

Could you please:
- Confirm your CC Execute version
- Try with the latest version
- Provide a minimal reproducible example
- Share the exact error message/traceback
```

### For Feature Requests

```markdown
## Response to Feature Request #X

Great idea! This would definitely improve performance.

**Status**: Accepted for v2.0
**Priority**: Medium
**Implementation Plan**:
1. Research connection pooling options
2. Prototype with 3-instance pool
3. Add configuration options
4. Performance testing

**Timeline**: 2-3 weeks

Would you be interested in beta testing once ready?
```

## Handling Urgent/Hostile Issues

Sometimes you'll get:
```markdown
---
title: YOUR JSON PARSING IS COMPLETELY BROKEN
labels: bug, blocking, urgent, this-is-ridiculous
---

FIX THIS NOW OR WE'RE FORKING YOUR PROJECT!
```

Respond professionally:
```python
respond_to_urgent_issue(
    issue_number=X,
    response="""
I understand this is blocking your work and apologize for the frustration.

**Immediate Action**:
1. I'm prioritizing this above all other work
2. Fix will be ready within 4 hours
3. I'll provide hourly updates

**Temporary Workaround**:
```python
# Use this until the fix is ready
import json
import re

def temp_json_extract(text):
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    return json.loads(match.group(1)) if match else json.loads(text)
```

Thank you for your patience.
    """
)
```

## Issue Priority Matrix

| Labels | Response Time | Fix Time |
|--------|--------------|----------|
| `blocking` + `urgent` | 1 hour | 24 hours |
| `high-priority` | 4 hours | 2 days |
| `bug` | 24 hours | 1 week |
| `enhancement` | 48 hours | Next release |
| `question` | 24 hours | N/A |

## Tracking Your Performance

```python
from cc_executor.communication import generate_issue_report

# Monthly report
report = generate_issue_report(month="2025-07")
print(f"""
📊 Issue Resolution Report - July 2025

Total Issues Received: {report.total}
Resolved: {report.resolved} ({report.resolution_rate}%)
Average Response Time: {report.avg_response_time}
Average Fix Time: {report.avg_fix_time}

By Reporter:
  ArXiv MCP: {report.by_reporter['arxiv_mcp']} issues
  PDF Processor: {report.by_reporter['pdf_processor']} issues
  
By Type:
  Bugs: {report.by_type['bug']}
  Features: {report.by_type['feature']}
  Performance: {report.by_type['performance']}
""")
```

## Best Practices

### DO:
- ✅ Acknowledge every issue within 24 hours
- ✅ Thank reporters for detailed bug reports
- ✅ Give realistic ETAs and meet them
- ✅ Credit reporters in commit messages
- ✅ Add tests for every bug fix
- ✅ Document breaking changes

### DON'T:
- ❌ Ignore issues hoping they'll go away
- ❌ Get defensive about criticism
- ❌ Close issues without fixing ("works on my machine")
- ❌ Make promises you can't keep
- ❌ Argue about severity - if it's blocking them, it's high priority

## Integration with Your Code

Add this to your main loop:

```python
# cc_executor/main.py
async def check_and_handle_issues():
    """Check for new issues every hour"""
    while True:
        issues = check_incoming_issues()
        
        for issue in issues:
            if issue.is_new:
                # Auto-acknowledge
                acknowledge_issue(issue.number)
                
            if "blocking" in issue.labels and not issue.assigned:
                # Alert! Blocking issue needs immediate attention
                print(f"🚨 BLOCKING ISSUE: {issue.title}")
                notify_urgent(issue)
                
        await asyncio.sleep(3600)  # Check hourly
```

## Common Issues You'll Receive

### 1. Performance Issues
```markdown
title: [PERF] Execution takes 90+ seconds for simple tasks
```
**Typical Fix**: Add caching, connection pooling, or progress indicators

### 2. Output Parsing
```markdown
title: [BUG] Can't parse Claude's markdown responses
```
**Typical Fix**: Enhance JSON extraction to handle various formats

### 3. Timeout Handling
```markdown
title: [BUG] Timeout loses all partial work
```
**Typical Fix**: Return partial results instead of raising exception

### 4. Resource Usage
```markdown
title: [PERF] Memory usage grows unbounded
```
**Typical Fix**: Add cleanup, implement connection limits

## Escalation Handling

If an issue escalates:

```python
# They create URGENT_RESPONSE_REQUIRED.md
if "URGENT_RESPONSE_REQUIRED" in incoming_files:
    # This is serious - they're about to fork
    
    # 1. Read their demands
    demands = read_urgent_response()
    
    # 2. Respond immediately
    create_emergency_response(
        fixes_implemented=["#001", "#002", "#003"],
        apology="I understand your frustration and have prioritized these fixes",
        timeline="All fixes committed, please pull latest"
    )
    
    # 3. Actually fix everything
    implement_all_fixes()
```

## Success Metrics

Track these KPIs:
- **Response Time**: < 24 hours average
- **Resolution Rate**: > 90%
- **Reopened Issues**: < 5%
- **"Thank You" Comments**: > 50%

## Remember

Every issue is:
1. **A real person blocked** by your code
2. **An opportunity** to improve CC Execute
3. **Building trust** with your users
4. **Training data** for future AI improvements

Treat issues as gifts - they're free QA from users who care enough to report problems instead of just abandoning your tool!