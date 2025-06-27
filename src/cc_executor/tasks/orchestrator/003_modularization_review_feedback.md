# Review Feedback 003: Modularization of CC Executor Core

**Date**: 2025-06-25  
**Reviewer**: O3  
**Component**: core modularization (config.py, models.py, session_manager.py, process_manager.py, stream_handler.py, websocket_handler.py, main.py, __init__.py)

---

## 1  Summary

The refactor succeeds in splitting the monolithic 503-line `implementation.py` into eight focused modules, each < 500 lines and richly documented. All provided usage examples execute without error. Service health endpoint responds ✅.

Overall code quality is high; nevertheless I identified nine concrete issues (2 critical, 4 major, 3 minor) that should be addressed before declaring the refactor production-ready.

---

## 2  Execution Log

```
REVIEW_START_20250625_144310
$ python core/config.py            → exit 0
$ python core/models.py            → exit 0
$ python core/session_manager.py   → exit 0
$ python core/process_manager.py   → exit 0
$ python core/stream_handler.py    → exit 0
$ python core/websocket_handler.py → exit 0
$ python core/main.py --test       → exit 0
REVIEW_END_20250625_144623
```

All examples ran successfully. Unit results reproduced the marker `USAGE_TEST_20250625_140606`.

---

## 3  Findings & Fixes

| ID | Severity | File | Line | Issue | Recommended Fix |
|---|---|---|---|---|---|
| 1 | critical | process_manager.py | ≈40 | **Shell-Injection Risk** – commands are passed to `/bin/bash -c <string>` directly, allowing arbitrary shell meta-chars from untrusted clients. | Replace with `asyncio.create_subprocess_exec(*shlex.split(cmd))` **or** validate/whitelist commands before execution. Provide explicit unit tests for injection attempts. |
| 2 | critical | websocket_handler.py | n/a | **Missing Authentication / Origin Check** – any client can open a WebSocket. | Enforce origin/API-key header or token auth before accepting sessions. |
| 3 | major | stream_handler.py | ≈150 | Back-pressure loop uses fixed delay `await asyncio.sleep(0.01)` which can still fall behind on very high throughput (>1 MB/s). | Switch to `await queue.put(chunk)` with `queue_maxsize` and use `await writer.drain()`; propagate `asyncio.CancelledError` upward. |
| 4 | major | session_manager.py | cleanup_expired_sessions | Expired sessions are collected inside lock, but removal happens outside **without re-checking presence**, risking `KeyError` if a concurrent remove happened. | Hold the lock while popping, or copy keys then safely pop with `.pop(key, None)`. Add race-condition test. |
| 5 | major | process_manager.py | control_process | SIGKILL fallback after SIGTERM is missing – long-running children may ignore SIGTERM. | After timeout (configurable) send `SIGKILL` to pgid. |
| 6 | major | main.py | health endpoint | Health metrics exclude queue length / back-pressure stats, making Grafana alerting harder. | Include stream queue depth & average latency in `/health`. |
| 7 | minor | models.py | ≈120 | `SessionInfo.websocket` annotated as `Any`; should be `WebSocket` from `fastapi`. | Update type and add `typing.TYPE_CHECKING` guard to avoid heavy import. |
| 8 | minor | config.py | constants | Magic numbers (timeouts, max buffer size) hard-coded. | Expose via environment variables and document defaults. |
| 9 | minor | __init__.py | top | Module exports are implicit. | Add `__all__` list for public API clarity. |

---

## 4  Template Compliance Check (prompts)

Prompts `T01`, `T02`, `T03`, `T05` were **not present** in `/prompts/`; hence compliance could not be verified. They must be added or relocated before next review.

---

## 5  Conclusion

Great progress – code is cleaner, testable, and under 500 lines per file. Address the critical command-injection vector and authentication gap immediately, then tackle the remaining items. After fixes, please rerun usage tests and stress suite.

_O3 out._
