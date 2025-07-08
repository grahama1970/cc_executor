#!/usr/bin/env python3
"""
Demonstration comparing original vs enhanced progress monitoring.
Shows the improvements based on arxiv-mcp-server critique.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_executor.client.cc_execute import cc_execute
from cc_executor.client.cc_execute_enhanced import cc_execute_enhanced, ProgressData


class OriginalProgressCollector:
    """Simulates original progress callback behavior."""
    def __init__(self):
        self.callbacks_received = 0
        self.start_time = time.time()
        self.last_callback_time = None
    
    async def callback(self, message: str):
        self.callbacks_received += 1
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if self.last_callback_time:
            gap = current_time - self.last_callback_time
            print(f"[ORIGINAL] {elapsed:.1f}s: {message} (gap: {gap:.1f}s)")
        else:
            print(f"[ORIGINAL] {elapsed:.1f}s: {message}")
        
        self.last_callback_time = current_time


class EnhancedProgressCollector:
    """Shows enhanced progress monitoring capabilities."""
    def __init__(self):
        self.lines_received = 0
        self.heartbeats_received = 0
        self.patterns_detected = 0
        self.start_time = time.time()
        self.last_output_time = None
    
    async def callback(self, progress: ProgressData):
        self.lines_received += 1
        
        # Only show interesting updates to avoid spam
        show_update = False
        message = ""
        
        if progress.is_heartbeat:
            self.heartbeats_received += 1
            show_update = True
            message = f"💓 HEARTBEAT #{self.heartbeats_received}: {progress.elapsed_seconds:.1f}s elapsed"
        
        elif progress.detected_progress:
            self.patterns_detected += 1
            detected = progress.detected_progress
            show_update = True
            
            if detected['type'] == 'percentage':
                message = f"📊 Progress: {detected['value']:.1f}%"
            elif detected['type'] == 'steps':
                message = f"📋 Step {detected['current']}/{detected['total']}"
            elif detected['type'] == 'status':
                message = f"✅ Status: {detected['status']}"
            else:
                message = f"🔍 Detected: {detected['type']}"
        
        # Show periodic updates if quiet
        elif self.last_output_time and time.time() - self.last_output_time > 3:
            show_update = True
            message = f"⏱️  Working... (line {progress.line_count})"
        
        if show_update:
            elapsed = progress.elapsed_seconds
            print(f"[ENHANCED] {elapsed:.1f}s: {message}")
            self.last_output_time = time.time()


async def run_comparison():
    """Run the same task with both implementations."""
    
    # Task that should show the differences
    task = """Create a Python function that:
1. Prints "Starting analysis..."
2. Processes a list of 5 items, printing progress for each
3. Shows percentage complete after each item (20%, 40%, etc.)
4. Prints "Analysis complete!" at the end

Make sure to show clear progress indicators."""
    
    print("=" * 70)
    print("PROGRESS MONITORING COMPARISON")
    print("Original vs Enhanced Implementation")
    print("=" * 70)
    
    # Run with original implementation
    print("\n1. ORIGINAL IMPLEMENTATION (callbacks only on keywords):")
    print("-" * 50)
    original_collector = OriginalProgressCollector()
    
    start = time.time()
    result1 = await cc_execute(
        task,
        progress_callback=original_collector.callback
    )
    original_time = time.time() - start
    
    print(f"\nOriginal Summary:")
    print(f"  - Total callbacks: {original_collector.callbacks_received}")
    print(f"  - Execution time: {original_time:.1f}s")
    
    # Run with enhanced implementation  
    print("\n\n2. ENHANCED IMPLEMENTATION (callbacks on every line + patterns):")
    print("-" * 50)
    enhanced_collector = EnhancedProgressCollector()
    
    start = time.time()
    result2 = await cc_execute_enhanced(
        task,
        progress_callback=enhanced_collector.callback
    )
    enhanced_time = time.time() - start
    
    print(f"\nEnhanced Summary:")
    print(f"  - Total lines: {enhanced_collector.lines_received}")
    print(f"  - Heartbeats: {enhanced_collector.heartbeats_received}")
    print(f"  - Patterns detected: {enhanced_collector.patterns_detected}")
    print(f"  - Execution time: {enhanced_time:.1f}s")
    
    # Show the key differences
    print("\n\n" + "=" * 70)
    print("KEY DIFFERENCES:")
    print("=" * 70)
    
    print("\n1. Callback Frequency:")
    print(f"   Original: {original_collector.callbacks_received} callbacks (only on keywords)")
    print(f"   Enhanced: {enhanced_collector.lines_received} lines processed (every output line)")
    
    print("\n2. Progress Detection:")
    print(f"   Original: Manual parsing required")
    print(f"   Enhanced: {enhanced_collector.patterns_detected} patterns auto-detected")
    
    print("\n3. Long Task Support:")
    print(f"   Original: No heartbeats - could be silent for minutes")
    print(f"   Enhanced: Heartbeats every 30s + continuous updates")
    
    print("\n4. Data Structure:")
    print(f"   Original: Simple string messages")
    print(f"   Enhanced: Structured ProgressData with elapsed time, line count, patterns")
    
    print("\n\nCONCLUSION:")
    print("-" * 50)
    print("The enhanced implementation addresses the arxiv-mcp-server critique by:")
    print("✅ Providing callbacks on every line (not just keywords)")
    print("✅ Sending heartbeats for long-running tasks")
    print("✅ Delivering structured progress data")
    print("✅ Auto-detecting common progress patterns")
    print("✅ Maintaining backward compatibility")


async def demonstrate_long_task():
    """Demonstrate heartbeat functionality for longer tasks."""
    print("\n\n" + "=" * 70)
    print("LONG TASK DEMONSTRATION (Heartbeats)")
    print("=" * 70)
    
    # Note: This is simulated since we can't actually make Claude wait 30+ seconds
    print("\nFor tasks > 30 seconds, the enhanced version sends heartbeats:")
    print("- Every 30 seconds: 'Still running... X seconds elapsed'")
    print("- Prevents 'is it frozen?' uncertainty")
    print("- Includes line count to show activity")
    
    # Show what it would look like
    print("\nExample output for a 2-minute task:")
    print("[ENHANCED] 0.1s: ✅ Status: starting")
    print("[ENHANCED] 5.2s: 📋 Step 1/10")
    print("[ENHANCED] 15.3s: 📋 Step 3/10")
    print("[ENHANCED] 30.0s: 💓 HEARTBEAT #1: 30.0s elapsed")
    print("[ENHANCED] 45.5s: 📋 Step 6/10")
    print("[ENHANCED] 60.0s: 💓 HEARTBEAT #2: 60.0s elapsed")
    print("[ENHANCED] 75.2s: 📋 Step 8/10")
    print("[ENHANCED] 90.0s: 💓 HEARTBEAT #3: 90.0s elapsed")
    print("[ENHANCED] 95.3s: ✅ Status: complete")


if __name__ == "__main__":
    print("CC_EXECUTOR PROGRESS MONITORING COMPARISON")
    print("Addressing the arxiv-mcp-server critique\n")
    
    asyncio.run(run_comparison())
    asyncio.run(demonstrate_long_task())