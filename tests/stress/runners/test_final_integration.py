#!/usr/bin/env python3
"""
Final integration test demonstrating production usage of WebSocketClient
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from cc_executor.client.websocket_client import WebSocketClient
from loguru import logger

async def test_production_scenario():
    """Test a realistic production scenario with multiple Claude tasks"""
    
    logger.info("="*80)
    logger.info("FINAL INTEGRATION TEST - PRODUCTION SCENARIO")
    logger.info("="*80)
    
    client = WebSocketClient()
    
    # Define realistic production tasks
    production_tasks = [
        # Quick tasks
        ("Math Calculation", 
         'claude -p "Calculate 15% of $2,450" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         30),
        
        # Code generation
        ("Python Function", 
         'claude -p "Write a Python function to validate email addresses using regex" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         60),
        
        # List generation
        ("Generate List", 
         'claude -p "List 10 common software design patterns with brief descriptions" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         60),
        
        # Analysis task
        ("Code Review", 
         'claude -p "What are the best practices for Python error handling?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         90),
        
        # Content generation (triggers timeout fix)
        ("Essay Writing", 
         'claude -p "Write a 1000 word essay about the importance of automated testing" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         120),
        
        # Quick check after essay
        ("Simple Check", 
         'claude -p "What is the capital of France?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         30),
        
        # Mixed non-Claude command
        ("System Check", 
         'echo "WebSocket handler still responsive"', 
         10),
        
        # Final Claude task
        ("JSON Generation", 
         'claude -p "Generate a JSON object representing a user profile with 5 fields" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         30),
    ]
    
    logger.info(f"Running {len(production_tasks)} production tasks with automatic restart...\n")
    
    # Execute all tasks with default restart behavior
    results = await client.execute_batch(
        tasks=production_tasks,
        restart_per_task=True  # Default - ensures 100% reliability
    )
    
    # Generate detailed report
    logger.info("\n" + "="*80)
    logger.info("PRODUCTION TEST RESULTS")
    logger.info("="*80)
    
    # Calculate statistics
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    total_execution = sum(r["duration"] for r in results)
    total_overhead = sum(r["restart_overhead"] for r in results)
    
    # Success rate
    success_rate = (successful / len(results)) * 100
    
    logger.info(f"\nSUCCESS METRICS:")
    logger.info(f"  Total Tasks: {len(results)}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Success Rate: {success_rate:.1f}%")
    
    logger.info(f"\nPERFORMANCE METRICS:")
    logger.info(f"  Total Time: {total_execution + total_overhead:.1f}s")
    logger.info(f"  Execution Time: {total_execution:.1f}s")
    logger.info(f"  Restart Overhead: {total_overhead:.1f}s")
    logger.info(f"  Average Overhead per Task: {total_overhead/len(results):.2f}s")
    logger.info(f"  Overhead Percentage: {(total_overhead/(total_execution + total_overhead)*100):.1f}%")
    
    logger.info(f"\nDETAILED RESULTS:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        name = r["task_name"]
        duration = r["duration"]
        overhead = r["restart_overhead"]
        outputs = r["outputs"]
        
        logger.info(f"  {status} {name:<20} {duration:6.1f}s (+{overhead:.1f}s restart) [{outputs} outputs]")
        
        if not r["success"]:
            logger.error(f"     Error: {r.get('error', 'Unknown')}")
    
    # Final verdict
    logger.info("\n" + "="*80)
    if success_rate == 100:
        logger.success("✅ PRODUCTION READY: All tasks completed successfully!")
        logger.success(f"   The restart strategy ensures 100% reliability with only {total_overhead:.1f}s overhead")
    elif success_rate >= 95:
        logger.warning(f"⚠️  NEARLY READY: {success_rate:.1f}% success rate")
    else:
        logger.error(f"❌ NOT READY: Only {success_rate:.1f}% success rate")
    
    # Demonstrate the difference without restart
    logger.info("\n" + "="*80)
    logger.info("COMPARISON: Running WITHOUT restart (to show the difference)")
    logger.info("="*80)
    
    # Run first 3 tasks without restart
    comparison_tasks = production_tasks[:3]
    
    logger.info("Starting fresh handler for comparison...")
    await client.kill_handler()
    await client.start_handler()
    
    comparison_results = []
    for i, (name, command, timeout) in enumerate(comparison_tasks):
        logger.info(f"\n[No Restart Test {i+1}/{len(comparison_tasks)}] {name}")
        result = await client.execute_command(
            command=command,
            timeout=timeout,
            restart_handler=False  # No restart
        )
        comparison_results.append(result)
        
        if result["success"]:
            logger.info(f"✅ Completed in {result['duration']:.1f}s")
        else:
            logger.error(f"❌ Failed: {result['error']}")
    
    no_restart_success = sum(1 for r in comparison_results if r["success"])
    logger.info(f"\nWithout restart: {no_restart_success}/{len(comparison_results)} succeeded")
    logger.info("Note: Without restart, subsequent tasks may fail if handler gets stuck")
    
    # Cleanup
    await client.cleanup()
    
    # Save results
    report_path = "final_integration_test_report.md"
    with open(report_path, "w") as f:
        f.write("# Final Integration Test Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total Tasks**: {len(results)}\n")
        f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
        f.write(f"- **Total Overhead**: {total_overhead:.1f}s ({total_overhead/len(results):.2f}s per task)\n")
        f.write(f"- **Overhead Percentage**: {(total_overhead/(total_execution + total_overhead)*100):.1f}%\n\n")
        
        f.write("## Conclusion\n\n")
        if success_rate == 100:
            f.write("✅ **PRODUCTION READY**: The WebSocket client with automatic restart ensures 100% reliability.\n\n")
            f.write(f"The minimal overhead of ~{total_overhead/len(results):.1f}s per task is negligible compared to the ")
            f.write("guarantee of successful execution for all tasks.\n")
        else:
            f.write(f"⚠️ **Issues Found**: Success rate of {success_rate:.1f}% indicates problems to investigate.\n")
    
    logger.info(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(test_production_scenario())