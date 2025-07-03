# Prompt and Code Templates

This directory contains templates for creating self-improving prompts and structured code patterns used in CC Executor.

## Active Templates

- **[SELF_IMPROVING_PROMPT_TEMPLATE.md](SELF_IMPROVING_PROMPT_TEMPLATE.md)** - The main template for creating self-improving prompts
  - Comprehensive structure with metrics tracking
  - Evolution history management
  - Graduation criteria
  - Self-verification patterns

- **[PROMPT_SYSTEM_GUIDELINES.md](PROMPT_SYSTEM_GUIDELINES.md)** - Guidelines for the prompt system
  - Test runner variants
  - Evolution history tracking
  - Execution results management
  - Three-tier system for results

- **[REVIEW_PROMPT_AND_CODE_TEMPLATE.md](REVIEW_PROMPT_AND_CODE_TEMPLATE.md)** - Template for code review processes
  - Review criteria
  - Feedback format
  - Improvement tracking

- **[REASONABLE_OUTPUT_ASSESSMENT.md](REASONABLE_OUTPUT_ASSESSMENT.md)** - Guide for evaluating output quality
  - Assessment criteria
  - Common patterns
  - Quality metrics

- **[SELF_IMPROVING_TASK_LIST_TEMPLATE.md](SELF_IMPROVING_TASK_LIST_TEMPLATE.md)** - Template for task list management
  - Task organization
  - Progress tracking
  - Dependencies

## Using Templates

### Creating a New Self-Improving Prompt

1. Copy `SELF_IMPROVING_PROMPT_TEMPLATE.md`
2. Fill in the architect's briefing section
3. Implement the code in the implementer's workspace
4. Track metrics and evolution history
5. Graduate when reaching 10:1 success ratio

### Key Principles

- **Metrics-Driven**: Track success/failure ratios
- **Evolution**: Document all changes and their impact
- **Self-Verification**: Include test blocks
- **Graduation**: Clear criteria for moving to production

## Archive

The `archive/` subdirectory contains historical templates:
- Previous versions of templates
- Experimental formats
- Deprecated patterns

These are preserved for reference but should not be used for new work.

Last updated: 2025-07-02