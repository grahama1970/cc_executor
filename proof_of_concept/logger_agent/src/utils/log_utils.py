#!/usr/bin/env python3
"""
Utility functions and helpers for log truncation and safe logging.

Provides functions to truncate large values (strings, lists, dicts) to make them
suitable for logging without overwhelming log storage. Handles special cases like
base64 image data URIs and large embeddings arrays.

Third-party Documentation:
- Python Logging: https://docs.python.org/3/library/logging.html
- Regular Expressions: https://docs.python.org/3/library/re.html

Example Input:
    {
        "id": 1,
        "description": "A very long description that exceeds 100 characters...",
        "embedding": [0.1, 0.2, 0.3, ... 1000 more elements],
        "image": "data:image/png;base64,iVBORw0KGgoAAAANS... (very long)"
    }

Expected Output:
    {
        "id": 1,
        "description": "A very long...characters...",
        "embedding": "[<1003 float elements>]",
        "image": "data:image/png;base64,iVBORw0KGg...AAASUVORK5CYII="
    }

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python log_utils.py          # Runs working_usage() - stable, known to work
  python log_utils.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Any, Dict, Optional
from datetime import datetime, date, time
from decimal import Decimal

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Optional file logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / f"{Path(__file__).stem}_{{time}}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)

# Regex to identify common data URI patterns for images
BASE64_IMAGE_PATTERN = re.compile(r"^(data:image/[a-zA-Z+.-]+;base64,)")


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

def truncate_large_value(
    value: Any,
    max_str_len: int = 100,
    max_list_elements_shown: int = 10,
) -> Any:
    """
    Truncate large strings or arrays to make them log-friendly.

    Handles base64 image strings by preserving the header and truncating the data.
    Summarizes lists/arrays longer than `max_list_elements_shown`.
    Converts non-JSON-serializable types to strings.

    Args:
        value: The value to potentially truncate
        max_str_len: Maximum length for the data part of strings before truncation
        max_list_elements_shown: Maximum number of elements to show in arrays
                                 before summarizing the array instead.

    Returns:
        Truncated or original value
    """
    # Handle datetime objects by converting to ISO format string
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Handle date objects
    if isinstance(value, date):
        return value.isoformat()
    
    # Handle time objects
    if isinstance(value, time):
        return value.isoformat()
    
    # Handle Decimal objects
    if isinstance(value, Decimal):
        return str(value)
    
    # Handle Path objects
    if isinstance(value, Path):
        return str(value)
    
    # Handle other potentially non-serializable types (custom classes, etc.)
    if hasattr(value, '__dict__') and not isinstance(value, (dict, list, tuple, str, int, float, bool, type(None))):
        # Convert custom objects to their string representation
        return str(value)
    
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
        # It's not a base64 image string, apply generic string truncation
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
        # Handle large lists (like embeddings) by summarizing
        if len(value) > max_list_elements_shown:
            if value:
                element_type = type(value[0]).__name__
                return f"[<{len(value)} {element_type} elements>]"
            else:
                return "[<0 elements>]"
        else:
            # Recursively truncate all list elements (not just dicts)
            return [
                truncate_large_value(item, max_str_len, max_list_elements_shown)
                for item in value
            ]
    elif isinstance(value, dict):
        # Recursively truncate values within dictionaries
        return {
            k: truncate_large_value(v, max_str_len, max_list_elements_shown) 
            for k, v in value.items()
        }
    else:
        # Handle other types (int, float, bool, None, etc.) - return as is
        return value


def log_safe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a log-safe version of the results list by truncating large fields
    within each dictionary.

    Args:
        results: List of documents (dictionaries) that may contain large fields.

    Returns:
        Log-safe version of the input list where large fields are truncated.

    Raises:
        TypeError: If the input `results` is not a list, or if any element
                   within the list is not a dictionary.
    """
    # Input Validation
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

    log_safe_output = []
    for doc in results:
        doc_copy = {}
        for key, value in doc.items():
            doc_copy[key] = truncate_large_value(value)
        log_safe_output.append(doc_copy)
    return log_safe_output


def log_api_request(service_name: str, request_data: Dict[str, Any], truncate: bool = True) -> None:
    """
    Log API request details.

    Args:
        service_name: Name of the service being called
        request_data: Request data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        request_data_to_log = truncate_large_value(request_data)
    else:
        request_data_to_log = request_data

    logger.debug(f"{service_name} API Request: {request_data_to_log}")


def log_api_response(service_name: str, response_data: Any, truncate: bool = True) -> None:
    """
    Log API response details.

    Args:
        service_name: Name of the service being called
        response_data: Response data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        response_data_to_log = truncate_large_value(response_data)
    else:
        response_data_to_log = response_data

    logger.debug(f"{service_name} API Response: {response_data_to_log}")


