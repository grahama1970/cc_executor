# Run Stress Tests with Full Response Capture

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-26
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation with full response capture

## PURPOSE
Run comprehensive stress tests on cc-executor with FULL response capture, not just pattern matching.

## FEATURES
- Captures complete Claude responses (not just pattern matching)
- Saves full responses to files for verification
- Shows response previews in report
- Tracks execution times in Redis
- Generates detailed reports with actual content
- Verifies execution in transcript logs

## IMPLEMENTATION

```python
# Extract to: src/cc_executor/tests/stress/unified_stress_test_executor_v3.py
# Already created - see file for full implementation

# Key improvements:
# 1. Captures FULL responses, not just pattern checks
# 2. Saves responses to stress_test_outputs/ directory
# 3. Shows response previews in report
# 4. Generates both text and JSON reports
```

## USAGE

```bash
# Run all stress tests with full capture
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress
python unified_stress_test_executor_v3.py

# Run specific categories
python unified_stress_test_executor_v3.py unified_stress_test_tasks.json simple,parallel

# View results
ls -la stress_test_outputs/
cat stress_test_detailed_report_*.txt
```

## VERIFICATION

```bash
# Verify execution happened
MARKER="VERIFY_STRESS_TEST_$(date +%Y%m%d_%H%M%S)"
echo "$MARKER"

# Check outputs directory was created
ls -la stress_test_outputs/ | head -10

# Show a sample captured response
cat stress_test_outputs/simple_*.txt | head -50
```

## OUTPUT FILES

1. **stress_test_detailed_report_TIMESTAMP.txt** - Full report with response previews
2. **stress_test_summary_TIMESTAMP.json** - JSON summary for programmatic access
3. **stress_test_outputs/CATEGORY_TASKID_TIMESTAMP.txt** - Full response for each task

## REPORT FEATURES

The detailed report includes:
- Request sent to Claude
- Full response received (preview + file location)
- Pattern matching results
- Execution duration
- Transcript verification status
- Category summaries with average times

## EXAMPLE OUTPUT

```
================================================================================
CATEGORY: simple
================================================================================

────────────────────────────────────────────────────────
Task: daily_standup (ID: simple_1)
Duration: 12.37s
Success: ✅ Yes

Request: Help me write my daily standup update. Ask me what I worked on yesterday...

Pattern Verification:
  ✓ 'yesterday'
  ✓ 'today'
  ✓ 'blocker'

Response Preview (2451 chars total):
------------------------------------------------------------
I'd be happy to help you write your daily standup update! Let me ask you a few questions:

**Yesterday:**
- What tasks or features did you work on yesterday?
- Did you complete anything significant?
- Were there any unexpected challenges?

**Today:**
- What are your main priorities for today?
- Which tasks will you be focusing on?
- Are there any meetings or collaborations planned?

**Blockers:**
- Is there anything preventing you from making progress?
- Do you need help from anyone on the team?
- Are there any dependencies you're waiting on?

Once you provide these details, I'll format them into a nice Slack-friendly standup update!
------------------------------------------------------------

Transcript Verified: ✓ Yes
```

## IMPROVEMENTS OVER V2

1. **Full Response Capture**: V2 only checked patterns, V3 captures everything
2. **Response Storage**: All responses saved to files for manual verification
3. **Better Reporting**: Shows actual content, not just "pattern found/missing"
4. **Accurate Success Metrics**: Based on actual execution, not pattern matching
5. **Debugging Support**: Can review exact responses to understand failures

## RECOVERY SCENARIOS

1. **Timeout**: Increases timeout and retries
2. **Connection Error**: Waits and retries with backoff
3. **Pattern Mismatch**: Shows actual response for debugging
4. **Transcript Missing**: Continues but flags in report

## KNOWN ISSUES

- Pattern matching is still too strict (looks for exact strings)
- Large responses (10K+ words) may truncate in preview
- Redis recording may fail silently

## TODO

- [ ] Add response size statistics
- [ ] Implement smarter pattern matching (regex, fuzzy)
- [ ] Add response quality scoring
- [ ] Generate HTML report with syntax highlighting