#!/usr/bin/env python3
"""
REAL test with actual Claude CLI calls - NO MOCKING.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from executor import cc_execute, cc_execute_list, CCExecutorConfig


async def test_real_simple():
    """Test with real Claude CLI - simple task."""
    print("=== Test 1: Real Claude Simple Task ===")
    
    result = await cc_execute(
        "Write a Python function to check if a number is prime",
        stream=True  # See output in real-time
    )
    
    print(f"\nResult length: {len(result)} chars")
    
    # Check saved response
    files = sorted(Path("/tmp/responses").glob("cc_execute_*.json"), 
                   key=lambda p: p.stat().st_mtime)
    if files:
        latest = files[-1]
        with open(latest) as f:
            data = json.load(f)
        print(f"✅ Saved to: {latest.name}")
        print(f"   Execution time: {data['execution_time']:.2f}s")


async def test_real_complex():
    """Test with real Claude CLI - complex task."""
    print("\n=== Test 2: Real Claude Complex Task ===")
    
    complex_task = """Create a Python class called TaskQueue with these features:
1. Add tasks with priority (1-5)
2. Process tasks in priority order
3. Support async task execution
4. Include error handling
5. Add method to get queue statistics"""

    result = await cc_execute(complex_task, stream=True)
    
    print(f"\nGenerated {len(result)} chars of code")
    
    # Verify it created actual code
    if "class TaskQueue" in result:
        print("✅ Claude generated the TaskQueue class")
    if "async def" in result:
        print("✅ Claude included async methods")


async def test_real_task_list():
    """Test with real Claude CLI - task list."""
    print("\n=== Test 3: Real Claude Task List ===")
    
    tasks = [
        "Create a simple Calculator class with add, subtract, multiply, divide methods",
        "Add error handling for division by zero to the Calculator class",
        "Write unit tests for the Calculator class using pytest"
    ]
    
    print("Executing 3 real tasks sequentially...")
    results = await cc_execute_list(tasks, sequential=True)
    
    print(f"\n✅ Completed {len(results)} tasks")
    for i, result in enumerate(results):
        print(f"   Task {i+1}: Generated {len(result)} chars")


async def test_real_streaming():
    """Test real-time streaming with Claude."""
    print("\n=== Test 4: Real Claude Streaming ===")
    
    print("Watch the output stream in real-time:")
    print("-" * 40)
    
    result = await cc_execute(
        "Count from 1 to 5 with explanations for each number",
        stream=True
    )
    
    print("-" * 40)
    print(f"Total output: {len(result)} chars")


async def test_real_error():
    """Test error handling with impossible task."""
    print("\n=== Test 5: Real Error Handling ===")
    
    config = CCExecutorConfig(timeout=30)  # 30 second timeout
    
    try:
        # This should work but might be cut off by timeout
        await cc_execute(
            "Create a complete operating system kernel in C",
            config=config,
            stream=True
        )
    except TimeoutError as e:
        print(f"✅ Correctly handled timeout: {str(e)[:100]}...")
    except Exception as e:
        print(f"Got error: {type(e).__name__}: {e}")


async def main():
    """Run all real tests."""
    print("CC Executor - REAL Claude CLI Tests")
    print("===================================")
    print("Using Claude Max Plan - NO MOCKING")
    print(f"Start time: {datetime.now()}\n")
    
    await test_real_simple()
    await test_real_complex()
    await test_real_task_list()
    await test_real_streaming()
    await test_real_error()
    
    # Summary
    print("\n=== Summary ===")
    response_files = list(Path("/tmp/responses").glob("cc_execute_*.json"))
    print(f"Total responses saved: {len(response_files)}")
    
    # Show recent files
    recent = sorted(response_files, key=lambda p: p.stat().st_mtime)[-5:]
    print("\nRecent response files:")
    for f in recent:
        print(f"  - {f.name}")


if __name__ == "__main__":
    asyncio.run(main())