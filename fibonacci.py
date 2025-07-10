def fibonacci(n, memo={}):
    """Calculate nth fibonacci number with memoization.
    
    Args:
        n: The position in sequence (0-indexed)
        memo: Dictionary to store previously calculated values
        
    Returns:
        The nth fibonacci number
    """
    if n in memo:
        return memo[n]
    
    if n <= 1:
        return n
    
    memo[n] = fibonacci(n - 1, memo) + fibonacci(n - 2, memo)
    return memo[n]


if __name__ == "__main__":
    # Test the function
    result = fibonacci(10)
    print(f"fibonacci(10) = {result}")  # Should print 55
    
    # Test a few more values
    for i in range(15):
        print(f"fibonacci({i}) = {fibonacci(i)}")