#!/usr/bin/env python3
"""Fibonacci number calculator with error handling and usage examples."""


def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using iterative approach.
    
    The Fibonacci sequence is defined as:
    - F(0) = 0
    - F(1) = 1
    - F(n) = F(n-1) + F(n-2) for n > 1
    
    This implementation uses an iterative approach for efficiency,
    avoiding the exponential time complexity of naive recursion.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
        
    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError(f"Input must be non-negative, got {n}")
    
    if n <= 1:
        return n
    
    # Iterative calculation for efficiency
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    
    return curr


if __name__ == "__main__":
    # Usage examples
    print("Fibonacci Number Calculator")
    print("-" * 30)
    
    # Example 1: Calculate first 10 Fibonacci numbers
    print("\nFirst 10 Fibonacci numbers:")
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")
    
    # Example 2: Calculate specific Fibonacci numbers
    print("\nSpecific examples:")
    test_values = [15, 20, 30]
    for n in test_values:
        result = fibonacci(n)
        print(f"F({n}) = {result}")
    
    # Example 3: Error handling demonstration
    print("\nError handling:")
    try:
        result = fibonacci(-5)
    except ValueError as e:
        print(f"Error caught: {e}")
    
    # Example 4: Performance test with larger number
    print("\nPerformance test:")
    import time
    
    n = 100
    start_time = time.time()
    result = fibonacci(n)
    end_time = time.time()
    
    print(f"F({n}) = {result}")
    print(f"Calculation time: {(end_time - start_time) * 1000:.4f} ms")
    
    # Example 5: Verify known Fibonacci numbers
    print("\nVerification of known values:")
    known_fibs = {
        0: 0,
        1: 1,
        2: 1,
        3: 2,
        4: 3,
        5: 5,
        6: 8,
        7: 13,
        8: 21,
        9: 34
    }
    
    all_correct = True
    for n, expected in known_fibs.items():
        actual = fibonacci(n)
        status = "✓" if actual == expected else "✗"
        print(f"F({n}) = {actual} (expected {expected}) {status}")
        if actual != expected:
            all_correct = False
    
    print(f"\nAll verifications passed: {'Yes' if all_correct else 'No'}")