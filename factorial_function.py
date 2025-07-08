#!/usr/bin/env python3
"""
Factorial calculation utility.

This module provides a function to calculate the factorial of a non-negative integer.
The factorial of n (denoted as n!) is the product of all positive integers less than or equal to n.
"""

from typing import Union


def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer.
    
    The factorial of n is defined as:
    - 0! = 1
    - n! = n × (n-1) × (n-2) × ... × 1 for n > 0
    
    Args:
        n: A non-negative integer to calculate the factorial of.
        
    Returns:
        The factorial of n.
        
    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.
        
    Examples:
        >>> factorial(0)
        1
        >>> factorial(5)
        120
        >>> factorial(10)
        3628800
    """
    # Type validation
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}")
    
    # Value validation
    if n < 0:
        raise ValueError(f"Factorial is not defined for negative numbers: {n}")
    
    # Base case: 0! = 1
    if n == 0:
        return 1
    
    # Calculate factorial iteratively (more efficient than recursion for large n)
    result = 1
    for i in range(1, n + 1):
        result *= i
    
    return result


def factorial_recursive(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer using recursion.
    
    This is an alternative implementation using recursion. Note that this
    approach may hit Python's recursion limit for large values of n.
    
    Args:
        n: A non-negative integer to calculate the factorial of.
        
    Returns:
        The factorial of n.
        
    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.
    """
    # Type validation
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}")
    
    # Value validation
    if n < 0:
        raise ValueError(f"Factorial is not defined for negative numbers: {n}")
    
    # Base case
    if n <= 1:
        return 1
    
    # Recursive case
    return n * factorial_recursive(n - 1)


if __name__ == "__main__":
    # Test the factorial function with real data
    test_values = [0, 1, 5, 10, 15, 20]
    
    print("Factorial calculations (iterative):")
    print("-" * 40)
    for n in test_values:
        result = factorial(n)
        print(f"{n}! = {result:,}")
    
    print("\nFactorial calculations (recursive):")
    print("-" * 40)
    for n in test_values[:5]:  # Limit recursive tests to smaller values
        result = factorial_recursive(n)
        print(f"{n}! = {result:,}")
    
    # Test error handling
    print("\nError handling tests:")
    print("-" * 40)
    
    try:
        factorial(-1)
    except ValueError as e:
        print(f"ValueError caught: {e}")
    
    try:
        factorial(3.14)
    except TypeError as e:
        print(f"TypeError caught: {e}")
    
    # Verify some known factorials
    assert factorial(0) == 1, "0! should be 1"
    assert factorial(1) == 1, "1! should be 1"
    assert factorial(5) == 120, "5! should be 120"
    assert factorial(10) == 3628800, "10! should be 3,628,800"
    
    print("\nAll assertions passed! ✓")