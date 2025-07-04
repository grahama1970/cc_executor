#!/usr/bin/env python3
"""
Test the TODO API example to ensure it works correctly.
This demonstrates cc_execute.md's value for sequential task execution.
"""

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

def cleanup_previous_run():
    """Clean up any previous test artifacts."""
    todo_api_dir = Path("todo_api")
    if todo_api_dir.exists():
        logger.info("Cleaning up previous todo_api directory...")
        shutil.rmtree(todo_api_dir)

def check_server_status() -> bool:
    """Check if WebSocket server is running."""
    try:
        result = subprocess.run(
            ["cc-executor", "server", "status"],
            capture_output=True,
            text=True
        )
        return "running" in result.stdout.lower()
    except Exception:
        return False

def start_server_if_needed():
    """Start the WebSocket server if it's not running."""
    if not check_server_status():
        logger.warning("WebSocket server not running. Starting it...")
        subprocess.run(["cc-executor", "server", "start"], check=False)
        # Give it time to start
        import time
        time.sleep(3)
        
        # Verify it started
        if not check_server_status():
            logger.error("Failed to start WebSocket server!")
            sys.exit(1)
    else:
        logger.info("WebSocket server is running ✓")


def verify_task1_output() -> bool:
    """Verify that Task 1 created the expected files."""
    todo_api_dir = Path("todo_api")
    main_py = todo_api_dir / "main.py"
    
    if not todo_api_dir.exists():
        logger.error("todo_api directory not created")
        return False
        
    if not main_py.exists():
        logger.error("main.py not created")
        return False
        
    # Check that main.py has the expected content
    content = main_py.read_text()
    required_elements = [
        "FastAPI",
        "@app.get",
        "@app.post", 
        "@app.delete",
        "/todos",
        "id",
        "title",
        "completed"
    ]
    
    missing = [elem for elem in required_elements if elem not in content]
    if missing:
        logger.error(f"Missing elements in main.py: {missing}")
        return False
        
    logger.success("✓ Task 1 output verified")
    return True

def verify_task2_output() -> bool:
    """Verify that Task 2 created tests."""
    test_file = Path("todo_api/test_api.py")
    
    if not test_file.exists():
        logger.error("test_api.py not created")
        return False
        
    content = test_file.read_text()
    required_elements = [
        "test_",
        "get",
        "post",
        "delete"
    ]
    
    missing = [elem for elem in required_elements if elem not in content]
    if missing:
        logger.error(f"Missing elements in test_api.py: {missing}")
        return False
        
    logger.success("✓ Task 2 output verified")
    return True

def verify_task3_output() -> bool:
    """Verify that Task 3 added the PUT endpoint."""
    main_py = Path("todo_api/main.py")
    test_py = Path("todo_api/test_api.py")
    
    if not main_py.exists() or not test_py.exists():
        logger.error("Required files missing")
        return False
        
    main_content = main_py.read_text()
    test_content = test_py.read_text()
    
    if "@app.put" not in main_content and "put" not in main_content.lower():
        logger.error("PUT endpoint not found in main.py")
        return False
        
    if "put" not in test_content.lower() and "update" not in test_content.lower():
        logger.error("PUT tests not found in test_api.py")
        return False
        
    logger.success("✓ Task 3 output verified")
    return True

def save_results(results: list):
    """Save test results to a file."""
    output_dir = Path("/tmp/responses")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"todo_api_example_test_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test": "todo_api_example",
            "results": results
        }, f, indent=2)
    
    logger.info(f"\n💾 Results saved to: {output_file}")

def main():
    """Run the complete TODO API example test."""
    logger.info("\n" + "="*60)
    logger.info("TODO API EXAMPLE TEST")
    logger.info("Testing cc_execute.md sequential task execution")
    logger.info("="*60)
    
    # Setup
    cleanup_previous_run()
    start_server_if_needed()
    
    # Define the tasks following the self-improving format
    tasks = [
        # Task 1: Create TODO API Structure
        """What is the implementation of a FastAPI TODO application? Create folder todo_api/ with main.py containing GET /todos, POST /todos, and DELETE /todos/{id} endpoints. Use in-memory list storage where each todo has id (int), title (str), and completed (bool) fields.""",
        
        # Task 2: Test the API
        """What tests are needed for the TODO API in todo_api/main.py? Read the implementation and create todo_api/test_api.py with pytest tests covering all endpoints (GET, POST, DELETE) including edge cases like deleting non-existent todos.""",
        
        # Task 3: Add Update Feature
        """How can I add update functionality to the TODO API? Read todo_api/main.py and todo_api/test_api.py, then add PUT /todos/{id} endpoint for updating title and completed status. Include corresponding tests in test_api.py."""
    ]
    
    # Tool configurations for each task
    task_configs = [
        {"tools": ["Write"], "timeout": 120},
        {"tools": ["Read", "Write"], "timeout": 120},
        {"tools": ["Read", "Edit", "Write"], "timeout": 150}
    ]
    
    results = []
    all_success = True
    
    # Execute tasks sequentially with proper configurations
    for i, (task, config) in enumerate(zip(tasks, task_configs), 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"TASK {i}: {task[:50]}...")
        logger.info(f"{'='*60}")
        logger.info(f"Using tools: {config['tools']}, timeout: {config['timeout']}s")
        
        # Execute with specific config
        start_time = datetime.now()
        result = execute_task_via_websocket(
            task=task,
            timeout=config["timeout"],
            tools=config["tools"]
        )
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Task {i} completed in {duration:.1f}s")
        logger.info(f"Success: {result['success']}")
        
        if not result['success']:
            logger.error(f"Error: {result.get('stderr', 'Unknown error')}")
        
        results.append({
            "task_number": i,
            "description": task[:100] + "...",
            "success": result["success"],
            "duration": duration,
            "tools_used": config["tools"]
        })
        
        if not result["success"]:
            all_success = False
            logger.error(f"Task {i} failed. Stopping execution.")
            break
        
        # Verify outputs after each task
        if i == 1 and not verify_task1_output():
            all_success = False
            break
        elif i == 2 and not verify_task2_output():
            all_success = False
            break
        elif i == 3 and not verify_task3_output():
            all_success = False
            break
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"Task {i}: {status}")
    
    if all_success:
        logger.success("\n🎉 ALL TASKS COMPLETED SUCCESSFULLY!")
        logger.info("\nWhat this demonstrated:")
        logger.info("1. Fresh Context: Each task had full 200K tokens")
        logger.info("2. Sequential Dependencies: Task 2 tested Task 1's output")
        logger.info("3. Incremental Development: Task 3 extended previous work")
        logger.info("4. No Context Pollution: Each task started clean")
        
        # Show final structure
        logger.info("\nCreated structure:")
        for file in Path("todo_api").rglob("*.py"):
            logger.info(f"  - {file}")
    else:
        logger.error("\n❌ TEST FAILED")
        logger.info("This example requires cc_execute.md to work properly.")
        logger.info("Ensure WebSocket server is running: cc-executor server start")
    
    # Save results
    save_results(results)
    
    # Don't clean up on success so user can inspect
    if all_success:
        logger.info("\n📁 Output files left in todo_api/ for inspection")
    
    return all_success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)