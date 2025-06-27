# CC Executor MCP - Issues Claude Could Not Fix

## Current Status
- **Component**: WebSocket to HTTP bridge for Claude Docker execution
- **Success Ratio**: 1:3 (Need 5:1 minimum, 10:1 preferred)
- **Main Blocker**: Docker container networking

## What Claude Actually Fixed
1. ✅ `docker-compose` → `docker compose` (v2 syntax)
2. ✅ `timeout` → `open_timeout` for websockets.connect()
3. ✅ Recognized stream format is plain text, not JSON
4. ✅ Simplified test commands from natural language to direct Python

## What Claude Could NOT Fix

### 1. Docker Container Communication
**Problem**: MCP container cannot reach claude-api container
- MCP tries to connect to `http://claude-api:8000`
- This hostname only resolves within docker-compose network
- Getting: `[Errno -2] Name or service not known`

**What I Tried**: 
- Nothing useful, just ran tests repeatedly

**What Needs Fixing**:
- Proper docker network configuration
- Possibly use `host.docker.internal` or proper service discovery
- Health checks with retries

### 2. Test Orchestration Failures
**Problem**: Full test suite times out even though individual components work
- Basic E2E test passes when run manually
- Fails when run through orchestration script

**What I Tried**:
- Simplified test commands (this helped a bit)
- Added more test files (made it worse)

**What Needs Fixing**:
- Debug why docker-compose orchestration fails
- Add proper startup sequencing
- Fix service dependencies

### 3. Stream Completion Detection
**Problem**: Sometimes WebSocket doesn't receive COMPLETED status
- Stream outputs data correctly
- But status update might not be sent/received

**What I Tried**:
- Looked at the code, didn't understand the issue

**What Needs Fixing**:
- Verify claude-code-docker actually sends completion signal
- Add timeout handling for missing status updates
- Consider detecting end-of-stream differently

## File Organization

```
prompts/cc_executor_mcp/
├── implementation.py          # Main WebSocket bridge service
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container definition
├── cc_executor_mcp.md       # Main prompt with metrics
├── scripts/
│   └── run_capability_tests.sh  # Test orchestration
├── tests/
│   ├── test_e2e_client.py      # Basic E2E test
│   ├── mcp_stress_test.py      # 8 stress tests
│   ├── mcp_concurrent_test.py  # Concurrent connection tests
│   └── mcp_hallucination_test.py # Hallucination detection
└── docs/
    └── (this file)
```

## How to Run Tests
```bash
cd /home/graham/workspace/experiments/cc_executor/docker-simple
bash ./prompts/cc_executor_mcp/scripts/run_capability_tests.sh
```

## Critical Environment Variable
- **ANTHROPIC_API_KEY=""** must be set to empty string for local execution

## Test Results Pattern
- Basic E2E: Usually passes
- Stress tests: All timeout
- Concurrent: Network errors
- Hallucination: Never reached (prior tests fail)

## What Gemini Should Focus On
1. Fix Docker networking between containers
2. Add robust health checks and retries
3. Debug why orchestration fails when components work individually
4. Consider if architecture needs fundamental changes

## Honest Assessment
Claude (me) is capable of fixing typos and simple syntax errors. Debugging distributed systems with Docker networking is beyond my capabilities. I made 9 failed attempts without understanding the root cause.