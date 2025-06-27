# Docker Stress Test — Self-Improving Prompt

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-27
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation - Docker container stress test

---

## 📋 TASK DEFINITION

Execute ALL stress tests from `unified_stress_test_tasks.json` through Docker container running FastAPI.

### Requirements:
1. Force rebuild Docker image (no cache)
2. Stop any existing containers
3. Start fresh container with docker-compose
4. Execute all tests via container endpoint
5. Track success/failure metrics
6. Clean up after completion

### Success Criteria:
- Docker image builds successfully
- Container starts and passes health checks
- All tests execute without hanging
- Expected patterns found in outputs
- No hallucinations (verified in transcript)
- Results saved to test_outputs/
- 10:1 success ratio achieved

---

## 🚀 IMPLEMENTATION

```python
#!/usr/bin/env python3
"""Docker Stress Test - Run all tests through Docker container"""

import asyncio
import json
import subprocess
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
import websockets
import docker

class DockerStressTest:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.container_name = "cc_executor_mcp"
        self.image_name = "cc-executor"
        self.base_url = "http://localhost:8003"
        self.ws_url = "ws://localhost:8003/ws/mcp"
        self.results = {"success": 0, "failure": 0, "tests": []}
        self.test_outputs_dir = Path("test_outputs/docker")
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
    def force_rebuild_docker(self):
        """Force rebuild Docker image without cache"""
        print("Force rebuilding Docker image...")
        
        # Change to directory with Dockerfile
        docker_dir = Path("src/cc_executor")
        
        # Build without cache
        cmd = [
            "docker", "build",
            "--no-cache",
            "-t", self.image_name,
            "-f", "Dockerfile",
            "."
        ]
        
        result = subprocess.run(
            cmd,
            cwd=docker_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Docker image built successfully")
            return True
        else:
            print(f"✗ Docker build failed: {result.stderr}")
            return False
            
    def stop_existing_containers(self):
        """Stop and remove existing containers"""
        print("Stopping existing containers...")
        
        try:
            # Find container by name
            container = self.docker_client.containers.get(self.container_name)
            print(f"  Stopping {self.container_name}...")
            container.stop(timeout=10)
            container.remove()
            print("  ✓ Container stopped and removed")
        except docker.errors.NotFound:
            print("  No existing container found")
        except Exception as e:
            print(f"  Error stopping container: {e}")
            
    def start_docker_container(self):
        """Start Docker container with docker-compose"""
        print("Starting Docker container...")
        
        docker_compose_path = Path("src/cc_executor/docker-compose.yml")
        
        # Start with docker-compose
        cmd = ["docker-compose", "-f", str(docker_compose_path), "up", "-d"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ docker-compose failed: {result.stderr}")
            return False
            
        # Wait for container to be healthy
        print("Waiting for container to be healthy...")
        for i in range(60):  # 60 second timeout
            time.sleep(1)
            try:
                container = self.docker_client.containers.get(self.container_name)
                if container.status == "running":
                    # Check health endpoint
                    try:
                        resp = requests.get(f"{self.base_url}/health", timeout=1)
                        if resp.status_code == 200:
                            health = resp.json()
                            print(f"✓ Container healthy: {health['service']} v{health['version']}")
                            return True
                    except:
                        continue
            except:
                continue
                
        print("✗ Container failed to become healthy")
        return False
        
    def stop_docker_container(self):
        """Stop Docker container"""
        print("Stopping Docker container...")
        
        docker_compose_path = Path("src/cc_executor/docker-compose.yml")
        cmd = ["docker-compose", "-f", str(docker_compose_path), "down"]
        subprocess.run(cmd, capture_output=True, text=True)
        
    def get_container_logs(self):
        """Get container logs for debugging"""
        try:
            container = self.docker_client.containers.get(self.container_name)
            logs = container.logs(tail=50).decode('utf-8')
            return logs
        except:
            return "Could not retrieve container logs"
            
    async def check_container_health(self):
        """Check if container is healthy"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2)
            return resp.status_code == 200
        except:
            return False
            
    async def execute_test(self, test):
        """Execute a single test"""
        marker = f"DOCKER_{test['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n[{test['id']}] {test['name']}")
        print(f"Marker: {marker}")
        
        # Check container health before test
        if not await self.check_container_health():
            print("  ✗ Container unhealthy!")
            print("  Container logs:")
            print(self.get_container_logs())
            self.results["failure"] += 1
            return False
        
        try:
            request = test['natural_language_request']
            metatags = test.get('metatags', '')
            
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "executable": "claude",
                    "args": [
                        "--print",
                        f"[marker:{marker}] {metatags} {request}",
                        "--output-format", "stream-json",
                        "--verbose"
                    ]
                },
                "id": 1
            }
            
            # Execute via WebSocket
            output_lines = []
            patterns_found = []
            start_time = time.time()
            
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.send(json.dumps(execute_request))
                
                timeout = test['verification']['timeout']
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        if "params" in data and "output" in data["params"]:
                            output = data["params"]["output"]
                            output_lines.append(output)
                            
                            # Check patterns
                            for pattern in test['verification']['expected_patterns']:
                                if pattern.lower() in output.lower() and pattern not in patterns_found:
                                    patterns_found.append(pattern)
                                    
                        elif "result" in data:
                            duration = time.time() - start_time
                            exit_code = data["result"].get("exit_code", -1)
                            
                            success = exit_code == 0 and len(patterns_found) > 0
                            
                            # Save output
                            self.save_output(test, "\n".join(output_lines), success, duration)
                            
                            if success:
                                self.results["success"] += 1
                                print(f"  ✓ PASSED in {duration:.1f}s")
                                print(f"    Patterns: {patterns_found}")
                            else:
                                self.results["failure"] += 1
                                print(f"  ✗ FAILED in {duration:.1f}s")
                                print(f"    Exit code: {exit_code}")
                                
                            self.results["tests"].append({
                                "id": test['id'],
                                "success": success,
                                "duration": duration,
                                "patterns_found": patterns_found,
                                "container_healthy": True
                            })
                            
                            return success
                            
                    except asyncio.TimeoutError:
                        continue
                        
            # Timeout reached
            self.results["failure"] += 1
            print(f"  ✗ TIMEOUT after {timeout}s")
            return False
            
        except Exception as e:
            self.results["failure"] += 1
            print(f"  ✗ ERROR: {e}")
            return False
            
    def save_output(self, test, output, success, duration):
        """Save test output"""
        filename = f"{test['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.test_outputs_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(f"Test: {test['id']} - {test['name']}\n")
            f.write(f"Success: {success}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Environment: Docker Container\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("-" * 80 + "\n")
            f.write(output)
            
    async def run_all_tests(self):
        """Run all tests from JSON"""
        # Load tests
        json_path = Path("src/cc_executor/tasks/unified_stress_test_tasks.json")
        with open(json_path) as f:
            test_data = json.load(f)
            
        # Force rebuild and start container
        if not self.force_rebuild_docker():
            print("Failed to build Docker image!")
            return
            
        self.stop_existing_containers()
        
        if not self.start_docker_container():
            print("Failed to start Docker container!")
            return
            
        try:
            # Get container info
            container = self.docker_client.containers.get(self.container_name)
            print(f"\nContainer Info:")
            print(f"  ID: {container.short_id}")
            print(f"  Status: {container.status}")
            print(f"  Image: {container.image.tags[0] if container.image.tags else 'untagged'}")
            
            # Get server stats
            resp = requests.get(f"{self.base_url}/health")
            health = resp.json()
            print(f"\nServer Stats:")
            print(f"  Service: {health['service']} v{health['version']}")
            print(f"  Active Sessions: {health['active_sessions']}")
            print(f"  Max Sessions: {health['max_sessions']}")
            
            print(f"\nRunning {sum(len(cat['tasks']) for cat in test_data['categories'].values())} tests...")
            
            # Execute all tests
            for category, cat_data in test_data['categories'].items():
                print(f"\n{'='*60}")
                print(f"Category: {category}")
                print(f"{'='*60}")
                
                for test in cat_data['tasks']:
                    await self.execute_test(test)
                    
            # Check final container health
            if await self.check_container_health():
                resp = requests.get(f"{self.base_url}/health")
                final_health = resp.json()
                print(f"\nFinal Server Stats:")
                print(f"  Active Sessions: {final_health['active_sessions']}")
                print(f"  Uptime: {final_health['uptime_seconds']}s")
                
            # Get final container stats
            container.reload()
            stats = container.stats(stream=False)
            print(f"\nContainer Resource Usage:")
            print(f"  CPU: {stats['cpu_stats']['cpu_usage']['total_usage'] / 1e9:.2f}s")
            memory_usage = stats['memory_stats']['usage'] / 1024 / 1024
            print(f"  Memory: {memory_usage:.1f} MB")
                    
            # Generate report
            self.generate_report()
            
        finally:
            print("\nCleaning up...")
            self.stop_docker_container()
            
    def generate_report(self):
        """Generate test report"""
        print(f"\n{'='*60}")
        print("DOCKER STRESS TEST REPORT")
        print(f"{'='*60}")
        
        total = self.results["success"] + self.results["failure"]
        success_rate = self.results["success"] / max(1, total) * 100
        
        print(f"Total Tests: {total}")
        print(f"Successful: {self.results['success']}")
        print(f"Failed: {self.results['failure']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        ratio = self.results["success"] / max(1, self.results["failure"])
        print(f"Success Ratio: {ratio:.1f}:1 (need 10:1 to graduate)")
        
        # Save detailed report
        report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed report: {report_path}")

if __name__ == "__main__":
    print("DOCKER STRESS TEST - Full Container Deployment")
    print("=" * 60)
    
    # Check docker available
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        print(f"Docker not available: {e}")
        print("Please ensure Docker daemon is running")
        sys.exit(1)
    
    tester = DockerStressTest()
    asyncio.run(tester.run_all_tests())
```

---

## 📊 EXECUTION LOG

### Run 1: [Date]
```
MARKER_DOCKER_20250627_000000
[Results will be logged here]
```

---

## 🔧 RECOVERY TESTS

### Test 1: Docker Available
```python
def test_docker_available():
    """Ensure Docker daemon is running"""
    import docker
    client = docker.from_env()
    client.ping()
    print("✓ Docker daemon is running")
```

### Test 2: Build Context
```python
def test_build_context():
    """Ensure Dockerfile and requirements exist"""
    from pathlib import Path
    dockerfile = Path("src/cc_executor/Dockerfile")
    requirements = Path("src/cc_executor/requirements.txt")
    
    assert dockerfile.exists(), "Dockerfile not found"
    assert requirements.exists(), "requirements.txt not found"
```

### Test 3: Port Available
```python
def test_port_available():
    """Ensure port 8003 is not in use"""
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8003))
    sock.close()
    
    assert result != 0, "Port 8003 already in use"
```

### Test 4: Docker Compose
```python
def test_docker_compose():
    """Ensure docker-compose is available"""
    import subprocess
    
    result = subprocess.run(["docker-compose", "--version"], capture_output=True)
    assert result.returncode == 0, "docker-compose not available"
```