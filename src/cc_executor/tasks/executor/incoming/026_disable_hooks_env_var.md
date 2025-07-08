# 026 – Disable Hooks via Env Var (Safest Hotfix)

The recent attempts to add timeouts directly into `websocket_handler.py` introduced indentation and syntax errors.
To unblock Docker + MCP testing **without touching runtime code** we will:

1. **Disable hook subsystem at runtime.**  Set `CC_EXECUTOR_ENABLE_HOOKS=0` in `deployment/docker-compose.yml` under the `cc_execute` service.

```yaml
    environment:
      LOG_LEVEL: INFO
      PYTHONUNBUFFERED: "1"
      REDIS_URL: redis://redis:6379
      DISABLE_VENV_WRAPPING: "1"
      CC_EXECUTOR_ENABLE_HOOKS: "0"   # <— add this
```

2. **Rebuild & restart**
```bash
docker compose build cc_execute && docker compose up -d --force-recreate
```

3. **Test MCP**
Run the Loguru debug script (or Claude prompt) again; the WebSocket should execute commands instead of hanging.

4. **Next Steps** (separate task)
If hooks are required, implement a clean, fully-tested timeout wrapper in a small utility module rather than inline edits.

## Rationale
• Fastest path to recover working container.
• Avoids complex in-place patching that causes lints/errors.
• Keeps codebase stable for other devs.

---
**No further code edits performed in this hotfix.**
