# Hooks Example

This example demonstrates how to use cc_executor's pre-flight and post-execution hooks for quality assurance.

## What You'll Learn

- Setting up `.claude-hooks.json` configuration
- Using pre-flight checks to assess complexity
- Generating post-execution reports
- Ensuring quality through automated verification

## The Example

We'll build a blog platform API with hooks that:
1. **Pre-flight**: Assess complexity and predict success
2. **Execute**: Build the API with monitoring
3. **Post-execute**: Generate comprehensive reports

## Files in This Example

- `task_list.md` - Blog platform tasks
- `.claude-hooks.json` - Hook configuration
- `run_example.py` - Execution with hooks
- After execution:
  - `blog_platform/` - Generated API code
  - `reports/` - Pre-flight and post-execution reports

## How to Run

```bash
cd examples/03_with_hooks
python run_example.py
```

## Key Concepts Demonstrated

1. **Pre-flight Assessment**:
   - Complexity calculation
   - Risk identification
   - Success prediction
   - Timeout recommendations

2. **Post-execution Reports**:
   - Complete execution metrics
   - File verification
   - Cross-task validation
   - Quality assessment

## Hook Features

### Pre-flight Check
- Analyzes task list before execution
- Identifies high-risk tasks
- Suggests optimizations
- Provides go/no-go recommendation

### Post-execution Report
- Captures all outputs
- Verifies file creation
- Validates task dependencies
- Generates actionable insights