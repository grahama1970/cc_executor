# Known Issues & Operational Notes

> Last updated: 2025-06-28

This document tracks non-blocking bugs, configuration quirks, and operational gotchas discovered during stress-testing of **cc_executor**. When an item is resolved the *Status* column should be updated and the entry moved to the *Resolved* section.

## Open Issues

| ID | Area | Symptom / Log Snippet | Work-around | Status |
|----|------|-----------------------|-------------|--------|
| KI-001 | WebSocket frame size | Client disconnect with code **1009** (`Message Too Big`) when a single process output line exceeds ~60 KB JSON | Apply outbound-chunking patch (see issue #42) or reduce process verbosity | Open |
| KI-002 | Back-pressure | Server stall: last log `websocket send blocked…`; no further `process.output` events | Restart client or disable proxy buffering (`proxy_buffering off` in Nginx) | Open |
| KI-003 | Windows signals | `PAUSE` / `RESUME` have no effect under Windows because `os.setsid` / `killpg` are POSIX-only | Use `CANCEL` only; document limitation | Docs pending |

## Resolved Issues

| ID | Area | Fix Version | Notes |
|----|------|-------------|-------|
| KI-004 | Session TTL race could exceed `MAX_SESSIONS` by 1 | v0.4.3 (commit `4f7c215`) | `cleanup_expired_sessions()` now deletes while holding the lock |

---

### Adding a new entry
1. Add a unique *ID* (`KI-xxx`).
2. Provide a concise one-line *Symptom* with any log keywords.
3. Record the *Work-around* so on-call engineers can react quickly.
4. Link to the GitHub issue / ticket in *Status* (e.g. `PR #99 open`).

### Updating this file
After merging a fix, move the row to **Resolved Issues**, fill in *Fix Version*, and replace *Status* with “Fixed”.
