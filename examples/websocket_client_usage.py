#!/usr/bin/env python3
"""
Example usage of WebSocketClient with restart functionality
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cc_executor.client.websocket_client import WebSocketClient
from loguru import logger

async def production_example():
    """Production example: 40-50 Claude tasks with automatic restart"""
    
    client = WebSocketClient()
    
    # Define your production tasks
    tasks = [
        ("Task 1: Simple Math", 
         'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         30),
        
        ("Task 2: Generate List", 
         'claude -p "List 10 programming languages" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         30),
        
        ("Task 3: Write Code", 
         'claude -p "Write a Python function to reverse a string" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         60),
        
        ("Task 4: Essay Writing", 
         'claude -p "Write a 500 word essay about AI" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 
         120),
        
        # Add more tasks as needed...
    ]
    
    logger.info("Starting production run with automatic per-task restart...")
    
    # Execute all tasks with default restart=True for each task
    results = await client.execute_batch(
        tasks=tasks,
        restart_per_task=True  # Default behavior - restart for each task
    )
    
    # Generate summary
    successful = sum(1 for r in results if r["success"])
    total_time = sum(r["duration"] for r in results)
    total_overhead = sum(r["restart_overhead"] for r in results)
    
    logger.info("\n" + "="*60)
    logger.info("PRODUCTION RUN SUMMARY")
    logger.info("="*60)
    logger.info(f"Total tasks: {len(results)}")
    logger.info(f"Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    logger.info(f"Total execution time: {total_time:.1f}s")
    logger.info(f"Total restart overhead: {total_overhead:.1f}s ({total_overhead/len(results):.1f}s average)")
    logger.info(f"Overhead percentage: {total_overhead/total_time*100:.1f}%")
    
    # Cleanup
    await client.cleanup()


async def optimized_example():
    """Optimized example: Mix of restart strategies"""
    
    client = WebSocketClient()
    
    # For simple commands, you can disable restart
    logger.info("=== Simple command without restart ===")
    result = await client.execute_command(
        command='echo "Hello World"',
        timeout=10,
        restart_handler=False  # No restart for simple commands
    )
    
    # For Claude commands, keep restart enabled (default)
    logger.info("\n=== Claude command with restart (default) ===")
    result = await client.execute_command(
        command='claude -p "What is AI?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
        timeout=60
        # restart_handler=True is the default
    )
    
    # Cleanup
    await client.cleanup()


async def single_command_example():
    """Simple example: Single Claude command"""
    
    client = WebSocketClient()
    
    # Execute a single Claude command with automatic restart
    result = await client.execute_command(
        command='claude -p "Explain quantum computing in simple terms" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none',
        timeout=60
        # restart_handler defaults to True
    )
    
    if result["success"]:
        logger.success(f"Command succeeded in {result['duration']:.1f}s")
        logger.info(f"Restart overhead: {result['restart_overhead']:.1f}s")
        logger.info(f"Output lines: {result['outputs']}")
    else:
        logger.error(f"Command failed: {result['error']}")
    
    await client.cleanup()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket client examples")
    parser.add_argument("--example", choices=["production", "optimized", "single"], 
                        default="single", help="Which example to run")
    
    args = parser.parse_args()
    
    if args.example == "production":
        asyncio.run(production_example())
    elif args.example == "optimized":
        asyncio.run(optimized_example())
    else:
        asyncio.run(single_command_example())