#!/usr/bin/env python3
"""
Simple progress updates for cc_execute - NOT WebSocket-style heartbeats.

This shows how to add basic "still alive" indicators without the complexity
of the WebSocket heartbeat system, which serves a different purpose.
"""

import asyncio
import time
from typing import Optional, Any, Dict, Union
from pathlib import Path

# Import the original cc_execute
from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig


async def cc_execute_with_progress(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    update_interval: int = 30,
    show_elapsed: bool = True,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    """
    cc_execute with simple periodic progress updates.
    
    This is NOT like WebSocket heartbeats (which keep connections alive).
    This is simple user feedback during Claude's silent thinking period.
    
    Args:
        task: The task to execute
        config: Executor configuration
        update_interval: Seconds between updates (default: 30)
        show_elapsed: Show elapsed time updates
        **kwargs: Other arguments passed to cc_execute
        
    Returns:
        Result from cc_execute
    """
    if not show_elapsed:
        # If they don't want updates, just run normally
        return await cc_execute(task, config=config, **kwargs)
    
    # Start tracking time
    start_time = time.time()
    stop_updates = asyncio.Event()
    update_count = 0
    
    async def show_progress_updates():
        """Show simple elapsed time updates."""
        nonlocal update_count
        
        # Initial message
        print("⏳ Submitting task to Claude...")
        print("💭 Claude typically thinks in silence for 3-4 minutes before outputting results.")
        
        while not stop_updates.is_set():
            try:
                # Wait for interval or stop signal
                await asyncio.wait_for(stop_updates.wait(), timeout=update_interval)
                break  # Stop signal received
            except asyncio.TimeoutError:
                # Time for an update
                update_count += 1
                elapsed = time.time() - start_time
                
                # Simple, honest updates
                if update_count == 1:
                    print(f"\n⏱️  Still waiting... {elapsed:.0f}s elapsed")
                elif update_count == 2:
                    print(f"⏱️  Claude is still thinking... {elapsed:.0f}s elapsed")
                elif update_count == 3:
                    print(f"⏱️  This is normal for complex tasks... {elapsed:.0f}s elapsed")
                else:
                    # After 2 minutes, acknowledge it's taking a while
                    minutes = elapsed / 60
                    print(f"⏱️  {minutes:.1f} minutes elapsed... (Claude thinks deeply)")
    
    # Start progress updates
    progress_task = asyncio.create_task(show_progress_updates())
    
    try:
        # Run the actual command
        print(f"🚀 Starting execution...")
        result = await cc_execute(task, config=config, **kwargs)
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Success message
        print(f"\n✅ Task completed in {total_time:.1f}s!")
        
        return result
        
    except Exception as e:
        # Show error with timing
        total_time = time.time() - start_time
        print(f"\n❌ Task failed after {total_time:.1f}s: {e}")
        raise
        
    finally:
        # Stop progress updates
        stop_updates.set()
        try:
            await progress_task
        except:
            pass


async def cc_execute_with_spinner(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    """
    cc_execute with a simple spinner animation.
    
    More visual than elapsed time, but same concept.
    """
    start_time = time.time()
    stop_spinner = asyncio.Event()
    
    async def show_spinner():
        """Show a simple spinner."""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_index = 0
        
        print("🤔 Claude is thinking", end='', flush=True)
        
        while not stop_spinner.is_set():
            try:
                await asyncio.wait_for(stop_spinner.wait(), timeout=0.1)
                break
            except asyncio.TimeoutError:
                # Update spinner
                print(f"\r🤔 Claude is thinking {frames[frame_index % len(frames)]}", end='', flush=True)
                frame_index += 1
                
                # Add elapsed time every 10 seconds
                if frame_index % 100 == 0:
                    elapsed = time.time() - start_time
                    print(f" ({elapsed:.0f}s)", end='', flush=True)
    
    spinner_task = asyncio.create_task(show_spinner())
    
    try:
        result = await cc_execute(task, config=config, **kwargs)
        print("\r✅ Claude responded!              ")  # Clear spinner line
        return result
    finally:
        stop_spinner.set()
        await spinner_task


# Comparison with WebSocket approach
def explain_the_difference():
    """
    Explain why this is different from WebSocket heartbeats.
    """
    print("""
    🔍 Understanding the Difference:
    
    WebSocket Heartbeats (from websocket_handler.py):
    - Purpose: Keep TCP connection alive
    - Mechanism: Protocol-level ping/pong frames
    - Visibility: Hidden from user
    - Problem solved: Network timeouts
    
    Simple Progress Updates (this file):
    - Purpose: Show user that process is alive
    - Mechanism: Periodic console output
    - Visibility: Direct user feedback
    - Problem solved: "Is it frozen?" anxiety
    
    Why NOT add WebSocket-style heartbeats to cc_execute:
    1. No network connection to keep alive
    2. Different problem domain
    3. Unnecessary complexity
    4. Users can already Ctrl+C if needed
    
    This simple approach is more appropriate for cc_execute.
    """)


# Example usage
async def example():
    """Show the different approaches."""
    
    print("=== Simple Progress Updates for cc_execute ===\n")
    
    # Example 1: With elapsed time updates
    print("1. With periodic updates (every 30s):")
    result = await cc_execute_with_progress(
        "What is 2+2?",
        update_interval=5  # Faster for demo
    )
    print(f"Result: {result}\n")
    
    # Example 2: With spinner
    print("2. With spinner animation:")
    result = await cc_execute_with_spinner(
        "List 3 benefits of Python"
    )
    print(f"Result preview: {result[:100]}...\n")
    
    # Example 3: No progress (original behavior)
    print("3. Original behavior (no progress):")
    result = await cc_execute(
        "What is the capital of France?"
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    import sys
    
    if "--explain" in sys.argv:
        explain_the_difference()
    else:
        print("CC_EXECUTE: SIMPLE PROGRESS UPDATES")
        print("This is NOT WebSocket heartbeats - it's simple user feedback\n")
        
        asyncio.run(example())