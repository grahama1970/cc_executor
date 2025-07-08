"""
Performance Benchmark Suite for Fast Inverse Square Root Algorithms
===================================================================

This module provides comprehensive benchmarks comparing:
1. Original Quake III algorithm
2. Improved Quake III algorithm (Lomont's constant)
3. Novel lookup table-based algorithm
4. Standard library 1/sqrt(x)
5. NumPy's vectorized operations

The benchmarks measure:
- Execution time
- Accuracy (absolute and relative error)
- Cache efficiency
- Vectorization performance
"""

import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, Dict, List, Tuple
import pandas as pd
from functools import wraps
import gc

# Import our implementations
from original_fast_inverse_sqrt import (
    original_fast_inverse_sqrt,
    original_fast_inverse_sqrt_improved
)
from novel_fast_inverse_sqrt import (
    NovelFastInverseSqrt,
    novel_hybrid_inverse_sqrt
)


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()  # Clear garbage before timing
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    return wrapper


class InverseSqrtBenchmark:
    """Comprehensive benchmark suite for inverse square root algorithms."""
    
    def __init__(self):
        """Initialize benchmark suite with test data."""
        # Initialize novel algorithm
        self.novel_algo = NovelFastInverseSqrt()
        
        # Generate test datasets
        self._generate_test_data()
        
        # Store results
        self.results = {
            'timing': {},
            'accuracy': {},
            'vectorization': {}
        }
        
    def _generate_test_data(self):
        """Generate various test datasets for benchmarking."""
        np.random.seed(42)  # Reproducible results
        
        self.test_data = {
            # Small numbers (common in normalization)
            'small': np.random.uniform(0.001, 1.0, size=10000),
            
            # Medium range (typical game physics)
            'medium': np.random.uniform(1.0, 100.0, size=10000),
            
            # Large numbers
            'large': np.random.uniform(100.0, 10000.0, size=10000),
            
            # Mixed range (realistic scenario)
            'mixed': np.concatenate([
                np.random.uniform(0.001, 1.0, size=3333),
                np.random.uniform(1.0, 100.0, size=3334),
                np.random.uniform(100.0, 10000.0, size=3333)
            ]),
            
            # Edge cases
            'edge': np.array([0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0])
        }
        
    @timing_decorator
    def benchmark_standard(self, data: np.ndarray) -> np.ndarray:
        """Benchmark standard 1/sqrt(x) implementation."""
        return 1.0 / np.sqrt(data)
    
    @timing_decorator
    def benchmark_original_quake(self, data: np.ndarray) -> np.ndarray:
        """Benchmark original Quake III algorithm."""
        return np.array([original_fast_inverse_sqrt(x) for x in data])
    
    @timing_decorator
    def benchmark_improved_quake(self, data: np.ndarray) -> np.ndarray:
        """Benchmark improved Quake III algorithm."""
        return np.array([original_fast_inverse_sqrt_improved(x) for x in data])
    
    @timing_decorator
    def benchmark_novel_single(self, data: np.ndarray) -> np.ndarray:
        """Benchmark novel algorithm (single value mode)."""
        return np.array([self.novel_algo.novel_inverse_sqrt(x) for x in data])
    
    @timing_decorator
    def benchmark_novel_vectorized(self, data: np.ndarray) -> np.ndarray:
        """Benchmark novel algorithm (vectorized mode)."""
        return NovelFastInverseSqrt.vectorized_inverse_sqrt(data)
    
    def run_timing_benchmarks(self):
        """Run timing benchmarks on all algorithms."""
        algorithms = {
            'Standard (1/sqrt)': self.benchmark_standard,
            'Original Quake III': self.benchmark_original_quake,
            'Improved Quake III': self.benchmark_improved_quake,
            'Novel (Single)': self.benchmark_novel_single,
            'Novel (Vectorized)': self.benchmark_novel_vectorized
        }
        
        print("Running Timing Benchmarks")
        print("=" * 80)
        
        for dataset_name, data in self.test_data.items():
            if dataset_name == 'edge':
                continue  # Skip edge cases for timing
                
            print(f"\nDataset: {dataset_name} (size: {len(data)})")
            print("-" * 40)
            
            self.results['timing'][dataset_name] = {}
            
            for algo_name, algo_func in algorithms.items():
                # Skip vectorized for very small datasets
                if 'Vectorized' in algo_name and len(data) < 100:
                    continue
                    
                # Run benchmark
                result, exec_time = algo_func(data)
                
                # Store results
                self.results['timing'][dataset_name][algo_name] = {
                    'time': exec_time,
                    'ops_per_second': len(data) / exec_time
                }
                
                print(f"{algo_name:20}: {exec_time:8.4f}s ({len(data)/exec_time:12.0f} ops/sec)")
        
    def run_accuracy_benchmarks(self):
        """Measure accuracy of each algorithm."""
        print("\n\nRunning Accuracy Benchmarks")
        print("=" * 80)
        
        # Use edge cases for accuracy testing
        test_values = self.test_data['edge']
        true_values = 1.0 / np.sqrt(test_values)
        
        algorithms = {
            'Original Quake III': lambda x: original_fast_inverse_sqrt(x),
            'Improved Quake III': lambda x: original_fast_inverse_sqrt_improved(x),
            'Novel Algorithm': lambda x: self.novel_algo.novel_inverse_sqrt(x),
        }
        
        self.results['accuracy'] = {}
        
        for algo_name, algo_func in algorithms.items():
            errors = []
            rel_errors = []
            
            for x, true_val in zip(test_values, true_values):
                approx = algo_func(x)
                error = abs(approx - true_val)
                rel_error = error / true_val * 100
                
                errors.append(error)
                rel_errors.append(rel_error)
            
            self.results['accuracy'][algo_name] = {
                'mean_error': np.mean(errors),
                'max_error': np.max(errors),
                'mean_rel_error': np.mean(rel_errors),
                'max_rel_error': np.max(rel_errors)
            }
            
            print(f"\n{algo_name}:")
            print(f"  Mean Error: {np.mean(errors):.6f}")
            print(f"  Max Error:  {np.max(errors):.6f}")
            print(f"  Mean Relative Error: {np.mean(rel_errors):.3f}%")
            print(f"  Max Relative Error:  {np.max(rel_errors):.3f}%")
    
    def plot_results(self):
        """Generate visualization of benchmark results."""
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Fast Inverse Square Root Algorithm Benchmarks', fontsize=16)
        
        # Plot 1: Timing comparison
        ax1 = axes[0, 0]
        datasets = ['small', 'medium', 'large', 'mixed']
        algorithms = ['Standard (1/sqrt)', 'Original Quake III', 'Improved Quake III', 
                     'Novel (Single)', 'Novel (Vectorized)']
        
        timing_data = []
        for dataset in datasets:
            row = []
            for algo in algorithms:
                if algo in self.results['timing'].get(dataset, {}):
                    row.append(self.results['timing'][dataset][algo]['ops_per_second'])
                else:
                    row.append(0)
            timing_data.append(row)
        
        x = np.arange(len(datasets))
        width = 0.15
        
        for i, algo in enumerate(algorithms):
            values = [timing_data[j][i] for j in range(len(datasets))]
            ax1.bar(x + i * width, values, width, label=algo)
        
        ax1.set_xlabel('Dataset')
        ax1.set_ylabel('Operations per Second')
        ax1.set_title('Performance Comparison')
        ax1.set_xticks(x + width * 2)
        ax1.set_xticklabels(datasets)
        ax1.legend()
        ax1.set_yscale('log')
        
        # Plot 2: Accuracy comparison
        ax2 = axes[0, 1]
        accuracy_algos = list(self.results['accuracy'].keys())
        mean_errors = [self.results['accuracy'][algo]['mean_rel_error'] 
                      for algo in accuracy_algos]
        
        ax2.bar(accuracy_algos, mean_errors)
        ax2.set_xlabel('Algorithm')
        ax2.set_ylabel('Mean Relative Error (%)')
        ax2.set_title('Accuracy Comparison')
        ax2.tick_params(axis='x', rotation=45)
        
        # Plot 3: Error distribution
        ax3 = axes[1, 0]
        test_range = np.logspace(-3, 3, 100)
        
        for algo_name, algo_func in [
            ('Original Quake', original_fast_inverse_sqrt),
            ('Improved Quake', original_fast_inverse_sqrt_improved),
            ('Novel', self.novel_algo.novel_inverse_sqrt)
        ]:
            errors = []
            for x in test_range:
                approx = algo_func(x)
                true_val = 1.0 / np.sqrt(x)
                rel_error = abs(approx - true_val) / true_val * 100
                errors.append(rel_error)
            
            ax3.semilogx(test_range, errors, label=algo_name)
        
        ax3.set_xlabel('Input Value')
        ax3.set_ylabel('Relative Error (%)')
        ax3.set_title('Error Distribution Across Input Range')
        ax3.legend()
        ax3.grid(True)
        
        # Plot 4: Speedup comparison
        ax4 = axes[1, 1]
        baseline = 'Standard (1/sqrt)'
        speedups = {}
        
        for dataset in datasets:
            speedups[dataset] = {}
            baseline_time = self.results['timing'][dataset][baseline]['time']
            
            for algo in algorithms:
                if algo != baseline and algo in self.results['timing'][dataset]:
                    algo_time = self.results['timing'][dataset][algo]['time']
                    speedups[dataset][algo] = baseline_time / algo_time
        
        # Plot speedups
        for i, dataset in enumerate(datasets):
            values = []
            labels = []
            for algo, speedup in speedups[dataset].items():
                values.append(speedup)
                labels.append(algo)
            
            if i == 0:
                ax4.bar(np.arange(len(values)) + i * 0.2, values, 0.2, 
                       label=dataset)
            else:
                ax4.bar(np.arange(len(values)) + i * 0.2, values, 0.2, 
                       label=dataset)
        
        ax4.set_xlabel('Algorithm')
        ax4.set_ylabel('Speedup vs Standard')
        ax4.set_title('Speedup Comparison (Higher is Better)')
        ax4.legend()
        ax4.axhline(y=1, color='r', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig('game_engine_test_prompt/benchmark_results.png', dpi=150)
        print("\nBenchmark visualization saved to benchmark_results.png")
    
    def generate_report(self):
        """Generate a comprehensive benchmark report."""
        report = []
        report.append("Fast Inverse Square Root Algorithm Benchmark Report")
        report.append("=" * 70)
        report.append("\nEXECUTIVE SUMMARY")
        report.append("-" * 70)
        
        # Find best performing algorithm
        best_speed = {}
        for dataset in ['small', 'medium', 'large', 'mixed']:
            max_ops = 0
            best_algo = ''
            for algo, data in self.results['timing'][dataset].items():
                if data['ops_per_second'] > max_ops:
                    max_ops = data['ops_per_second']
                    best_algo = algo
            best_speed[dataset] = (best_algo, max_ops)
        
        report.append("\nBest Performing Algorithms by Dataset:")
        for dataset, (algo, ops) in best_speed.items():
            report.append(f"  {dataset:10}: {algo} ({ops:,.0f} ops/sec)")
        
        # Accuracy summary
        report.append("\n\nAccuracy Summary (Mean Relative Error):")
        for algo, data in self.results['accuracy'].items():
            report.append(f"  {algo:20}: {data['mean_rel_error']:.3f}%")
        
        # Detailed results
        report.append("\n\nDETAILED RESULTS")
        report.append("-" * 70)
        
        # Performance table
        report.append("\nPerformance Results (operations/second):")
        report.append("\n" + "-" * 90)
        report.append(f"{'Algorithm':<25} {'Small':<15} {'Medium':<15} {'Large':<15} {'Mixed':<15}")
        report.append("-" * 90)
        
        for algo in ['Standard (1/sqrt)', 'Original Quake III', 'Improved Quake III', 
                    'Novel (Single)', 'Novel (Vectorized)']:
            row = f"{algo:<25}"
            for dataset in ['small', 'medium', 'large', 'mixed']:
                if algo in self.results['timing'].get(dataset, {}):
                    ops = self.results['timing'][dataset][algo]['ops_per_second']
                    row += f" {ops:>14,.0f}"
                else:
                    row += f" {'N/A':>14}"
            report.append(row)
        
        # Save report
        with open('game_engine_test_prompt/benchmark_report.txt', 'w') as f:
            f.write('\n'.join(report))
        
        print("\nDetailed report saved to benchmark_report.txt")
        
        return '\n'.join(report)


def main():
    """Run the complete benchmark suite."""
    print("Fast Inverse Square Root Algorithm Benchmark Suite")
    print("=" * 80)
    
    # Create and run benchmarks
    benchmark = InverseSqrtBenchmark()
    
    # Run all benchmarks
    benchmark.run_timing_benchmarks()
    benchmark.run_accuracy_benchmarks()
    
    # Generate visualizations
    benchmark.plot_results()
    
    # Generate report
    report = benchmark.generate_report()
    
    print("\n\nBenchmark Complete!")
    print("Files generated:")
    print("  - benchmark_results.png: Visual comparison of algorithms")
    print("  - benchmark_report.txt: Detailed performance report")
    
    # Completion marker
    print("\n\nResearch and benchmarking completed successfully!")


if __name__ == "__main__":
    main()