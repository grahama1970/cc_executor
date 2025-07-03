# Known Issues & Operational Notes

> Last updated: 2025-07-02

This document tracks non-blocking bugs, configuration quirks, and operational gotchas discovered during stress-testing of **cc_executor**. When an item is resolved the *Status* column should be updated and the entry moved to the *Resolved* section.

## Open Issues

| ID | Area | Symptom / Log Snippet | Work-around | Status |
|----|------|-----------------------|-------------|--------|
| KI-002 | Back-pressure | Server stall: last log `websocket send blocked…`; no further `process.output` events | Restart client or disable proxy buffering (`proxy_buffering off` in Nginx) | Under investigation |
| KI-007 | Memory usage | High memory consumption with very large outputs (>100MB) | Monitor memory usage, consider streaming to disk for large operations | Open |
| KI-008 | Concurrent session limits | Performance degradation when approaching MAX_SESSIONS limit | Reduce MAX_SESSIONS or scale horizontally | Open |

## Resolved Issues

| ID | Area | Fix Version | Notes |
|----|------|-------------|-------|
| KI-001 | WebSocket frame size | v0.5.0 | Implemented chunking for large messages |
| KI-003 | Windows signals | v0.4.5 | Documented in guides/troubleshooting.md |
| KI-004 | Session TTL race could exceed `MAX_SESSIONS` by 1 | v0.4.3 (commit `4f7c215`) | `cleanup_expired_sessions()` now deletes while holding the lock |
| KI-005 | Process stdin deadlock | v0.4.8 | Added `stdin=asyncio.subprocess.DEVNULL` to prevent hanging |
| KI-006 | Large output truncation | v0.5.0 | Added transcript logging to capture full output |

---

### Adding a new entry
1. Add a unique *ID* (`KI-xxx`).
2. Provide a concise one-line *Symptom* with any log keywords.
3. Record the *Work-around* so on-call engineers can react quickly.
4. Link to the GitHub issue / ticket in *Status* (e.g. `PR #99 open`).

### Updating this file
After merging a fix, move the row to **Resolved Issues**, fill in *Fix Version*, and replace *Status* with “Fixed”.
