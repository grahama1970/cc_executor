# Claude Code Hooks - Definitive Findings

## Summary

After extensive testing, here are the definitive findings about Claude Code hooks:

## 1. Hook Behavior

**Hooks DO NOT trigger for:**
- ❌ Subprocess commands (`subprocess.run()`, `os.system()`, etc.)
- ❌ Tool use within THIS Claude session (Write, Edit, Bash, etc.)
- ❌ External calls to `claude` CLI from Python scripts

**Hooks MIGHT trigger for:**
- ❓ New Claude sessions started from command line with specific flags
- ❓ Specific Claude Code UI interactions (not tested here)

## 2. Configuration Formats

Claude supports multiple hook configuration formats:

### Format 1: Simple (used by cc_executor)
```json
{
  "hooks": {
    "pre-execute": "python /path/to/hook.py",
    "post-execute": ["python /path/to/hook1.py", "python /path/to/hook2.py"]
  }
}
```

### Format 2: Matcher-based (from documentation)
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python /path/to/hook.py"
      }]
    }]
  }
}
```

## 3. Test Results

| Test Case | Result | Notes |
|-----------|--------|-------|
| Subprocess Python commands | ❌ No hooks | Expected - hooks don't intercept subprocess |
| Subprocess shell commands | ❌ No hooks | Expected - hooks don't intercept subprocess |
| Claude CLI from subprocess | ❌ No hooks | Hooks don't trigger even for claude commands |
| Tool use in THIS session | ❌ No hooks | Write, Edit, Bash tools don't trigger hooks |
| Manual hook execution | ✅ Works | Hooks are valid Python scripts |

## 4. Implications for cc_executor

1. **Claude hooks are irrelevant for cc_executor's use case**
   - cc_executor runs subprocess commands directly
   - Claude hooks only work within Claude's tool execution context
   - Even then, they don't work reliably

2. **The "workaround" is actually the correct implementation**
   - Running `setup_environment.py` manually before subprocess
   - This is not a workaround but the proper approach
   - It gives full control over environment setup

3. **Hook files in cc_executor serve a different purpose**
   - They're utility scripts for environment setup
   - They're not actually Claude hooks in the traditional sense
   - They're manually executed helpers

## 5. Conclusion

Claude Code hooks appear to be:
- Partially implemented or broken in current version
- Only relevant for Claude's internal tool execution
- Not applicable to subprocess command execution

For cc_executor, the current approach of manually running setup scripts is:
- ✅ Correct
- ✅ Reliable
- ✅ Not a workaround

The `.claude-hooks.json` file in cc_executor could be renamed to avoid confusion, as these aren't really Claude hooks but rather utility scripts for the WebSocket executor.