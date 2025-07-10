#!/usr/bin/env python3
"""Fibonacci number calculator."""


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
    
    # Iterative approach for efficiency
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b


def fibonacci_sequence(count):
    """
    Generate a sequence of Fibonacci numbers.
    
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
    result = fibonacci_sequence(10)
    print(f"Result: {result}")
    assert result == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34], "Fibonacci sequence incorrect"
    
    print("\n15th Fibonacci number (0-indexed):")
    fib_15 = fibonacci(15)
    print(f"Result: {fib_15}")
    assert fib_15 == 610, "15th Fibonacci number incorrect"
    
    print("\nAll tests passed!")