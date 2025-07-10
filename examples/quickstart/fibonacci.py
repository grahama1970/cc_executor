"""
Fibonacci number calculator with memoization.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python fibonacci.py          # Runs working_usage() - stable, known to work
  python fibonacci.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

def fibonacci(n: int, memo: dict = None) -> int:
    """
    Calculate the nth Fibonacci number using memoization.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        memo: Dictionary for memoization (created automatically if None)
    
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if memo is None:
        memo = {}
    
    if n < 0:
        raise ValueError("n must be non-negative")
    
    if n in memo:
        return memo[n]
    
    if n <= 1:
        return n
    
    memo[n] = fibonacci(n - 1, memo) + fibonacci(n - 2, memo)
    return memo[n]


def fibonacci_sequence(count: int) -> list[int]:
    """
    Generate the first 'count' Fibonacci numbers.
    
    Args:
        count: Number of Fibonacci numbers to generate
        
    Returns:
        List of the first 'count' Fibonacci numbers
    """
    if count <= 0:
        return []
    
    memo = {}
    return [fibonacci(i, memo) for i in range(count)]


def working_usage():
    """Demonstrate proper usage of the fibonacci function.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    # Calculate individual Fibonacci numbers
    print("Individual Fibonacci numbers:")
    for n in [0, 1, 5, 10, 20, 30]:
        result = fibonacci(n)
        print(f"F({n}) = {result}")
    
    print("\nFirst 15 Fibonacci numbers:")
    sequence = fibonacci_sequence(15)
    print(sequence)
    
    # Demonstrate memoization efficiency
    print("\nCalculating F(100) with memoization:")
    result = fibonacci(100)
    print(f"F(100) = {result}")
    
    return True


def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Testing edge cases and performance
    test_cases = [
        (0, 0),
        (1, 1),
        (2, 1),
        (10, 55),
        (50, 12586269025),
    ]
    
    print("Testing edge cases:")
    for n, expected in test_cases:
        result = fibonacci(n)
        status = "✓" if result == expected else "✗"
        print(f"{status} F({n}) = {result} (expected: {expected})")
    
    # Test error handling
    print("\nTesting error handling:")
    try:
        fibonacci(-1)
        print("✗ Should have raised ValueError for negative input")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
    
    # Performance comparison
    import time
    print("\nPerformance test - F(35):")
    
    # Without memoization (naive recursive approach)
    def fib_naive(n):
        if n <= 1:
            return n
        return fib_naive(n - 1) + fib_naive(n - 2)
    
    start = time.time()
    result_naive = fib_naive(35)
    time_naive = time.time() - start
    
    start = time.time()
    result_memo = fibonacci(35)
    time_memo = time.time() - start
    
    print(f"Naive approach: {result_naive} in {time_naive:.4f} seconds")
    print(f"With memoization: {result_memo} in {time_memo:.4f} seconds")
    print(f"Speedup: {time_naive/time_memo:.0f}x faster")


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