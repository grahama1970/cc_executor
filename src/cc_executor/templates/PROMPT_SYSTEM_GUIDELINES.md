# Prompt System Guidelines

This document defines the conventions and workflows for the self-improving prompt system.

## Test Runner Variants

Test runner prompts are a valid variant of the standard `SELF_IMPROVING_PROMPT_TEMPLATE`. They follow the spirit of the template (metrics, history, clear goals) but adapt the structure to their execution-focused purpose.

### Structural Deviations

Test runners should document their variant status with a "Note on Template Compliance" section that explains why standard sections don't apply:
- **Architect's Briefing:** Not applicable - the architecture IS the test runner
- **Step-by-Step Execution:** Complete script executed as a whole
- **Graduation & Verification:** Success ratio achievement, not code promotion  
- **Diagnostics & Recovery:** Focused on runner startup, not component building

## Evolution History Tracking

The Evolution History should track any intentional modification that alters behavior, scope, or effectiveness:

1. **Implementation Code Changes** - Direct modifications to the prompt's code
2. **Test Suite Changes** - Modifications to dependencies that affect scope
3. **Performance Improvements** - Logged as results of specific changes

### Example Entry
```markdown
| Version | Date       | Author | Change Description                                              | Reason for Change                                           |
| ------- | ---------- | ------ | --------------------------------------------------------------- | ----------------------------------------------------------- |
| v2.1    | 2025-06-29 | Gemini | Refactored WebSocket client to reuse single connection         | To reduce connection overhead. Result: 12% faster execution |
```

## Execution Results vs Source Code

### The Golden Rule
Do not modify source control for a test run. Results are artifacts, not source code modifications.

### Three-Tier System

**Tier 1 (Primary): External Files**
- Detailed JSON reports saved to `test_outputs/`
- This is the mandatory "ground truth" for any run
- Add to `.gitignore` to keep out of version control

**Tier 2 (Manual): Execution Log**
- Updated manually for milestone summaries only
- Log significant runs that validate major changes
- Reference the full report in `test_outputs/`

**Tier 3 (Manual): Metrics Table**
- Updated only when committing code changes
- Couples quality metrics to specific versions
- Not a live dashboard

### Workflow Example
When fixing a bug and getting 15 successes, 2 failures:
1. Run tests → Results saved to `test_outputs/`
2. Update Evolution History with bug fix entry
3. Update TASK METRICS table to reflect 15/2
4. Add one-line summary to EXECUTION LOG
5. Commit all changes together

## Graduation for Test Runners

Test runners become "calibrated instruments" when they achieve 10:1 ratio:

1. **Remains .md file** - Value is in the self-contained unit
2. **Gets status marker** - Update metrics table with "✅ Graduated"
3. **Stable for automation** - Ready for CI/CD integration
4. **Continues evolving** - Updates reset status to "In Development"

## Cross-Prompt Dependencies

### Documentation Requirements

Add a `🔗 PROMPT DEPENDENCIES` section to any prompt with dependencies:

```markdown
## 🔗 PROMPT DEPENDENCIES

This prompt executes other prompts and is dependent on their public contracts.

| Dependency Prompt              | Version Tested Against | Nature of Dependency                                    |
| ------------------------------ | ---------------------- | ------------------------------------------------------- |
| `ask-litellm.md`               | v1.0                   | Executes this prompt via shell command to invoke LLM   |
| `unified_stress_test_tasks.json` | v1.5                 | Parses this JSON file to define test execution plan    |
```

### Breaking Change Workflow

**The Golden Rule:** The author of a breaking change must update immediate dependents in the same atomic commit.

1. **Identify** the breaking change
2. **Increment** MAJOR version (e.g., v1.2 → v2.0)
3. **Find** dependents: `grep "prompt_name.md" src/cc_executor/**/*.md`
4. **Update** all dependent prompts:
   - Modify implementation for new interface
   - Update dependency table version
   - Add Evolution History entry
5. **Commit** all changes atomically with clear message

### Public Contract
A prompt's public contract includes:
- Command-line interface (arguments, flags)
- Primary output format (text, JSON, etc.)

This approach ensures:
- No dependency hell
- Repository always in working state
- Clear responsibility assignment
- Simple, grep-based discovery