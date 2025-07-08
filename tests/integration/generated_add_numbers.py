def add_numbers(a, b):
    """Add two numbers and return the result."""
    return a + b


if __name__ == "__main__":
    # Test the function with real data
    result1 = add_numbers(5, 3)
    print(f"5 + 3 = {result1}")
    assert result1 == 8, "Failed to add 5 + 3"
    
    result2 = add_numbers(10.5, 2.5)
    print(f"10.5 + 2.5 = {result2}")
    assert result2 == 13.0, "Failed to add 10.5 + 2.5"
    
    result3 = add_numbers(-4, 7)
    print(f"-4 + 7 = {result3}")
    assert result3 == 3, "Failed to add -4 + 7"
    
    print("All tests passed!")