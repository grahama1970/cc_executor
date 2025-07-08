# Docker Deployment Failure Report

**Date**: 2025-07-05
**Author**: Claude

## Summary

The Docker deployment is failing due to issues with the WebSocket container startup command and build times.

## What Was Done

1. **Fixed Initial Issues**:
   - Created `requirements.txt` file from `pyproject.toml` dependencies
   - Removed unnecessary dependencies (claude-code-sdk, heavy ML libraries)
   - Fixed Dockerfile CMD from non-existent module to correct one

2. **Docker Setup Process**:
   - Used `docker_setup.py` which analyzes the Docker environment first
   - Successfully starts Redis container on port 6380
   - Builds WebSocket and API containers

3. **Current Status**:
   - Redis container: ✅ Running and healthy
   - WebSocket container: ❌ Crashes on startup
   - API container: ❌ Cannot start (depends on WebSocket)

## Key Failure Points

### 1. WebSocket Container Startup Command Issue

**Location**: `/deployment/Dockerfile` line 21
```dockerfile
CMD ["python", "-m", "cc_executor.core.main"]
```

**Problem**: The `main.py` script has a conditional in its `__main__` block:
- When run without arguments, it executes a test/demo mode and exits
- When run with `--server` flag, it starts the actual server
- But argparse doesn't accept `--server` as a valid argument

**File**: `/src/cc_executor/core/main.py` lines 206-217
```python
if __name__ == "__main__":
    # Check if being run with --server flag to start actual server
    if len(sys.argv) > 1 and "--server" in sys.argv:
        main()
    else:
        # Runs demo/test code and exits
```

### 2. Build Time Issues

**Problem**: Docker build takes 5+ minutes due to:
- Installing heavy dependencies (numpy, scipy, pandas, matplotlib)
- Building wheels for all packages
- The `pip install -e .` reinstalls everything

### 3. Health Check Failure

**Location**: `docker-compose.yml` lines 38-46
```yaml
healthcheck:
  test:
  - CMD
  - curl
  - -f
  - http://localhost:8003/health
```

The health check fails because the container exits before the server starts.

## Files Being Used in Dockerfile

1. **Context**: `..` (parent directory of deployment/)
2. **Dockerfile Path**: `deployment/Dockerfile`
3. **Files Copied**:
   - `requirements.txt` - Dependencies list
   - `.` (entire project) - All source code
4. **Key Modules Referenced**:
   - `cc_executor.core.main` - Main entry point
   - `cc_executor.core.start_server` - Attempted wrapper (created but may not work)

## Attempted Solutions

1. Created `start_server.py` wrapper to bypass the `__main__` logic
2. Tried various CMD variations:
   - `CMD ["python", "-m", "cc_executor.core.websocket_server"]` - Module doesn't exist
   - `CMD ["python", "-m", "cc_executor.core.main", "--server"]` - Argparse rejects --server
   - `CMD ["python", "-m", "cc_executor.core.main"]` - Runs demo mode and exits

## Recommended Fix

The simplest fix would be to modify the `main()` function in `main.py` to:
1. Remove the `--server` check from `__main__`
2. Always run the server when called as main module
3. Move the demo/test code to a separate script

Or create a proper entry point script that directly starts uvicorn without the conditional logic.

## Docker Environment Analysis

The `docker_setup.py` script successfully:
- Runs `docker ps --format json` to analyze environment
- Detects port conflicts
- Handles existing deployments
- Creates backups before modifications

But it cannot overcome the fundamental issue of the WebSocket container exiting immediately due to the command issue.