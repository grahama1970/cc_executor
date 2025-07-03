# Hooks Usage Guide for cc_executor

## Quick Start

The cc_executor now includes 6 Anthropic Claude Code hooks that automatically enhance task execution:

1. **`pre-execute`** - Virtual environment setup
2. **`pre-edit`** - Task complexity analysis
3. **`post-edit`** - Code review
4. **`pre-tool`** - Dependency validation
5. **`post-tool`** - Status updates
6. **`post-output`** - Metrics collection

## Virtual Environment Hook (NEW!)

The `pre-execute` hook ensures all Python commands run in the correct virtual environment.

### What it does:
- Detects project `.venv` directory
- Wraps Python/pip/pytest commands with venv activation
- Stores environment configuration in Redis
- Preserves non-Python commands unchanged

### Example transformations:
```bash
# Input command
pytest tests/

# Hook transforms to:
source /path/to/.venv/bin/activate && pytest tests/

# But leaves these unchanged:
echo "Hello"
ls -la
```

### Benefits:
- No more "module not found" errors
- Consistent Python environment
- Automatic for all WebSocket executions
- Works with pytest, pip, uv, python, etc.

## Common Usage Patterns

### 1. Running Tests
```python
# Task list command
"What happens when I run pytest tests/unit/?"

# Hooks automatically:
# 1. Setup venv (pre-execute)
# 2. Estimate timeout from history (pre-edit)
# 3. Check WebSocket ready (pre-tool)
# 4. Record success/failure (post-tool)
# 5. Analyze test output (post-output)
```

### 2. Installing Dependencies
```python
# Task list command  
"What packages are installed when I run: pip install -r requirements.txt?"

# Hooks ensure:
# - Runs in correct venv
# - Monitors for timeout
# - Records installation time
# - Detects any errors
```

### 3. Code Generation with Review
```python
# Task using cc_execute.md
"What is a FastAPI endpoint that validates email addresses?"

# Hooks provide:
# - Complexity analysis (300s timeout for API endpoints)
# - Automatic code review via perplexity-ask
# - Quality scoring
# - Security checks
```

## Monitoring Hook Execution

### Via WebSocket
```json
// Request hook status
{
  "jsonrpc": "2.0",
  "method": "hook_status",
  "id": 1
}

// Response
{
  "result": {
    "enabled": true,
    "hooks_configured": ["pre-execute", "pre-edit", ...],
    "recent_executions": [...],
    "statistics": {
      "total_executions": 42,
      "average_duration": 1.3
    }
  }
}
```

### Via Redis CLI
```bash
# Check recent hook executions
redis-cli lrange hook:executions 0 5

# View environment setups
redis-cli get hook:env_setup:session-id

# Check task complexity estimates
redis-cli hgetall task:complexity
```

### Via Logs
```bash
# Watch WebSocket logs for hook activity
tail -f logs/websocket_handler_*.log | grep HOOK

# Common log patterns:
# [HOOK ENV] - Virtual environment setup
# [HOOK TIMEOUT] - Complexity-based timeout
# [HOOK POST-EXEC] - Post-execution metrics
```

## Troubleshooting

### Issue: Commands fail with "module not found"
**Solution**: The venv hook should prevent this. Check:
```bash
# Verify hook is configured
cat .claude-hooks.json | grep pre-execute

# Test hook manually
CLAUDE_COMMAND="pytest" python src/cc_executor/hooks/setup_environment.py
```

### Issue: Timeouts too short/long
**Solution**: Build history for better estimates:
```bash
# Check timeout history
redis-cli hgetall task:timing

# Manual override in task list
"Execute with 300s timeout: What is..."
```

### Issue: Code review not happening
**Solution**: Ensure perplexity-ask is available:
```bash
# Test perplexity MCP tool
mcp list | grep perplexity

# Check review logs
tail logs/code_reviews.log
```

## Best Practices

### 1. Let Hooks Work Automatically
- Don't manually activate venv in commands
- Trust timeout estimates (they improve over time)
- Review hook suggestions in logs

### 2. Build Good History
- Execute variety of tasks
- Let successful tasks complete
- History improves all estimates

### 3. Monitor Quality Metrics
```bash
# Check average quality scores
redis-cli get metrics:average_quality

# View high-risk code changes
redis-cli lrange high_risk_changes 0 10
```

### 4. Use with Task Lists
The hooks are especially powerful with task lists:
- Sequential dependency validation
- Automatic retries with improvements
- Quality tracking across tasks

## Advanced Usage

### Custom Hook Configuration
Add your own hooks to `.claude-hooks.json`:
```json
{
  "hooks": {
    "pre-commit": "python check_commit_message.py",
    "post-test": "python send_test_report.py"
  }
}
```

### Conditional Execution
Hooks can check context and exit early:
```python
# In your hook script
if "skip_review" in os.environ.get('CLAUDE_CONTEXT', ''):
    sys.exit(0)  # Skip this hook
```

### Hook Chaining
Use Redis to pass data between hooks:
```python
# In pre-tool hook
r.set("hook:data:session", json.dumps(data))

# In post-tool hook  
data = json.loads(r.get("hook:data:session"))
```

## Summary

The hooks system provides:
- ✅ Automatic venv activation
- ✅ Intelligent timeout estimation
- ✅ Dependency validation
- ✅ Code quality reviews
- ✅ Execution metrics
- ✅ Self-improvement triggers

All working together to make task execution more reliable and efficient!