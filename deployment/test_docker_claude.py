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