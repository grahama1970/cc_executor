"""
Module: log_utils.py
Description: Utility functions and helpers for log utils

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import logging
import re
from typing import List, Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Regex to identify common data URI patterns for images
BASE64_IMAGE_PATTERN = re.compile(r"^(data:image/[a-zA-Z+.-]+;base64,)")


def truncate_large_value(
    value: Any,
    max_str_len: int = 100,
    max_list_elements_shown: int = 10,  # Threshold above which list is summarized
) -> Any:
    """
    Truncate large strings or arrays to make them log-friendly.

    Handles base64 image strings by preserving the header and truncating the data.
    Summarizes lists/arrays longer than `max_list_elements_shown`.

    Args:
        value: The value to potentially truncate
        max_str_len: Maximum length for the data part of strings before truncation
        max_list_elements_shown: Maximum number of elements to show in arrays
                                 before summarizing the array instead.

    Returns:
        Truncated or original value
    """
    if isinstance(value, str):
        # Check if it's a base64 image data URI
        match = BASE64_IMAGE_PATTERN.match(value)
        if match:
            header = match.group(1)
            data = value[len(header) :]
            if len(data) > max_str_len:
                half_len = max_str_len // 2
                if half_len == 0 and max_str_len > 0:
                    half_len = 1
                truncated_data = (
                    f"{data[:half_len]}...{data[-half_len:]}" if half_len > 0 else "..."
                )
                return header + truncated_data
            else:
                return value
        # --- It's not a base64 image string, apply generic string truncation ---
        elif len(value) > max_str_len:
            half_len = max_str_len // 2
            if half_len == 0 and max_str_len > 0:
                half_len = 1
            return (
                f"{value[:half_len]}...{value[-half_len:]}" if half_len > 0 else "..."
            )
        else:
            return value

    elif isinstance(value, list):
        # --- Handle large lists (like embeddings) by summarizing ---
        if len(value) > max_list_elements_shown:
            if value:
                element_type = type(value[0]).__name__
                return f"[<{len(value)} {element_type} elements>]"
            else:
                return "[<0 elements>]"
        else:
            # If list elements are dicts, truncate them recursively
            return [truncate_large_value(item, max_str_len, max_list_elements_shown) if isinstance(item, dict) else item for item in value]
    elif isinstance(value, dict): # Add explicit check for dict
            # Recursively truncate values within dictionaries
            return {k: truncate_large_value(v, max_str_len, max_list_elements_shown) for k, v in value.items()}
    else:
        # Handle other types (int, float, bool, None, etc.) - return as is
        return value


def log_safe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a log-safe version of the results list by truncating large fields
    within each dictionary.

    Args:
        results (list): List of documents (dictionaries) that may contain large fields.

    Returns:
        list: Log-safe version of the input list where large fields are truncated.

    Raises:
        TypeError: If the input `results` is not a list, or if any element
                   within the list is not a dictionary.
    """
    # --- Input Validation ---
    if not isinstance(results, list):
        raise TypeError(
            f"Expected input to be a List[Dict[str, Any]], but got {type(results).__name__}."
        )

    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise TypeError(
                f"Expected all elements in the input list to be dictionaries (dict), "
                f"but found element of type {type(item).__name__} at index {index}."
            )
    # --- End Input Validation ---

    log_safe_output = []
    for doc in results:  # We now know 'doc' is a dictionary
        doc_copy = {}
        for key, value in doc.items():
            doc_copy[key] = truncate_large_value(value)
        log_safe_output.append(doc_copy)
    return log_safe_output


