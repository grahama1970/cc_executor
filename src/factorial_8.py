def factorial(n):
    """Calculate factorial of n"""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


if __name__ == "__main__":
    n = 8
    result = factorial(n)
    print(f"Factorial of {n} is {result}")
    assert result == 40320, f"Expected 40320, got {result}"
    print("✓ Test passed")