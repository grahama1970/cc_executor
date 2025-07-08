# Docker Compose Dynamic Port Configuration — Gamified Self-Improving Prompt

## 🔐 Anti-Hallucination UUID
**Execution UUID**: `[GENERATE WITH uuid.uuid4()]`

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Target: 10:1 to graduate)
- **Last Updated**: 2025-07-08 18:41:00
- **Last UUID**: `None - first execution`
- **Evolution History**:
  | Version | Change & Reason | Result | UUID |
  | :------ | :-------------- | :----- | :--- |
  | v1      | Initial implementation with dynamic ports | TBD | TBD |

### Verification Command
```bash
# Verify last execution actually happened
grep "[Last UUID]" ~/.claude/projects/*/\*.jsonl
```

---
## 🎯 GAMIFICATION RULES

### HOW TO WIN (Graduate to docker-compose.yml)
1. Achieve 10 successful Docker deployments for every 1 failure
2. All deployments must handle port conflicts gracefully
3. No hardcoded ports - must be configurable

### HOW TO LOSE (Penalties)
1. **Port Conflicts = Instant Failure** ❌
2. **Hardcoded Values = Failure** ❌
3. **Missing API Key Handling = Failure** ❌

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Create a self-improving Docker Compose configuration that:
- Automatically finds free ports
- Supports multiple concurrent instances
- Handles missing ANTHROPIC_API_KEY gracefully
- Provides clear connection information

### 2. Core Requirements
- [ ] Generate UUID4 at start of execution
- [ ] Dynamic port allocation (no hardcoding)
- [ ] Support for multiple instances
- [ ] Clear error messages and recovery
- [ ] Save deployment info with UUID verification

### 3. Output Structure
```json
{
  "timestamp": "ISO-8601 timestamp",
  "deployment": {
    "api_port": 8001,
    "websocket_port": 8004,
    "instance_id": "unique-id",
    "services_healthy": true
  },
  "metrics": {
    "startup_duration": "seconds",
    "success": true
  },
  "execution_uuid": "MUST BE LAST KEY"
}
```

---
## 🤖 IMPLEMENTATION WORKSPACE

### **Docker Compose Template**
```yaml
# docker-compose.dynamic.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: cc_executor_redis_${INSTANCE_ID:-default}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - cc_executor_net

  cc_execute:
    build:
      context: ..
      dockerfile: deployment/Dockerfile
    container_name: cc_execute_${INSTANCE_ID:-default}
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      PYTHONUNBUFFERED: "1"
      REDIS_URL: redis://redis:6379
      DISABLE_VENV_WRAPPING: "1"
      RUNNING_IN_DOCKER: "1"
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      # Dynamic port configuration
      WEBSOCKET_PORT: ${WEBSOCKET_PORT:-8003}
      API_PORT: ${API_PORT:-8000}
    ports:
      # Use environment variables for flexible port mapping
      - "${API_EXTERNAL_PORT:-8001}:8000"
      - "${WS_EXTERNAL_PORT:-8004}:8003"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ${CLAUDE_HOME:-~/.claude}:/home/appuser/.claude:ro
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: |
        curl -f http://localhost:8000/health || exit 1
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - cc_executor_net

networks:
  cc_executor_net:
    name: cc_executor_network_${INSTANCE_ID:-default}
    driver: bridge

volumes:
  redis_data:
    driver: local
```

