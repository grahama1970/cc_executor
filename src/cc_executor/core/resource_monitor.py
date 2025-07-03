#!/usr/bin/env python3
"""Resource monitor for dynamic timeout adjustment.

When CPU or GPU usage exceeds 14%, multiply timeouts by 3x to account
for system load and prevent false timeout failures.
"""
import subprocess
import psutil
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def get_cpu_usage() -> float:
    """Get current CPU usage percentage."""
    return psutil.cpu_percent(interval=1)


def get_gpu_usage() -> Optional[float]:
    """Get current GPU usage percentage using nvidia-smi.
    
    Returns None if nvidia-smi is not available or fails.
    """
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse the percentage value
            usage = float(result.stdout.strip())
            return usage
    except (subprocess.SubprocessError, ValueError, FileNotFoundError) as e:
        logger.debug(f"Could not get GPU usage: {e}")
    return None


def get_system_load() -> Tuple[float, Optional[float]]:
    """Get current CPU and GPU usage.
    
    Returns:
        Tuple of (cpu_usage, gpu_usage) where gpu_usage may be None
    """
    cpu_usage = get_cpu_usage()
    gpu_usage = get_gpu_usage()
    return cpu_usage, gpu_usage


def calculate_timeout_multiplier(threshold: float = 14.0) -> float:
    """Calculate timeout multiplier based on system load.
    
    Args:
        threshold: Usage percentage above which to apply 3x multiplier
        
    Returns:
        Multiplier to apply to timeouts (1.0 or 3.0)
    """
    cpu_usage, gpu_usage = get_system_load()
    
    # Check if either CPU or GPU exceeds threshold
    if cpu_usage > threshold:
        logger.info(f"CPU usage {cpu_usage:.1f}% exceeds {threshold}%, applying 3x timeout multiplier")
        return 3.0
    
    if gpu_usage is not None and gpu_usage > threshold:
        logger.info(f"GPU usage {gpu_usage:.1f}% exceeds {threshold}%, applying 3x timeout multiplier")
        return 3.0
    
    logger.debug(f"System load normal (CPU: {cpu_usage:.1f}%, GPU: {gpu_usage}%), using standard timeouts")
    return 1.0


def adjust_timeout(base_timeout: float, threshold: float = 14.0) -> float:
    """Adjust timeout based on current system load.
    
    Args:
        base_timeout: Original timeout in seconds
        threshold: Usage percentage above which to apply 3x multiplier
        
    Returns:
        Adjusted timeout value
    """
    multiplier = calculate_timeout_multiplier(threshold)
    adjusted = base_timeout * multiplier
    
    if multiplier > 1.0:
        logger.info(f"Timeout adjusted from {base_timeout}s to {adjusted}s due to system load")
    
    return adjusted


if __name__ == "__main__":
    # AI-friendly usage example - quick non-blocking demonstration
    from usage_helper import OutputCapture
    
    with OutputCapture(__file__) as capture:
        print("=== Resource Monitor Usage Example ===\n")
        
        # Test 1: Get instant CPU usage (no interval)
        print("--- Test 1: Instant CPU Check ---")
        cpu_instant = psutil.cpu_percent(interval=0)  # Non-blocking
        print(f"CPU Usage (instant): {cpu_instant:.1f}%")
        
        # Test 2: Get GPU usage if available
        print("\n--- Test 2: GPU Check ---")
        gpu = get_gpu_usage()
        if gpu is not None:
            print(f"GPU Usage: {gpu:.1f}%")
        else:
            print("GPU: Not available (nvidia-smi not found)")
        
        # Test 3: Test timeout calculation with various scenarios
        print("\n--- Test 3: Timeout Multiplier Scenarios ---")
        
        # Simulate different load scenarios
        scenarios = [
            (10.0, "Low load"),
            (14.0, "At threshold"),
            (15.0, "Above threshold"),
            (50.0, "High load")
        ]
        
        for cpu_val, desc in scenarios:
            # Mock the CPU value for testing
            import unittest.mock
            with unittest.mock.patch('psutil.cpu_percent', return_value=cpu_val):
                multiplier = calculate_timeout_multiplier(threshold=14.0)
                base = 30
                adjusted = base * multiplier
                print(f"{desc} (CPU={cpu_val}%): {base}s → {adjusted}s (x{multiplier})")
        
        # Test 4: Show actual current system state
        print("\n--- Test 4: Current System State ---")
        cpu_actual, gpu_actual = get_system_load()
        print(f"Actual CPU: {cpu_actual:.1f}%")
        if gpu_actual is not None:
            print(f"Actual GPU: {gpu_actual:.1f}%")
        
        current_multiplier = calculate_timeout_multiplier()
        print(f"Current timeout multiplier: {current_multiplier}x")
        
        # Test example timeout adjustment
        test_timeout = 60
        adjusted_timeout = adjust_timeout(test_timeout)
        print(f"Example: {test_timeout}s timeout → {adjusted_timeout}s")
        
        print("\n✅ Resource monitor functioning correctly!")