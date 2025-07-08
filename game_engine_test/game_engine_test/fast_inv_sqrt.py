#!/usr/bin/env python3
"""
Fast Inverse Square Root Algorithm Implementations
Comparing the classic Quake III method with modern optimized versions
"""

import struct
import time
import numpy as np
from typing import List, Tuple
import math
import matplotlib.pyplot as plt


def fast_inverse_sqrt_classic(number: float) -> float:
    """
    Classic Quake III fast inverse square root implementation.
    Uses the famous magic number 0x5f3759df.
    """
    threehalfs = 1.5
    x2 = number * 0.5
    
    # Convert float to 32-bit integer representation
    i = struct.unpack('>I', struct.pack('>f', number))[0]
    
    # The famous magic number
    i = 0x5f3759df - (i >> 1)
    
    # Convert back to float
    y = struct.unpack('>f', struct.pack('>I', i))[0]
    
    # Newton-Raphson iteration (once is usually enough)
    y = y * (threehalfs - (x2 * y * y))
    
    return y


class FastInvSqrtLookup:
    """
    Modern optimized version using lookup tables for common ranges.
    """
    def __init__(self, table_size: int = 1024):
        self.table_size = table_size
        self.lookup_table = {}
        self._build_lookup_table()
    
    def _build_lookup_table(self):
        """Build lookup table for common values."""
        # Create lookup table for values from 0.1 to 100
        for i in range(self.table_size):
            value = 0.1 + (i / self.table_size) * 99.9
            self.lookup_table[i] = 1.0 / (value ** 0.5)
    
    def _get_table_index(self, number: float) -> int:
        """Get the closest lookup table index for a number."""
        if number < 0.1:
            return 0
        if number > 100:
            return self.table_size - 1
        
        normalized = (number - 0.1) / 99.9
        index = int(normalized * (self.table_size - 1))
        return min(index, self.table_size - 1)
    
    def fast_inverse_sqrt_lookup(self, number: float) -> float:
        """
        Fast inverse square root using lookup table with interpolation.
        """
        if number <= 0:
            return float('inf')
        
        # For values outside our table range, fall back to classic method
        if number < 0.1 or number > 100:
            return fast_inverse_sqrt_classic(number)
        
        # Get table index
        idx = self._get_table_index(number)
        
        # Get base value from lookup table
        base_value = self.lookup_table[idx]
        
        # Apply one Newton-Raphson iteration for refinement
        x2 = number * 0.5
        base_value = base_value * (1.5 - (x2 * base_value * base_value))
        
        return base_value


def standard_inverse_sqrt(number: float) -> float:
    """Standard Python implementation for comparison."""
    return 1.0 / (number ** 0.5)


def fast_inverse_sqrt_optimized(number: float) -> float:
    """
    Optimized version with better magic number and two iterations.
    Uses magic number 0x5f375a86 which gives better initial approximation.
    """
    threehalfs = 1.5
    x2 = number * 0.5
    
    # Convert float to 32-bit integer representation
    i = struct.unpack('>I', struct.pack('>f', number))[0]
    
    # Better magic number (Chris Lomont's analysis)
    i = 0x5f375a86 - (i >> 1)
    
    # Convert back to float
    y = struct.unpack('>f', struct.pack('>I', i))[0]
    
    # Two Newton-Raphson iterations for better accuracy
    y = y * (threehalfs - (x2 * y * y))
    y = y * (threehalfs - (x2 * y * y))
    
    return y


def benchmark_implementations(test_values: List[float], iterations: int = 100000) -> dict:
    """
    Benchmark all implementations and return timing results.
    """
    results = {
        'standard': 0.0,
        'math_module': 0.0,
        'classic': 0.0,
        'optimized': 0.0,
        'lookup': 0.0
    }
    
    # Initialize lookup table
    lookup_impl = FastInvSqrtLookup()
    
    # Benchmark standard implementation
    start = time.perf_counter()
    for _ in range(iterations):
        for val in test_values:
            _ = standard_inverse_sqrt(val)
    results['standard'] = time.perf_counter() - start
    
    # Benchmark math module (for reference)
    start = time.perf_counter()
    for _ in range(iterations):
        for val in test_values:
            _ = 1.0 / math.sqrt(val)
    results['math_module'] = time.perf_counter() - start
    
    # Benchmark classic implementation
    start = time.perf_counter()
    for _ in range(iterations):
        for val in test_values:
            _ = fast_inverse_sqrt_classic(val)
    results['classic'] = time.perf_counter() - start
    
    # Benchmark optimized implementation
    start = time.perf_counter()
    for _ in range(iterations):
        for val in test_values:
            _ = fast_inverse_sqrt_optimized(val)
    results['optimized'] = time.perf_counter() - start
    
    # Benchmark lookup table implementation
    start = time.perf_counter()
    for _ in range(iterations):
        for val in test_values:
            _ = lookup_impl.fast_inverse_sqrt_lookup(val)
    results['lookup'] = time.perf_counter() - start
    
    return results


