"""
Advanced Benchmarking and Profiling Infrastructure
==================================================

This module provides high-precision benchmarking tools for evaluating
fast approximation algorithms with nanosecond precision timing,
memory usage profiling, and statistical analysis.

Features:
- Nanosecond precision timing using perf_counter_ns
- Memory usage profiling with tracemalloc
- Statistical analysis (mean, std, percentiles)
- Visualization setup for performance charts
- Cache warming and CPU affinity options
"""

import time
import tracemalloc
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Callable, List, Dict, Any, Tuple, Optional
import statistics
import gc
import os
import psutil
from contextlib import contextmanager
from dataclasses import dataclass, field
import json


@dataclass
class BenchmarkResult:
    """Container for benchmark results with statistical analysis."""
    name: str
    times_ns: List[int]
    memory_peak_kb: float
    memory_current_kb: float
    iterations: int
    
    # Computed statistics
    mean_ns: float = field(init=False)
    std_ns: float = field(init=False)
    min_ns: float = field(init=False)
    max_ns: float = field(init=False)
    median_ns: float = field(init=False)
    p95_ns: float = field(init=False)
    p99_ns: float = field(init=False)
    
    def __post_init__(self):
        """Compute statistics from raw timing data."""
        if self.times_ns:
            self.mean_ns = statistics.mean(self.times_ns)
            self.std_ns = statistics.stdev(self.times_ns) if len(self.times_ns) > 1 else 0
            self.min_ns = min(self.times_ns)
            self.max_ns = max(self.times_ns)
            self.median_ns = statistics.median(self.times_ns)
            self.p95_ns = np.percentile(self.times_ns, 95)
            self.p99_ns = np.percentile(self.times_ns, 99)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'iterations': self.iterations,
            'mean_ns': self.mean_ns,
            'std_ns': self.std_ns,
            'min_ns': self.min_ns,
            'max_ns': self.max_ns,
            'median_ns': self.median_ns,
            'p95_ns': self.p95_ns,
            'p99_ns': self.p99_ns,
            'memory_peak_kb': self.memory_peak_kb,
            'memory_current_kb': self.memory_current_kb,
            'mean_us': self.mean_ns / 1000,
            'mean_ms': self.mean_ns / 1_000_000
        }


class HighPrecisionTimer:
    """Context manager for nanosecond precision timing."""
    
    def __init__(self):
        self.start_ns = 0
        self.end_ns = 0
        self.elapsed_ns = 0
    
    def __enter__(self):
        # Force garbage collection before timing
        gc.collect()
        gc.disable()
        self.start_ns = time.perf_counter_ns()
        return self
    
    def __exit__(self, *args):
        self.end_ns = time.perf_counter_ns()
        self.elapsed_ns = self.end_ns - self.start_ns
        gc.enable()


@contextmanager
def memory_profiler():
    """Context manager for memory usage profiling."""
    tracemalloc.start()
    
    yield
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return current / 1024, peak / 1024  # Convert to KB


def warm_cache(func: Callable, *args, warmup_iterations: int = 100):
    """Warm up CPU caches by running function multiple times."""
    for _ in range(warmup_iterations):
        func(*args)


def benchmark_function(
    func: Callable,
    args: tuple = (),
    iterations: int = 10000,
    warmup_iterations: int = 100,
    name: Optional[str] = None
) -> BenchmarkResult:
    """
    Benchmark a function with high precision timing and memory profiling.
    
    Args:
        func: Function to benchmark
        args: Arguments to pass to function
        iterations: Number of iterations for timing
        warmup_iterations: Number of warmup iterations
        name: Optional name for the benchmark
    
    Returns:
        BenchmarkResult with timing and memory statistics
    """
    name = name or func.__name__
    
    # Warm up caches
    warm_cache(func, *args, warmup_iterations=warmup_iterations)
    
    # Memory profiling
    tracemalloc.start()
    initial_memory = tracemalloc.get_traced_memory()[0]
    
    # Timing runs
    times_ns = []
    
    for _ in range(iterations):
        with HighPrecisionTimer() as timer:
            func(*args)
        times_ns.append(timer.elapsed_ns)
    
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return BenchmarkResult(
        name=name,
        times_ns=times_ns,
        memory_peak_kb=(peak_memory - initial_memory) / 1024,
        memory_current_kb=(current_memory - initial_memory) / 1024,
        iterations=iterations
    )


