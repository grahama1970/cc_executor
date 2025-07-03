#!/usr/bin/env python3
"""
Example component showing how to save raw responses in usage functions.
"""

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


if __name__ == "__main__":
    # Import the usage helper
    from usage_helper import capture_usage_output
    
    # Use context manager to automatically capture and save output
    with capture_usage_output(__file__) as capture:
        print("=== Simple Math Component Usage ===\n")
        
        # Test addition
        print("--- Test 1: Addition ---")
        result1 = add_numbers(5, 3)
        capture.add_result('addition', result1)
        print(f"5 + 3 = {result1}")
        assert result1 == 8, "Addition failed"
        print("✓ Addition test passed")
        
        # Test multiplication
        print("\n--- Test 2: Multiplication ---")
        result2 = multiply_numbers(4, 7)
        capture.add_result('multiplication', result2)
        print(f"4 × 7 = {result2}")
        assert result2 == 28, "Multiplication failed"
        print("✓ Multiplication test passed")
        
        # Summary
        print("\n✅ All tests passed!")
    
    # The output is automatically saved and the save location is printed