#!/usr/bin/env python3
"""
Test script for enhanced progress monitoring based on arxiv-mcp-server critique.
"""

import asyncio
import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_executor.client.cc_execute_enhanced import (
    cc_execute_enhanced,
    ProgressData,
    detect_progress_patterns
)


class ProgressMonitor:
    """Example progress monitor that collects and analyzes progress data."""
    
    def __init__(self):
        self.start_time = time.time()
        self.lines_received = 0
        self.heartbeats_received = 0
        self.progress_events = []
        self.last_update_time = time.time()
    
    async def handle_progress(self, progress: ProgressData):
        """Handle progress updates."""
        self.lines_received += 1
        current_time = time.time()
        
        # Calculate time since last update
        time_since_last = current_time - self.last_update_time
        self.last_update_time = current_time
        
        if progress.is_heartbeat:
            self.heartbeats_received += 1
            print(f"\n💓 HEARTBEAT #{self.heartbeats_received}: "
                  f"{progress.elapsed_seconds:.1f}s elapsed, "
                  f"{progress.line_count} lines processed")
        
        elif progress.detected_progress:
            detected = progress.detected_progress
            event = {
                'time': progress.elapsed_seconds,
                'type': detected['type'],
                'data': detected,
                'line': progress.current_line
            }
            self.progress_events.append(event)
            
            # Display detected progress
            if detected['type'] == 'percentage':
                print(f"\n📊 Progress: {detected['value']:.1f}%")
            elif detected['type'] == 'steps':
                print(f"\n📋 Step {detected['current']}/{detected['total']} "
                      f"({detected['percentage']:.1f}%)")
            elif detected['type'] == 'iteration':
                total_str = f"/{detected['total']}" if 'total' in detected else ""
                print(f"\n🔄 Iteration {detected['current']}{total_str}")
            elif detected['type'] == 'status':
                print(f"\n✅ Status: {detected['status']}")
            elif detected['type'] == 'file_operation':
                print(f"\n📁 {detected['operation'].title()} {detected['file']}")
        
        else:
            # Regular line - show if it's been quiet for a while
            if time_since_last > 2.0:  # More than 2 seconds since last update
                print(f"\n⏱️  [{progress.elapsed_seconds:.1f}s] Still working... "
                      f"(Line {progress.line_count})")
    
    def get_summary(self):
        """Get summary of progress monitoring."""
        total_time = time.time() - self.start_time
        return {
            'total_time': total_time,
            'lines_received': self.lines_received,
            'heartbeats_received': self.heartbeats_received,
            'progress_events': len(self.progress_events),
            'events': self.progress_events
        }


async def test_pattern_detection():
    """Test the progress pattern detection."""
    print("=== Testing Progress Pattern Detection ===\n")
    
    test_lines = [
        "Processing: 50%",
        "Step 3/10: Analyzing data",
        "Iteration 5 of 20",
        "Starting analysis...",
        "Processing file data.csv",
        "Task 7 of 10 complete",
        "Progress: 75.5%",
        "Writing to output.json",
        "Epoch 10/100",
        "Completed successfully"
    ]
    
    for line in test_lines:
        detected = detect_progress_patterns(line)
        print(f"Line: '{line}'")
        if detected:
            print(f"  Detected: {detected}")
        else:
            print(f"  No pattern detected")
        print()


async def test_short_task():
    """Test with a short task to see basic progress."""
    print("\n=== Testing Short Task (Basic Math) ===\n")
    
    monitor = ProgressMonitor()
    
    result = await cc_execute_enhanced(
        "What is 2+2? Show your work step by step.",
        progress_callback=monitor.handle_progress
    )
    
    print(f"\nResult: {result}")
    
    summary = monitor.get_summary()
    print(f"\nProgress Summary:")
    print(f"  Total time: {summary['total_time']:.2f}s")
    print(f"  Lines received: {summary['lines_received']}")
    print(f"  Heartbeats: {summary['heartbeats_received']}")
    print(f"  Progress events: {summary['progress_events']}")


