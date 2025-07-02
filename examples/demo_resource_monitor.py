#!/usr/bin/env python3
"""Demonstration of resource monitor with dynamic timeout adjustment.

This script shows how timeouts are automatically adjusted when system
load is high (CPU or GPU usage > 14%).
"""
import os
import sys
import time
import subprocess
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cc_executor.core.resource_monitor import get_system_load, calculate_timeout_multiplier, adjust_timeout


def cpu_stress_worker():
    """CPU stress worker - performs intensive calculations."""
    result = 0
    for i in range(10**8):
        result += i ** 2
    return result


def simulate_high_cpu_load(duration=5):
    """Simulate high CPU load using multiprocessing."""
    print(f"🔥 Starting CPU stress test for {duration} seconds...")
    
    # Use all CPU cores
    num_cores = multiprocessing.cpu_count()
    with ThreadPoolExecutor(max_workers=num_cores) as executor:
        futures = []
        
        # Start CPU intensive tasks
        start_time = time.time()
        while time.time() - start_time < duration:
            for _ in range(num_cores):
                futures.append(executor.submit(cpu_stress_worker))
            time.sleep(0.1)
        
        # Wait for remaining tasks
        for future in futures:
            try:
                future.result(timeout=1)
            except:
                pass
    
    print("✅ CPU stress test completed")


def main():
    """Demonstrate resource monitor functionality."""
    print("Resource Monitor Demonstration")
    print("=" * 50)
    
    # Show current system load
    print("\n📊 Current System Load:")
    cpu_usage, gpu_usage = get_system_load()
    print(f"  CPU: {cpu_usage:.1f}%")
    if gpu_usage is not None:
        print(f"  GPU: {gpu_usage:.1f}%")
    else:
        print("  GPU: Not available")
    
    # Calculate timeout multiplier
    multiplier = calculate_timeout_multiplier()
    print(f"\n⏱️  Timeout multiplier: {multiplier}x")
    
    # Show timeout adjustment
    base_timeout = 30
    adjusted = adjust_timeout(base_timeout)
    print(f"  Base timeout: {base_timeout}s")
    print(f"  Adjusted timeout: {adjusted}s")
    
    # Demonstrate under normal load
    print("\n--- Normal Load Scenario ---")
    print("With low system load, timeouts remain at base values.")
    
    # Simulate high load scenario
    print("\n--- High Load Scenario ---")
    print("Simulating high CPU load...")
    
    # Start monitoring in background
    from threading import Thread, Event
    stop_monitoring = Event()
    
    def monitor_loop():
        """Monitor system load during stress test."""
        max_cpu = 0
        max_gpu = 0
        
        while not stop_monitoring.is_set():
            cpu, gpu = get_system_load()
            max_cpu = max(max_cpu, cpu)
            if gpu is not None:
                max_gpu = max(max_gpu, gpu)
            
            multiplier = calculate_timeout_multiplier()
            if multiplier > 1.0:
                print(f"  ⚠️  High load detected! CPU: {cpu:.1f}%, Multiplier: {multiplier}x")
            
            time.sleep(1)
        
        print(f"\n📈 Peak usage during test:")
        print(f"  Max CPU: {max_cpu:.1f}%")
        if max_gpu > 0:
            print(f"  Max GPU: {max_gpu:.1f}%")
    
    # Start monitoring
    monitor_thread = Thread(target=monitor_loop)
    monitor_thread.start()
    
    # Run CPU stress test
    try:
        simulate_high_cpu_load(duration=3)
    finally:
        stop_monitoring.set()
        monitor_thread.join()
    
    # Show final state
    print("\n📊 After stress test:")
    cpu_usage, gpu_usage = get_system_load()
    print(f"  CPU: {cpu_usage:.1f}%")
    if gpu_usage is not None:
        print(f"  GPU: {gpu_usage:.1f}%")
    
    multiplier = calculate_timeout_multiplier()
    adjusted = adjust_timeout(base_timeout)
    print(f"  Timeout multiplier: {multiplier}x")
    print(f"  Adjusted timeout: {adjusted}s")
    
    # Usage example
    print("\n💡 Usage Example:")
    print("```python")
    print("# In your WebSocket handler or process executor:")
    print("from cc_executor.core.resource_monitor import adjust_timeout")
    print("")
    print("# Original timeout")
    print("base_timeout = 60  # seconds")
    print("")
    print("# Automatically adjust based on system load")
    print("actual_timeout = adjust_timeout(base_timeout)")
    print("# If CPU/GPU > 14%, timeout becomes 180s (3x)")
    print("# Otherwise, remains 60s")
    print("")
    print("# Use the adjusted timeout")
    print("await asyncio.wait_for(long_operation(), timeout=actual_timeout)")
    print("```")
    
    print("\n✅ Demonstration completed!")


if __name__ == "__main__":
    main()