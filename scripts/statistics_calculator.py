import collections

def calculate_statistics(numbers):
    """
    Calculates the mean, median, and mode for a list of numbers.

    Args:
        numbers: A list of numeric values.

    Returns:
        A dictionary containing the mean, median, mode, and count.
        
    Raises:
        TypeError: If the input is not a list or contains non-numeric elements.
        ValueError: If the input list is empty.
    """
    if not isinstance(numbers, list):
        raise TypeError("Input must be a list.")
    if not numbers:
        raise ValueError("Input list cannot be empty.")
    if not all(isinstance(n, (int, float)) for n in numbers):
        raise TypeError("All elements in the list must be numeric.")

    # Calculate Mean
    mean = sum(numbers) / len(numbers)

    # Calculate Median
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid_index = n // 2
    
    if n % 2 == 0:
        # Even number of elements: average of the two middle elements
        median = (sorted_nums[mid_index - 1] + sorted_nums[mid_index]) / 2
    else:
        # Odd number of elements: the middle element
        median = sorted_nums[mid_index]

    # Calculate Mode
    # collections.Counter is an efficient way to count item frequencies
    counts = collections.Counter(numbers)
    # Find the maximum frequency
    max_freq = max(counts.values())
    # Find all numbers that have the maximum frequency
    modes = [num for num, freq in counts.items() if freq == max_freq]
    # To match the original function's behavior of returning a single value,
    # we'll return the first mode found. For multiple modes, we return the list.
    mode = modes[0] if len(modes) == 1 else modes


    return {
        "mean": mean,
        "median": median,
        "mode": mode,
        "count": len(numbers)
    }
