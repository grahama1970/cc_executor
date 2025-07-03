def factorial(n):
    """
    Calculate the factorial of a non-negative integer.
    
    Args:
        n: A non-negative integer
        
    Returns:
        The factorial of n (n!)
        
    Raises:
        ValueError: If n is negative
        TypeError: If n is not an integer
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    
    return result


if __name__ == "__main__":
    # Test the function with real data
    test_values = [0, 1, 5, 10, 20]
    
    for n in test_values:
        result = factorial(n)
        print(f"factorial({n}) = {result}")
    
    # Verify some known values
    assert factorial(0) == 1, "0! should be 1"
    assert factorial(1) == 1, "1! should be 1"
    assert factorial(5) == 120, "5! should be 120"
    assert factorial(10) == 3628800, "10! should be 3628800"
    
    print("\nAll tests passed!")