def add_numbers(a, b):
    """Add two numbers and return the result."""
    return a + b


if __name__ == "__main__":
    # Test with real data
    result = add_numbers(5, 3)
    print(f"Result: {result}")
    assert result == 8, "Addition failed"
    
    result2 = add_numbers(10.5, 2.5)
    print(f"Result: {result2}")
    assert result2 == 13.0, "Float addition failed"
    
    result3 = add_numbers(-5, 3)
    print(f"Result: {result3}")
    assert result3 == -2, "Negative number addition failed"
    
    print("All tests passed!")