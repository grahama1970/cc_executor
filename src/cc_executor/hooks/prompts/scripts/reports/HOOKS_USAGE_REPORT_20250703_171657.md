# Hooks Usage Function Assessment Report

**Generated**: 2025-07-03 17:17:27

**Report Location**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/prompts/scripts/reports/HOOKS_USAGE_REPORT_20250703_171657.md
**Temp Directory**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/prompts/scripts/tmp/hook_assess_20250703_171657
**Raw Responses Saved**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/prompts/scripts/tmp/responses/

**Total Hooks Tested**: 1
**Redis Available**: Yes
**Hooks Available**: Yes
**Test Session ID**: hook_assess_20250703_171657
**Total Time**: 30.1s

---

## Hook Chain Usage

**Pre-hooks Used**: None
**Post-hooks Used**: None

---

## Summary

- **Passed**: 0/1 (0.0%)
- **Failed**: 1/1
- **Average Confidence**: 95.0%
- **Hooks with Redis Evidence**: 0/1


### Category Performance:


---

## Detailed Results

### ❌ assess_all_hooks_usage.py

**Description**: Hook functionality test

**Expected Test Indicators**: Test, Hook

**Assessment**: FAIL (Confidence: 95%)
**Execution Time**: 30.03s

**Reasons**:

- Hook test timed out

**Raw Output**:
```
Command: python assess_all_hooks_usage.py --test
Exit Code: -1
Working Directory: /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/prompts/scripts/tmp/hook_assess_20250703_171657

--- STDOUT ---


--- STDERR ---
Process timed out after 30 seconds
```

---

## Recommendations

### For Failed Hooks:

- **assess_all_hooks_usage.py**: Hook test timed out

### Pattern Recommendation:
Hooks use --test flags for production safety, but for new non-hook components:
- Use direct `if __name__ == '__main__':` implementation
- No flags needed for simpler AI agent interaction
- See core/ components for AI-friendly patterns