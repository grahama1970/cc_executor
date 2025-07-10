#!/usr/bin/env python3
"""
Medium Example - Concurrent task execution with CC Executor.

Demonstrates:
- Concurrent execution with asyncio
- Semaphore for rate limiting
- Progress tracking with tqdm
- Batch processing patterns
"""

import asyncio
import time
from asyncio import Semaphore, as_completed, gather
from cc_executor.client.cc_execute import cc_execute

from tqdm.asyncio import tqdm


async def concurrent_with_semaphore():
    """Execute tasks concurrently with rate limiting."""
    print("\n=== Concurrent Execution Example ===\n")
    
    # Independent tasks that can run in parallel
    tasks = [
        "Generate a comprehensive README.md for a Python web scraping project",
        "Create API documentation in OpenAPI 3.0 format for a REST API",
        "Write unit tests for a user authentication module",
        "Generate a Docker compose file for a microservices architecture",
        "Create a GitHub Actions workflow for Python CI/CD",
        "Write a CONTRIBUTING.md guide for open source contributors"
    ]
    
    # Limit to 3 concurrent executions
    semaphore = Semaphore(3)
    start_time = time.time()
    
    async def execute_with_limit(task: str, index: int):
        """Execute a task with semaphore limiting."""
        async with semaphore:
            result = await cc_execute(task)
            # Return summary of result
            summary = result.split('\n')[0] if result else "Empty result"
            return {
                "index": index,
                "task": task[:50] + "..." if len(task) > 50 else task,
                "summary": summary[:100] + "..." if len(summary) > 100 else summary
            }
    
    # Create all coroutines
    coroutines = [execute_with_limit(task, i) for i, task in enumerate(tasks)]
    
    # Execute with progress tracking
    results = []
    # With progress bar
    async for future in tqdm(as_completed(coroutines), 
                            total=len(tasks), 
                            desc="Processing"):
        result = await future
        results.append(result)
    
    # Sort results back to original order
    results.sort(key=lambda x: x['index'])
    
    # Display results
    print("\nResults:")
    for r in results:
        print(f"✅ {r['task']}")
        print(f"   → {r['summary']}\n")
    
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.1f}s (vs ~{len(tasks)*7:.0f}s sequential)")
    print(f"Speedup: ~{(len(tasks)*7)/total_time:.1f}x")


async def batch_processing():
    """Alternative: Process tasks in batches."""
    print("\n\n=== Batch Processing Example ===\n")
    
    tasks = [
        "Analyze Python code complexity for module_a.py",
        "Analyze Python code complexity for module_b.py",
        "Analyze Python code complexity for module_c.py",
        "Analyze Python code complexity for module_d.py"
    ]
    
    batch_size = 2
    start_time = time.time()
    
    print(f"Processing {len(tasks)} tasks in batches of {batch_size}...")
    
    all_results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"\n🔄 Batch {i//batch_size + 1}:")
        
        # Execute batch concurrently
        batch_results = await gather(*[cc_execute(task) for task in batch])
        all_results.extend(batch_results)
        
        # Show batch results
        for task, result in zip(batch, batch_results):
            summary = result.split('\n')[0] if result else "Empty"
            print(f"  ✅ {task[:40]}... → {summary[:50]}...")
    
    total_time = time.time() - start_time
    print(f"\nBatch processing completed in {total_time:.1f}s")


async def main():
    """Run both examples."""
    print("🚀 CC Executor - Medium Example: Concurrent Execution")
    print("=" * 60)
    
    # Example 1: Concurrent with semaphore
    await concurrent_with_semaphore()
    
    # Example 2: Batch processing
    await batch_processing()
    
    print("\n🎉 Done! Check out ../advanced/ for production patterns.")


if __name__ == "__main__":
    asyncio.run(main())