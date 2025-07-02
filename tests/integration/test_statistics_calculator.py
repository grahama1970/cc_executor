import pytest
from statistics_calculator import calculate_statistics

# Test case 1: Basic test with an odd number of elements
def test_odd_list():
    result = calculate_statistics([1, 2, 2, 3, 5])
    assert result == {"mean": 2.6, "median": 2, "mode": 2, "count": 5}

# Test case 2: Basic test with an even number of elements
def test_even_list():
    result = calculate_statistics([1, 2, 3, 4, 5, 6])
    assert result == {"mean": 3.5, "median": 3.5, "mode": [1, 2, 3, 4, 5, 6], "count": 6}

# Test case 3: Test with negative numbers
def test_negative_numbers():
    result = calculate_statistics([-1, -2, -2, -3, -5])
    assert result == {"mean": -2.6, "median": -2, "mode": -2, "count": 5}

# Test case 4: Test with floating-point numbers
def test_float_numbers():
    result = calculate_statistics([1.5, 2.5, 2.5, 3.5, 5.5])
    assert result == {"mean": 3.1, "median": 2.5, "mode": 2.5, "count": 5}

# Test case 5: Test for multiple modes (bimodal)
def test_multiple_modes():
    result = calculate_statistics([1, 1, 2, 3, 4, 4])
    assert result["mode"] == [1, 4] # Order may vary
    assert result["mean"] == 2.5
    assert result["median"] == 2.5

# Test case 6: Error handling for an empty list
def test_empty_list():
    with pytest.raises(ValueError, match="Input list cannot be empty."):
        calculate_statistics([])

# Test case 7: Error handling for invalid input type (not a list)
def test_invalid_input_type():
    with pytest.raises(TypeError, match="Input must be a list."):
        calculate_statistics("not a list")

# Test case 8: Error handling for list with non-numeric elements
def test_non_numeric_elements():
    with pytest.raises(TypeError, match="All elements in the list must be numeric."):
        calculate_statistics([1, 2, 'three', 4])