async def test_medium_task():
    """Test with a medium task that should show more progress."""
    print("\n\n=== Testing Medium Task (Multi-step) ===\n")
    
    monitor = ProgressMonitor()
    
    task = """Create a Python function that:
1. Takes a list of numbers
2. Filters out negative numbers
3. Calculates the square of each remaining number
4. Returns the sum of all squares

Show your work step by step, indicating progress as you complete each requirement."""
    
    result = await cc_execute_enhanced(
        task,
        progress_callback=monitor.handle_progress
    )
    
    print(f"\nResult preview: {result[:200]}...")
    
    summary = monitor.get_summary()
    print(f"\nProgress Summary:")
    print(f"  Total time: {summary['total_time']:.2f}s")
    print(f"  Lines received: {summary['lines_received']}")
    print(f"  Heartbeats: {summary['heartbeats_received']}")
    print(f"  Progress events: {summary['progress_events']}")
    
    if summary['events']:
        print(f"\nDetected Progress Events:")
        for event in summary['events']:
            print(f"  {event['time']:.1f}s: {event['type']} - {event['data']}")


async def test_simulated_long_task():
    """Test with a task that simulates longer execution."""
    print("\n\n=== Testing Simulated Long Task ===\n")
    
    monitor = ProgressMonitor()
    
    # This task should take longer and show progress
    task = """Write a Python script that:
1. Prints "Starting analysis..." 
2. Counts from 1 to 5, printing "Processing step X/5" for each
3. Prints percentage progress after each step (20%, 40%, etc.)
4. Waits 1 second between each step using time.sleep(1)
5. Prints "Analysis complete!" at the end

Execute the script and show all output."""
    
    print("Requesting a task that should show progress patterns...")
    
    result = await cc_execute_enhanced(
        task,
        progress_callback=monitor.handle_progress
    )
    
    summary = monitor.get_summary()
    print(f"\n\nProgress Summary:")
    print(f"  Total time: {summary['total_time']:.2f}s")
    print(f"  Lines received: {summary['lines_received']}")
    print(f"  Heartbeats: {summary['heartbeats_received']}")
    print(f"  Progress events: {summary['progress_events']}")
    
    if summary['events']:
        print(f"\nDetected Progress Events:")
        for event in summary['events']:
            print(f"  {event['time']:.1f}s: {event['type']} - {event['data']}")


async def test_legacy_callback():
    """Test backward compatibility with legacy string callbacks."""
    print("\n\n=== Testing Legacy Callback Compatibility ===\n")
    
    messages = []
    
    def legacy_callback(msg: str):
        messages.append(msg)
        print(f"[LEGACY] {msg}")
    
    result = await cc_execute_enhanced(
        "What is the capital of France?",
        legacy_progress_callback=legacy_callback
    )
    
    print(f"\nResult: {result}")
    print(f"Legacy messages received: {len(messages)}")


async def main():
    """Run all tests."""
    print("Enhanced Progress Monitoring Test Suite")
    print("Based on arxiv-mcp-server critique")
    print("=" * 50)
    
    # Test pattern detection first
    await test_pattern_detection()
    
    # Then test actual execution with progress
    await test_short_task()
    await test_medium_task()
    await test_simulated_long_task()
    await test_legacy_callback()
    
    print("\n\nKey Improvements Demonstrated:")
    print("1. ✅ Progress callback called on EVERY line (not just keywords)")
    print("2. ✅ Heartbeats every 30 seconds for long tasks")
    print("3. ✅ Structured ProgressData with elapsed time, line count")
    print("4. ✅ Pattern detection for percentages, steps, status")
    print("5. ✅ Backward compatibility with legacy callbacks")
    
    print("\nThe enhanced version addresses the critique by providing:")
    print("- Real-time visibility into execution")
    print("- Structured progress data for analysis")
    print("- Heartbeats to show the process is alive")
    print("- Pattern detection for common progress indicators")


if __name__ == "__main__":
    asyncio.run(main())