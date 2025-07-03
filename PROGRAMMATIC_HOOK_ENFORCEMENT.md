# Programmatic Hook Enforcement for cc_executor

## Summary

Since Claude Code hooks don't work reliably, we've implemented programmatic hook enforcement directly in Python code. This ensures that critical environment setup, validation, and monitoring tasks are always executed.

## Implementation Details

### 1. Hook Integration Module (`src/cc_executor/core/hook_integration.py`)

The module now includes two main classes:

- **`ProgrammaticHookEnforcement`**: Direct Python implementation of hook functionality
  - Virtual environment detection and activation
  - Redis connection checking
  - Environment validation using imported hook modules
  - Command wrapping for venv activation
  - Pre/post execution hooks with metrics tracking

- **`HookIntegration`**: Maintains backward compatibility while using programmatic enforcement
  - Falls back to programmatic enforcement for critical hooks
  - Still supports config-based hooks for non-critical operations

### 2. Core Components Updated

#### Process Manager (`process_manager.py`)
- Added `@ensure_hooks` decorator to `execute_command`
- Automatically wraps commands with venv activation when needed
- Applies pre-execution hooks before command execution

#### WebSocket Handler (`websocket_handler.py`)
- Already integrated with hook system
- Uses hooks for environment validation and command analysis
- Handles hook failures gracefully with warnings

### 3. Key Features

1. **Automatic Virtual Environment Activation**
   - Detects project .venv directory
   - Updates environment variables
   - Wraps Python/pip/pytest commands with activation

2. **Redis Integration**
   - Stores hook execution data
   - Tracks metrics (successful/failed executions)
   - Gracefully handles Redis unavailability

3. **Environment Validation**
   - Checks working directory
   - Validates MCP configuration
   - Ensures PYTHONPATH includes src/
   - Verifies dependencies are installed

4. **Command Wrapping**
   - Intelligently wraps commands that need venv
   - Uses `shlex` for secure command parsing
   - Preserves original command structure

### 4. Usage

The system automatically initializes when any core component is used:

```python
from cc_executor.core.hook_integration import get_hook_integration, ensure_hooks

# Get global hook instance
hook = get_hook_integration()

# Decorator ensures hooks are initialized
@ensure_hooks
async def my_function():
    # Hooks are guaranteed to be active here
    pass

# Manual hook execution
result = await hook.pre_execution_hook(command, session_id)
wrapped_command = result['pre-execute']['wrapped_command']
```

### 5. Benefits

1. **Reliability**: No dependency on external hook system
2. **Performance**: Direct Python execution is faster
3. **Debugging**: Easier to trace and debug
4. **Flexibility**: Can be extended with Python code
5. **Graceful Degradation**: Works even if Redis or other deps are unavailable

### 6. Testing

Run the test to verify hook integration:

```bash
source .venv/bin/activate
python -m src.cc_executor.core.hook_integration
```

This will show:
- System initialization status
- Virtual environment detection
- Redis connection status
- Available hooks from config
- Command wrapping examples

## Conclusion

This programmatic enforcement ensures that cc_executor always runs with the correct environment setup, regardless of whether Claude Code hooks are functional. It's a more robust solution that integrates directly with the Python codebase.