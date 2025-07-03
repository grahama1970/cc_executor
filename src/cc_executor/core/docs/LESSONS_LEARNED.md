# Lessons Learned - Core Module Development

## 1. Response Saving is Critical
**Issue**: AI assistants can hallucinate about execution results.

**Solution**: Every Python file MUST have an `if __name__ == "__main__":` block that saves output as JSON.

**Pattern**:
```python
from usage_helper import OutputCapture

with OutputCapture(__file__) as capture:
    # Demo code here
```

## 2. Anthropic Hooks Are Broken
**Issue**: Claude Code subprocess hooks don't trigger (GitHub issue #2891).

**Workaround**: Manual hook execution in websocket_handler.py:
```python
if "claude" in req.command.lower():
    # Manually run setup scripts
    subprocess.run([sys.executable, "setup_environment.py"])
```

## 3. Claude Max SDK Incompatibility
**Issue**: Claude Max uses OAuth tokens, not API keys. The SDK doesn't support this.

**Solution**: Use subprocess calls to `claude` CLI, not the Python SDK.

## 4. MockWebSocket Confusion
**Issue**: Mock objects in `__main__` blocks can be mistaken for test-only code.

**Clarification**: These are demonstration objects showing how the module works without requiring full service setup. They serve as usage examples, not unit tests.

## 5. Directory Organization Matters
**Issue**: Temporary files cluttering the core directory.

**Solution**: Organized structure:
```
core/
├── tmp/
│   ├── responses/          # JSON outputs
│   ├── scripts_generated/  # Helper scripts
│   └── broken_files/       # Backups
```

## 6. JSON-Only Response Format
**Issue**: Saving both .json and .txt files is redundant.

**Solution**: Save only prettified JSON since Claude Code uses streaming JSON output.

## 7. Self-Improving Prompts Need Structure
**Issue**: Self-improving prompts must verify actual execution.

**Solution**: 
1. Structured JSON responses with metadata
2. Clear success/failure indicators
3. Automatic file saving prevents "I ran it" hallucinations

## 8. Process Group Management
**Issue**: Child processes can become zombies if not properly managed.

**Solution**: 
- Always use `os.setsid` for new process groups
- Kill entire process group with `os.killpg()`
- Handle both SIGTERM (graceful) and SIGKILL (forced)

## 9. Stream Buffer Deadlocks
**Issue**: Subprocess pipes can deadlock when buffer fills (typically 64KB).

**Solution**: Always drain streams actively:
```python
asyncio.create_task(_drain_stream(proc.stdout, 'STDOUT'))
asyncio.create_task(_drain_stream(proc.stderr, 'STDERR'))
```

## 10. Documentation as Code
**Issue**: Documentation gets outdated quickly.

**Solution**: 
- Keep docs close to code (in module directories)
- Use self-documenting patterns (OutputCapture)
- Generate reports from actual execution

## Key Takeaways
1. **Trust but Verify** - Save all outputs for verification
2. **Workarounds are OK** - Document them clearly
3. **Structure Prevents Chaos** - Organize files properly from the start
4. **Real Examples > Mock Data** - Use actual execution in demos
5. **Automation Requires Discipline** - Consistent patterns enable self-improving systems