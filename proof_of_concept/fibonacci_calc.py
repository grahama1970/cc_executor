#!/usr/bin/env python3
"""Calculate Fibonacci numbers."""


def fibonacci(n):
    """
    Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    
    if n <= 1:
        return n
    
    # Use iterative approach for efficiency
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b


def fibonacci_sequence(count):
    """
    Generate a list of Fibonacci numbers.
    
    Args:
        count: Number of Fibonacci numbers to generate
        
    Returns:
        List of the first 'count' Fibonacci numbers
    """
    if count <= 0:
        return []
    
    sequence = []
    for i in range(count):
        sequence.append(fibonacci(i))
    
    return sequence


if __name__ == "__main__":
    # Demonstrate usage with real data
    print("First 10 Fibonacci numbers:")
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")
    
    print("\nFibonacci sequence (first 15 numbers):")
    sequence = fibonacci_sequence(15)
    print(sequence)
    
    # Verify some known values
    assert fibonacci(0) == 0, "F(0) should be 0"
    assert fibonacci(1) == 1, "F(1) should be 1"
    assert fibonacci(10) == 55, "F(10) should be 55"
    assert fibonacci(20) == 6765, "F(20) should be 6765"
    
    print("\nAll assertions passed!")