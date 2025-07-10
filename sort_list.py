def sort_list(lst, reverse=False):
    """
    Sort a list in ascending or descending order.
    
    Args:
        lst: List to be sorted
        reverse: If True, sort in descending order (default: False)
    
    Returns:
        A new sorted list
    """
    return sorted(lst, reverse=reverse)


if __name__ == "__main__":
    # Test with numbers
    numbers = [64, 34, 25, 12, 22, 11, 90]
    print(f"Original list: {numbers}")
    print(f"Sorted ascending: {sort_list(numbers)}")
    print(f"Sorted descending: {sort_list(numbers, reverse=True)}")
    
    # Test with strings
    fruits = ["banana", "apple", "cherry", "date", "elderberry"]
    print(f"\nOriginal list: {fruits}")
    print(f"Sorted ascending: {sort_list(fruits)}")
    print(f"Sorted descending: {sort_list(fruits, reverse=True)}")
    
    # Test with mixed types (numbers)
    mixed_numbers = [3.14, 2, 5.5, 1, 4.2]
    print(f"\nOriginal list: {mixed_numbers}")
    print(f"Sorted ascending: {sort_list(mixed_numbers)}")