def log_api_request(service_name: str, request_data: Dict[str, Any], truncate: bool = True) -> None:
    """Log API request details.

    Args:
        service_name: Name of the service being called
        request_data: Request data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        # Don't modify the original data
        request_data_to_log = truncate_large_value(request_data)
    else:
        request_data_to_log = request_data

    logger.debug(f"{service_name} API Request: {request_data_to_log}")

def log_api_response(service_name: str, response_data: Any, truncate: bool = True) -> None:
    """Log API response details.

    Args:
        service_name: Name of the service being called
        response_data: Response data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        # Don't modify the original data
        response_data_to_log = truncate_large_value(response_data)
    else:
        response_data_to_log = response_data

    logger.debug(f"{service_name} API Response: {response_data_to_log}")

def log_api_error(service_name: str, error: Exception, request_data: Optional[Dict[str, Any]] = None) -> None:
    """Log API error details.

    Args:
        service_name: Name of the service being called
        error: The error that occurred
        request_data: Optional request data for context
    """
    error_message = f"{service_name} API Error: {str(error)}"

    if request_data:
        truncated_data = truncate_large_value(request_data)
        error_message += f" (Request: {truncated_data})"

    logger.error(error_message)


if __name__ == "__main__":
    # --- Valid Test Data ---
    valid_test_data = [
        {
            "id": 1,
            "description": "A short description.",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "image_small": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            "tags": ["short", "list"],
        },
        {
            "id": 2,
            "description": "This description is quite long, much longer than the default one hundred characters allowed, so it should definitely be truncated according to the rules specified in the function."
            * 2,
            "embedding": [float(i) / 100 for i in range(150)],
            "image_large": "data:image/jpeg;base64," + ("B" * 500),
            "tags": ["tag" + str(i) for i in range(20)],
        },
        {
            "id": 3,
            "description": "Edge case string." + "C" * 100,
            "embedding": [],
            "image_none": None,
            "image_weird_header": "data:application/octet-stream;base64," + ("D" * 150),
            "tags": [
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
                "ten",
                "eleven",
            ],
        },
    ]

    print("--- Processing Valid Data ---")
    try:
        safe_results = log_safe_results(valid_test_data)
        print("Valid data processed successfully.")
        # print("\n--- Log-Safe Results (Valid Data) ---")
        # for item in safe_results:
        #     print(item) # Optional: print results if needed
    except TypeError as e:
        print(f" ERROR processing valid data: {e}")

    print("\n--- Testing Invalid Inputs ---")

    # Test Case 1: Input is not a list
    invalid_input_1 = {"a": 1, "b": 2}  # A dictionary
    print(f"\nTesting input: {invalid_input_1} ({type(invalid_input_1).__name__})")
    try:
        log_safe_results(invalid_input_1)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 2: Input is a list, but contains non-dict elements
    invalid_input_2 = [{"a": 1}, "string_element", {"c": 3}]  # List with a string
    print(f"\nTesting input: {invalid_input_2}")
    try:
        log_safe_results(invalid_input_2)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 3: Input is a list of simple types
    invalid_input_3 = [1, 2, 3, 4]  # List of integers
    print(f"\nTesting input: {invalid_input_3}")
    try:
        log_safe_results(invalid_input_3)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 4: Input is None
    invalid_input_4 = None
    print(f"\nTesting input: {invalid_input_4}")
    try:
        log_safe_results(invalid_input_4)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 5: Empty list (should be valid)
    valid_input_empty = []
    print(f"\nTesting input: {valid_input_empty}")
    try:
        result = log_safe_results(valid_input_empty)
        if result == []:
            print(f" Successfully processed empty list.")
        else:
            print(f" Processing empty list resulted in unexpected output: {result}")
    except Exception as e:
        print(f" Caught unexpected error processing empty list: {e}")

    # Test API logging functions
    print("\n--- Testing API Logging Functions ---")
    try:
        log_api_request("TestService", {"model": "test-model", "prompt": "This is a test prompt"})
        log_api_response("TestService", {"result": "This is a test result", "status": "success"})
        log_api_error("TestService", Exception("Test error"), {"model": "test-model"})
        print(" API logging functions executed successfully.")
    except Exception as e:
        print(f" Error testing API logging functions: {e}")
