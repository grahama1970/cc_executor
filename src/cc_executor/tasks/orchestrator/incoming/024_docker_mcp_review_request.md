# Code Review Request: Docker Container Startup Issues

## Summary

The Docker container for CC Executor repeatedly fails to start with "python: can't open file '/app/start_services.py': [Errno 2] No such file or directory" error. Despite multiple attempts to fix the Dockerfile CMD path and rebuild without cache, the container continues using an old CMD configuration.

**CRITICAL: Multi-Task Sequential Execution Status**
- [x] Changes maintain WebSocket blocking for sequential execution
- [x] No parallel execution introduced
- [x] Orchestrator pattern preserved

## Changes Made

### Files Modified/Created
- `deployment/Dockerfile` - Updated to use uv package manager and fix CMD path
- `deployment/docker-compose.yml` - Added DISABLE_VENV_WRAPPING environment variable
- `deployment/start_services.py` - Unified startup script for FastAPI and WebSocket
- `deployment/test_mcp_protocol.py` - Created to test MCP protocol
- `src/cc_executor/hooks/hook_integration.py` - Added venv wrapping disable for Docker

### Key Changes

1. **Docker Configuration**:
   - Changed from separate containers to unified cc_execute container
   - Updated Dockerfile to use uv instead of pip
   - Added environment variable to disable venv wrapping in containers
   - Fixed CMD path to use relative "deployment/start_services.py"

2. **MCP Integration**:
   - Added MCP manifest endpoint at `/.well-known/mcp/cc-executor.json`
   - WebSocket accepts connections at `/ws/mcp`
   - Supports standard JSON-RPC methods

## Testing Performed

### Automated Tests
- [x] MCP protocol connects successfully locally
- [x] WebSocket handler accepts execute commands
- [ ] Docker container starts successfully (FAILING)

### Manual Testing
```bash
# Local MCP test works
python deployment/test_mcp_protocol.py
# Output: Successfully connects to WebSocket, receives "connected" notification

# Docker build completes but container fails to start
docker compose build --no-cache cc_execute
docker compose up -d
# Error: python: can't open file '/app/start_services.py': [Errno 2] No such file or directory
```

### Test Results Summary
- **Success Rate**: Local MCP works, Docker fails to start
- **Performance**: N/A - container won't start
- **Edge Cases**: Not tested due to startup failure

## Potential Issues to Review

### 1. Docker Image Cache Not Updating
**File**: `deployment/Dockerfile`
**Line**: 38 (CMD line)
**Description**: Despite rebuilding with --no-cache, docker inspect shows old CMD
**Risk Level**: High
**Attempted Fixes**: 
- docker compose down --rmi all --volumes --remove-orphans
- docker system prune -f
- docker rmi deployment-cc_execute
- Still uses cached CMD configuration

### 2. Volume Mount Overriding Container Files
**File**: `deployment/docker-compose.yml`
**Line**: 30-31
**Description**: Mounting source directory may override container's file structure
**Risk Level**: High
**Suggested Fix**: Review volume mounts and ensure critical files aren't overwritten

### 3. Python Path Issues in Container
**File**: `src/cc_executor/hooks/hook_integration.py`
**Line**: 172-179
**Description**: Container tries to use /app/.venv/bin/python which doesn't exist
**Risk Level**: Medium
**Current Fix**: Added DISABLE_VENV_WRAPPING=1 environment variable

## Questions for Reviewer

1. Why does Docker continue using old CMD despite multiple cache-clearing attempts?
2. Is there a better way to handle the source code volume mount without overriding container files?
3. Should we simplify to a single process instead of using start_services.py?

## Review Focus Areas

Please pay special attention to:
1. Docker build cache behavior and CMD persistence
2. Volume mounting strategy in docker-compose.yml
3. Whether the unified container approach is appropriate

## Definition of Done

- [ ] Docker container starts successfully
- [ ] MCP protocol works inside Docker container
- [ ] All services (FastAPI + WebSocket) run properly
- [ ] Documentation updated with working Docker instructions