def calculate_accuracy(test_values: List[float]) -> dict:
    """
    Calculate accuracy of each implementation compared to standard.
    """
    lookup_impl = FastInvSqrtLookup()
    
    errors = {
        'classic': [],
        'optimized': [],
        'lookup': []
    }
    
    for val in test_values:
        standard_result = standard_inverse_sqrt(val)
        
        # Classic implementation error
        classic_result = fast_inverse_sqrt_classic(val)
        classic_error = abs(classic_result - standard_result) / standard_result * 100
        errors['classic'].append(classic_error)
        
        # Optimized implementation error
        optimized_result = fast_inverse_sqrt_optimized(val)
        optimized_error = abs(optimized_result - standard_result) / standard_result * 100
        errors['optimized'].append(optimized_error)
        
        # Lookup implementation error
        lookup_result = lookup_impl.fast_inverse_sqrt_lookup(val)
        lookup_error = abs(lookup_result - standard_result) / standard_result * 100
        errors['lookup'].append(lookup_error)
    
    return {
        'classic_avg_error': np.mean(errors['classic']),
        'classic_max_error': np.max(errors['classic']),
        'optimized_avg_error': np.mean(errors['optimized']),
        'optimized_max_error': np.max(errors['optimized']),
        'lookup_avg_error': np.mean(errors['lookup']),
        'lookup_max_error': np.max(errors['lookup'])
    }


def main():
    """
    Main function to demonstrate and compare implementations.
    """
    print("Fast Inverse Square Root Algorithm Comparison")
    print("=" * 70)
    
    # Test with specific values
    test_values = [4.0, 9.0, 16.0, 25.0, 0.5, 2.0, 100.0]
    lookup_impl = FastInvSqrtLookup()
    
    print("\nExample calculations:")
    print(f"{'Value':<10} {'Standard':<15} {'Classic':<15} {'Optimized':<15} {'Lookup':<15}")
    print("-" * 70)
    
    for val in test_values:
        standard = standard_inverse_sqrt(val)
        classic = fast_inverse_sqrt_classic(val)
        optimized = fast_inverse_sqrt_optimized(val)
        lookup = lookup_impl.fast_inverse_sqrt_lookup(val)
        
        print(f"{val:<10.2f} {standard:<15.6f} {classic:<15.6f} {optimized:<15.6f} {lookup:<15.6f}")
    
    # Performance benchmark
    print("\nPerformance Benchmark")
    print("=" * 70)
    
    # Generate random test values
    np.random.seed(42)
    benchmark_values = np.random.uniform(0.1, 100.0, 10).tolist()
    
    print(f"Testing with {len(benchmark_values)} random values, 100,000 iterations")
    results = benchmark_implementations(benchmark_values)
    
    print(f"\nExecution times:")
    print(f"Standard (1/x**0.5):   {results['standard']:.4f} seconds")
    print(f"Math module:           {results['math_module']:.4f} seconds")
    print(f"Classic (Quake III):   {results['classic']:.4f} seconds")
    print(f"Optimized (2 iter):    {results['optimized']:.4f} seconds")
    print(f"Lookup Table:          {results['lookup']:.4f} seconds")
    
    print(f"\nSpeedup vs Standard:")
    fastest = min(results['standard'], results['math_module'])
    print(f"Classic:   {fastest/results['classic']:.2f}x")
    print(f"Optimized: {fastest/results['optimized']:.2f}x")
    print(f"Lookup:    {fastest/results['lookup']:.2f}x")
    
    # Accuracy comparison
    print("\nAccuracy Analysis")
    print("=" * 70)
    
    accuracy_results = calculate_accuracy(benchmark_values)
    print(f"Classic    - Average Error: {accuracy_results['classic_avg_error']:.4f}%, Max: {accuracy_results['classic_max_error']:.4f}%")
    print(f"Optimized  - Average Error: {accuracy_results['optimized_avg_error']:.6f}%, Max: {accuracy_results['optimized_max_error']:.6f}%")
    print(f"Lookup     - Average Error: {accuracy_results['lookup_avg_error']:.6f}%, Max: {accuracy_results['lookup_max_error']:.6f}%")
    
    # Magic number explanation
    print("\nAbout the Magic Numbers")
    print("=" * 70)
    print("0x5f3759df - Original Quake III magic number")
    print("0x5f375a86 - Chris Lomont's optimized constant (slightly better accuracy)")
    print("\nHow it works:")
    print("1. Treats float bits as integer for fast approximation")
    print("2. Uses bit shift to approximate log₂(x)/2")
    print("3. Magic number corrects for IEEE 754 format quirks")
    print("4. Newton-Raphson iteration(s) refine the result")
    print("\nNote: In Python, struct pack/unpack overhead makes it slower than")
    print("standard methods. The algorithm shines in C/C++ with direct memory access.")
    
    # Generate visualization
    print("\nGenerating visualization...")
    create_visualization()


