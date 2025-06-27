# Next Steps: Architecture & Testing Strategy

## Current Status

1. **MCP WebSocket Service**: ✅ Implemented in `core/implementation.py`
   - FastAPI with WebSocket endpoint at `/ws/mcp`
   - All critical fixes from O3 review implemented
   - Ready for containerization

2. **Architecture Issues to Address**:
   - 600+ line monolithic file needs refactoring
   - No Docker setup yet
   - Tests scattered in /executor instead of proper test directory

## Proposed Architecture

### 1. Refactor Monolithic File
```
src/cc_executor/core/
├── __init__.py
├── main.py              # FastAPI app and entry point
├── websocket_handler.py # WebSocket endpoint logic
├── process_manager.py   # Process execution/control
├── session_manager.py   # Session tracking with locks
├── security.py          # Command validation
├── logging_config.py    # Structured logging setup
└── models.py           # Pydantic models for requests/responses
```

### 2. Docker Setup
```
docker-simple/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

### 3. Proper Test Structure
```
tests/
├── unit/
│   ├── test_process_manager.py
│   ├── test_security.py
│   └── test_session_manager.py
├── integration/
│   ├── test_websocket_reliability.py
│   └── test_stress_scenarios.py
└── e2e/
    └── test_docker_mcp_integration.py
```

## Testing Strategy

### Stage 1: Local MCP Testing ✅ (Current)
- Direct testing of FastAPI WebSocket service
- Verify all O3 fixes work correctly
- Run stress tests locally

### Stage 2: Docker Integration
- Create Dockerfile with proper Python environment
- Expose port 8003 for MCP service
- Test container isolation and resource limits

### Stage 3: Full E2E with Claude Code
- Docker Compose with cc_executor service
- Mount volumes for code execution
- Test bidirectional communication reliability

## Critical Issues Found

### O3 Review Error
**IMPORTANT**: O3's Fix #1 was technically incorrect:
- Suggested: `os.killpg(-pgid, signal)` 
- Correct: `os.killpg(pgid, signal)`
- This has been documented in implementation reports

### Current Execution Context
- Running tests from `/executor` directory is incorrect
- Service should run from: `python src/cc_executor/core/implementation.py`
- `/executor` is only for tracking implementation progress

## Immediate Next Actions

1. **Refactor** `implementation.py` into proper modules
2. **Create** Dockerfile and docker-compose.yml
3. **Move** tests to proper test directory structure
4. **Document** the complete architecture in README

## Questions for User

1. Should we refactor the monolithic file before Docker setup?
2. Do you want the full Docker Compose setup now or after refactoring?
3. Should we prioritize E2E testing with Claude Code integration?