#!/usr/bin/env python3
"""
Practical progress monitoring for cc_execute that acknowledges Claude's behavior.

Reality: Claude often thinks for 3-4 minutes in complete silence before outputting anything.
This implementation focuses on what actually helps rather than theoretical callbacks.
"""

import asyncio
import time
from typing import Optional, Callable, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from cc_executor.client.cc_execute import (
    cc_execute,
    CCExecutorConfig,
    estimate_timeout,
    export_execution_history
)


@dataclass
class PracticalProgress:
    """Practical progress information for Claude tasks."""
    elapsed_seconds: float
    estimated_total_seconds: Optional[float]  # From historical data
    estimated_remaining: Optional[float]
    is_outputting: bool  # False during silent period, True when output starts
    output_lines: int
    last_heartbeat: float
    status: str  # 'waiting', 'outputting', 'completed', 'failed'
    
    @property
    def progress_percentage(self) -> Optional[float]:
        """Estimate progress based on elapsed vs estimated time."""
        if self.estimated_total_seconds and self.estimated_total_seconds > 0:
            return min(100, (self.elapsed_seconds / self.estimated_total_seconds) * 100)
        return None
    
    def format_status(self) -> str:
        """Human-readable status message."""
        if self.status == 'waiting':
            msg = f"⏳ Claude is thinking... {self.elapsed_seconds:.0f}s elapsed"
            if self.estimated_remaining:
                msg += f" (est. {self.estimated_remaining:.0f}s remaining)"
        elif self.status == 'outputting':
            msg = f"📝 Receiving output... {self.output_lines} lines"
        elif self.status == 'completed':
            msg = f"✅ Completed in {self.elapsed_seconds:.1f}s"
        else:
            msg = f"❌ {self.status}"
        
        if self.progress_percentage:
            msg += f" [{self.progress_percentage:.0f}%]"
        
        return msg


class PracticalProgressMonitor:
    """Realistic progress monitoring for Claude tasks."""
    
    def __init__(self, 
                 task: str,
                 heartbeat_interval: int = 30,
                 update_callback: Optional[Callable[[PracticalProgress], Any]] = None):
        self.task = task
        self.heartbeat_interval = heartbeat_interval
        self.update_callback = update_callback
        self.start_time = time.time()
        self.output_started = False
        self.output_lines = 0
        self.last_heartbeat = self.start_time
        self.estimated_duration = None
        self._estimate_duration()
    
    def _estimate_duration(self):
        """Estimate duration from historical data."""
        try:
            # Use the built-in estimation
            self.estimated_duration = estimate_timeout(self.task, default=180)
        except:
            self.estimated_duration = 180  # 3 minute default
    
    async def heartbeat_loop(self, process_future):
        """Send realistic heartbeats during execution."""
        while not process_future.done():
            current_time = time.time()
            elapsed = current_time - self.start_time
            
            # Send heartbeat every interval
            if current_time - self.last_heartbeat >= self.heartbeat_interval:
                progress = PracticalProgress(
                    elapsed_seconds=elapsed,
                    estimated_total_seconds=self.estimated_duration,
                    estimated_remaining=max(0, self.estimated_duration - elapsed) if self.estimated_duration else None,
                    is_outputting=self.output_started,
                    output_lines=self.output_lines,
                    last_heartbeat=current_time,
                    status='outputting' if self.output_started else 'waiting'
                )
                
                if self.update_callback:
                    await self._safe_callback(progress)
                
                self.last_heartbeat = current_time
            
            await asyncio.sleep(1)  # Check every second
    
    async def _safe_callback(self, progress: PracticalProgress):
        """Safely call the callback."""
        try:
            if asyncio.iscoroutinefunction(self.update_callback):
                await self.update_callback(progress)
            else:
                self.update_callback(progress)
        except Exception as e:
            print(f"Progress callback error: {e}")
    
    def on_output_start(self):
        """Called when Claude starts outputting."""
        self.output_started = True
        self.output_lines = 0
    
    def on_output_line(self):
        """Called for each output line."""
        self.output_lines += 1
    
    async def get_final_progress(self, success: bool) -> PracticalProgress:
        """Get final progress report."""
        elapsed = time.time() - self.start_time
        return PracticalProgress(
            elapsed_seconds=elapsed,
            estimated_total_seconds=self.estimated_duration,
            estimated_remaining=0,
            is_outputting=True,
            output_lines=self.output_lines,
            last_heartbeat=time.time(),
            status='completed' if success else 'failed'
        )


