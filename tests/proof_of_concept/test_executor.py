#!/usr/bin/env python3
"""
Test the CC Executor with real complex tasks.
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

from executor import cc_execute, cc_execute_list, CCExecutorConfig


async def test_basic_execution():
    """Test basic task execution."""
    print("\n=== Test 1: Basic Execution ===")
    
    start = time.time()
    result = await cc_execute(
        "Write a Python function to merge two sorted lists",
        stream=True
    )
    elapsed = time.time() - start
    
    print(f"\nExecution time: {elapsed:.2f}s")
    print(f"Result length: {len(result)} characters")
    
    # Save result
    Path("/tmp/cc_executor_test_basic.md").write_text(result)
    print("Result saved to: /tmp/cc_executor_test_basic.md")
    
    return {"test": "basic", "success": True, "time": elapsed}


async def test_complex_execution():
    """Test complex multi-file task."""
    print("\n=== Test 2: Complex Multi-File Task ===")
    
    config = CCExecutorConfig(
        timeout=600,  # 10 minutes for complex task
        stream_output=True
    )
    
    complex_task = """Create a simple web scraper with the following requirements:
1. Use aiohttp for async requests
2. Parse HTML with BeautifulSoup
3. Include rate limiting (max 2 requests per second)
4. Save results to JSON
5. Include error handling and retries
6. Add a simple CLI interface with argparse
"""
    
    start = time.time()
    result = await cc_execute(complex_task, config)
    elapsed = time.time() - start
    
    print(f"\nExecution time: {elapsed:.2f}s")
    print(f"Result length: {len(result)} characters")
    
    # Save result
    Path("/tmp/cc_executor_test_complex.md").write_text(result)
    print("Result saved to: /tmp/cc_executor_test_complex.md")
    
    return {"test": "complex", "success": True, "time": elapsed}


async def test_task_list():
    """Test executing a list of related tasks."""
    print("\n=== Test 3: Task List Execution ===")
    
    tasks = [
        "Create a FastAPI application with a simple /health endpoint",
        "Add a User model with SQLAlchemy (id, email, created_at)",
        "Add CRUD endpoints for the User model",
        "Add input validation using Pydantic models"
    ]
    
    config = CCExecutorConfig(
        timeout=300,  # 5 minutes per task
        stream_output=True
    )
    
    start = time.time()
    results = await cc_execute_list(tasks, config, sequential=True)
    elapsed = time.time() - start
    
    print(f"\nTotal execution time: {elapsed:.2f}s")
    print(f"Completed {len(results)} tasks")
    
    # Save results
    for i, (task, result) in enumerate(zip(tasks, results)):
        output_file = Path(f"/tmp/cc_executor_task_{i+1}.md")
        output_file.write_text(
            f"# Task {i+1}\n\n{task}\n\n## Result\n\n{result}"
        )
        print(f"Task {i+1} result saved to: {output_file}")
    
    return {"test": "task_list", "success": True, "time": elapsed, "tasks": len(tasks)}


async def test_streaming_output():
    """Test real-time streaming output."""
    print("\n=== Test 4: Streaming Output ===")
    
    config = CCExecutorConfig(stream_output=True)
    
    # Task that produces gradual output
    streaming_task = """Write a Python script that:
1. Prints "Starting..." 
2. Implements bubble sort with step-by-step output
3. Sorts the list [64, 34, 25, 12, 22, 11, 90]
4. Shows each swap operation
5. Prints "Completed!" at the end
"""
    
    print("Streaming output in real-time...")
    start = time.time()
    result = await cc_execute(streaming_task, config)
    elapsed = time.time() - start
    
    print(f"\nStreaming completed in: {elapsed:.2f}s")
    
    return {"test": "streaming", "success": True, "time": elapsed}


async def test_error_handling():
    """Test error handling for invalid requests."""
    print("\n=== Test 5: Error Handling ===")
    
    # Test with very short timeout
    config = CCExecutorConfig(timeout=1)  # 1 second timeout
    
    try:
        await cc_execute(
            "Create a complete e-commerce platform with 50 features",
            config
        )
        return {"test": "error_handling", "success": False, "error": "Should have timed out"}
    except TimeoutError as e:
        print(f"✓ Correctly caught timeout: {str(e)[:100]}...")
        return {"test": "error_handling", "success": True, "error": "timeout"}


async def main():
    """Run all tests."""
    print("CC Executor Proof of Concept Tests")
    print("==================================")
    
    # Check API key
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    results = []
    
    # Run tests
    results.append(await test_basic_execution())
    results.append(await test_complex_execution())
    results.append(await test_task_list())
    results.append(await test_streaming_output())
    results.append(await test_error_handling())
    
    # Summary
    print("\n=== Test Summary ===")
    total_time = sum(r.get("time", 0) for r in results)
    successful = sum(1 for r in results if r.get("success"))
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Total time: {total_time:.2f}s")
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "successful": successful,
        "total_time": total_time,
        "results": results
    }
    
    summary_file = Path(f"/tmp/cc_executor_poc_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    summary_file.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())