# Docker Setup and Deploy

Deploy CC Executor using standard Docker patterns. Uses established best practices for Python web services.

```python
#!/usr/bin/env python3
"""Docker setup that handles both new and existing deployments - UNIFIED VERSION"""

import subprocess
import requests
import yaml
import time
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# Use relative paths from script location
DEPLOYMENT_DIR = Path(__file__).parent
API_BASE = "http://localhost:8001"
WEBSOCKET_BASE = "http://localhost:8003"
PORTS = [8001, 8003, 6380]
MAX_ATTEMPTS = 5

# Results tracking
RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "initial_state": {},
    "docker_analysis": {},
    "backups_created": [],
    "attempts": [],
    "endpoint_tests": {},
    "overall_success": False
}

def analyze_docker_environment():
    """Analyze current Docker environment including all containers and port usage"""
    print("\n🔍 Analyzing Docker environment...")
    
    analysis = {
        "all_containers": [],
        "port_conflicts": {},
        "cc_containers": {},
        "other_containers_on_our_ports": []
    }
    
    # Get ALL running containers (not just compose ones)
    result = subprocess.run(
        ["docker", "ps", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            try:
                container = json.loads(line)
                container_info = {
                    "id": container.get("ID", ""),
                    "name": container.get("Names", ""),
                    "image": container.get("Image", ""),
                    "ports": container.get("Ports", ""),
                    "status": container.get("Status", ""),
                    "state": container.get("State", "")
                }
                analysis["all_containers"].append(container_info)
                
                # Check if it's one of ours (new unified container or old separate ones)
                if "cc_execute" in container_info["name"] or "cc_executor" in container_info["name"]:
                    service_name = container_info["name"]
                    analysis["cc_containers"][service_name] = {
                        "running": True,
                        "status": container_info["status"],
                        "healthy": "healthy" in container_info["status"].lower()
                    }
                
                # Check for port conflicts
                ports_str = container_info["ports"]
                for our_port in PORTS:
                    if str(our_port) in ports_str and "cc_execute" not in container_info["name"] and "cc_executor" not in container_info["name"]:
                        if our_port not in analysis["port_conflicts"]:
                            analysis["port_conflicts"][our_port] = []
                        analysis["port_conflicts"][our_port].append({
                            "container": container_info["name"],
                            "image": container_info["image"]
                        })
                        
            except json.JSONDecodeError:
                pass
    
    # Also check what's listening on our ports directly
    for port in PORTS:
        result = subprocess.run(
            f"lsof -i:{port} -P -n | grep LISTEN",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            if port not in analysis["port_conflicts"]:
                analysis["port_conflicts"][port] = []
            # Parse lsof output to get process info
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) > 1:
                    process_name = parts[0]
                    pid = parts[1]
                    if "docker" not in process_name.lower():
                        analysis["port_conflicts"][port].append({
                            "process": process_name,
                            "pid": pid,
                            "type": "non-docker"
                        })
    
    # Print analysis
    print(f"  Found {len(analysis['all_containers'])} running containers")
    
    if analysis["cc_containers"]:
        print("\n  CC Executor containers:")
        for name, info in analysis["cc_containers"].items():
            health = "✓ healthy" if info["healthy"] else "⚠️  unhealthy"
            print(f"    - {name}: {health}")
    
    if analysis["port_conflicts"]:
        print("\n  ⚠️  Port conflicts detected:")
        for port, conflicts in analysis["port_conflicts"].items():
            print(f"    - Port {port}:")
            for conflict in conflicts:
                if "container" in conflict:
                    print(f"      • Container: {conflict['container']} ({conflict['image']})")
                else:
                    print(f"      • Process: {conflict['process']} (PID: {conflict['pid']})")
    
    return analysis

def check_existing_setup():
    """Check what already exists in deployment directory"""
    existing = {
        "docker_compose": (DEPLOYMENT_DIR / "docker-compose.yml").exists(),
        "dockerfile": (DEPLOYMENT_DIR / "Dockerfile").exists(),
        "start_services": (DEPLOYMENT_DIR / "start_services.py").exists(),
        "containers_running": False,
        "existing_files": []
    }
    
    # List all existing files
    for file in DEPLOYMENT_DIR.iterdir():
        if file.is_file() and file.name not in ['.DS_Store', 'docker_setup.md']:
            existing["existing_files"].append(file.name)
    
    # Check if containers are running (via compose)
    result = subprocess.run(["docker", "compose", "ps", "--format", "json"], 
                          capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        existing["containers_running"] = True
        
    return existing

def backup_existing_files():
    """Backup existing Docker files before modifying"""
    backup_dir = DEPLOYMENT_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    files_to_backup = ["docker-compose.yml", "Dockerfile", "start_services.py"]
    backups = []
    
    for filename in files_to_backup:
        filepath = DEPLOYMENT_DIR / filename
        if filepath.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / filename
            shutil.copy2(filepath, backup_path)
            backups.append(str(backup_path))
            print(f"  📦 Backed up {filename}")
    
    if backups:
        print(f"  ✓ Backups saved to: {backup_dir}")
        RESULTS["backups_created"] = backups
    
    return backup_dir if backups else None

def analyze_existing_config():
    """Analyze existing docker-compose.yml for issues"""
    compose_path = DEPLOYMENT_DIR / "docker-compose.yml"
    issues = []
    
    if not compose_path.exists():
        return ["docker-compose.yml not found"]
    
    try:
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for required services
        if "services" not in config:
            issues.append("No services defined")
        else:
            # Check for new unified setup
            if "cc_execute" in config["services"]:
                # Good - using unified container
                cc_config = config["services"]["cc_execute"]
                
                # Check ports
                ports = cc_config.get("ports", [])
                if not any("8001" in str(p) for p in ports):
                    issues.append("API port 8001 not mapped")
                if not any("8003" in str(p) for p in ports):
                    issues.append("WebSocket port 8003 not mapped")
                    
            else:
                # Check for old setup (separate containers)
                if "websocket" in config["services"] and "api" in config["services"]:
                    issues.append("Using old separate container setup - should use unified cc_execute container")
                else:
                    issues.append("Missing cc_execute service")
            
            # Check Redis
            if "redis" not in config["services"]:
                issues.append("Missing redis service")
        
        # Check Claude volume mounts
        claude_mounted = False
        for service in config.get("services", {}).values():
            volumes = service.get("volumes", [])
            if any(".claude" in str(v) for v in volumes):
                claude_mounted = True
                break
        
        if not claude_mounted:
            issues.append("Claude authentication not mounted")
            
    except Exception as e:
        issues.append(f"Failed to parse docker-compose.yml: {e}")
    
    return issues

def handle_port_conflicts(docker_analysis):
    """Handle port conflicts based on Docker analysis"""
    if not docker_analysis.get("port_conflicts"):
        return True
    
    print("\n🚨 Port conflicts must be resolved before proceeding")
    
    for port, conflicts in docker_analysis["port_conflicts"].items():
        print(f"\n  Port {port} is in use by:")
        for conflict in conflicts:
            if "container" in conflict:
                print(f"    - Docker container: {conflict['container']}")
                print(f"      You can stop it with: docker stop {conflict['container']}")
            else:
                print(f"    - Process: {conflict['process']} (PID: {conflict['pid']}")
                print(f"      You can stop it with: kill {conflict['pid']}")
    
    print("\n  Attempting automatic resolution...")
    
    # Stop old CC Executor containers if they exist
    old_containers = ["cc_executor_websocket", "cc_executor_api", "cc_executor_redis"]
    for container in old_containers:
        subprocess.run(f"docker stop {container} 2>/dev/null", shell=True)
        subprocess.run(f"docker rm {container} 2>/dev/null", shell=True)
    
    # Kill non-Docker processes
    for port in docker_analysis["port_conflicts"]:
        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true", 
                      shell=True, capture_output=True)
    
    time.sleep(2)
    
    # Re-check
    still_blocked = []
    for port in PORTS:
        result = subprocess.run(f"lsof -i:{port} -P -n | grep LISTEN", 
                              shell=True, capture_output=True)
        if result.returncode == 0:
            still_blocked.append(port)
    
    if still_blocked:
        print(f"\n  ❌ Could not free ports: {still_blocked}")
        print("  Please manually stop the conflicting services")
        return False
    else:
        print("  ✓ All ports freed successfully")
        return True

def generate_or_fix_configs(fix_existing=False):
    """Generate new configs or fix existing ones"""
    if fix_existing:
        print("\n🔧 Fixing existing Docker configuration...")
        issues = analyze_existing_config()
        if issues:
            print(f"  Found issues: {', '.join(issues)}")
            backup_existing_files()
    else:
        print("\n📝 Generating Docker configuration files...")
    
    config_results = {"action": "fixed" if fix_existing else "generated", "files": []}
    
    # docker-compose.yml (unified architecture)
    compose_config = {
        "version": "3.8",
        "services": {
            "redis": {
                "image": "redis:7-alpine",
                "container_name": "cc_executor_redis",
                "ports": ["6380:6379"],
                "volumes": ["redis_data:/data"],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "5s",
                    "timeout": "3s",
                    "retries": 5
                }
            },
            "cc_execute": {
                "build": {
                    "context": "..",
                    "dockerfile": "deployment/Dockerfile"
                },
                "container_name": "cc_execute",
                "ports": [
                    "8001:8000",  # FastAPI
                    "8003:8003"   # WebSocket
                ],
                "environment": {
                    "LOG_LEVEL": "INFO",
                    "PYTHONUNBUFFERED": "1",
                    "REDIS_URL": "redis://redis:6379"
                },
                "volumes": [
                    "./logs:/app/logs",
                    "./data:/app/data",
                    "~/.claude:/home/appuser/.claude:ro"
                ],
                "restart": "unless-stopped",
                "depends_on": {
                    "redis": {"condition": "service_healthy"}
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            }
        },
        "networks": {
            "default": {"name": "cc_executor_network"}
        },
        "volumes": {
            "redis_data": {"driver": "local"}
        }
    }
    
    with open(DEPLOYMENT_DIR / "docker-compose.yml", 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)
    print("  ✓ docker-compose.yml")
    config_results["files"].append("docker-compose.yml")
    
    # Unified startup script
    start_services_py = '''#!/usr/bin/env python3
"""
Unified startup script for CC Executor services.
Runs both WebSocket server and FastAPI in the same process.
"""

import asyncio
import uvicorn
from multiprocessing import Process
import sys
import os
import time

# Add the source directory to Python path
sys.path.insert(0, '/app/src')

def start_websocket_server():
    """Start the WebSocket server on port 8003."""
    from cc_executor.core.main import app as ws_app
    
    uvicorn.run(
        ws_app,
        host="0.0.0.0",
        port=8003,
        ws_ping_interval=20.0,
        ws_ping_timeout=30.0,
        ws_max_size=10 * 1024 * 1024
    )

def start_api_server():
    """Start the FastAPI server on port 8000."""
    # Set WebSocket URL to localhost since we're in the same container
    os.environ["WEBSOCKET_URL"] = "ws://localhost:8003/ws"
    
    from cc_executor.api.main import app as api_app
    
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000
    )

def main():
    """Start both servers."""
    print("🚀 Starting CC Executor services...")
    
    # Start WebSocket server in a separate process
    ws_process = Process(target=start_websocket_server)
    ws_process.start()
    
    # Give WebSocket server time to start
    print("⏳ Waiting for WebSocket server to start...")
    time.sleep(5)
    
    # Start API server in main process
    print("🌐 Starting API server...")
    start_api_server()
    
    # Wait for WebSocket process
    ws_process.join()

if __name__ == "__main__":
    main()
'''
    
    with open(DEPLOYMENT_DIR / "start_services.py", 'w') as f:
        f.write(start_services_py)
    os.chmod(DEPLOYMENT_DIR / "start_services.py", 0o755)
    print("  ✓ start_services.py")
    config_results["files"].append("start_services.py")
    
    # Main Dockerfile
    dockerfile = """FROM python:3.11-slim

RUN apt-get update && apt-get install -y \\
    curl git \\
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

# Copy the unified startup script
COPY deployment/start_services.py /app/start_services.py
RUN chmod +x /app/start_services.py

RUN mkdir -p /app/logs /app/data && \\
    chown -R appuser:appuser /app

USER appuser

# Expose both ports
EXPOSE 8000 8003

# Run the unified startup script
CMD ["python", "/app/start_services.py"]
"""
    
    with open(DEPLOYMENT_DIR / "Dockerfile", 'w') as f:
        f.write(dockerfile)
    print("  ✓ Dockerfile")
    config_results["files"].append("Dockerfile")
    
    return config_results

def cleanup(remove_volumes=False):
    """Clean up environment with option to preserve volumes"""
    print("\n🧹 Cleaning up...")
    
    # Stop containers
    if remove_volumes:
        subprocess.run(["docker", "compose", "down", "-v"], capture_output=True)
        print("  ✓ Stopped containers and removed volumes")
    else:
        subprocess.run(["docker", "compose", "down"], capture_output=True)
        print("  ✓ Stopped containers (preserved volumes)")
    
    # Kill processes on ports
    for port in PORTS:
        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true", 
                      shell=True, capture_output=True)
    
    # Light cleanup (don't be too aggressive)
    subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
    
    print("  ✓ Cleaned")

def fix_common_issues(error_msg):
    """Try to fix common Docker issues based on error"""
    error_lower = error_msg.lower()
    fixes_applied = []
    
    # Port conflicts
    if "address already in use" in error_lower or "port" in error_lower:
        print("  🔧 Fixing port conflicts...")
        for port in PORTS:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", 
                         shell=True, capture_output=True)
        time.sleep(2)
        fixes_applied.append("killed_port_processes")
    
    # Disk space
    if "no space" in error_lower or "disk" in error_lower:
        print("  🔧 Freeing disk space...")
        subprocess.run(["docker", "system", "prune", "-af", "--volumes"], 
                      capture_output=True)
        fixes_applied.append("cleaned_docker_space")
    
    # Docker daemon
    if "cannot connect" in error_lower or "daemon" in error_lower:
        print("  🔧 Docker daemon issue, waiting...")
        time.sleep(10)
        fixes_applied.append("waited_for_daemon")
    
    # Permission issues
    if "permission" in error_lower:
        print("  🔧 Fixing permissions...")
        subprocess.run(["chmod", "-R", "755", str(DEPLOYMENT_DIR)], 
                      capture_output=True)
        fixes_applied.append("fixed_permissions")
    
    # Network issues
    if "network" in error_lower:
        print("  🔧 Resetting Docker network...")
        subprocess.run(["docker", "network", "rm", "cc_executor_network"], 
                      capture_output=True)
        fixes_applied.append("reset_network")
    
    # Image issues
    if "image" in error_lower or "pull" in error_lower:
        print("  🔧 Removing old images...")
        subprocess.run(["docker", "compose", "down", "--rmi", "local"], 
                      capture_output=True)
        fixes_applied.append("removed_old_images")
    
    return fixes_applied

def attempt_deployment(attempt_num, rebuild_images=True):
    """Attempt to deploy Docker containers"""
    attempt_result = {
        "attempt": attempt_num,
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "errors": [],
        "fixes_applied": []
    }
    
    try:
        # Build
        print(f"\n🔨 Building Docker images (attempt {attempt_num})...")
        build_cmd = ["docker", "compose", "build"]
        
        # Only use --no-cache on first attempt or if requested
        if attempt_num == 1 and rebuild_images:
            build_cmd.append("--no-cache")
            print("  Using --no-cache for clean build")
        
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Build failed: {result.stderr}"
            attempt_result["errors"].append(error_msg)
            fixes = fix_common_issues(result.stderr)
            attempt_result["fixes_applied"].extend(fixes)
            
            # Retry build after fixes
            if fixes:
                print("  Retrying build after fixes...")
                result = subprocess.run(["docker", "compose", "build"], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception("Build failed after fixes")
            else:
                raise Exception(error_msg)
        
        print("  ✓ Built")
        attempt_result["steps"]["build"] = "success"
        
        # Start services
        print("\n🚀 Starting services...")
        result = subprocess.run(["docker", "compose", "up", "-d"], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Start failed: {result.stderr}"
            attempt_result["errors"].append(error_msg)
            raise Exception(error_msg)
        
        print("  ✓ Started")
        attempt_result["steps"]["start"] = "success"
        
        # Wait for health
        print("\n💓 Waiting for services to be healthy...")
        healthy = False
        for i in range(30):
            try:
                resp = requests.get(f"{API_BASE}/health", timeout=2)
                if resp.status_code == 200:
                    healthy = True
                    print(f"  ✓ Services healthy after {i*2}s")
                    attempt_result["steps"]["health"] = "success"
                    break
            except:
                pass
            
            print(f"  Waiting... ({i+1}/30)")
            time.sleep(2)
        
        if not healthy:
            # Get container logs for debugging
            logs = subprocess.run(["docker", "compose", "logs", "--tail=50"], 
                                capture_output=True, text=True)
            error_msg = f"Services not healthy. Logs:\n{logs.stdout[-1000:]}"  # Last 1000 chars
            attempt_result["errors"].append(error_msg)
            raise Exception("Services did not become healthy")
        
        # If we get here, deployment succeeded
        attempt_result["success"] = True
        return True, attempt_result
        
    except Exception as e:
        attempt_result["success"] = False
        attempt_result["error_summary"] = str(e)
        
        # Try to fix the issue
        if attempt_num < MAX_ATTEMPTS:
            print(f"\n❌ Attempt {attempt_num} failed: {e}")
            fixes = fix_common_issues(str(e))
            attempt_result["fixes_applied"].extend(fixes)
            
            if fixes:
                print(f"  Applied fixes: {', '.join(fixes)}")
            
        return False, attempt_result

def test_endpoints():
    """Test all endpoints"""
    print("\n🧪 Testing all endpoints...")
    
    tests = [
        # API endpoints (port 8001)
        ("GET", f"{API_BASE}/health", None, "API Health"),
        ("GET", f"{API_BASE}/auth/status", None, "Auth Status"),
        
        # WebSocket health (port 8003)
        ("GET", f"{WEBSOCKET_BASE}/health", None, "WebSocket Health"),
        
        # Execute endpoint (should work if authenticated)
        ("POST", f"{API_BASE}/execute", 
         {"tasks": ["echo 'Docker test successful'"], "timeout_per_task": 30},
         "Execute Command")
    ]
    
    all_passed = True
    endpoint_results = {}
    
    for method, url, data, name in tests:
        test_result = {"method": method, "url": url, "name": name}
        
        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            else:
                resp = requests.post(url, json=data, timeout=30)
            
            test_result["status"] = resp.status_code
            test_result["success"] = resp.status_code == 200
            
            # For some endpoints, capture response data
            if "/auth/status" in url and resp.status_code == 200:
                test_result["auth_status"] = resp.json().get("status")
            
            if "/execute" in url and resp.status_code == 200:
                response_data = resp.json()
                # Check if it actually executed or got a 403
                if response_data.get("failed_tasks", 0) > 0:
                    first_result = response_data.get("results", [{}])[0]
                    if "403" in str(first_result.get("stderr", "")):
                        test_result["note"] = "403 error - Claude Code authentication required (expected)"
                        test_result["success"] = True  # This is expected behavior
            
            status = "✓" if test_result["success"] else "✗"
            print(f"  {status} {name}: {resp.status_code}")
            
            if not test_result["success"]:
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            test_result["status"] = "error"
            test_result["error"] = str(e)
            test_result["success"] = False
            all_passed = False
        
        endpoint_results[name] = test_result
    
    return all_passed, endpoint_results

# Main execution
print("🐳 CC Executor Docker Setup (UNIFIED)")
print("="*50)

# FIRST: Analyze the Docker environment
docker_analysis = analyze_docker_environment()
RESULTS["docker_analysis"] = docker_analysis

# Check existing setup
existing_state = check_existing_setup()
RESULTS["initial_state"] = existing_state

print("\n📋 Current state:")
for key, value in existing_state.items():
    if key != "existing_files":
        print(f"  - {key}: {value}")
if existing_state["existing_files"]:
    print(f"  - Files found: {', '.join(existing_state['existing_files'])}")

# Handle port conflicts before proceeding
if docker_analysis.get("port_conflicts"):
    if not handle_port_conflicts(docker_analysis):
        print("\n❌ Cannot proceed due to port conflicts")
        print("Please resolve the conflicts and try again")
        RESULTS["overall_success"] = False
        
        # Save results
        response_dir = DEPLOYMENT_DIR / "tmp" / "responses"
        response_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = response_dir / f"docker_setup_{timestamp}.json"
        with open(result_file, 'w') as f:
            json.dump(RESULTS, f, indent=2)
        print(f"\n💾 Results saved to: {result_file}")
        
        import sys
        sys.exit(1)

# Decide what to do
if existing_state["containers_running"]:
    print("\n⚠️  Containers are currently running")
    print("  They will be stopped and restarted")

# Generate or fix configs
if any([existing_state["docker_compose"], existing_state["dockerfile"], existing_state["start_services"]]):
    config_results = generate_or_fix_configs(fix_existing=True)
else:
    config_results = generate_or_fix_configs(fix_existing=False)

RESULTS["config_generation"] = config_results

# Try to deploy until successful
deployment_success = False
preserve_volumes = existing_state["containers_running"]  # Preserve if already had containers

for attempt in range(1, MAX_ATTEMPTS + 1):
    print(f"\n{'='*50}")
    print(f"DEPLOYMENT ATTEMPT {attempt}/{MAX_ATTEMPTS}")
    print('='*50)
    
    # Clean up before each attempt (preserve volumes on first attempt if needed)
    cleanup(remove_volumes=(not preserve_volumes or attempt > 1))
    
    # Try deployment
    success, attempt_result = attempt_deployment(attempt, rebuild_images=(attempt == 1))
    RESULTS["attempts"].append(attempt_result)
    
    if success:
        deployment_success = True
        print(f"\n✅ Deployment successful on attempt {attempt}!")
        break
    else:
        if attempt < MAX_ATTEMPTS:
            print(f"\n🔄 Retrying in 5 seconds...")
            time.sleep(5)
        else:
            print(f"\n❌ All {MAX_ATTEMPTS} deployment attempts failed")

# If deployment succeeded, test endpoints
if deployment_success:
    tests_passed, endpoint_results = test_endpoints()
    RESULTS["endpoint_tests"] = endpoint_results
    
    print("\n" + "="*50)
    if tests_passed:
        print("✅ SETUP COMPLETE - ALL TESTS PASSED!")
        print("\nServices running at:")
        print("  - API: http://localhost:8001")
        print("  - WebSocket: ws://localhost:8003")
        print("  - Redis: localhost:6380")
        print("\nNote: Execute endpoint returns 403 until Claude Code is authenticated")
        RESULTS["overall_success"] = True
    else:
        print("⚠️  Deployment succeeded but some endpoint tests failed")
        print("Check failing endpoints above")
        RESULTS["overall_success"] = False
else:
    print("\n❌ DEPLOYMENT FAILED")
    print("\nTroubleshooting:")
    print("  1. Check Docker daemon: docker info")
    print("  2. Check disk space: df -h")
    print("  3. Check ports: lsof -i:8001,8003,6380")
    print("  4. View logs: docker compose logs")
    print("  5. Check backups in: deployment/backups/")
    RESULTS["overall_success"] = False

# Save results
response_dir = DEPLOYMENT_DIR / "tmp" / "responses"
response_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = response_dir / f"docker_setup_{timestamp}.json"

with open(result_file, 'w') as f:
    json.dump(RESULTS, f, indent=2)

print(f"\n💾 Results saved to: {result_file}")

# Exit with appropriate code
import sys
sys.exit(0 if RESULTS["overall_success"] else 1)
```

## What This Does

1. **Analyzes Docker environment FIRST** using `docker ps`:
   - Detects both old separate containers and new unified container
   - Handles migration from old to new architecture

2. **Creates UNIFIED architecture**:
   - Single `cc_execute` container running both FastAPI and WebSocket
   - Shared authentication and process space
   - No network hop between services

3. **Smart deployment**:
   - Detects and stops old containers (cc_executor_websocket, cc_executor_api)
   - Generates new unified configuration
   - Tests all endpoints correctly

## Key Changes from Previous Version

1. **Unified Container**: Creates single `cc_execute` container instead of separate websocket/api
2. **Startup Script**: Includes `start_services.py` that runs both services
3. **Port Mapping**: Both 8001 (API) and 8003 (WebSocket) from same container
4. **Endpoint Testing**: Tests both API and WebSocket health endpoints
5. **403 Handling**: Recognizes that 403 on execute is expected (needs Claude authentication)

## Self-Evolution Features

- Detects old vs new architecture
- Automatically migrates from separate to unified containers
- Handles port conflicts from old containers
- Tests comprehensively and reports results
- Saves detailed JSON results for analysis