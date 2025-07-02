# cc_executor Hook Scripts

This directory contains **all lifecycle hooks** that the `cc_executor` runtime can execute before, during, or after a task. Think of hooks as small Python utilities that:

* validate pre-conditions (env, deps, task list)
* harden security (structured output enforcement, hallucination detection)
* collect metrics
* mutate the command or Claude prompt when needed

Hooks are opt-in and wired up via `.claude-hooks.json`.

> 📚 Background: Anthropic hook architecture → <https://docs.anthropic.com/claude/hooks> (conceptual)  
> 🌐 Project overview → `docs/HOOK_SYSTEM_COMPREHENSIVE_GUIDE.md`

---

## Lifecycle

| Stage | Common Key | Purpose |
|-------|------------|---------|
| **pre-tool** | `check_task_dependencies.py` | Ensure earlier tasks & WebSocket readiness; extract required packages. |
| **pre-claude** | `claude_instance_pre_check.py` | Validate env/venv, MCP config, missing pkgs, generate init commands. |
| **pre-execute** | `setup_environment.py` | Activate local `.venv`, record wrapped command in Redis. |
| **post-claude** | `claude_response_validator.py` | Grade Claude JSON & hallucination risk. |
| **post-tool** | `record_execution_metrics.py` | Push exec time, complexity, hallucination stats to Redis. |
| **post-output** | `truncate_logs.py` | Remove/shorten base64 blobs & embeddings from logs. |

Additional helpers (may be wired to any stage):

* `analyze_task_complexity.py` – Classifies commands 0-4 (used for dynamic timeouts).
* `task_list_preflight_check.py` – Lints & sanity-checks user task lists.
* `update_task_status.py` – Stores task status progress.
* `debug_hooks.py` – Run a dry-run of ALL hooks locally.
* `review_code_changes.py` – Static analysis of code edits before execution.

---

## Configuration Example

```json
{
  "timeout": 60,
  "env": {
    "AUTO_INSTALL_MISSING_PKGS": "true"
  },
  "hooks": {
    "pre-tool":       "python src/cc_executor/hooks/check_task_dependencies.py",
    "pre-claude":     "python src/cc_executor/hooks/claude_instance_pre_check.py",
    "pre-execute":    {"command": "python src/cc_executor/hooks/setup_environment.py", "timeout": 30},
    "post-claude":    "python src/cc_executor/hooks/claude_response_validator.py",
    "post-tool":      "python src/cc_executor/hooks/record_execution_metrics.py",
    "post-output":    "python src/cc_executor/hooks/truncate_logs.py"
  }
}
```

---

## Debugging Tips

1. **Run a hook in isolation**
   ```bash
   python src/cc_executor/hooks/check_task_dependencies.py --test
   ```
   Most scripts implement a `--test` flag that prints demo output without side-effects.

2. **Simulate the full chain**
   ```bash
   python src/cc_executor/hooks/debug_hooks.py --session dev_session_123 --command "echo hi"
   ```

3. **View metrics in Redis**
   ```bash
   redis-cli lrange claude:exec_time:complexity:2 0 10
   redis-cli hgetall task:status
   ```

4. **Tail logs while hacking**
   ```bash
   tail -f logs/hook_*.log | grep -v ANTHROPIC_API_KEY
   ```

---

## Template – Creating a New Hook

Create `my_new_hook.py` and start with:

```python
#!/usr/bin/env python3
"""Short description of what this hook does."""

import os
import sys
import json
from loguru import logger

DEFAULT_TIMEOUT = 45  # seconds


def main():
    # Access context via env vars (prefixed by CLAUDE_*)
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    command     = os.environ.get("CLAUDE_COMMAND", "")

    logger.info("Running my_new_hook for session %s", session_id)

    # TODO: implement logic
    result = {
        "success": True,
        "note": "All good"
    }

    # Output JSON to stdout so the orchestrator can parse it
    print(json.dumps(result))


if __name__ == "__main__":
    if "--test" in sys.argv:
        # Local smoke-test
        os.environ["CLAUDE_COMMAND"] = "echo 'hello'"
        main()
    else:
        main()
```

1. Add the script to `src/cc_executor/hooks/`.
2. Wire it in `.claude-hooks.json` under the desired stage.
3. Document any new env vars or Redis keys in this README.

---

## Contributing

* Follow the **security guidelines**: no `shell=True`, parse commands with `shlex.split`, remove sensitive env vars from logs.
* Keep runtime <200 ms; heavy work should be async or scheduled later.
* Add a `--test` mode so others can run the hook standalone.

Every hook **must expose** a `--test` mode that exercises its core logic (run: `python hook.py --test`).
If a change affects cross-hook contracts (e.g., JSON schema, Redis keys), also update the lightweight smoke tests in `tests/unit/contract_checks.py` so CI can catch regressions.
