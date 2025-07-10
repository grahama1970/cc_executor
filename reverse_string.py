"""
Function to reverse a string.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python reverse_string.py          # Runs working_usage() - stable, known to work
  python reverse_string.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""


def reverse_string(s: str) -> str:
    """
    Reverse a string.
    
    Args:
        s: The string to reverse
        
    Returns:
        The reversed string
    """
    return s[::-1]


def working_usage():
    """Demonstrate proper usage of the reverse_string function.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    test_strings = [
        "hello",
        "Python",
        "12345",
        "Hello World!",
        "",  # empty string
        "a",  # single character
    ]
    
    for test in test_strings:
        result = reverse_string(test)
        print(f"reverse_string('{test}') = '{result}'")
    
    return True


def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Testing edge cases and special characters
    test_cases = [
        "racecar",  # palindrome
        "A man a plan a canal Panama",  # palindrome with spaces
        "😀🎉🐍",  # emojis
        "Hello\nWorld",  # newline
        "\t\tTabbed",  # tabs
        "Unicode: αβγδε",  # unicode characters
    ]
    
    for test in test_cases:
        result = reverse_string(test)
        print(f"Input:  '{test}'")
        print(f"Output: '{result}'")
        print(f"Is palindrome: {test == result}")
        print("-" * 40)


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        debug_function()
    else:
        print("Running working usage mode...")
        working_usage()