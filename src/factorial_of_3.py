def factorial(n):
    """Calculate the factorial of a number."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    elif n == 0 or n == 1:
        return 1
    else:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result


if __name__ == "__main__":
    # Calculate factorial of 3
    result = factorial(3)
    print(f"Factorial of 3 is: {result}")
    assert result == 6, f"Expected 6, but got {result}"
    print("✓ Test passed!")