# Hook Workaround for Claude Code

Since Claude Code's built-in hook system doesn't work, we need to manually call the cc_executor hooks.

## When to Call Hooks (for Agents/Claude):

### Before ANY Python/pip/pytest command:
```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/setup_environment.py
```

### Before executing complex tasks:
```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/analyze_task_complexity.py
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/check_task_dependencies.py
```

### Before Claude operations:
```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/claude_instance_pre_check.py
```

### After execution:
```bash
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/record_execution_metrics.py
```

## The Problem:
- Claude Code hooks (`~/.claude/hooks/`) should run automatically but don't
- This means I (Claude) must remember to run these hooks manually
- Without deterministic execution, I often forget

## The Reality:
- There's no way to FORCE me to run these hooks
- It relies on my voluntary compliance
- This is why hooks are "not useful" - they're optional, not enforced