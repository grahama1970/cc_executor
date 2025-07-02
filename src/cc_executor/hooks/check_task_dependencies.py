#!/usr/bin/env python3
"""
Check task dependencies before execution.
Ensures previous tasks in sequence have completed and WebSocket is ready.
"""

import sys
import os
import json
import redis
import re
from typing import List, Dict, Optional
from loguru import logger

# --- Dependency extraction helpers ---
PKG_PATTERN = re.compile(r"(?:uv\s+pip\s+install\s+)([a-zA-Z0-9_\-]+)|(?:import\s+([a-zA-Z0-9_]+))")

def extract_required_packages(text: str) -> List[str]:
    """Return unique package names referenced via `uv pip install` or `import` statements."""
    pkgs = set()
    for install_match, import_match in PKG_PATTERN.findall(text):
        name = install_match or import_match
        if name:
            pkgs.add(name.lower())
    return list(pkgs)


def extract_current_task(context: str) -> Optional[Dict[str, any]]:
    """Extract current task information from context."""
    try:
        # Look for task patterns in context
        task_patterns = [
            r'Task (\d+):\s*(.+)',
            r'\*\*Task (\d+)\*\*:\s*(.+)',
            r'### Task (\d+):\s*(.+)'
        ]
        
        for pattern in task_patterns:
            match = re.search(pattern, context, re.MULTILINE)
            if match:
                return {
                    "number": int(match.group(1)),
                    "description": match.group(2).strip()
                }
                
        # Look for cc_execute.md mentions
        if "cc_execute.md" in context:
            # Extract task being executed
            exec_match = re.search(r'executing:\s*(.+)', context, re.IGNORECASE)
            if exec_match:
                return {
                    "number": 0,  # Unknown number
                    "description": exec_match.group(1).strip()
                }
                
        return None
        
    except Exception as e:
        logger.error(f"Error extracting task: {e}")
        return None

def get_task_dependencies(task_info: Dict[str, any]) -> List[int]:
    """Determine which tasks must complete before current task."""
    task_num = task_info.get("number", 0)
    description = task_info.get("description", "").lower()
    
    dependencies = []
    
    # Sequential dependency - all previous tasks
    if task_num > 1:
        dependencies.extend(range(1, task_num))
        
    # Explicit dependency keywords
    if "after" in description or "depends on" in description:
        # Extract task numbers mentioned
        dep_matches = re.findall(r'task (\d+)', description)
        for dep in dep_matches:
            dependencies.append(int(dep))
            
    # Service dependencies
    if any(word in description for word in ["test", "verify", "check endpoint"]):
        # Testing tasks depend on launch/setup tasks
        dependencies.extend([1, 2])  # Typically setup and launch
        
    return list(set(dependencies))  # Remove duplicates

def check_websocket_ready() -> bool:
    """Check if WebSocket handler is ready for connections."""
    try:
        r = redis.Redis(decode_responses=True)
        
        # Check WebSocket status
        ws_status = r.get("websocket:status")
        if ws_status == "ready":
            return True
            
        # Check if handler process is running
        ws_pid = r.get("websocket:pid")
        if ws_pid:
            try:
                # Check if process exists
                os.kill(int(ws_pid), 0)
                return True
            except (OSError, ValueError):
                pass
                
        # Check last heartbeat
        last_heartbeat = r.get("websocket:last_heartbeat")
        if last_heartbeat:
            import time
            if time.time() - float(last_heartbeat) < 30:
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Error checking WebSocket status: {e}")
        return False

def check_system_resources() -> Dict[str, bool]:
    """Check if system resources are adequate."""
    checks = {
        "memory": True,
        "cpu": True,
        "disk": True
    }
    
    try:
        # Check system load
        load_avg = os.getloadavg()[0]
        if load_avg > 14:
            checks["cpu"] = False
            logger.warning(f"High system load: {load_avg}")
            
        # Check available memory
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            available = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1))
            if available < 1000000:  # Less than 1GB
                checks["memory"] = False
                logger.warning(f"Low memory: {available/1024/1024:.1f}GB")
                
    except Exception as e:
        logger.error(f"Error checking resources: {e}")
        
    return checks

