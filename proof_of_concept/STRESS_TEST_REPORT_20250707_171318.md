2025-07-07 17:13:19.045 | WARNING  | cc_executor.hooks.analyze_task_complexity:<module>:27 - rank_bm25 not installed, using simple matching
2025-07-07 17:13:19 | INFO     | cc_executor.core.session_manager:__init__:86 - Redis connection established for session storage
2025-07-07 17:13:19 | INFO     | core.session_manager:__init__:86 - Redis connection established for session storage
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcore.session_manager[0m:[36m__init__[0m:[36m86[0m - [1mRedis connection established for session storage[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcc_executor.hooks.hook_integration[0m:[36m_load_config[0m:[36m335[0m - [1mLoaded hook configuration from /home/graham/workspace/experiments/cc_executor/.claude-hooks.json[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcc_executor.core.websocket_handler[0m:[36m__init__[0m:[36m211[0m - [1mHook integration enabled with 2 hooks configured[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcc_executor.core.session_manager[0m:[36m__init__[0m:[36m86[0m - [1mRedis connection established for session storage[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcc_executor.hooks.hook_integration[0m:[36m_load_config[0m:[36m335[0m - [1mLoaded hook configuration from /home/graham/workspace/experiments/cc_executor/.claude-hooks.json[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36mcc_executor.core.websocket_handler[0m:[36m__init__[0m:[36m211[0m - [1mHook integration enabled with 2 hooks configured[0m
[32m2025-07-07 17:13:19[0m | [33m[1mWARNING [0m | [36m__main__[0m:[36m<module>[0m:[36m33[0m - [33m[1mCould not import json_utils, using basic JSON parsing[0m
Testing CC Executor...
============================================================

1. Running simple test...
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m180[0m - [1mAmending prompt for better reliability...[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m190[0m - [1mApplied basic amendment: Write a Python function that calculates fibonacci ... → What is a Python function that calculates fibonacc...[0m
[32m2025-07-07 17:13:19[0m | [33m[1mWARNING [0m | [36m__main__[0m:[36mestimate_timeout[0m:[36m104[0m - [33m[1mRedis returned suspiciously low timeout: 18s, using base: 90s[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m257[0m - [1mTimeout set to: 300s (estimated: 90s) for task: What is a Python function that calculates fibonacc...[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m266[0m - [1m[197de14d] === CC_EXECUTE LIFECYCLE START ===[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m267[0m - [1m[197de14d] Task: What is a Python function that calculates fibonacci numbers?...[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m268[0m - [1m[197de14d] Session ID: 197de14d[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m269[0m - [1m[197de14d] Execution UUID: 574ce5a4-d79a-4a3f-a4f3-0db27adf01dc[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m270[0m - [1m[197de14d] Timeout: 300s[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m271[0m - [1m[197de14d] Stream: True[0m
🔐 Starting execution with UUID: 574ce5a4-d79a-4a3f-a4f3-0db27adf01dc
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m323[0m - [1mFound MCP config at: /home/graham/.claude/claude_code/.mcp.json[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m345[0m - [1mExecuting command: claude -p "What is a Python function that calculates fibonacci numbers?" --mcp-config "/home/graham/.claude/claude_code/.mcp.json" --dangerously-skip-permissions --model claude-opus-4-20250514[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m348[0m - [1m[197de14d] Creating subprocess...[0m
[32m2025-07-07 17:13:19[0m | [1mINFO    [0m | [36m__main__[0m:[36mcc_execute[0m:[36m357[0m - [1m[197de14d] Subprocess created with PID: 1578356[0m
