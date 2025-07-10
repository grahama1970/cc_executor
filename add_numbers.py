from typing import Union


def add_numbers(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """Add two numbers and return the result.
    
    Args:
        a: First number (int or float)
        b: Second number (int or float)
        
    Returns:
        The sum of a and b
        
    Examples:
        >>> add_numbers(2, 3)
        5
        >>> add_numbers(2.5, 3.7)
        6.2
        >>> add_numbers(-5, 10)
        5
    """
    return a + b


if __name__ == "__main__":
    # Test the function
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")
    
    result = add_numbers(10.5, 2.7)
    print(f"10.5 + 2.7 = {result}")
    
    result = add_numbers(-4, 8)
    print(f"-4 + 8 = {result}")