def create_visualization():
    """Create visual comparison of the algorithms."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Test range
    x_values = np.linspace(0.1, 100, 1000)
    lookup_impl = FastInvSqrtLookup()
    
    # Calculate results
    standard_results = [standard_inverse_sqrt(x) for x in x_values]
    classic_results = [fast_inverse_sqrt_classic(x) for x in x_values]
    optimized_results = [fast_inverse_sqrt_optimized(x) for x in x_values]
    lookup_results = [lookup_impl.fast_inverse_sqrt_lookup(x) for x in x_values]
    
    # Plot 1: All implementations
    ax1.plot(x_values, standard_results, 'k-', label='Standard', linewidth=2)
    ax1.plot(x_values, classic_results, 'r--', label='Classic', alpha=0.7)
    ax1.plot(x_values, optimized_results, 'g-.', label='Optimized', alpha=0.7)
    ax1.plot(x_values, lookup_results, 'b:', label='Lookup', alpha=0.7)
    ax1.set_xlabel('Input Value')
    ax1.set_ylabel('1/√x')
    ax1.set_title('Fast Inverse Square Root Implementations')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Error comparison
    classic_errors = [abs((c - s) / s * 100) for c, s in zip(classic_results, standard_results)]
    optimized_errors = [abs((o - s) / s * 100) for o, s in zip(optimized_results, standard_results)]
    lookup_errors = [abs((l - s) / s * 100) for l, s in zip(lookup_results, standard_results)]
    
    ax2.semilogy(x_values, classic_errors, 'r-', label='Classic Error')
    ax2.semilogy(x_values, optimized_errors, 'g-', label='Optimized Error')
    ax2.semilogy(x_values, lookup_errors, 'b-', label='Lookup Error')
    ax2.set_xlabel('Input Value')
    ax2.set_ylabel('Error (%)')
    ax2.set_title('Relative Error Comparison (Log Scale)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Performance comparison bar chart
    methods = ['Math\nModule', 'Standard', 'Classic', 'Optimized', 'Lookup']
    test_vals = np.random.uniform(0.1, 100, 10).tolist()
    times = []
    
    # Quick benchmark
    iterations = 10000
    
    # Math module
    start = time.perf_counter()
    for _ in range(iterations):
        for v in test_vals:
            _ = 1.0 / math.sqrt(v)
    times.append(time.perf_counter() - start)
    
    # Standard
    start = time.perf_counter()
    for _ in range(iterations):
        for v in test_vals:
            _ = standard_inverse_sqrt(v)
    times.append(time.perf_counter() - start)
    
    # Classic
    start = time.perf_counter()
    for _ in range(iterations):
        for v in test_vals:
            _ = fast_inverse_sqrt_classic(v)
    times.append(time.perf_counter() - start)
    
    # Optimized
    start = time.perf_counter()
    for _ in range(iterations):
        for v in test_vals:
            _ = fast_inverse_sqrt_optimized(v)
    times.append(time.perf_counter() - start)
    
    # Lookup
    start = time.perf_counter()
    for _ in range(iterations):
        for v in test_vals:
            _ = lookup_impl.fast_inverse_sqrt_lookup(v)
    times.append(time.perf_counter() - start)
    
    bars = ax3.bar(methods, times, color=['blue', 'gray', 'red', 'green', 'orange'])
    ax3.set_ylabel('Time (seconds)')
    ax3.set_title(f'Performance Comparison ({iterations} iterations)')
    ax3.grid(True, axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar, time_val in zip(bars, times):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{time_val:.3f}s', ha='center', va='bottom')
    
    # Plot 4: Zoomed error view for optimized methods
    x_zoom = np.linspace(1, 10, 200)
    standard_zoom = [standard_inverse_sqrt(x) for x in x_zoom]
    optimized_zoom = [fast_inverse_sqrt_optimized(x) for x in x_zoom]
    lookup_zoom = [lookup_impl.fast_inverse_sqrt_lookup(x) for x in x_zoom]
    
    optimized_errors_zoom = [abs((o - s) / s * 100) for o, s in zip(optimized_zoom, standard_zoom)]
    lookup_errors_zoom = [abs((l - s) / s * 100) for l, s in zip(lookup_zoom, standard_zoom)]
    
    ax4.plot(x_zoom, optimized_errors_zoom, 'g-', label='Optimized', linewidth=2)
    ax4.plot(x_zoom, lookup_errors_zoom, 'b-', label='Lookup', linewidth=2)
    ax4.set_xlabel('Input Value')
    ax4.set_ylabel('Error (%)')
    ax4.set_title('Detailed Error View (1-10 range)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('game_engine_test/fast_inv_sqrt_comparison.png', dpi=150)
    print("Visualization saved to: game_engine_test/fast_inv_sqrt_comparison.png")
    plt.close()


if __name__ == "__main__":
    main()