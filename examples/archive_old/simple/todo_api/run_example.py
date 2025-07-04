#!/usr/bin/env python3
"""
Simple TODO API Example Runner
Executes the task list demonstrating cc_execute.md's sequential execution.
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

# Add project root to path and change to it
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
os.chdir(project_root)  # Change to project root for consistent paths

from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

# Directory setup - use paths relative to project root
EXAMPLE_REL_PATH = "examples/simple/todo_api"
EXAMPLE_DIR = project_root / EXAMPLE_REL_PATH
TMP_DIR = EXAMPLE_DIR / "tmp"
RESPONSES_DIR = TMP_DIR / "responses"
OUTPUT_DIR = EXAMPLE_DIR / "todo_api"


def setup():
    """Setup directories and verify environment."""
    # Clean previous outputs
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    
    # Ensure tmp structure exists
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check WebSocket server
    result = subprocess.run(
        ["cc-executor", "server", "status"], 
        capture_output=True, 
        text=True
    )
    if "not running" in result.stdout:
        print("Starting WebSocket server...")
        subprocess.run(["cc-executor", "server", "start"])
        import time
        time.sleep(3)


def run_simple_example():
    """Run the simple TODO API task sequence."""
    print("\n" + "="*60)
    print("SIMPLE TODO API EXAMPLE")
    print("Sequential task execution with fresh context")
    print("="*60)
    
    # Task definitions
    tasks = [
        {
            "name": "Create API",
            "question": "What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints using in-memory storage.",
            "tools": ["Write"],
            "timeout": 120
        },
        {
            "name": "Write Tests",
            "question": "What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all endpoints.",
            "tools": ["Read", "Write"],
            "timeout": 120
        },
        {
            "name": "Add Update Feature",
            "question": "How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint with tests.",
            "tools": ["Read", "Edit"],
            "timeout": 150
        }
    ]
    
    results = []
    
    for i, task in enumerate(tasks, 1):
        print(f"\n→ Task {i}: {task['name']}")
        print(f"  Fresh 200K context")
        print(f"  Tools: {task['tools']}")
        
        start_time = datetime.now()
        
        result = execute_task_via_websocket(
            task=task["question"],
            timeout=task["timeout"],
            tools=task["tools"]
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        task_result = {
            "task": i,
            "name": task["name"],
            "success": result["success"],
            "duration": f"{duration:.1f}s",
            "timestamp": datetime.now().isoformat()
        }
        results.append(task_result)
        
        if result["success"]:
            print(f"  ✓ Success in {duration:.1f}s")
        else:
            print(f"  ✗ Failed: {result.get('stderr', 'Unknown error')}")
            break
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESPONSES_DIR / f"execution_results_{timestamp}.json"
    
    with open(results_file, "w") as f:
        json.dump({
            "example": "simple_todo_api",
            "timestamp": datetime.now().isoformat(),
            "tasks_completed": len([r for r in results if r["success"]]),
            "total_tasks": len(tasks),
            "results": results
        }, f, indent=2)
    
    print(f"\n📊 Results saved to: tmp/responses/")
    
    # Summary
    successful = len([r for r in results if r["success"]])
    print(f"\n{'='*60}")
    print(f"SUMMARY: {successful}/{len(tasks)} tasks completed")
    print("="*60)
    
    if successful == len(tasks):
        print("\n✓ What this demonstrated:")
        print("  1. Each task got fresh 200K context")
        print("  2. Task 2 tested what Task 1 built")
        print("  3. Task 3 extended previous work")
        print("  4. No context pollution between tasks")
        print(f"\n📁 Generated code in: {OUTPUT_DIR}")
    
    return successful == len(tasks)


if __name__ == "__main__":
    setup()
    success = run_simple_example()
    sys.exit(0 if success else 1)