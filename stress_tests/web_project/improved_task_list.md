# Improved Task List for WebSocket Execution

## Overview
This task list demonstrates reliable WebSocket-based task execution using cc_execute.md. Each task spawns a Claude instance through WebSocket for bidirectional communication and proper completion tracking.

## Task Format Template
```
**Task N**: [Brief Title]
Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: [Specific action in question format]
- Timeout: [seconds or "Redis estimate"]
- Success Criteria:
  1. [Specific check 1]
  2. [Specific check 2]
  3. [Specific check 3]
- Retry Strategy: [How to improve if failed]
```

---

## Task 1: Create Configuration File

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is a Python config.py file with DATABASE_URL='sqlite:///test.db' and DEBUG=True? Create this file with proper Python syntax.
- Timeout: 45 seconds
- Success Criteria:
  1. File config.py exists in current directory
  2. Contains DATABASE_URL = 'sqlite:///test.db'
  3. Contains DEBUG = True
- Retry Strategy: Add explicit instructions to use Write tool and show exact Python syntax

## Task 2: Verify Configuration Import

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What happens when I run: python -c "from config import DATABASE_URL, DEBUG; print(f'DB: {DATABASE_URL}, Debug: {DEBUG}')"? Execute this command and show the output.
- Timeout: 30 seconds
- Success Criteria:
  1. Output displays "DB: sqlite:///test.db, Debug: True"
  2. No ImportError or ModuleNotFoundError
  3. Command exits with code 0
- Retry Strategy: First verify config.py exists with ls -la config.py

## Task 3: Test Redis Connection

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: How do I check if Redis is running? Execute redis-cli ping and show the result.
- Timeout: Redis estimate
- Success Criteria:
  1. Output contains "PONG"
  2. No "Could not connect" errors
  3. Command completes successfully
- Retry Strategy: Check Redis service status with systemctl status redis or ps aux | grep redis