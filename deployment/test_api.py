#!/usr/bin/env python3
"""Test the CC Executor API deployment."""

import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8001"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_simple_execution():
    """Test simple task execution."""
    print("\nTesting simple task execution...")
    
    # Simple math question
    task_data = {
        "tasks": ["What is 2 + 2?"],
        "timeout_per_task": 30
    }
    
    print(f"Request: {json.dumps(task_data, indent=2)}")
    
    start_time = time.time()
    response = requests.post(f"{API_URL}/execute", json=task_data)
    duration = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Duration: {duration:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_multi_task_execution():
    """Test multiple task execution."""
    print("\nTesting multiple task execution...")
    
    # Multiple related tasks
    task_data = {
        "tasks": [
            "List the first 5 prime numbers",
            "What is the sum of those prime numbers?",
            "Is the sum itself a prime number?"
        ],
        "timeout_per_task": 60
    }
    
    print(f"Request: {json.dumps(task_data, indent=2)}")
    
    start_time = time.time()
    response = requests.post(f"{API_URL}/execute", json=task_data)
    duration = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Duration: {duration:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Execution ID: {result['execution_id']}")
        print(f"Total tasks: {result['total_tasks']}")
        print(f"Completed: {result['completed_tasks']}")
        print(f"Failed: {result['failed_tasks']}")
        print(f"Total time: {result['total_execution_time']:.2f}s")
        
        # Check status
        status_response = requests.get(f"{API_URL}/executions/{result['execution_id']}/status")
        if status_response.status_code == 200:
            print(f"\nStatus check: {json.dumps(status_response.json(), indent=2)}")
        
        return True
    else:
        print(f"Error: {response.text}")
        return False

def main():
    """Run all tests."""
    print("CC Executor API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Simple Execution", test_simple_execution),
        ("Multi-Task Execution", test_multi_task_execution)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running: {test_name}")
        print(f"{'=' * 50}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"Test failed with error: {e}")
            results.append((test_name, False))
    
    print(f"\n{'=' * 50}")
    print("Test Summary")
    print(f"{'=' * 50}")
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

if __name__ == "__main__":
    main()