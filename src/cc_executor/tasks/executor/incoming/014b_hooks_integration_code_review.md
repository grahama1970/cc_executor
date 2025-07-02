# 014b – Code Review Report: Hook Integration for `cc_executor`

**Reviewer:** Cascade AI
**Date:** 2025-07-02
**Scope:** Entire repository, with focus on new hook framework (`src/cc_executor/hooks/`), core plumbing (`hook_integration.py`, `websocket_handler.py`) and supporting artefacts.

---

## 1. Executive Summary
The hook architecture is well-conceived and already lifts reliability (~ 60 % → 85 %).  Implementation quality is high, but several hotspots could yield further robustness, maintainability and security wins with **low complexity cost**.  No blocking issues were found – all recommendations are incremental.

---

## 2. Strengths Observed
1. **Clear Separation of Concerns** – Hook execution is encapsulated in `HookIntegration`; core handler remains readable.
2. **Async-friendly Design** – `asyncio.create_subprocess_shell` avoids event-loop blocking.
3. **Solid Logging** – Extensive `loguru` usage aids diagnosis.
4. **Forward-looking Metrics** – Redis-backed complexity/timeout analytics lay groundwork for adaptive tuning.

---

## 3. Findings & Recommendations
Priority legend ⬤ High ◯ Medium ○ Low

| # | Topic | Finding | Rec | Prio |
|---|-------|---------|-----|------|
| F1 | **Config path calculation** | `hook_integration.py` ascends four `os.path.dirname` calls – brittle if tree changes. | Use `pathlib.Path(__file__).resolve().parents[3]` or inject root via env var. | ◯ |
| F2 | **Shell-string execution** | `execute_hook` feeds hook cmd to `/bin/sh` – risk if config is user-editable. | Prefer `asyncio.create_subprocess_exec(*shlex.split(cmd))` or explicit arg list. | ⬤ |
| F3 | **Context env-var marshalling** | Values are blindly cast to `str`; complex types (dict) lose fidelity. | JSON-encode non-primitives, e.g. `env[KEY] = json.dumps(value)` when `isinstance(value, (dict, list))`. | ◯ |
| F4 | **Timeout granularity** | Single global timeout (60 s) may be too coarse. | Allow per-hook override via `hooks.<name>.timeout` fallback to default. | ○ |
| F5 | **Parallelism control** | Future parallel hook runs not yet serialised → race for shared resources (Redis). | Add optional semaphore (`max_concurrency`) in `HookIntegration`. | ○ |
| F6 | **Logging of sensitive data** | Handler logs when `ANTHROPIC_API_KEY` present/removed – could seep into files. | Drop or redact secret-related logs. | ⬤ |
| F7 | **Redis hard dependency in hooks** | Most hook scripts fail-soft but still import Redis; offline devs will see noisy tracebacks. | Graceful fallback: wrap `import redis` in try/except and skip metrics silently. | ◯ |
| F8 | **`create_activation_wrapper` heuristics** | Sub-string check treats `pytest-cov` as `pytest`, may double-wrap; also fails on flags (`python3`). | Use `shlex.split` + first token comparison (`Path(cmd).name`). | ◯ |
| F9 | **`websocket_handler` complexity** | `_handle_execute` is ~300 LOC with deep nesting. | Extract hook-related branch into helper    (e.g. `_apply_pre_hooks`). Improves testability without new features. | ◯ |
| F10| **Unit-test coverage gaps** | Tests exist for individual hooks but not for failure-path in `HookIntegration`. | Add parametrised tests simulating timeouts, non-zero exit codes, malformed JSON. | ○ |
| F11| **Doc-string drift** | Many new hook scripts have accurate doc-strings, but `analyze_task_complexity.py` uses outdated Arg names. | Regenerate via `pydoc-md`. | ○ |

---

## 4. Quick Wins (≤ 30 min)
* Replace manual path ascension with `pathlib` (F1).
* Redact secret-bearing logs (F6).
* Enhance `create_activation_wrapper` with tokenised match (F8).

---

## 5. Medium Effort (≤ 2 h)
* Harden `execute_hook` against injection (F2).
* Introduce per-hook timeout config (F4).
* Factor hook logic out of `_handle_execute` (F9).

---

## 6. Deferred / Nice-to-have
* Parallel-safety semaphore (F5).
* Extended failure-path unit tests (F10).
* Doc-string housekeeping (F11).

---

## 7. Compatibility & Risk
All suggestions preserve current public behaviour.  Changes around F2/F6 warrant a minor sem-ver bump if external consumers parse logs/scripts.

---

## 8. Conclusion
The hook integration is a significant step forward.  Addressing the highlighted items will tighten security and sustain maintainability with minimal added complexity.  No blockers to merge; recommend incorporating Quick-Wins before next release cycle.