def compare_functions(
    functions: List[Tuple[Callable, str]],
    test_data: Any,
    iterations: int = 10000
) -> List[BenchmarkResult]:
    """
    Compare multiple functions with the same input data.
    
    Args:
        functions: List of (function, name) tuples
        test_data: Input data for all functions
        iterations: Number of iterations per function
    
    Returns:
        List of BenchmarkResult objects
    """
    results = []
    
    for func, name in functions:
        print(f"Benchmarking {name}...")
        result = benchmark_function(
            func,
            args=(test_data,) if not isinstance(test_data, tuple) else test_data,
            iterations=iterations,
            name=name
        )
        results.append(result)
        
        # Print summary
        print(f"  Mean: {result.mean_ns/1000:.2f} μs")
        print(f"  Std:  {result.std_ns/1000:.2f} μs")
        print(f"  Memory: {result.memory_peak_kb:.2f} KB")
        print()
    
    return results


def plot_benchmark_results(
    results: List[BenchmarkResult],
    title: str = "Benchmark Comparison",
    save_path: Optional[str] = None
):
    """Create visualization of benchmark results."""
    # Set up the plot style
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    
    names = [r.name for r in results]
    
    # Plot 1: Mean execution time with error bars
    means = [r.mean_ns / 1000 for r in results]  # Convert to microseconds
    stds = [r.std_ns / 1000 for r in results]
    
    ax1.bar(names, means, yerr=stds, capsize=5, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Execution Time (μs)')
    ax1.set_title('Mean Execution Time')
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Distribution boxplot
    all_times = [np.array(r.times_ns) / 1000 for r in results]
    ax2.boxplot(all_times, labels=names, showfliers=False)
    ax2.set_ylabel('Execution Time (μs)')
    ax2.set_title('Time Distribution')
    ax2.tick_params(axis='x', rotation=45)
    
    # Plot 3: Memory usage
    memory_usage = [r.memory_peak_kb for r in results]
    ax3.bar(names, memory_usage, alpha=0.7, color='orange', edgecolor='black')
    ax3.set_ylabel('Peak Memory (KB)')
    ax3.set_title('Memory Usage')
    ax3.tick_params(axis='x', rotation=45)
    
    plt.suptitle(title, fontsize=16)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()


def create_performance_report(
    results: List[BenchmarkResult],
    output_path: str = "performance_report.json"
):
    """Generate a detailed performance report in JSON format."""
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'system_info': {
            'cpu_count': os.cpu_count(),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A',
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': os.sys.version
        },
        'benchmarks': [r.to_dict() for r in results],
        'summary': {
            'fastest': min(results, key=lambda r: r.mean_ns).name,
            'most_memory_efficient': min(results, key=lambda r: r.memory_peak_kb).name,
            'most_consistent': min(results, key=lambda r: r.std_ns).name
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


# Example usage and testing
if __name__ == "__main__":
    import math
    import numpy as np
    
    # Test functions
    def test_math_sqrt(x):
        return 1.0 / math.sqrt(x)
    
    def test_numpy_sqrt(x):
        return 1.0 / np.sqrt(x)
    
    # Generate test data
    test_value = 2.0
    
    # Run benchmarks
    print("Running nanosecond precision benchmarks...")
    results = compare_functions(
        [
            (test_math_sqrt, "math.sqrt"),
            (test_numpy_sqrt, "numpy.sqrt"),
        ],
        test_value,
        iterations=100000
    )
    
    # Visualize results
    plot_benchmark_results(results, "Fast Inverse Square Root Benchmarks")
    
    # Generate report
    report = create_performance_report(results, "benchmark_results.json")
    print(f"\nPerformance report saved to benchmark_results.json")
    print(f"Fastest implementation: {report['summary']['fastest']}")
    
    # Demonstrate statistical analysis
    print("\nDetailed Statistics:")
    for result in results:
        print(f"\n{result.name}:")
        print(f"  Mean: {result.mean_ns:,.0f} ns ({result.mean_ns/1000:.2f} μs)")
        print(f"  Median: {result.median_ns:,.0f} ns")
        print(f"  95th percentile: {result.p95_ns:,.0f} ns")
        print(f"  99th percentile: {result.p99_ns:,.0f} ns")
        print(f"  Std deviation: {result.std_ns:,.0f} ns")
        print(f"  Min-Max range: {result.min_ns:,.0f} - {result.max_ns:,.0f} ns")

print("Benchmark setup complete")