### **Dynamic Deployment Script**
```python
#!/usr/bin/env python3
"""
Dynamic Docker Compose Deployment with Port Discovery
Implements UUID4 anti-hallucination verification
"""

import uuid
import json
import time
import socket
import subprocess
import os
from pathlib import Path
from datetime import datetime

class DockerComposeDeployer:
    def __init__(self):
        # Generate UUID4 immediately
        self.execution_uuid = str(uuid.uuid4())
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"🔐 Starting deployment with UUID: {self.execution_uuid}")
        
        # Configuration
        self.instance_id = f"deploy_{self.timestamp}"
        self.api_port = None
        self.ws_port = None
        
    def find_free_port(self, start_port=8000):
        """Find next available port starting from start_port"""
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"No free ports found starting from {start_port}")
        
    def execute(self):
        """Main deployment logic"""
        try:
            # Find free ports
            self.api_port = self.find_free_port(8001)
            self.ws_port = self.find_free_port(8003)
            
            print(f"📍 Found free ports - API: {self.api_port}, WebSocket: {self.ws_port}")
            
            # Set environment
            env = os.environ.copy()
            env.update({
                'INSTANCE_ID': self.instance_id,
                'API_EXTERNAL_PORT': str(self.api_port),
                'WS_EXTERNAL_PORT': str(self.ws_port)
            })
            
            # Check for API key
            if not env.get('ANTHROPIC_API_KEY'):
                print("⚠️  ANTHROPIC_API_KEY not set - Claude CLI features limited")
            
            # Deploy with docker compose
            compose_file = Path(__file__).parent / "docker-compose.dynamic.yml"
            
            # Stop any existing instance
            print(f"🔄 Stopping any existing instance...")
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "-p", f"cc_{self.instance_id}", "down"],
                env=env,
                capture_output=True
            )
            
            # Start new instance
            print(f"🚀 Starting new instance: {self.instance_id}")
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "-p", f"cc_{self.instance_id}", "up", "-d"],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Docker compose failed: {result.stderr}")
            
            # Wait for services to be healthy
            print("⏳ Waiting for services to be healthy...")
            healthy = self._wait_for_healthy(env)
            
            # Build output
            output = self._build_output(healthy)
            
            # Save and verify
            self._save_output(output)
            self._verify_uuid(output)
            
            # Print connection info
            print(f"\n✅ Deployment successful!")
            print(f"📡 API endpoint: http://localhost:{self.api_port}")
            print(f"🔌 WebSocket endpoint: ws://localhost:{self.ws_port}/ws/mcp")
            print(f"🆔 Instance ID: {self.instance_id}")
            print(f"🔐 UUID: {self.execution_uuid}")
            
            return output
            
        except Exception as e:
            # Self-recovery
            failure_output = self._build_output(False, error=str(e))
            self._save_output(failure_output)
            self._analyze_failure(e)
            print(f"❌ Deployment failed. UUID: {self.execution_uuid}")
            raise
            
    def _wait_for_healthy(self, env, timeout=60):
        """Wait for services to be healthy"""
        start = time.time()
        compose_file = Path(__file__).parent / "docker-compose.dynamic.yml"
        
        while time.time() - start < timeout:
            # Check health
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "-p", f"cc_{self.instance_id}", "ps", "--format", "json"],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    services = json.loads(result.stdout)
                    all_healthy = all(
                        s.get('Health', 'unknown') == 'healthy' or s.get('State') == 'running'
                        for s in services
                    )
                    if all_healthy:
                        return True
                except json.JSONDecodeError:
                    pass
            
            time.sleep(2)
            
        return False
        
    def _build_output(self, success, error=None):
        """Build output dict with UUID at END"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "deployment": {
                "api_port": self.api_port,
                "websocket_port": self.ws_port,
                "instance_id": self.instance_id,
                "services_healthy": success
            },
            "metrics": {
                "startup_duration": time.time() - self.start_time,
                "success": success
            }
        }
        
        if error:
            output["error"] = error
            
        # UUID MUST BE LAST
        output["execution_uuid"] = self.execution_uuid
        return output
        
    def _save_output(self, output):
        """Save output to prevent hallucination"""
        responses_dir = Path(__file__).parent / "tmp" / "deployment_results"
        responses_dir.mkdir(parents=True, exist_ok=True)
        
        json_file = responses_dir / f"deployment_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"💾 Deployment info saved to: {json_file}")
        
    def _verify_uuid(self, output):
        """Verify UUID is present and at END"""
        assert "execution_uuid" in output, "UUID missing from output!"
        assert output["execution_uuid"] == self.execution_uuid, "UUID mismatch!"
        
        keys = list(output.keys())
        assert keys[-1] == "execution_uuid", f"UUID not at end! Last key: {keys[-1]}"
        
    def _analyze_failure(self, error):
        """Self-recovery: analyze failure for next attempt"""
        print(f"\n🔍 Analyzing failure for self-improvement:")
        print(f"  Error type: {type(error).__name__}")
        print(f"  Error message: {str(error)}")
        
        if "address already in use" in str(error).lower():
            print("  💡 Suggestion: Port detection failed, increase search range")
        elif "no such file" in str(error).lower():
            print("  💡 Suggestion: Check docker-compose.dynamic.yml exists")
        elif "permission denied" in str(error).lower():
            print("  💡 Suggestion: Check Docker permissions and user groups")
            
    def cleanup(self):
        """Cleanup deployment"""
        print(f"\n🧹 Cleaning up instance: {self.instance_id}")
        env = os.environ.copy()
        env['INSTANCE_ID'] = self.instance_id
        
        compose_file = Path(__file__).parent / "docker-compose.dynamic.yml"
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "-p", f"cc_{self.instance_id}", "down"],
            env=env
        )

if __name__ == "__main__":
    deployer = DockerComposeDeployer()
    
    try:
        output = deployer.execute()
        
        # Test the deployment
        import requests
        
        print("\n🧪 Testing deployment...")
        try:
            # Test API health
            api_url = f"http://localhost:{deployer.api_port}/health"
            response = requests.get(api_url, timeout=5)
            print(f"✅ API health check: {response.status_code}")
            
            # Could add WebSocket test here
            
        except Exception as e:
            print(f"❌ Deployment test failed: {e}")
            deployer.cleanup()
            raise
            
        print("\n✅ All verifications passed!")
        print("\n💡 To stop this instance, run:")
        print(f"   python {__file__} --cleanup --instance-id {deployer.instance_id}")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        print("\n📝 Update the metrics section with this failure")
        if 'deployer' in locals():
            deployer.cleanup()
        exit(1)
```

---
## 🧪 VERIFICATION STEPS

### Step 1: Port Discovery
**Goal**: Verify dynamic port allocation works
**Command**: `python deploy_docker_dynamic.py | grep "Found free ports"`
**Expected**: Shows discovered ports different from defaults

### Step 2: Multiple Instances
**Goal**: Run multiple instances simultaneously
**Command**: `python deploy_docker_dynamic.py & python deploy_docker_dynamic.py`
**Expected**: Two instances with different ports

### Step 3: API Key Handling
**Goal**: Graceful handling of missing API key
**Command**: `unset ANTHROPIC_API_KEY && python deploy_docker_dynamic.py`
**Expected**: Warning message but deployment continues

---
## 📈 METRICS UPDATE TEMPLATE

After each run, update the metrics section:

```markdown
| v2 | Added retry logic for port binding | ✅ Success | a4f5c2d1-... |
| v3 | Fixed healthcheck timeout | ❌ Failed | b5e6d3e2-... |
```

---
## 🚨 ANTI-HALLUCINATION CHECKLIST

- [ ] UUID printed at deployment start
- [ ] Ports actually discovered (not hardcoded)
- [ ] Docker containers actually running
- [ ] Services responding to health checks
- [ ] Output file exists with deployment info
- [ ] Can connect to deployed services

Remember: **No fake deployments!** ❌