Hi everyone! I've been working with hooks and found a workaround that might help others while waiting for the official fix.

## Workaround: Subprocess-level Hook Execution

Instead of relying on Claude Code's hook system, you can intercept commands at the subprocess level and run hooks programmatically. This approach has been working reliably in my testing.

### Basic Implementation

```python
import subprocess
import sys
import os
from pathlib import Path

def execute_with_hooks(command: str, hooks_dir: Path = Path("~/.claude/hooks").expanduser()):
    """Execute command with pre/post hooks."""
    
    # Pre-execution hooks
    pre_hooks = ["pre-tool", "setup_environment.py"]
    for hook in pre_hooks:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            try:
                subprocess.run([sys.executable, str(hook_path)], check=True)
                print(f"✓ Ran pre-hook: {hook}")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Pre-hook failed: {hook} - {e}")
    
    # Setup environment (e.g., activate venv)
    env = os.environ.copy()
    venv_path = Path(".venv")
    if venv_path.exists():
        env["VIRTUAL_ENV"] = str(venv_path.absolute())
        env["PATH"] = f"{venv_path}/bin:{env['PATH']}"
    
    # Execute main command
    result = subprocess.run(command, shell=True, env=env, capture_output=True, text=True)
    
    # Post-execution hooks
    post_hooks = ["post-tool", "record_metrics.py"]
    for hook in post_hooks:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            try:
                # Pass execution results to post-hooks via env vars
                hook_env = env.copy()
                hook_env["CLAUDE_EXIT_CODE"] = str(result.returncode)
                hook_env["CLAUDE_OUTPUT_LENGTH"] = str(len(result.stdout))
                subprocess.run([sys.executable, str(hook_path)], env=hook_env, check=True)
                print(f"✓ Ran post-hook: {hook}")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Post-hook failed: {hook} - {e}")
    
    return result

# Example usage
if __name__ == "__main__":
    result = execute_with_hooks("python --version")
    print(f"Command output: {result.stdout}")
    print(f"Exit code: {result.returncode}")
```

### Integration with Async Subprocess (for WebSocket/API servers)

```python
import asyncio

async def execute_with_hooks_async(command: list, hooks_dir: Path = Path("~/.claude/hooks").expanduser()):
    """Async version for integration with FastAPI/WebSocket servers."""
    
    # Run pre-hooks synchronously (they're usually quick)
    pre_hooks = ["pre-tool", "setup_environment.py"]
    for hook in pre_hooks:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(hook_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
    
    # Setup environment
    env = os.environ.copy()
    venv_path = Path(".venv")
    if venv_path.exists():
        env["VIRTUAL_ENV"] = str(venv_path.absolute())
        env["PATH"] = f"{venv_path}/bin:{env['PATH']}"
    
    # Execute main command
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await proc.communicate()
    
    # Run post-hooks
    post_hooks = ["post-tool", "record_metrics.py"]
    for hook in post_hooks:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            hook_env = env.copy()
            hook_env["CLAUDE_EXIT_CODE"] = str(proc.returncode)
            hook_proc = await asyncio.create_subprocess_exec(
                sys.executable, str(hook_path),
                env=hook_env
            )
            await hook_proc.communicate()
    
    return proc.returncode, stdout.decode(), stderr.decode()
```

### Key Benefits

1. **Deterministic execution** - Hooks run every time, not dependent on AI compliance
2. **Environment isolation** - Each subprocess gets proper venv activation
3. **Error handling** - Hook failures don't crash the main process
4. **Async support** - Works with modern async Python applications

### Testing Results

I've tested this approach with:
- Multiple sequential Claude commands ✓
- Long-running processes (3-5 minutes) ✓
- Commands that generate large outputs ✓
- Both sync and async implementations ✓

All tests show consistent hook execution, unlike the current Claude Code hook system.

### Example Hook Scripts

**~/.claude/hooks/setup_environment.py**
```python
#!/usr/bin/env python3
import os
import sys

# Activate virtual environment
venv_path = ".venv"
if os.path.exists(venv_path):
    activate_script = os.path.join(venv_path, "bin", "activate_this.py")
    if os.path.exists(activate_script):
        exec(open(activate_script).read(), {'__file__': activate_script})

# Set any required environment variables
os.environ["PYTHONPATH"] = "./src"
print(f"[HOOK] Environment configured - Python: {sys.executable}")
```

**~/.claude/hooks/record_metrics.py**
```python
#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path

# Read execution results from environment
exit_code = os.environ.get("CLAUDE_EXIT_CODE", "unknown")
output_length = os.environ.get("CLAUDE_OUTPUT_LENGTH", "0")

# Log metrics (example using JSON file, could use Redis/DB)
metrics = {
    "timestamp": time.time(),
    "exit_code": exit_code,
    "output_length": int(output_length),
}

log_file = Path("~/.claude/metrics.jsonl").expanduser()
with open(log_file, "a") as f:
    f.write(json.dumps(metrics) + "\n")

print(f"[HOOK] Metrics recorded - Exit: {exit_code}, Output: {output_length} bytes")
```

Hope this helps anyone who needs hook functionality while we wait for the official fix! The subprocess approach has been working reliably in production for my use cases.