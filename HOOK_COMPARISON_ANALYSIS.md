# Hook System Analysis - cc_executor

## Overview

After analyzing the three key files that interact with hooks in cc_executor, I've found the following patterns and differences in how hooks are implemented and used.

## Files Analyzed

1. **`/src/cc_executor/client/cc_execute.py`** - Client-side execution interface
2. **`/src/cc_executor/core/websocket_handler.py`** - WebSocket server handling
3. **`/src/cc_executor/core/process_manager.py`** - Process management

## Key Findings

### 1. Hook System Architecture

The hook system is defined in `/src/cc_executor/hooks/hook_integration.py` and provides:
- **`HookIntegration`** class - Main hook management interface
- **`ProgrammaticHookEnforcement`** class - Programmatic enforcement of hooks
- Pre-execution and post-execution hooks
- Environment setup and validation
- Redis integration for metrics

### 2. Current Hook Implementation Status

#### **CRITICAL FINDING: Hooks are currently DISABLED**

Both `websocket_handler.py` and `process_manager.py` have the hook system **temporarily disabled** due to a blocking issue:

```python
# TEMPORARY FIX: Disable hooks to prevent hanging
# The hook system uses blocking subprocess.run() which hangs the async event loop
# TODO: Fix hook system to use async subprocess execution
if False and self.hooks and self.hooks.enabled:
```

This appears in:
- `websocket_handler.py` line 403
- `process_manager.py` line 85

### 3. Hook Usage Patterns

#### A. **cc_execute.py** (Client)
- **Does NOT use the formal hook system**
- Instead, directly runs hook scripts using subprocess:
  ```python
  # Lines 513-522: Direct hook script execution
  hooks_dir = Path(__file__).parent.parent / "hooks"
  for hook in ["setup_environment.py", "claude_instance_pre_check.py"]:
      hook_path = hooks_dir / hook
      if hook_path.exists():
          subprocess.run([sys.executable, str(hook_path)], check=True)
  ```
- Runs hooks synchronously before Claude commands
- No integration with `HookIntegration` class

#### B. **websocket_handler.py** (Server)
- **Imports and initializes `HookIntegration`** (lines 208-215)
- **Pre-execution hooks**: 
  - Would analyze command complexity (line 407)
  - Would validate and wrap commands (lines 421-490)
  - Currently DISABLED with `if False` check
- **Post-execution hooks**:
  - Would collect metrics and output (lines 987-1010)
  - Currently executes despite hooks being disabled
- **Direct hook execution**: Also runs hook scripts directly (lines 513-522), similar to cc_execute.py

#### C. **process_manager.py** (Process Management)
- **Uses `@ensure_hooks` decorator** on `execute_command` method (line 68)
- **Pre-execution hook integration**:
  - Would wrap commands with virtual environment (lines 86-94)
  - Currently DISABLED with `if False` check
- No post-execution hooks implemented

### 4. Hook Execution Methods

The codebase uses **three different approaches** to execute hooks:

1. **Formal Hook System** (via `HookIntegration` class)
   - Async-safe execution using `asyncio.create_subprocess_exec`
   - Configuration-based (`/claude-hooks.json`)
   - Currently DISABLED due to hanging issues

2. **Direct Script Execution** (subprocess.run)
   - Used in both `cc_execute.py` and `websocket_handler.py`
   - Synchronous execution
   - No configuration needed
   - Actually working

3. **Programmatic Enforcement** (`ProgrammaticHookEnforcement` class)
   - Newer approach to work around hook issues
   - Built into `HookIntegration` as a fallback
   - Uses `asyncio.to_thread` for async compatibility

### 5. The Hanging Problem

The root cause of the hook system being disabled:
- Original hook implementation used `subprocess.run()` (blocking)
- This blocks the async event loop in WebSocket/asyncio contexts
- The fix in `hook_integration.py` now uses `asyncio.create_subprocess_exec`
- However, the main code still has hooks disabled with `if False`

### 6. Environment Variables

No environment variables found for disabling hooks. The disabling is hard-coded with `if False` conditions.

## Recommendations

1. **Re-enable the hook system** - The hanging issue appears to be fixed in `hook_integration.py` with async subprocess execution

2. **Unify hook execution** - Currently using three different methods. Should standardize on the `HookIntegration` class

3. **Remove temporary disabling** - Change `if False and self.hooks` back to `if self.hooks` in:
   - `websocket_handler.py` line 403
   - `process_manager.py` line 85

4. **Consolidate direct script execution** - Move the direct `subprocess.run` calls to use the hook system

5. **Add integration tests** - Verify hooks work correctly in async contexts without hanging

## Summary

The hook system is well-designed but currently disabled due to a past hanging issue that appears to have been resolved. The codebase has evolved to work around the disabled hooks by using direct script execution, creating inconsistency. Re-enabling the formal hook system and consolidating the different execution methods would improve code maintainability and consistency.