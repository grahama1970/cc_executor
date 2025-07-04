#!/usr/bin/env python3
"""Test basic command execution through CC Executor API."""

import requests
import json
import time

API_URL = "http://localhost:8001"

def test_basic_command():
    """Test basic command execution."""
    print("Testing basic command execution...")
    
    request_data = {
        "tasks": ["echo 'Hello from CC Executor!'"],
        "timeout_per_task": 10
    }
    
    response = requests.post(f"{API_URL}/execute", json=request_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nExecution ID: {result['execution_id']}")
        print(f"Total tasks: {result['total_tasks']}")
        print(f"Completed tasks: {result['completed_tasks']}")
        print(f"Failed tasks: {result['failed_tasks']}")
        
        for task_result in result['results']:
            print(f"\nTask {task_result['task_number']}: {task_result['task_description']}")
            print(f"Exit code: {task_result['exit_code']}")
            if task_result['stdout']:
                print(f"Output: {task_result['stdout']}")
            if task_result['stderr']:
                print(f"Error: {task_result['stderr']}")
            
        return result
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Run basic command test."""
    print("CC Executor Basic Command Test")
    print("=" * 50)
    
    # First check health
    try:
        health_response = requests.get(f"{API_URL}/health")
        print(f"Health check: {health_response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test basic command
    print("\n" + "=" * 50)
    result = test_basic_command()
    
    if result and result['failed_tasks'] == 0:
        print("\n✅ Basic command execution works!")
    else:
        print("\n❌ Basic command execution failed.")

if __name__ == "__main__":
    main()