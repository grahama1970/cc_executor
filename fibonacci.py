"""
Fibonacci sequence calculator module.

This module provides a function to calculate Fibonacci numbers up to n terms.
"""

from typing import List


def calculate_fibonacci(n: int) -> List[int]:
    """
    Calculate the Fibonacci sequence up to n terms.
    
    The Fibonacci sequence is a series of numbers where each number is the sum
    of the two preceding ones, starting from 0 and 1.
    
    Args:
        n: The number of terms to calculate. Must be a positive integer.
    
    Returns:
        A list containing the first n terms of the Fibonacci sequence.
    
    Raises:
        TypeError: If n is not an integer.
        ValueError: If n is less than or equal to 0.
    
    Examples:
        >>> calculate_fibonacci(1)
        [0]
        
        >>> calculate_fibonacci(2)
        [0, 1]
        
        >>> calculate_fibonacci(5)
        [0, 1, 1, 2, 3]
        
        >>> calculate_fibonacci(10)
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
        
        >>> calculate_fibonacci(0)
        Traceback (most recent call last):
            ...
        ValueError: Number of terms must be a positive integer, got 0
        
        >>> calculate_fibonacci("5")
        Traceback (most recent call last):
            ...
        TypeError: Number of terms must be an integer, got <class 'str'>
    """
    # Type validation
    if not isinstance(n, int):
        raise TypeError(f"Number of terms must be an integer, got {type(n)}")
    
    # Value validation
    if n <= 0:
        raise ValueError(f"Number of terms must be a positive integer, got {n}")
    
    # Handle edge cases
    if n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    # Calculate Fibonacci sequence
    fibonacci_sequence: List[int] = [0, 1]
    
    for i in range(2, n):
        next_term = fibonacci_sequence[i - 1] + fibonacci_sequence[i - 2]
        fibonacci_sequence.append(next_term)
    
    return fibonacci_sequence


def working_usage() -> None:
    """
    Demonstrate proper usage of the Fibonacci calculator.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    print("Fibonacci Sequence Calculator Demo")
    print("=" * 40)
    
    # Test various inputs
    test_cases = [1, 2, 5, 10, 15]
    
    for n in test_cases:
        result = calculate_fibonacci(n)
        print(f"First {n} terms: {result}")
    
    print("\nError handling examples:")
    
    # Test error cases
    error_cases = [
        (0, "Zero terms"),
        (-5, "Negative terms"),
        (3.14, "Float input"),
        ("10", "String input"),
        (None, "None input")
    ]
    
    for value, description in error_cases:
        try:
            calculate_fibonacci(value)
        except (TypeError, ValueError) as e:
            print(f"{description}: {type(e).__name__} - {e}")


def debug_function() -> None:
    """
    Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Testing performance with larger values
    import time
    
    print("Performance testing with larger values:")
    
    test_values = [10, 50, 100, 500, 1000]
    
    for n in test_values:
        start_time = time.time()
        result = calculate_fibonacci(n)
        end_time = time.time()
        
        print(f"n={n}: Generated {len(result)} terms in {end_time - start_time:.6f} seconds")
        print(f"  Last 3 terms: {result[-3:]}")
        print(f"  Largest value: {result[-1]:,}")
        print()


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        debug_function()
    else:
        print("Running working usage mode...")
        working_usage()