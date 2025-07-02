# Stress Test Prompt Templates

This directory contains prompt templates for running various stress test scenarios.

## Main Test Runners

### Core Templates

1. **main_stress_test_runner.md** - The primary stress test runner with full metrics tracking
   - Executes tests from JSON configuration files
   - Tracks success/failure ratios
   - Implements self-improvement rules

2. **unified_test_runner.md** - Runs the unified test suite
   - Executes tests from unified_stress_test_tasks.json
   - Simpler than main runner, focused on execution

3. **extended_test_runner.md** - Extended test scenarios with UUID verification
   - 13 test scenarios including edge cases
   - UUID-based verification for reliability
   - Preflight checks before main execution

### Recovery and Resilience

4. **recovery_test_runner.md** - Tests with built-in recovery mechanisms
   - Handles timeouts gracefully
   - Implements retry logic
   - Focuses on system resilience

5. **self_reflecting_recovery_runner.md** - Combines self-reflection with recovery
   - Ultimate defense against timeouts
   - Self-aware execution patterns
   - Automatic error detection and recovery

### Pattern Templates

6. **self_reflecting_prompts.md** - Template patterns for self-reflection
   - Not a runner, but a pattern guide
   - Shows how to structure self-reflecting prompts
   - Used by other runners

7. **timeout_recovery_prompts.md** - Patterns for handling timeouts
   - Template collection for timeout scenarios
   - Recovery strategies and patterns
   - Best practices for resilient prompts

## Usage

These prompts are designed to be executed by Claude Code or similar LLM agents. They follow specific patterns:

1. **Self-Improvement Rules** - Track metrics and evolve based on results
2. **Gamification Metrics** - Success/failure tracking with graduation criteria
3. **Recovery Mechanisms** - Built-in error handling and retry logic

## Key Patterns

### Working Claude CLI Patterns
```bash
# ✅ Questions starting with "What is"
claude -p "What is 2 + 2?" --output-format stream-json --dangerously-skip-permissions

# ❌ Avoid imperative commands
claude -p "Write a function..." # May hang
```

### Required Flags
- `--output-format stream-json` - For proper output parsing
- `--dangerously-skip-permissions` - Skip interactive prompts
- `--allowedTools none` - Prevent tool loading issues
- `--verbose` - Required with stream-json format

## Archive

The `archive/` directory contains older versions and specialized variants that have been superseded by the main templates.