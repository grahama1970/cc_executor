# Fix Docker Claude CLI Integration - Self-Improving Prompt

## 🎯 Goal
Iteratively fix Docker configuration until `claude -p "What is 2+2?"` works inside the container.

## 🔐 Execution UUID: `[GENERATE FRESH]`

## 📊 Current Status
- WebSocket streaming: ✅ FIXED
- Direct commands: ✅ WORKING  
- Claude CLI execution: ❌ WORKING BUT SLOW (7-8 seconds for simple prompts)
- Issue: Need to understand why Claude CLI works without ANTHROPIC_API_KEY

## 🔍 Iteration Log

### Iteration 1: Initial Analysis
```bash
# Test current state
docker exec cc_execute claude --version
# Output: 1.0.44 (Claude Code)

docker exec cc_execute env | grep ANTHROPIC
# Output: ANTHROPIC_API_KEY= (empty)

# Yet Claude works:
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"tasks": ["What is 2+2?"]}'
# Output: "4" (takes ~8 seconds)
```

### Iteration 2: Understand Claude CLI Auth
```bash
# Check Claude CLI config in container
docker exec cc_execute ls -la ~/.claude/
docker exec cc_execute cat ~/.claude/config.json 2>/dev/null || echo "No config"

# Check if using browser auth
docker exec cc_execute claude --help | grep -i auth

# Test Claude directly in container
docker exec -it cc_execute claude -p "test"
```

### Iteration 3: Fix Authentication
Based on findings, update Dockerfile or docker-compose.yml:

```dockerfile
# Option A: If Claude needs API key
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Option B: If Claude uses config file
COPY claude-config.json /home/appuser/.claude/config.json

# Option C: If Claude uses browser auth
# Document this in README
```

### Iteration 4: Optimize Performance
```yaml
# docker-compose.yml improvements
environment:
  # Add any missing env vars discovered
  CLAUDE_CACHE_DIR: /app/.claude-cache
  
volumes:
  # Add cache persistence
  - claude-cache:/app/.claude-cache
```

## 🤖 Test Script
```python
#!/usr/bin/env python3
"""Test and fix Docker Claude integration"""

import subprocess
import json
import time
import uuid

execution_uuid = str(uuid.uuid4())
print(f"🔐 Execution UUID: {execution_uuid}")

def run_test(test_name, command):
    """Run a test and return results"""
    print(f"\n🧪 {test_name}")
    start = time.time()
    
    result = subprocess.run(
        command, 
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    duration = time.time() - start
    success = result.returncode == 0
    
    print(f"  Exit code: {result.returncode}")
    print(f"  Duration: {duration:.2f}s")
    if result.stdout:
        print(f"  Output: {result.stdout[:100]}")
    if result.stderr:
        print(f"  Error: {result.stderr[:100]}")
    
    return {
        "test": test_name,
        "success": success,
        "duration": duration,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

# Run tests
tests = []

# 1. Check Claude version
tests.append(run_test(
    "Claude Version",
    "docker exec cc_execute claude --version"
))

# 2. Check environment
tests.append(run_test(
    "Check API Key",
    "docker exec cc_execute printenv ANTHROPIC_API_KEY"
))

# 3. Test Claude directly
tests.append(run_test(
    "Direct Claude Test",
    'docker exec cc_execute claude -p "What is 1+1?" --no-sse'
))

# 4. Test via API
tests.append(run_test(
    "API Claude Test",
    '''curl -s -X POST http://localhost:8001/execute \
    -H "Content-Type: application/json" \
    -d '{"tasks": ["Say hello"], "timeout_per_task": 30}' '''
))

# 5. Check Claude config
tests.append(run_test(
    "Claude Config",
    "docker exec cc_execute ls -la ~/.claude/"
))

# Save results
results = {
    "timestamp": time.time(),
    "tests": tests,
    "execution_uuid": execution_uuid
}

with open(f"docker-claude-test-{execution_uuid[:8]}.json", "w") as f:
    json.dump(results, f, indent=2)

# Analyze results
print("\n📊 Summary:")
for test in tests:
    status = "✅" if test["success"] else "❌"
    print(f"{status} {test['test']}: {test['duration']:.2f}s")

# Suggest fixes
print("\n💡 Suggested fixes based on results:")

if not any(t["success"] for t in tests if "API Key" in t["test"]):
    print("1. Add ANTHROPIC_API_KEY to docker-compose.yml:")
    print("   environment:")
    print("     ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}")

if any("permission" in t.get("stderr", "").lower() for t in tests):
    print("2. Fix permissions in Dockerfile:")
    print("   RUN chown -R appuser:appuser ~/.claude")

if any(t["duration"] > 10 for t in tests if t["success"]):
    print("3. Add performance optimizations:")
    print("   - Mount Claude cache as volume")
    print("   - Pre-warm Claude on container start")

print(f"\n🔐 Test UUID: {execution_uuid}")
```

## 🔧 Fix Implementation

### Step 1: Update docker-compose.yml
```yaml
services:
  cc_execute:
    environment:
      # Ensure API key is passed
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      # Don't remove it in process_manager.py
      RUNNING_IN_DOCKER: "1"
```

### Step 2: Update Dockerfile (if needed)
```dockerfile
# Ensure Claude CLI has proper setup
RUN mkdir -p /home/appuser/.claude && \
    chown -R appuser:appuser /home/appuser/.claude

# If Claude needs config
COPY --chown=appuser:appuser claude-config.json /home/appuser/.claude/config.json
```

### Step 3: Test and iterate
```bash
# Rebuild
docker compose build

# Test
docker compose up -d
python test_docker_claude.py

# Check logs
docker logs cc_execute | grep -i claude

# If still failing, check inside container
docker exec -it cc_execute /bin/bash
# Then manually test Claude
```

## ✅ Success Criteria
- [ ] `claude --version` works in container
- [ ] `claude -p "test"` completes in <5 seconds
- [ ] API endpoint executes Claude prompts successfully
- [ ] Clear documentation on auth method (API key vs browser)

## 📝 Final Documentation
Once working, document:
1. Exact auth method Claude CLI uses in Docker
2. Required environment variables
3. Any config files needed
4. Performance optimizations applied

Keep iterating this prompt until all success criteria are met!