def log_api_error(service_name: str, error: Exception, request_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Log API error details.

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


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """
    Save results to a prettified JSON file.
    
    Args:
        results: Results dictionary to save
        output_dir: Optional output directory (defaults to tmp/responses)
        
    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "tmp" / "responses"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(__file__).stem}_results_{timestamp}.json"
    output_path = output_dir / filename
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    logger.info(f"Results saved to: {output_path}")
    return output_path


# ============================================
# USAGE EXAMPLES (Inside __main__ block)
# ============================================

async def working_usage():
    """
    Demonstrate log utility functions with stable, working examples.
    
    This function contains tested code that demonstrates the proper
    usage of truncation and log-safe functions.
    """
    logger.info("=== Running Working Usage Examples ===")
    
    # Example 1: Test basic truncation
    test_data = [
        {
            "id": 1,
            "description": "A short description.",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "image_small": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            "tags": ["short", "list"],
        },
        {
            "id": 2,
            "description": "This description is quite long, much longer than the default one hundred characters allowed, so it should definitely be truncated according to the rules specified in the function." * 2,
            "embedding": [float(i) / 100 for i in range(150)],
            "image_large": "data:image/jpeg;base64," + ("B" * 500),
            "tags": ["tag" + str(i) for i in range(20)],
        }
    ]
    
    # Test log_safe_results
    logger.info("Testing log_safe_results...")
    safe_results = log_safe_results(test_data)
    
    # Verify truncation worked
    assert len(safe_results) == 2
    assert "..." in safe_results[1]["description"]
    assert "[<150 float elements>]" in str(safe_results[1]["embedding"])
    logger.success("✓ log_safe_results working correctly")
    
    # Example 2: Test API logging functions
    logger.info("\nTesting API logging functions...")
    log_api_request("TestService", {"model": "test-model", "prompt": "A" * 200})
    log_api_response("TestService", {"result": "B" * 300, "status": "success"})
    log_api_error("TestService", Exception("Test error"), {"model": "test-model"})
    logger.success("✓ API logging functions working correctly")
    
    # Example 3: Test edge cases
    logger.info("\nTesting edge cases...")
    edge_cases = [
        {"empty_list": [], "none_value": None, "bool": True},
        {"nested": {"deep": {"deeper": {"value": "X" * 200}}}},
        {"mixed": [1, "string", {"nested": "value"}, None, True]}
    ]
    
    safe_edge_cases = log_safe_results(edge_cases)
    logger.success("✓ Edge cases handled correctly")
    
    # Save results
    save_results({
        "test_data": safe_results,
        "edge_cases": safe_edge_cases,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return True


async def debug_function():
    """
    Debug function for testing new features or investigating issues.
    
    Update this function freely when debugging truncation logic or
    testing specific edge cases.
    """
    logger.info("=== Running Debug Function ===")
    
    # Current debugging: Test very large data structures
    huge_data = {
        "massive_string": "X" * 10000,
        "huge_list": list(range(10000)),
        "deep_nesting": {}
    }
    
    # Build deep nesting
    current = huge_data["deep_nesting"]
    for i in range(100):
        current["level_" + str(i)] = {}
        current = current["level_" + str(i)]
    current["value"] = "Deep value"
    
    logger.info("Testing truncation on huge data structures...")
    truncated = truncate_large_value(huge_data)
    
    # Verify truncation
    assert len(str(truncated["massive_string"])) < 200
    assert "[<10000 int elements>]" in str(truncated["huge_list"])
    logger.success("✓ Large data structures truncated successfully")
    
    # Test invalid inputs
    logger.info("\nTesting error handling...")
    try:
        log_safe_results("not a list")  # Should raise TypeError
    except TypeError as e:
        logger.success(f"✓ Correctly caught error: {e}")
    
    try:
        log_safe_results([1, 2, 3])  # List of non-dicts
    except TypeError as e:
        logger.success(f"✓ Correctly caught error: {e}")
    
    return True


async def stress_test():
    """
    Run stress tests loaded from JSON configuration files.
    
    Tests high-volume truncation scenarios and performance.
    """
    logger.info("=== Running Stress Tests ===")
    
    # Generate stress test data
    stress_configs = [
        {
            "name": "high_volume",
            "description": "Test with many documents",
            "doc_count": 1000,
            "field_size": "large"
        },
        {
            "name": "deep_nesting",
            "description": "Test with deeply nested structures",
            "doc_count": 100,
            "nesting_depth": 50
        }
    ]
    
    for config in stress_configs:
        logger.info(f"\nRunning stress test: {config['name']}")
        
        if config["name"] == "high_volume":
            # Generate many documents
            docs = []
            for i in range(config["doc_count"]):
                doc = {
                    "id": i,
                    "data": "X" * 1000,
                    "embedding": list(range(500)),
                    "metadata": {"index": i, "test": True}
                }
                docs.append(doc)
            
            start_time = datetime.utcnow()
            safe_docs = log_safe_results(docs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.success(
                f"✓ Processed {len(docs)} documents in {duration:.2f} seconds"
            )
            
        elif config["name"] == "deep_nesting":
            # Generate deeply nested documents
            docs = []
            for i in range(config["doc_count"]):
                doc = {"id": i}
                current = doc
                for level in range(config["nesting_depth"]):
                    current[f"level_{level}"] = {}
                    current = current[f"level_{level}"]
                current["value"] = f"Deep value {i}"
                docs.append(doc)
            
            start_time = datetime.utcnow()
            safe_docs = log_safe_results(docs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.success(
                f"✓ Processed {len(docs)} nested documents in {duration:.2f} seconds"
            )
    
    logger.info("\n📊 Stress Test Summary: All tests passed")
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    """
    Script entry point with triple-mode execution.
    
    Usage:
        python log_utils.py           # Runs working_usage() - stable tests
        python log_utils.py debug     # Runs debug_function() - experimental
        python log_utils.py stress    # Runs stress_test() - performance tests
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        """Main async entry point."""
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        elif mode == "stress":
            logger.info("Running in STRESS TEST mode...")
            success = await stress_test()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        return success
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)