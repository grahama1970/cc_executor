#!/usr/bin/env python3
"""Simple test for CC Executor API using bash commands."""

import requests
import json
import time

API_URL = "http://localhost:8001"

def test_bash_execution():
    """Test simple bash execution."""
    print("\nTesting bash command execution...")
    
    # Simple bash commands that don't require Claude
    task_data = {
        "tasks": [
            "echo 'Hello from CC Executor!'",
            "pwd",
            "ls -la /app"
        ],
        "timeout_per_task": 10
    }
    
    print(f"Request: {json.dumps(task_data, indent=2)}")
    
    start_time = time.time()
    response = requests.post(f"{API_URL}/execute", json=task_data)
    duration = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Duration: {duration:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nExecution ID: {result['execution_id']}")
        print(f"Total tasks: {result['total_tasks']}")
        print(f"Completed: {result['completed_tasks']}")
        print(f"Failed: {result['failed_tasks']}")
        
        print("\nResults:")
        for task_result in result['results']:
            print(f"\n  Task {task_result['task_number']}: {task_result['task_description']}")
            print(f"  Exit code: {task_result['exit_code']}")
            if task_result.get('stdout'):
                print(f"  Output: {task_result['stdout'].strip()}")
            if task_result.get('stderr'):
                print(f"  Error: {task_result['stderr'].strip()}")
        
        return True
    else:
        print(f"Error: {response.text}")
        return False

def main():
    """Run test."""
    print("CC Executor API Test - Bash Commands")
    print("=" * 50)
    
    # First check health
    try:
        health_response = requests.get(f"{API_URL}/health")
        print(f"Health check: {health_response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Run bash test
    success = test_bash_execution()
    
    if success:
        print("\n✓ Test PASSED")
    else:
        print("\n✗ Test FAILED")

if __name__ == "__main__":
    main()