async def cc_execute_practical(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    progress_callback: Optional[Callable[[PracticalProgress], Any]] = None,
    heartbeat_interval: int = 30,
    show_estimates: bool = True,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    """
    Practical cc_execute with realistic progress monitoring.
    
    Acknowledges that Claude may be silent for minutes, providing:
    - Time-based progress estimates from historical data
    - Heartbeats to confirm the process is alive
    - Clear communication about what's happening
    
    Args:
        task: The task to execute
        config: Executor configuration
        progress_callback: Called with PracticalProgress updates
        heartbeat_interval: Seconds between heartbeats (default: 30)
        show_estimates: Show time estimates based on historical data
        **kwargs: Additional arguments passed to cc_execute
    
    Returns:
        The result from cc_execute
    """
    monitor = PracticalProgressMonitor(task, heartbeat_interval, progress_callback)
    
    # Initial message
    if show_estimates and monitor.estimated_duration:
        est_minutes = monitor.estimated_duration / 60
        print(f"📊 Estimated duration: {est_minutes:.1f} minutes (based on similar tasks)")
        print(f"⏳ Claude typically thinks in silence before outputting results...")
    
    # Wrap the line callback to detect when output starts
    original_callback = kwargs.get('progress_callback')
    output_started = False
    
    async def line_callback(msg: str):
        nonlocal output_started
        if not output_started:
            output_started = True
            monitor.on_output_start()
            print(f"\n🎉 Output started after {time.time() - monitor.start_time:.1f}s of thinking!")
        
        monitor.on_output_line()
        
        if original_callback:
            await original_callback(msg)
    
    # Replace the callback
    if 'progress_callback' in kwargs:
        kwargs['progress_callback'] = line_callback
    
    # Create execution task
    exec_task = asyncio.create_task(cc_execute(task, config=config, **kwargs))
    
    # Create heartbeat task
    heartbeat_task = asyncio.create_task(monitor.heartbeat_loop(exec_task))
    
    try:
        # Wait for execution
        result = await exec_task
        success = True
    except Exception as e:
        result = str(e)
        success = False
        raise
    finally:
        # Cancel heartbeat
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        
        # Send final progress
        final_progress = await monitor.get_final_progress(success)
        if progress_callback:
            await monitor._safe_callback(final_progress)
    
    return result


# Practical helper functions

async def estimate_task_duration(task: str) -> Dict[str, Any]:
    """
    Estimate task duration based on historical data.
    
    Returns:
        Dict with 'estimated_seconds', 'confidence', 'similar_tasks'
    """
    try:
        # Get historical data
        history = await export_execution_history(format="json", limit=50)
        
        # Simple estimation based on task length and complexity
        estimated = estimate_timeout(task)
        
        return {
            'estimated_seconds': estimated,
            'confidence': 'medium',  # Could be enhanced with better analysis
            'based_on': 'task complexity and historical patterns'
        }
    except:
        return {
            'estimated_seconds': 180,  # 3 minute default
            'confidence': 'low',
            'based_on': 'default estimate'
        }


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


# Example usage
async def example_with_practical_progress():
    """Example showing practical progress monitoring."""
    
    def progress_handler(progress: PracticalProgress):
        """Handle progress updates practically."""
        print(f"\r{progress.format_status()}", end='', flush=True)
    
    task = "Create a comprehensive Python web scraping tutorial with examples"
    
    # First, estimate duration
    estimate = await estimate_task_duration(task)
    print(f"📊 Task estimation: {format_duration(estimate['estimated_seconds'])} "
          f"({estimate['confidence']} confidence)")
    
    # Execute with practical monitoring
    result = await cc_execute_practical(
        task,
        progress_callback=progress_handler,
        heartbeat_interval=20,  # More frequent updates
        show_estimates=True
    )
    
    print(f"\n\n✅ Task completed!")
    print(f"Result preview: {result[:200]}...")


if __name__ == "__main__":
    # Demonstrate practical progress monitoring
    print("PRACTICAL PROGRESS MONITORING FOR CLAUDE")
    print("=" * 50)
    print("\nKey insights:")
    print("1. Claude often thinks for 3-4 minutes in complete silence")
    print("2. Progress callbacks don't help during the silent period")
    print("3. Time-based estimates and heartbeats are more useful")
    print("4. Set realistic expectations for users")
    print("\n" + "=" * 50 + "\n")
    
    asyncio.run(example_with_practical_progress())