def main():
    """Main hook entry point."""
    context = sys.argv[1] if len(sys.argv) > 1 else ""
    
    # Extract current task
    task_info = extract_current_task(context)
    
    if not task_info:
        logger.info("No task context found, allowing execution")
        sys.exit(0)
        
    logger.info(f"Checking dependencies for Task {task_info['number']}: "
                f"{task_info['description'][:50]}...")
    
    try:
        r = redis.Redis(decode_responses=True)
        
        # Check task dependencies
        dependencies = get_task_dependencies(task_info)
        
        if dependencies:
            incomplete = []
            for dep_num in dependencies:
                status = r.hget("task:status", f"task_{dep_num}")
                if status != "completed":
                    incomplete.append(dep_num)
                    
            if incomplete:
                logger.error(f"Dependencies not met: Tasks {incomplete} not completed")
                sys.exit(1)
                
        # Check WebSocket readiness for cc_execute tasks
        if "cc_execute" in context or "websocket" in task_info['description']:
            if not check_websocket_ready():
                logger.error("WebSocket handler not ready")
                
                # Try to provide helpful info
                ws_logs = "/home/graham/workspace/experiments/cc_executor/logs/websocket_handler_*.log"
                logger.info(f"Check WebSocket logs: {ws_logs}")
                logger.info("Start WebSocket: cd /home/graham/workspace/experiments/cc_executor && "
                           "uvicorn src.cc_executor.servers.mcp_websocket_server:app --port 3000")
                           
                sys.exit(1)
                
        # Check system resources
        resources = check_system_resources()
        if not all(resources.values()):
            failed = [k for k, v in resources.items() if not v]
            logger.warning(f"Resource constraints: {failed}")
            
            # Don't block, just warn
            if task_info['number'] > 5:  # Later tasks more likely to fail
                logger.info("Consider waiting for resources to free up")
                
        # Extract and persist required package list for this session
        required_pkgs = extract_required_packages(context)
        if required_pkgs:
            session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
            try:
                r.setex(f"hook:req_pkgs:{session_id}", 600, json.dumps(required_pkgs))
                logger.info(f"Recorded required packages for session {session_id}: {required_pkgs}")
            except Exception as e:
                logger.debug(f"Could not store required packages: {e}")

        # Store dependency check result
        check_result = {
            "task": task_info,
            "dependencies_met": True,
            "websocket_ready": check_websocket_ready(),
            "resources": resources,
            "timestamp": os.environ.get('CLAUDE_TIMESTAMP', '')
        }
        
        r.setex(f"task:dep_check:{task_info['number']}", 300, json.dumps(check_result))
        
        logger.info("All dependencies satisfied ✓")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Dependency check failed: {e}")
        # Don't block execution on errors
        sys.exit(0)

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Task Dependencies Checker Test ===\n")
        
        # Test dependency extraction
        test_contexts = [
            "### Task 1: Set up the development environment",
            "**Task 3**: Create websocket handler (depends on Task 1)",
            "Task 5: Test the endpoint after Task 4 completes",
            "Run cc_execute.md on the WebSocket server",
            "Task 7: Verify everything works after all setup tasks"
        ]
        
        print("1. Testing task extraction:\n")
        for context in test_contexts:
            task_info = extract_current_task(context)
            print(f"Context: {context}")
            print(f"Extracted: {task_info}")
            if task_info:
                deps = get_task_dependencies(task_info)
                print(f"Dependencies: {deps}")
            print()
        
        # Test package extraction
        print("\n2. Testing package extraction:\n")
        test_code = """
        import redis
        import asyncio
        from loguru import logger
        
        # First we need to install
        uv pip install websockets
        uv pip install pytest-asyncio
        """
        
        packages = extract_required_packages(test_code)
        print(f"Code sample:\n{test_code}")
        print(f"Extracted packages: {packages}\n")
        
        # Test WebSocket readiness
        print("\n3. Testing WebSocket readiness check:\n")
        ws_ready = check_websocket_ready()
        print(f"WebSocket ready: {ws_ready}")
        
        # Mock some Redis data for testing
        try:
            r = redis.Redis(decode_responses=True)
            
            # Set up test data
            r.set("websocket:status", "ready")
            r.set("websocket:pid", str(os.getpid()))
            r.hset("task:status", "task_1", "completed")
            r.hset("task:status", "task_2", "completed")
            r.hset("task:status", "task_3", "failed")
            
            print("\nTest data set up in Redis")
            
            # Test dependency checking
            print("\n4. Testing dependency validation:\n")
            
            test_task = {
                "number": 4,
                "description": "Run tests after setup tasks"
            }
            
            deps = get_task_dependencies(test_task)
            print(f"Task 4 dependencies: {deps}")
            
            incomplete = []
            for dep_num in deps:
                status = r.hget("task:status", f"task_{dep_num}")
                print(f"  Task {dep_num}: {status or 'not found'}")
                if status != "completed":
                    incomplete.append(dep_num)
            
            if incomplete:
                print(f"\nIncomplete dependencies: {incomplete}")
            else:
                print("\nAll dependencies satisfied!")
                
            # Clean up test data
            r.delete("websocket:status", "websocket:pid")
            r.hdel("task:status", "task_1", "task_2", "task_3")
            
        except Exception as e:
            print(f"Redis test skipped: {e}")
        
        # Test resource checking
        print("\n5. Testing resource checks:\n")
        resources = check_system_resources()
        for resource, ok in resources.items():
            status = "✓" if ok else "✗"
            print(f"{resource}: {status}")
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()