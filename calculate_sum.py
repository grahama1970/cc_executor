#!/usr/bin/env python3
"""
Simple function to calculate the sum of numbers.
"""

from typing import List, Union


def calculate_sum(numbers: List[Union[int, float]]) -> Union[int, float]:
    """
    Calculate the sum of a list of numbers.
    
    Args:
        numbers: List of integers or floats to sum
        
    Returns:
        The sum of all numbers in the list
    """
    return sum(numbers)


if __name__ == "__main__":
    # Test the function with real data
    test_data = [1, 2, 3, 4, 5]
    result = calculate_sum(test_data)
    print(f"Sum of {test_data} = {result}")
    assert result == 15, f"Expected 15, got {result}"
    
    # Test with floats
    float_data = [1.5, 2.5, 3.0]
    float_result = calculate_sum(float_data)
    print(f"Sum of {float_data} = {float_result}")
    assert float_result == 7.0, f"Expected 7.0, got {float_result}"
    
    print("All tests passed!")