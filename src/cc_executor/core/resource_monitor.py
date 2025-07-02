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
    # Test the resource monitor
    import time
    
    print("Resource Monitor Test")
    print("-" * 40)
    
    # Monitor for 10 seconds
    for i in range(10):
        cpu, gpu = get_system_load()
        multiplier = calculate_timeout_multiplier()
        
        print(f"[{i+1}/10] CPU: {cpu:.1f}%", end="")
        if gpu is not None:
            print(f", GPU: {gpu:.1f}%", end="")
        print(f" -> Timeout multiplier: {multiplier}x")
        
        # Test timeout adjustment
        base_timeout = 30
        adjusted = adjust_timeout(base_timeout)
        if adjusted != base_timeout:
            print(f"         Timeout would be adjusted: {base_timeout}s -> {adjusted}s")
        
        time.sleep(1)