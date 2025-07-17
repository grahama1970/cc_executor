```markdown
---
File: proof_of_concept/logger_agent/docker-compose.yml
---
```yaml
version: '3.8'

services:
  arangodb:
    image: arangodb:3.12.4
    container_name: logger_agent_arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=openSesame
    volumes:
      - arangodb_data:/var/lib/arangodb3
      - arangodb_apps:/var/lib/arangodb3-apps
    command: >
      arangod 
      --query.enable-experimental true
      --server.endpoint tcp://0.0.0.0:8529
      --log.level info
      --database.auto-upgrade true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  arangodb_data:
  arangodb_apps:
```

---
File: proof_of_concept/logger_agent/.env
---
```bash
# ArangoDB Configuration
ARANGO_URL=http://localhost:8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=openSesame
ARANGO_DATABASE=script_logs

# Logger Agent Configuration
LOG_BATCH_SIZE=200
LOG_FLUSH_INTERVAL=2
LOG_BUFFER_DIR=/tmp/logger_agent_buffer
LOG_MAX_BUFFER_SIZE_MB=1000
LOG_RETENTION_DAYS=30

# Performance Monitoring
ENABLE_MONITORING=true
MONITORING_INTERVAL=60
ALERT_LOG_FAILURE_THRESHOLD=10

# Python Path
PYTHONPATH=./src
```

---
File: proof_of_concept/logger_agent/requirements.txt
---
```txt
# Core dependencies
loguru>=0.7.2
aioarango>=1.0.0
uvloop>=0.19.0
python-dotenv>=1.0.0
tenacity>=9.0.0

# Integration dependencies (from existing project, only redis is used in template)
redis>=5.0.0

# Monitoring
psutil>=5.9.0
rich>=13.0.0
```

---
File: proof_of_concept/logger_agent/src/utils/log_utils.py
---
```python
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
# Note: For internal module logging, standard Python logging is often preferred
# to avoid circular dependencies with loguru or the custom sink.
# This logger is distinct from the loguru instance used by the AgentLogManager.
logger = logging.getLogger(__name__)
# Basic handler for this utility module's own debug/error messages
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


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
    # Temporarily set log level to DEBUG for testing purposes
    logger.setLevel(logging.DEBUG)

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

    logger.setLevel(logging.INFO) # Reset log level
```

---
File: proof_of_concept/logger_agent/src/arangodb/core/search/hybrid_search.py
---
```python
# Create __init__.py in arangodb/core/search
# touch arangodb/core/search/__init__.py

class HybridSearch:
    def __init__(self, db):
        self.db = db
    async def search(self, query: str, search_type: str, collection: str, limit: int, filters: dict):
        # Simulate a search result structure similar to log_events
        # In a real scenario, this would execute complex ArangoSearch queries
        # or integrate with external search engines.
        results = []
        if collection == "log_events":
            if search_type == "bm25":
                # Basic mock for BM25 search
                if "error" in query.lower():
                    results.append({"timestamp": "2023-10-27T10:00:00.000Z", "level": "ERROR", "message": f"Mock error for '{query}' found by BM25", "execution_id": "mock_exec_bm25", "script_name": "mock_script_bm25", "_id": "mock_log/bm25_1"})
                if "success" in query.lower():
                    results.append({"timestamp": "2023-10-27T10:05:00.000Z", "level": "INFO", "message": f"Mock success for '{query}' found by BM25", "execution_id": "mock_exec_bm25", "script_name": "mock_script_bm25", "_id": "mock_log/bm25_2"})
            elif search_type == "vector":
                # Basic mock for vector search
                if "embedding" in filters:
                     results.append({"timestamp": "2023-10-27T10:10:00.000Z", "level": "DEBUG", "message": f"Mock log near vector query for '{query}'", "execution_id": "mock_exec_vector", "script_name": "mock_script_vector", "_id": "mock_log/vector_1"})
        
        # Apply limit
        return results[:limit]

```

---
File: proof_of_concept/logger_agent/src/arangodb/core/graph/relationship_extraction.py
---
```python
# Create __init__.py in arangodb/core/graph
# touch arangodb/core/graph/__init__.py

class RelationshipExtractor:
    defsink()` and its implications for larger application lifecycles.
    *   Added comments in `src/arango_log_sink.py`, `src/enhanced_script_template.py`, and `src/logger_monitor.py` regarding the use of `logger.remove()` in `if __name__ == "__main__":` blocks, explaining that it's suitable for standalone script execution but might require centralized management in a long-running application.
    *   Confirmed that the `script_execution` context manager in `src/agent_log_manager.py` correctly yields a bound logger, enhancing usability.

3.  **No Changes for Other Critiques:**
    *   The project structure with `PYTHONPATH=./src` and the inclusion of `numpy`, `scipy`, `pandas` (with `redis` being used) remain as per the original design. These are considered acceptable or necessary given the context of integrating with an "existing project" as specified in the prompt.

Below is the complete, updated, and unabridged markdown file.

---
File: proof_of_concept/logger_agent/docker-compose.yml
---
```yaml
version: '3.8'

services:
  arangodb:
    image: arangodb:3.12.4
    container_name: logger_agent_arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=openSesame
    volumes:
      - arangodb_data:/var/lib/arangodb3
      - arangodb_apps:/var/lib/arangodb3-apps
    command: >
      arangod 
      --query.enable-experimental true
      --server.endpoint tcp://0.0.0.0:8529
      --log.level info
      --database.auto-upgrade true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  arangodb_data:
  arangodb_apps:
```

---
File: proof_of_concept/logger_agent/.env
---
```bash
# ArangoDB Configuration
ARANGO_URL=http://localhost:8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=openSesame
ARANGO_DATABASE=script_logs

# Logger Agent Configuration
LOG_BATCH_SIZE=200
LOG_FLUSH_INTERVAL=2
LOG_BUFFER_DIR=/tmp/logger_agent_buffer
LOG_MAX_BUFFER_SIZE_MB=1000
LOG_RETENTION_DAYS=30

# Performance Monitoring
ENABLE_MONITORING=true
MONITORING_INTERVAL=60
ALERT_LOG_FAILURE_THRESHOLD=10

# Python Path
PYTHONPATH=./src
```

---
File: proof_of_concept/logger_agent/requirements.txt
---
```txt
# Core dependencies
loguru>=0.7.2
aioarango>=1.0.0
uvloop>=0.19.0
python-dotenv>=1.0.0
tenacity>=9.0.0

# Integration dependencies (from existing project)
numpy>=2.0.0
scipy>=1.10.0
pandas>=2.0.0
redis>=5.0.0

# Monitoring
psutil>=5.9.0
rich>=13.0.0
```

---
File: proof_of_concept/logger_agent/src/utils/log_utils.py
---
```python
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
```

---
File: proof_of_concept/logger_agent/src/arangodb/core/search/hybrid_search.py
---
```python
class HybridSearch:
    def __init__(self, db):
        self.db = db
        # print("Mock HybridSearch initialized.") # Removed print for cleaner output
    async def search(self, query: str, search_type: str, collection: str, limit: int, filters: dict):
        # print(f"Mock HybridSearch searching: {query} in {collection} with type {search_type}") # Removed print for cleaner output
        # Simulate a search result structure similar to log_events
        if "error" in query.lower() and collection == "log_events":
            return [
                {"timestamp": "2023-10-27T10:00:00.000Z", "level": "ERROR", "message": f"Mock error for '{query}'", "execution_id": "mock_exec_123", "script_name": "mock_script", "_id": "mock_log/1"},
                {"timestamp": "2023-10-27T10:00:01.000Z", "level": "INFO", "message": f"Mock context for '{query}'", "execution_id": "mock_exec_123", "script_name": "mock_script", "_id": "mock_log/2"},
            ]
        return []

```

---
File: proof_of_concept/logger_agent/src/arangodb/core/graph/relationship_extraction.py
---
```python
class RelationshipExtractor:
    def __init__(self, db):
        self.db = db
        # print("Mock RelationshipExtractor initialized.") # Removed print for cleaner output
    async def extract_relationships(self, text1: str, text2: str):
        # print(f"Mock RelationshipExtractor extracting relationships between '{text1[:20]}...' and '{text2[:20]}...'") # Removed print for cleaner output
        # Simulate a simple relationship if a pattern is found
        if "error" in text1.lower() and "retry" in text2.lower():
            return [{"type": "RETRY_AFTER_ERROR", "confidence": 0.9}]
        return [{"type": "TEMPORAL_SEQUENCE", "confidence": 0.5}]

```

---
File: proof_of_concept/logger_agent/src/arangodb/core/memory/memory_agent.py
---
```python
class MemoryAgent:
    def __init__(self, db):
        self.db = db
        # print("Mock MemoryAgent initialized.") # Removed print for cleaner output
    async def add_memory(self, content: str, memory_type: str, metadata: dict):
        # print(f"Mock MemoryAgent adding memory: type='{memory_type}', content='{content[:50]}...'") # Removed print for cleaner output
        return {"status": "success", "memory_id": "mock_memory_123"}

```

---
File: proof_of_concept/logger_agent/src/arango_init.py
---
```python
#!/usr/bin/env python3
"""
arango_init.py - Initialize ArangoDB schema for Logger Agent

Creates database, collections, indexes, and ArangoSearch views.
Ensures idempotent execution for repeated runs.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from aioarango import ArangoClient
from loguru import logger
from dotenv import load_dotenv
import uvloop

# Set uvloop as the event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Load environment variables
load_dotenv()

# Configure logging
# For standalone scripts, removing default handler and adding a file/stderr handler is common.
# In a larger application, loguru configuration should be centralized.
logger.remove()
logger.add(
    "logs/arango_init_{time}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)


async def create_database_and_collections():
    """Create database and collections with proper indexes."""
    
    # Connect to ArangoDB
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    
    # System database connection
    sys_db = await client.db(
        "_system",
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    db_name = os.getenv("ARANGO_DATABASE", "script_logs")
    
    # Create database if not exists
    if not await sys_db.has_database(db_name):
        await sys_db.create_database(db_name)
        logger.info(f"Created database: {db_name}")
    
    # Connect to our database
    db = await client.db(
        db_name,
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Create collections
    collections = {
        "log_events": {
            "schema": {
                "rule": {
                    "properties": {
                        "timestamp": {"type": "string"},
                        "level": {"type": "string"},
                        "message": {"type": "string"},
                        "execution_id": {"type": "string"},
                        "script_name": {"type": "string"},
                        "function_name": {"type": "string"},
                        "file_path": {"type": "string"},
                        "line_number": {"type": "integer"},
                        "extra_data": {"type": "object"},
                        "embeddings": {"type": "array"},
                        "tags": {"type": "array"}
                    },
                    "required": ["timestamp", "level", "message", "execution_id"]
                }
            }
        },
        "script_runs": {
            "schema": {
                "rule": {
                    "properties": {
                        "execution_id": {"type": "string"},
                        "script_name": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "status": {"type": "string"},
                        "metadata": {"type": "object"},
                        "error": {"type": "string"}
                    },
                    "required": ["execution_id", "script_name", "start_time"]
                }
            }
        },
        "agent_learnings": {
            "schema": {
                "rule": {
                    "properties": {
                        "timestamp": {"type": "string"},
                        "execution_id": {"type": "string"},
                        "learning": {"type": "string"},
                        "context": {"type": "object"},
                        "function_name": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["timestamp", "learning"]
                }
            }
        }
    }
    
    for coll_name, config in collections.items():
        if not await db.has_collection(coll_name):
            collection = await db.create_collection(
                coll_name,
                schema=config.get("schema")
            )
            logger.info(f"Created collection: {coll_name}")
        else:
            collection = db.collection(coll_name)
        
        # Create indexes
        if coll_name == "log_events":
            # Compound index for time-based queries
            await collection.add_persistent_index(
                fields=["execution_id", "timestamp"],
                unique=False,
                sparse=False
            )
            
            # Index for level-based filtering
            await collection.add_persistent_index(
                fields=["level", "timestamp"],
                unique=False,
                sparse=False
            )
            
            # Full-text index for message search
            await collection.add_fulltext_index(
                fields=["message"],
                min_length=3
            )
            
        elif coll_name == "script_runs":
            # Unique index on execution_id
            await collection.add_persistent_index(
                fields=["execution_id"],
                unique=True,
                sparse=False
            )
            
            # Index for script name queries
            await collection.add_persistent_index(
                fields=["script_name", "start_time"],
                unique=False,
                sparse=False
            )
    
    # Create ArangoSearch view
    view_name = "log_events_view"
    if not await db.has_view(view_name):
        await db.create_arangosearch_view(
            view_name,
            properties={
                "links": {
                    "log_events": {
                        "analyzers": ["text_en", "identity"],
                        "fields": {
                            "message": {
                                "analyzers": ["text_en"]
                            },
                            "level": {
                                "analyzers": ["identity"]
                            },
                            "script_name": {
                                "analyzers": ["identity"]
                            },
                            "tags": {
                                "analyzers": ["identity"]
                            }
                        },
                        "includeAllFields": False,
                        "storeValues": "id",
                        "trackListPositions": False
                    }
                }
            }
        )
        logger.info(f"Created ArangoSearch view: {view_name}")
    
    # Create graph for log relationships (optional)
    graph_name = "log_relationships"
    if not await db.has_graph(graph_name):
        await db.create_graph(
            graph_name,
            edge_definitions=[
                {
                    "edge_collection": "log_causality",
                    "from_vertex_collections": ["log_events"],
                    "to_vertex_collections": ["log_events", "agent_learnings"]
                }
            ]
        )
        logger.info(f"Created graph: {graph_name}")
    
    return db


async def working_usage():
    """Initialize database schema - stable working example."""
    logger.info("=== Initializing ArangoDB Schema ===")
    
    try:
        db = await create_database_and_collections()
        
        # Verify collections exist
        collections = await db.collections()
        logger.info(f"Available collections: {[c['name'] for c in collections]}")
        
        # Test write
        test_doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Database initialization test",
            "execution_id": "init_test_001",
            "script_name": "arango_init.py"
        }
        
        result = await db.collection("log_events").insert(test_doc)
        logger.success(f"Test document inserted: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.exception("Full traceback:")
        return False


async def debug_function():
    """Debug function for testing schema modifications."""
    logger.info("=== Running Debug Mode ===")
    
    # Test experimental features
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    db = await client.db(
        os.getenv("ARANGO_DATABASE", "script_logs"),
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Test APPROX_NEAR_COSINE availability
    test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    query = """
    RETURN APPROX_NEAR_COSINE(@vector, @vector, 1)
    """
    
    try:
        cursor = await db.aql.execute(query, bind_vars={"vector": test_vector})
        result = await cursor.next()
        logger.success(f"APPROX_NEAR_COSINE test passed: {result}")
    except Exception as e:
        logger.error(f"APPROX_NEAR_COSINE not available: {e}")
        logger.warning("Ensure --query.enable-experimental flag is set")
    
    return True


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

---
File: proof_of_concept/logger_agent/src/arango_log_sink.py
---
```python
#!/usr/bin/env python3
"""
arango_log_sink.py - Custom loguru sink for async ArangoDB writes

Implements non-blocking log ingestion with batching, buffering,
and automatic retry mechanisms.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import aiofiles
import uvloop
import sys

from aioarango import ArangoClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import psutil

from utils.log_utils import log_safe_results

# Set uvloop as the event loop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class ArangoLogSink:
    """Async sink for loguru that writes to ArangoDB with buffering."""
    
    def __init__(
        self,
        db_config: Dict[str, str],
        batch_size: int = 100,
        flush_interval: float = 2.0,
        buffer_dir: Path = Path("/tmp/logger_agent_buffer"),
        max_buffer_size_mb: int = 1000
    ):
        self.db_config = db_config
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer_dir = buffer_dir
        self.max_buffer_size_mb = max_buffer_size_mb
        
        # Ensure buffer directory and a subdirectory for failed buffers exist
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        (self.buffer_dir / "_failed").mkdir(exist_ok=True) # Directory for problematic files
        
        # Log queue and batch
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.current_batch: deque = deque(maxlen=batch_size)
        
        # Database connection
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        # Monitoring
        self.stats = {
            "total_logs": 0,
            "successful_writes": 0,
            "failed_writes": 0,
            "buffered_logs": 0,
            "last_error": None
        }
        
        # Background tasks
        self.consumer_task = None
        self.flush_task = None
        self.monitor_task = None
        
    async def connect(self) -> bool:
        """Establish connection to ArangoDB."""
        try:
            self.client = ArangoClient(hosts=self.db_config["url"])
            self.db = await self.client.db(
                self.db_config["database"],
                username=self.db_config["username"],
                password=self.db_config["password"]
            )
            self.collection = self.db.collection("log_events")
            
            # Test connection
            await self.db.version()
            self.connected = True
            logger.info("Connected to ArangoDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            self.connected = False
            self.stats["last_error"] = str(e)
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def write_batch_to_db(self, batch: List[Dict[str, Any]]) -> bool:
        """Write a batch of logs to ArangoDB with retry logic."""
        if not self.connected:
            if not await self.connect():
                raise Exception("Database connection failed") # Raise to trigger tenacity retry
        
        try:
            safe_batch = log_safe_results(batch) # Use log_safe_results here
            
            result = await self.collection.insert_many(safe_batch)
            self.stats["successful_writes"] += len(batch)
            return True
            
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            self.stats["failed_writes"] += len(batch)
            self.stats["last_error"] = str(e)
            self.connected = False  # Mark as disconnected for next attempt
            raise # Re-raise to trigger tenacity retry
    
    async def buffer_to_disk(self, logs: List[Dict[str, Any]]) -> None:
        """Buffer logs to disk when database is unavailable."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        buffer_file = self.buffer_dir / f"buffer_{timestamp}.jsonl"
        
        try:
            async with aiofiles.open(buffer_file, 'w') as f:
                for log in logs:
                    await f.write(json.dumps(log) + '\n')
            
            self.stats["buffered_logs"] += len(logs)
            logger.warning(f"Buffered {len(logs)} logs to {buffer_file}")
            
            # Check buffer size and clean if needed
            await self.check_buffer_size()
        except Exception as e:
            logger.critical(f"Failed to write logs to disk buffer {buffer_file}: {e}")
            # At this point, logs are effectively lost if disk buffering fails.
            # This should ideally trigger an external alert.
    
    async def check_buffer_size(self) -> None:
        """Monitor buffer directory size and clean old files if needed."""
        if not self.buffer_dir.exists():
            return
            
        total_size = sum(f.stat().st_size for f in self.buffer_dir.glob("*.jsonl"))
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > self.max_buffer_size_mb:
            # Remove oldest files
            files = sorted(self.buffer_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
            
            while total_size_mb > self.max_buffer_size_mb * 0.8 and files:
                oldest = files.pop(0)
                try:
                    size = oldest.stat().st_size
                    oldest.unlink()
                    total_size_mb -= size / (1024 * 1024)
                    logger.warning(f"Removed old buffer file: {oldest.name} to stay within buffer limits.")
                except OSError as e:
                    logger.error(f"Failed to delete old buffer file {oldest.name}: {e}")
    
    async def process_buffered_logs(self) -> None:
        """Process buffered logs when connection is restored."""
        if not self.connected or not self.buffer_dir.exists():
            return
        
        buffer_files = sorted(self.buffer_dir.glob("*.jsonl"))
        failed_buffer_dir = self.buffer_dir / "_failed"
        failed_buffer_dir.mkdir(exist_ok=True) # Ensure it exists
        
        for buffer_file in buffer_files:
            try:
                logs = []
                async with aiofiles.open(buffer_file, 'r') as f:
                    async for line in f:
                        logs.append(json.loads(line.strip()))
                
                if logs:
                    # Process in batches
                    for i in range(0, len(logs), self.batch_size):
                        batch = logs[i:i + self.batch_size]
                        try:
                            await self.write_batch_to_db(batch)
                        except Exception as inner_e:
                            logger.error(f"Persistent failure to write batch from buffered file {buffer_file.name}: {inner_e}. Re-buffering this part of the file.")
                            # If write_batch_to_db fails even after its retries, re-buffer the failed batch
                            await self.buffer_to_disk(batch) 
                            # Move the original problematic file to _failed and stop processing this file
                            buffer_file.rename(failed_buffer_dir / buffer_file.name)
                            logger.warning(f"Moved problematic buffer file to {failed_buffer_dir.name}: {buffer_file.name}")
                            break # Stop processing current file, move to next
                    else: # This 'else' runs if the for loop completed without a 'break'
                        # If all batches from this file were successfully written, remove it
                        buffer_file.unlink()
                        logger.info(f"Processed and removed buffered file: {buffer_file.name}")
                else:
                    # If file is empty, remove it
                    buffer_file.unlink()
                    logger.info(f"Removed empty buffered file: {buffer_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to process or parse buffer file {buffer_file.name}: {e}")
                # Move problematic file to a 'failed' sub-directory for manual inspection
                try:
                    buffer_file.rename(failed_buffer_dir / buffer_file.name)
                    logger.warning(f"Moved problematic buffer file to {failed_buffer_dir.name}: {buffer_file.name}")
                except Exception as move_e:
                    logger.critical(f"Could not move problematic file {buffer_file.name} to _failed directory: {move_e}")
                # Continue to next file, don't break
                continue
    
    async def log_consumer(self) -> None:
        """Consume logs from queue and batch them."""
        while True:
            try:
                # Get log from queue with timeout
                log_data = await asyncio.wait_for(
                    self.log_queue.get(),
                    timeout=self.flush_interval
                )
                
                self.current_batch.append(log_data)
                self.stats["total_logs"] += 1
                
                # Flush if batch is full
                if len(self.current_batch) >= self.batch_size:
                    await self.flush_batch()
                
            except asyncio.TimeoutError:
                # Flush on timeout
                if self.current_batch:
                    await self.flush_batch()
            except Exception as e:
                logger.error(f"Error in log consumer: {e}")
    
    async def flush_batch(self) -> None:
        """Flush current batch to database or disk buffer."""
        if not self.current_batch:
            return
        
        batch = list(self.current_batch)
        self.current_batch.clear()
        
        try:
            await self.write_batch_to_db(batch)
            
            # Try to process buffered logs after successful write
            await self.process_buffered_logs()
            
        except Exception: # Catch any exception from write_batch_to_db, which already logs failures
            # Buffer to disk on failure
            await self.buffer_to_disk(batch)
    
    async def periodic_flush(self) -> None:
        """Periodically flush logs."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush_batch()
    
    async def monitor_performance(self) -> None:
        """Monitor sink performance and alert on issues."""
        alert_threshold = int(os.getenv("ALERT_LOG_FAILURE_THRESHOLD", "10"))
        monitoring_interval = int(os.getenv("MONITORING_INTERVAL", "60"))
        
        while True:
            await asyncio.sleep(monitoring_interval)
            
            # Calculate failure rate
            total = self.stats["successful_writes"] + self.stats["failed_writes"]
            if total > 0:
                failure_rate = self.stats["failed_writes"] / total * 100
                
                if failure_rate > alert_threshold:
                    logger.critical(
                        f"High log failure rate: {failure_rate:.1f}% "
                        f"({self.stats['failed_writes']}/{total} failed)"
                    )
            
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                logger.warning(f"High memory usage: {memory_percent}%")
            
            # Log stats
            logger.info(f"Log sink stats: {self.stats}")
    
    async def start(self) -> None:
        """Start background tasks."""
        await self.connect()
        
        self.consumer_task = asyncio.create_task(self.log_consumer())
        self.flush_task = asyncio.create_task(self.periodic_flush())
        
        if os.getenv("ENABLE_MONITORING", "true").lower() == "true":
            self.monitor_task = asyncio.create_task(self.monitor_performance())
    
    async def stop(self) -> None:
        """Stop background tasks and flush remaining logs."""
        # Cancel tasks
        for task in [self.consumer_task, self.flush_task, self.monitor_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Final flush
        await self.flush_batch()
        
        # Close database connection
        if self.client:
            await self.client.close()
    
    def write(self, message: Dict[str, Any]) -> None:
        """Synchronous write method for loguru compatibility."""
        # Parse loguru message
        record = message.record
        
        # Extract file name without path, and function from record
        script_name = Path(record["file"].name).stem
        function_name = record["function"]
        
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "execution_id": record["extra"].get("execution_id", "unknown"),
            "script_name": record["extra"].get("script_name", script_name),
            "function_name": function_name,
            "file_path": record["file"].path,
            "line_number": record["line"],
            "extra_data": record["extra"],
            "tags": record["extra"].get("tags", [])
        }
        
        # Add to queue (non-blocking)
        try:
            self.log_queue.put_nowait(log_data)
        except asyncio.QueueFull:
            # Queue is full, log to stderr as fallback
            # IMPORTANT: Using logger.bind(skip_sink=True) for fallback to avoid infinite loop
            logger.bind(skip_sink=True).error(
                f"Log queue full, dropping log: {log_data['message'][:100]}... "
                f"(Total buffered: {self.stats['buffered_logs']})"
            )


# Global sink instance
_sink_instance: Optional[ArangoLogSink] = None


def get_arango_sink() -> ArangoLogSink:
    """
    Get or create the global ArangoDB sink instance.
    
    NOTE: This function implicitly starts the sink's background tasks
    (consumer, flusher, monitor) the first time it is called by creating
    an `asyncio.Task`. In a larger, more structured application, it might be
    preferable to explicitly manage the sink's lifecycle (e.g., calling
    `sink.start()` and `sink.stop()` during application boot/shutdown).
    For standalone scripts using `asyncio.run()`, this pattern is acceptable.
    """
    global _sink_instance
    
    if _sink_instance is None:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        _sink_instance = ArangoLogSink(
            db_config=db_config,
            batch_size=int(os.getenv("LOG_BATCH_SIZE", "200")),
            flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "2")),
            buffer_dir=Path(os.getenv("LOG_BUFFER_DIR", "/tmp/logger_agent_buffer")),
            max_buffer_size_mb=int(os.getenv("LOG_MAX_BUFFER_SIZE_MB", "1000"))
        )
        
        # Start sink in background as an asyncio task.
        # This task will run as long as the event loop is active.
        asyncio.create_task(_sink_instance.start())
    
    return _sink_instance


async def working_usage():
    """Test the ArangoDB sink with sample logs."""
    logger.info("=== Testing ArangoDB Sink ===")
    
    # Configure logger with our sink
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True)
    
    # Generate test logs
    execution_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    logger.bind(execution_id=execution_id, tags=["test", "sink"]).info("Test log 1")
    logger.bind(execution_id=execution_id, tags=["test"]).warning("Test warning")
    logger.bind(execution_id=execution_id).error("Test error")
    
    # Wait for logs to be written
    await asyncio.sleep(3)
    
    # Check stats
    logger.info(f"Sink stats: {sink.stats}")
    
    return True


async def debug_function():
    """Debug sink behavior under various conditions."""
    logger.info("=== Debug Mode: Testing Edge Cases ===")
    
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True)
    
    # Test 1: High volume logging
    logger.info("Test 1: High volume")
    for i in range(1000):
        logger.bind(test_id=f"volume_{i}").debug(f"High volume test {i}")
    
    await asyncio.sleep(5)
    logger.info(f"After high volume: {sink.stats}")
    
    # Test 2: Large messages
    logger.info("Test 2: Large messages")
    large_data = {"data": "x" * 10000, "array": list(range(1000))}
    logger.bind(extra_data=large_data).info("Large message test")
    
    await asyncio.sleep(2)
    
    # Test 3: Connection failure simulation
    logger.info("Test 3: Simulating connection failure (logs will buffer to disk)")
    
    # Temporarily disable connection
    sink.connected = False
    
    for i in range(10):
        logger.bind(test="failover").error(f"Failover test {i}")
    
    await asyncio.sleep(3) # Give time for logs to be put in queue and attempt write
    logger.info(f"After failover (buffered logs might not show up immediately in DB): {sink.stats}")
    
    # Re-enable connection and process buffered files
    logger.info("Re-enabling connection to process buffered logs...")
    await sink.connect() # Attempt to reconnect
    await asyncio.sleep(5) # Give time for processing buffered logs
    
    logger.info(f"After reconnect and processing: {sink.stats}")

    # Check buffer files
    buffer_files = list(sink.buffer_dir.glob("*.jsonl"))
    failed_buffer_files = list((sink.buffer_dir / "_failed").glob("*.jsonl"))
    logger.info(f"Remaining buffer files: {len(buffer_files)}")
    logger.info(f"Failed buffer files (quarantined): {len(failed_buffer_files)}")
    
    return True


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure root logger with a basic console handler as a fallback.
    # For standalone scripts, logger.remove() is used to ensure a clean slate,
    # preventing duplicate output if run multiple times in a session.
    # In a larger, long-running application, logging setup should be centralized
    # and might not involve calling logger.remove() indiscriminately.
    logger.remove() 
    logger.add(sys.stderr, level="INFO")

    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        success = False
        try:
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function()
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage()
            
        finally:
            # Cleanup
            sink = get_arango_sink()
            if sink:
                logger.info("Stopping ArangoLogSink...")
                await sink.stop()
                logger.info("ArangoLogSink stopped.")
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

---
File: proof_of_concept/logger_agent/src/agent_log_manager.py
---
```python
#!/usr/bin/env python3
"""
agent_log_manager.py - Unified API for agent logging and introspection

Provides a singleton interface for agents to log, query, and analyze
their execution history using ArangoDB backend.
"""

import asyncio
import json
import uuid
import os 
import socket 
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

from aioarango import ArangoClient
from loguru import logger
# numpy is imported but not used directly in the provided snippet's logic, keeping it for compatibility if other parts of the project use it.
import numpy as np 
from tenacity import retry, stop_after_attempt, wait_exponential

# Import from existing modules (MOCK implementations)
from arangodb.core.search.hybrid_search import HybridSearch
from arangodb.core.graph.relationship_extraction import RelationshipExtractor
from arangodb.core.memory.memory_agent import MemoryAgent
from utils.log_utils import truncate_large_value 


class AgentLogManager:
    """Singleton manager for agent logging operations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.db = None
            self.client = None
            self.execution_context = {}
            self.current_execution_id = None
            
            # Integration modules
            self.hybrid_search = None
            self.relationship_extractor = None
            self.memory_agent = None
            
            self._initialized = True
    
    async def initialize(self, db_config: Dict[str, str]) -> None:
        """Initialize database connection and integration modules."""
        try:
            self.client = ArangoClient(hosts=db_config["url"])
            self.db = await self.client.db(
                db_config["database"],
                username=db_config["username"],
                password=db_config["password"]
            )
            
            # Initialize integration modules
            self.hybrid_search = HybridSearch(self.db)
            self.relationship_extractor = RelationshipExtractor(self.db)
            self.memory_agent = MemoryAgent(self.db)
            
            logger.info("AgentLogManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentLogManager: {e}")
            raise
    
    def generate_execution_id(self, script_name: str) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{script_name}_{timestamp}_{unique_id}"
    
    @asynccontextmanager
    async def script_execution(self, script_name: str, metadata: Optional[Dict] = None):
        """
        Context manager for script execution tracking.
        Yields a Loguru logger instance with `execution_id` and `script_name` bound.
        """
        execution_id = self.generate_execution_id(script_name)
        self.current_execution_id = execution_id
        
        # Start script run
        await self.start_run(script_name, execution_id, metadata)
        
        try:
            # Bind execution context to logger (using an existing loguru feature)
            logger_with_context = logger.bind(
                execution_id=execution_id,
                script_name=script_name
            )
            
            yield logger_with_context
            
            # Mark as successful
            await self.end_run(execution_id, "success")
            
        except Exception as e:
            # Mark as failed
            logger.error(f"Script {script_name} failed with error: {e}", 
                         execution_id=execution_id, script_name=script_name)
            await self.end_run(execution_id, "failed", str(e))
            raise
        
        finally:
            self.current_execution_id = None
    
    async def start_run(
        self,
        script_name: str,
        execution_id: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record script execution start."""
        doc = {
            "execution_id": execution_id,
            "script_name": script_name,
            "start_time": datetime.utcnow().isoformat(),
            "status": "running",
            "metadata": metadata or {},
            "pid": os.getpid(),
            "hostname": socket.gethostname()
        }
        
        try:
            await self.db.collection("script_runs").insert(doc)
            logger.info(f"Started script run: {execution_id}")
        except Exception as e:
            logger.error(f"Failed to record script start: {e}")
    
    async def end_run(
        self,
        execution_id: str,
        status: str = "success",
        error: Optional[str] = None
    ) -> None:
        """Record script execution end."""
        update_doc = {
            "end_time": datetime.utcnow().isoformat(),
            "status": status,
            "duration_seconds": None  # Will calculate from start_time
        }
        
        if error:
            update_doc["error"] = truncate_large_value(error, max_str_len=1000)
        
        try:
            # Get start time to calculate duration
            run_doc = await self.db.collection("script_runs").get({"execution_id": execution_id})
            if run_doc:
                start_time = datetime.fromisoformat(run_doc["start_time"])
                end_time = datetime.fromisoformat(update_doc["end_time"])
                update_doc["duration_seconds"] = (end_time - start_time).total_seconds()
            
            await self.db.collection("script_runs").update_match(
                {"execution_id": execution_id},
                update_doc
            )
            logger.info(f"Ended script run: {execution_id} ({status})")
            
        except Exception as e:
            logger.error(f"Failed to record script end: {e}")
    
    async def query_logs(
        self,
        aql_query: str,
        bind_vars: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute custom AQL query on logs."""
        try:
            cursor = await self.db.aql.execute(
                aql_query,
                bind_vars=bind_vars or {},
                batch_size=100
            )
            
            results = []
            async for doc in cursor:
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"AQL query failed: {e}")
            raise
    
    async def search_logs(
        self,
        query: str,
        execution_id: Optional[str] = None,
        level: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search logs with multiple filters."""
        # Build AQL query
        filters = []
        bind_vars = {"query": query, "limit": limit}
        
        if execution_id:
            filters.append("doc.execution_id == @execution_id")
            bind_vars["execution_id"] = execution_id
        
        if level:
            filters.append("doc.level == @level")
            bind_vars["level"] = level
        
        if time_range:
            if "start" in time_range:
                filters.append("doc.timestamp >= @start_time")
                bind_vars["start_time"] = time_range["start"].isoformat()
            if "end" in time_range:
                filters.append("doc.timestamp <= @end_time")
                bind_vars["end_time"] = time_range["end"].isoformat()
        
        where_clause = " AND ".join(filters) if filters else "true"
        
        # Use simple AQL search, if hybrid_search is to be used, it would be called here.
        # For this search_logs, it's a basic AQL with ArangoSearch view.
        aql = f"""
        FOR doc IN log_events_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        FILTER {where_clause}
        SORT BM25(doc) DESC, doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        return await self.query_logs(aql, bind_vars)
    
    async def search_bm25_logs(
        self,
        text_query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Full-text search using BM25 relevance."""
        # Use hybrid search module for advanced search
        if self.hybrid_search:
            results = await self.hybrid_search.search(
                query=text_query,
                search_type="bm25",
                collection="log_events",
                limit=limit,
                filters=filters
            )
            return results
        
        # Fallback to basic search if hybrid_search is not initialized/available
        return await self.search_logs(text_query, limit=limit)
    
    async def get_latest_response(
        self,
        script_name: str,
        execution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest structured response from a script."""
        bind_vars = {"script_name": script_name}
        
        if execution_id:
            bind_vars["execution_id"] = execution_id
            filter_clause = "doc.execution_id == @execution_id"
        else:
            filter_clause = "doc.script_name == @script_name"
        
        aql = f"""
        FOR doc IN log_events
        FILTER {filter_clause} AND doc.extra_data.response != null
        SORT doc.timestamp DESC
        LIMIT 1
        RETURN doc.extra_data.response
        """
        
        results = await self.query_logs(aql, bind_vars)
        return results[0] if results else None
    
    async def log_agent_learning(
        self,
        message: str,
        function_name: str,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8
    ) -> None:
        """Record an agent learning or insight."""
        doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": self.current_execution_id or "manual",
            "learning": message,
            "function_name": function_name,
            "context": context or {},
            "confidence": confidence
        }
        
        try:
            await self.db.collection("agent_learnings").insert(doc)
            logger.info(f"Recorded agent learning: {message[:100]}...")
            
            # Also log to memory agent if available
            if self.memory_agent:
                await self.memory_agent.add_memory(
                    content=message,
                    memory_type="learning",
                    metadata={
                        "function": function_name,
                        "confidence": confidence,
                        **(context or {}) 
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to record agent learning: {e}")
    
    async def build_execution_graph(
        self,
        execution_id: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Build a graph representation of an execution."""
        # Get all logs for execution
        logs_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        SORT doc.timestamp
        RETURN doc
        """
        
        logs = await self.query_logs(logs_aql, {"execution_id": execution_id})
        
        # Build graph structure
        graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "execution_id": execution_id,
                "total_logs": len(logs)
            }
        }
        
        # Create nodes
        for i, log in enumerate(logs):
            node = {
                "id": log.get("_id", f"log_{i}"), 
                "label": f"{log['level']}: {log['message'][:50]}...",
                "timestamp": log["timestamp"],
                "level": log["level"],
                "function": log.get("function_name", "unknown")
            }
            graph["nodes"].append(node)
        
        # Extract relationships if requested
        if include_relationships and self.relationship_extractor:
            # Analyze log messages for relationships
            for i, log in enumerate(logs[:-1]):
                # Simple temporal relationship
                edge = {
                    "from": log.get("_id", f"log_{i}"),
                    "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                    "type": "FOLLOWED_BY",
                    "weight": 1.0
                }
                graph["edges"].append(edge)
                
                # Extract semantic relationships using mock extractor
                rels_from_extractor = await self.relationship_extractor.extract_relationships(
                    log["message"],
                    logs[i + 1]["message"]
                )
                for rel in rels_from_extractor:
                    graph["edges"].append({
                        "from": log.get("_id", f"log_{i}"),
                        "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                        "type": rel["type"],
                        "confidence": rel["confidence"]
                    })
        
        return graph
    
    async def prune_logs(
        self,
        older_than_days: Optional[int] = None,
        execution_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Prune old logs based on criteria."""
        stats = {"examined": 0, "deleted": 0}
        
        # Build filter conditions
        filters = []
        bind_vars = {}
        
        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            filters.append("doc.timestamp < @cutoff_date")
            bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            filters.append("doc.execution_id IN @execution_ids")
            bind_vars["execution_ids"] = execution_ids
        
        if not filters:
            logger.warning("No pruning criteria specified")
            return stats
        
        where_clause = " AND ".join(filters)
        
        # Count matching documents
        count_aql = f"""
        FOR doc IN log_events
        FILTER {where_clause}
        COLLECT WITH COUNT INTO total
        RETURN total
        """
        
        count_result = await self.query_logs(count_aql, bind_vars)
        stats["examined"] = count_result[0] if count_result else 0
        
        if not dry_run and stats["examined"] > 0:
            # Delete matching documents
            delete_aql = f"""
            FOR doc IN log_events
            FILTER {where_clause}
            REMOVE doc IN log_events
            RETURN OLD
            """
            
            deleted = await self.query_logs(delete_aql, bind_vars)
            stats["deleted"] = len(deleted)
            
            logger.info(f"Pruned {stats['deleted']} logs")
        
        return stats
    
    async def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a script execution."""
        # Get run info
        run_aql = """
        FOR doc IN script_runs
        FILTER doc.execution_id == @execution_id
        RETURN doc
        """
        
        run_info = await self.query_logs(run_aql, {"execution_id": execution_id})
        
        if not run_info:
            return {"error": "Execution not found"}
        
        # Get log statistics
        stats_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        COLLECT level = doc.level WITH COUNT INTO count
        RETURN {level: level, count: count}
        """
        
        log_stats = await self.query_logs(stats_aql, {"execution_id": execution_id})
        
        # Get errors if any
        errors_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id AND doc.level IN ["ERROR", "CRITICAL"]
        SORT doc.timestamp
        LIMIT 10
        RETURN {
            timestamp: doc.timestamp,
            message: doc.message,
            function: doc.function_name
        }
        """
        
        errors = await self.query_logs(errors_aql, {"execution_id": execution_id})
        
        # Get learnings
        learnings_aql = """
        FOR doc IN agent_learnings
        FILTER doc.execution_id == @execution_id
        RETURN {
            learning: doc.learning,
            confidence: doc.confidence,
            function: doc.function_name
        }
        """
        
        learnings = await self.query_logs(learnings_aql, {"execution_id": execution_id})
        
        summary = {
            "execution_id": execution_id,
            "run_info": run_info[0],
            "log_statistics": {stat["level"]: stat["count"] for stat in log_stats},
            "errors": errors,
            "learnings": learnings,
            "total_logs": sum(stat["count"] for stat in log_stats) if log_stats else 0
        }
        
        return summary


# Global instance getter
_manager_instance: Optional[AgentLogManager] = None


async def get_log_manager() -> AgentLogManager:
    """Get or create the global AgentLogManager instance."""
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = AgentLogManager()
        
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        await _manager_instance.initialize(db_config)
    
    return _manager_instance


async def working_usage():
    """Demonstrate AgentLogManager functionality."""
    logger.info("=== Testing AgentLogManager ===")
    
    manager = await get_log_manager()
    
    # Test 1: Script execution context
    # Note: The yield from script_execution is now the bound logger
    async with manager.script_execution("test_script", {"version": "1.0"}) as logger_ctx: 
        logger_ctx.info("Starting test operations")
        
        # Log some events
        logger_ctx.debug("Debug message")
        logger_ctx.info("Processing data")
        logger_ctx.warning("Resource usage high")
        
        # Log a learning
        await manager.log_agent_learning(
            "Discovered that batch size of 100 is optimal for this dataset",
            "process_data",
            {"batch_size": 100, "performance": "optimal"}
        )
        
        # Simulate some work
        await asyncio.sleep(1)
        
        logger_ctx.success("Operations completed")
    
    # Retrieve the execution_id from the manager after context exits
    # For a real scenario, you'd capture it when entering the context.
    # For this test, we'll get it from recent runs.
    recent_runs = await manager.query_logs(
        "FOR r IN script_runs SORT r.start_time DESC LIMIT 1 RETURN r"
    )
    exec_id = recent_runs[0]["execution_id"] if recent_runs else "unknown"


    # Test 2: Query logs
    logger.info(f"\nQuerying recent logs for execution: {exec_id}...")
    recent_logs = await manager.search_logs(
        "test",
        execution_id=exec_id,
        limit=5
    )
    logger.info(f"Found {len(recent_logs)} recent logs")
    
    # Test 3: Get execution summary
    logger.info(f"\nGetting execution summary for {exec_id}...")
    summary = await manager.get_execution_summary(exec_id)
    logger.info(f"Summary: {json.dumps(summary, indent=2)}")
    
    return True


async def debug_function():
    """Debug advanced features of AgentLogManager."""
    logger.info("=== Debug Mode: Advanced Features ===")
    
    manager = await get_log_manager()
    
    # Test 1: Complex AQL query
    logger.info("Test 1: Complex AQL query")
    aql = """
    FOR doc IN log_events
    FILTER doc.level IN ["ERROR", "CRITICAL"]
    COLLECT level = doc.level INTO logs
    RETURN {
        level: level,
        count: LENGTH(logs),
        recent: (
            FOR log IN logs
            SORT log.doc.timestamp DESC
            LIMIT 3
            RETURN log.doc.message
        )
    }
    """
    
    results = await manager.query_logs(aql)
    logger.info(f"Error summary: {results}")
    
    # Test 2: Build execution graph
    logger.info("\nTest 2: Building execution graph")
    
    # Create a test execution with related logs
    async with manager.script_execution("graph_test") as logger_ctx:
        logger_ctx.info("Step 1: Initialize")
        logger_ctx.info("Step 2: Load data")
        logger_ctx.error("Step 3: Connection failed")
        logger_ctx.info("Step 4: Retrying connection")
        logger_ctx.success("Step 5: Connection restored")
        
        await asyncio.sleep(1)

    recent_runs = await manager.query_logs(
        "FOR r IN script_runs SORT r.start_time DESC LIMIT 1 RETURN r"
    )
    exec_id_graph = recent_runs[0]["execution_id"] if recent_runs else "unknown"

    graph = await manager.build_execution_graph(exec_id_graph)
    logger.info(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    
    # Test 3: Prune logs (dry run)
    logger.info("\nTest 3: Pruning old logs (dry run)")
    prune_stats = await manager.prune_logs(
        older_than_days=30,
        dry_run=True
    )
    logger.info(f"Would prune: {prune_stats}")
    
    return True


if __name__ == "__main__":
    import sys
    import os
    import socket 
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logger with ArangoDB sink
    from arango_log_sink import get_arango_sink
    
    # For standalone scripts, logger.remove() is used to ensure a clean slate,
    # preventing duplicate output if run multiple times in a session.
    # In a larger, long-running application, logging setup should be centralized
    # and might not involve calling logger.remove() indiscriminately.
    logger.remove() 
    logger.add(sys.stderr, level="INFO") # Add a console handler for general output
    
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True, level="DEBUG") # Add ArangoDB sink
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        success = False
        try:
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function()
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage()
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            success = False
        finally:
            # Ensure sink is properly closed
            if sink:
                logger.info("Stopping ArangoLogSink...")
                await sink.stop()
                logger.info("ArangoLogSink stopped.")
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

---
File: proof_of_concept/logger_agent/src/enhanced_script_template.py
---
```python
#!/usr/bin/env python3
"""
enhanced_script_template.py - Python script template with Logger Agent integration

Demonstrates how to integrate the Logger Agent into standard Python scripts
for comprehensive logging and introspection capabilities.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta 

# Third-party imports
from loguru import logger
import redis
from dotenv import load_dotenv

# Logger Agent imports
from agent_log_manager import get_log_manager 
from arango_log_sink import get_arango_sink   

# Load environment
load_dotenv()

# Configure logging with ArangoDB sink
# For standalone scripts, logger.remove() is used to ensure a clean slate,
# preventing duplicate output if run multiple times in a session.
# In a larger, long-running application, logging setup should be centralized
# and might not involve calling logger.remove() indiscriminately.
logger.remove()  

# Add console output
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Add ArangoDB sink
sink = get_arango_sink()
logger.add(sink.write, enqueue=True, level="DEBUG")

# Optional: Add file logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / f"{Path(__file__).stem}_{{time}}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)

# Redis connection
try:
    redis_client = redis.Redis(decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis is available and connected.")
except Exception as e:
    logger.warning(f"Redis not available: {e} - some features will be limited")
    redis_client = None
    REDIS_AVAILABLE = False


# ============================================
# CORE FUNCTIONS
# ============================================

async def process_data_with_logging(
    data: List[Dict[str, Any]],
    threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Process data with comprehensive logging and learning capture.
    
    Args:
        data: List of data items to process
        threshold: Processing threshold
        
    Returns:
        Processing results with statistics
    """
    manager = await get_log_manager()
    
    logger.info(f"Processing {len(data)} items with threshold {threshold}")
    
    results = {
        "processed": 0,
        "above_threshold": 0,
        "errors": 0,
        "items": []
    }
    
    for i, item in enumerate(data):
        try:
            # Log progress periodically
            if i % 100 == 0:
                # Use logger_ctx (which is the default logger here as it's bound globally by script_execution)
                logger.debug(f"Processing item {i}/{len(data)}")
            
            # Simulate an error for stress test
            if 'execution_id' in logger._extra and 'stress_test' in logger._extra['script_name'] and item.get("id") == "item_500":
                 raise ValueError("Simulated error for item 500 in stress test")

            # Process item
            score = item.get("value", 0) * item.get("weight", 1)
            
            if score > threshold:
                results["above_threshold"] += 1
                
                # Log interesting findings
                if score > threshold * 1.5:
                    logger.info(
                        f"High score item found: {item.get('id')} (score: {score:.2f})"
                    )
            
            results["items"].append({
                "id": item.get("id"),
                "score": score,
                "passed": score > threshold
            })
            
            results["processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing item {i} (id: {item.get('id')}): {e}", 
                         extra_data={"item_id": item.get('id'), "error_type": type(e).__name__})
            results["errors"] += 1
            
            # Learn from error
            await manager.log_agent_learning(
                f"Item processing failed with: {type(e).__name__}. "
                f"Consider adding validation for {list(item.keys())}",
                "process_data_with_logging",
                {"error_type": type(e).__name__, "item_keys": list(item.keys())}
            )
    
    # Log summary
    logger.success(
        f"Processing complete: {results['processed']} processed, "
        f"{results['above_threshold']} above threshold, "
        f"{results['errors']} errors"
    )
    
    # Record learnings if we discovered patterns
    if len(data) > 0 and results["errors"] / len(data) > 0.1:  # More than 10% errors
        await manager.log_agent_learning(
            f"High error rate ({results['errors']}/{len(data)}) detected. "
            f"Data quality issues may be present.",
            "process_data_with_logging",
            {"error_rate": results["errors"] / len(data)},
            confidence=0.9
        )
    
    return results


async def analyze_historical_performance(
    script_name: str,
    lookback_days: int = 7
) -> Dict[str, Any]:
    """
    Analyze historical performance of a script using logged data.
    
    Args:
        script_name: Name of script to analyze
        lookback_days: Number of days to look back
        
    Returns:
        Performance analysis results
    """
    manager = await get_log_manager()
    
    # Query historical executions
    aql = """
    FOR run IN script_runs
    FILTER run.script_name == @script_name
    FILTER run.start_time >= DATE_SUBTRACT(DATE_NOW(), @days, "days")
    
    LET log_counts = (
        FOR log IN log_events
        FILTER log.execution_id == run.execution_id
        COLLECT level = log.level WITH COUNT INTO count
        RETURN {level: level, count: count}
    )
    
    RETURN {
        execution_id: run.execution_id,
        start_time: run.start_time,
        duration: run.duration_seconds,
        status: run.status,
        log_summary: log_counts
    }
    """
    
    results = await manager.query_logs(
        aql,
        {"script_name": script_name, "days": lookback_days}
    )
    
    # Analyze results
    analysis = {
        "total_runs": len(results),
        "successful_runs": sum(1 for r in results if r["status"] == "success"),
        "failed_runs": sum(1 for r in results if r["status"] == "failed"),
        "avg_duration": sum(r.get("duration", 0) for r in results) / len(results) if results else 0,
        "error_trend": []
    }
    
    # Calculate error trend
    for result in results:
        error_count = sum(
            log["count"] for log in result.get("log_summary", [])
            if log["level"] in ["ERROR", "CRITICAL"]
        )
        analysis["error_trend"].append({
            "time": result["start_time"],
            "errors": error_count
        })
    
    logger.info(f"Historical analysis complete: {analysis}")
    
    return analysis


async def working_usage():
    """Demonstrate working usage with Logger Agent integration."""
    logger.info("=== Running Working Usage Example ===")
    
    manager = await get_log_manager()
    
    # Use script execution context
    async with manager.script_execution(
        "enhanced_template_demo",
        {"mode": "working", "version": "1.0"}
    ) as logger_ctx: # `script_execution` yields logger_ctx with bound context
        
        logger_ctx.info("Starting test operations")
        
        # Generate test data
        test_data = [
            {"id": f"item_{i}", "value": i * 0.1, "weight": 1.0}
            for i in range(100)
        ]
        
        # Process data
        results = await process_data_with_logging(test_data, threshold=5.0)
        
        # Save results with execution context
        output_dir = Path("/tmp/logger_agent_responses") # Changed directory to avoid conflicts
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"results_{logger_ctx._extra['execution_id']}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "execution_id": logger_ctx._extra['execution_id'],
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }, f, indent=2)
        
        logger_ctx.info(f"Results saved to: {output_file}")
        
        # Query our own logs
        recent_errors = await manager.search_logs(
            "error",
            execution_id=logger_ctx._extra['execution_id'],
            level="ERROR"
        )
        
        if recent_errors:
            logger_ctx.warning(f"Found {len(recent_errors)} errors in this execution")
        
        # Analyze historical performance
        analysis = await analyze_historical_performance(
            "enhanced_template_demo",
            lookback_days=7
        )
        
        logger_ctx.info(f"Success rate: {analysis['successful_runs']}/{analysis['total_runs']}")
    
    return True


async def debug_function():
    """Debug function for testing Logger Agent features."""
    logger.info("=== Running Debug Function ===")
    
    manager = await get_log_manager()
    
    # Test querying across executions
    logger.info("Searching for patterns across all executions...")
    
    pattern_aql = """
    FOR learning IN agent_learnings
    FILTER learning.confidence >= 0.8
    COLLECT pattern = learning.learning WITH COUNT INTO occurrences
    FILTER occurrences > 1
    SORT occurrences DESC
    LIMIT 10
    RETURN {
        pattern: pattern,
        occurrences: occurrences
    }
    """
    
    patterns = await manager.query_logs(pattern_aql)
    
    if patterns:
        logger.info("Recurring patterns found:")
        for pattern in patterns:
            logger.info(f"  - {pattern['pattern'][:100]}... ({pattern['occurrences']} times)")
    else:
        logger.info("No recurring patterns found yet.")
    
    # Test error analysis
    logger.info("\nAnalyzing error patterns...")
    
    error_aql = """
    FOR log IN log_events
    FILTER log.level IN ["ERROR", "CRITICAL"]
    FILTER log.timestamp >= DATE_SUBTRACT(DATE_NOW(), 1, "days")
    COLLECT function = log.function_name INTO errors
    SORT LENGTH(errors) DESC
    LIMIT 5
    RETURN {
        function: function,
        error_count: LENGTH(errors),
        sample_messages: (
            FOR e IN errors
            LIMIT 3
            RETURN e.log.message
        )
    }
    """
    
    error_analysis = await manager.query_logs(error_aql)
    
    if error_analysis:
        for func_errors in error_analysis:
            logger.warning(
                f"Function '{func_errors['function']}' had "
                f"{func_errors['error_count']} errors"
            )
    else:
        logger.info("No error patterns found in the last day.")
    
    return True


async def stress_test():
    """Stress test Logger Agent with high volume."""
    logger.info("=== Running Stress Test ===")
    
    manager = await get_log_manager()
    
    async with manager.script_execution("stress_test") as logger_ctx:
        
        # Test 1: High volume logging
        logger_ctx.info("Test 1: High volume logging (10,000 logs)")
        
        start_time = datetime.utcnow()
        
        test_data = [
            {"id": f"item_{i}", "value": i * 0.01, "weight": 1.0}
            for i in range(10000)
        ]
        
        # Call processing function with data, which logs extensively
        # This function will also simulate an error for 'item_500' if running in stress_test mode
        results = await process_data_with_logging(test_data, threshold=0.5)

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger_ctx.success(f"Processed 10,000 messages and logged extensively in {duration:.2f} seconds")
        
        # Test 2: Complex queries
        logger_ctx.info("\nTest 2: Complex aggregation query")
        
        # Adding explicit batched logs for the AQL to pick up
        for i in range(0, 1000, 100):
            logger_ctx.bind(batch_num=i // 100).info(f"Batch {i//100} checkpoint.")

        complex_aql = """
        FOR log IN log_events
        FILTER log.execution_id == @execution_id
        FILTER log.extra_data.batch_num != null 
        COLLECT level = log.level, batch = log.extra_data.batch_num
        WITH COUNT INTO count
        RETURN {
            level: level,
            batch: batch,
            count: count
        }
        """
        
        results = await manager.query_logs(
            complex_aql,
            {"execution_id": logger_ctx._extra['execution_id']}
        )
        
        logger_ctx.info(f"Aggregation returned {len(results)} groups for batch checkpoints.")
        
        # Test 3: Concurrent operations
        logger_ctx.info("\nTest 3: Concurrent logging")
        
        async def concurrent_logger(worker_id: int):
            for i in range(100):
                # Ensure each concurrent log carries the main execution_id from the context manager
                logger_ctx.bind(worker=worker_id, concurrent_log_id=i).info(f"Worker {worker_id} log {i}")
                # Small sleep to simulate work and allow other tasks to run
                await asyncio.sleep(0.001) 
        
        workers = [concurrent_logger(i) for i in range(10)]
        await asyncio.gather(*workers)
        
        logger_ctx.success("Stress test completed")
    
    # Get final statistics (use the execution_id from the context manager)
    summary = await manager.get_execution_summary(logger_ctx._extra['execution_id'])
    logger.info(f"Total logs generated for stress test: {summary['total_logs']}")
    
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        """Main entry point with Logger Agent lifecycle."""
        success = False
        try:
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
            
        except Exception as e:
            logger.error(f"An unhandled error occurred in main: {e}", exc_info=True)
            return False
        finally:
            # Ensure sink is properly closed
            if sink:
                logger.info("Stopping ArangoLogSink...")
                await sink.stop()
                logger.info("ArangoLogSink stopped.")
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

---
File: proof_of_concept/logger_agent/src/logger_monitor.py
---
```python
#!/usr/bin/env python3
"""
logger_monitor.py - Simple terminal monitoring for Logger Agent
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from dotenv import load_dotenv 
import os 
import sys 

# Logger Agent imports
from agent_log_manager import get_log_manager 
from arango_log_sink import get_arango_sink   
from loguru import logger 


# Load environment variables
load_dotenv()

# Configure loguru for console output for the monitor script itself
# For standalone scripts, logger.remove() is used to ensure a clean slate,
# preventing duplicate output if run multiple times in a session.
# In a larger, long-running application, logging setup should be centralized
# and might not involve calling logger.remove() indiscriminately.
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

console = Console()

async def monitor_dashboard():
    """Display live monitoring dashboard."""
    # Initialize the log manager (this will also implicitly initialize the ArangoDB sink in the background)
    manager = await get_log_manager()
    
    console.print("[bold green]Starting Logger Agent Monitor...[/bold green]")
    
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            # Get current stats
            stats_aql = """
            LET recent_logs = (
                FOR log IN log_events
                FILTER log.timestamp >= DATE_SUBTRACT(DATE_NOW(), 5, "minutes")
                COLLECT level = log.level WITH COUNT INTO count
                RETURN {level: level, count: count}
            )
            
            LET active_runs = (
                FOR run IN script_runs
                FILTER run.status == "running"
                RETURN run
            )

            LET total_logs_in_db = (
                RETURN LENGTH(log_events)
            )
            
            LET total_runs_in_db = (
                RETURN LENGTH(script_runs)
            )

            LET total_learnings_in_db = (
                RETURN LENGTH(agent_learnings)
            )
            
            RETURN {
                recent_logs: recent_logs,
                active_runs: active_runs,
                total_logs_in_db: total_logs_in_db[0],
                total_runs_in_db: total_runs_in_db[0],
                total_learnings_in_db: total_learnings_in_db[0],
                timestamp: DATE_NOW()
            }
            """
            
            try:
                stats = await manager.query_logs(stats_aql)
            except Exception as e:
                logger.error(f"Failed to fetch stats from ArangoDB: {e}")
                stats = None # Set stats to None if query fails

            # Create table
            table = Table(title=f"Logger Agent Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            # Add stats
            if stats:
                data = stats[0]
                
                table.add_row("Total Logs (DB)", str(data.get("total_logs_in_db", 0)))
                table.add_row("Total Runs (DB)", str(data.get("total_runs_in_db", 0)))
                table.add_row("Total Learnings (DB)", str(data.get("total_learnings_in_db", 0)))

                table.add_section() # Separator

                # Log levels for recent logs
                recent_log_counts = {item['level']: item['count'] for item in data.get("recent_logs", [])}
                
                # Ensure all common levels are shown, even if 0
                for level_name in ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]:
                    table.add_row(
                        f"{level_name} (last 5 min)",
                        str(recent_log_counts.get(level_name, 0))
                    )
                
                table.add_section() # Separator

                # Active runs
                active_runs_list = data.get("active_runs", [])
                table.add_row(
                    "Active Runs",
                    str(len(active_runs_list))
                )
                if active_runs_list:
                    for run in active_runs_list:
                        table.add_row(
                            "", # Empty first column for sub-item
                            f"- [yellow]{run['script_name']}[/yellow] ({run['execution_id']})"
                        )

            else:
                table.add_row("Status", "[red]No data from ArangoDB or connection failed.[/red]")
            
            live.update(table)
            await asyncio.sleep(int(os.getenv("MONITORING_INTERVAL", "5"))) # Use interval from .env

if __name__ == "__main__":
    # Ensure uvloop is set early for consistency
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # Run the dashboard
    asyncio.run(monitor_dashboard())

```

---
File: proof_of_concept/logger_agent/prompts/queries/find_errors_in_execution.md
---
```markdown
# Find Errors in Execution

## Purpose
Query the Logger Agent to find all errors that occurred during a specific execution.

## Code Template

```python
from agent_log_manager import get_log_manager
from datetime import datetime, timedelta # Import for time context

async def find_execution_errors(execution_id: str):
    """Find all errors in a specific execution."""
    manager = await get_log_manager()
    
    # Query for errors and their context
    aql = """
    FOR log IN log_events
    FILTER log.execution_id == @execution_id
    FILTER log.level IN ["ERROR", "CRITICAL"]
    
    LET context = (
        FOR ctx IN log_events
        FILTER ctx.execution_id == log.execution_id
        FILTER ctx.timestamp >= DATE_SUBTRACT(log.timestamp, 5, "seconds")
        FILTER ctx.timestamp <= DATE_ADD(log.timestamp, 5, "seconds")
        SORT ctx.timestamp
        RETURN {
            time: ctx.timestamp,
            level: ctx.level,
            message: ctx.message
        }
    )
    
    RETURN {
        error: log,
        context: context
    }
    """
    
    results = await manager.query_logs(aql, {"execution_id": execution_id})
    
    for error_data in results:
        error = error_data["error"]
        print(f"\n❌ ERROR at {error['timestamp']}")
        print(f"   Function: {error['function_name']}")
        print(f"   Message: {error['message']}")
        print(f"   File: {error['file_path']}:{error['line_number']}")
        
        print("\n   Context:")
        for ctx in error_data["context"]:
            print(f"   [{ctx['level']}] {ctx['message'][:80]}...")

# Example Usage (assuming you have an execution_id)
# async def main():
#     # Replace with an actual execution ID from your logs
#     test_execution_id = "test_script_20231027_123456_abcdef" 
#     await find_execution_errors(test_execution_id)
#
# if __name__ == "__main__":
#     import asyncio
#     from dotenv import load_dotenv
#     load_dotenv() # Load environment variables for DB connection
#     asyncio.run(main())
```

## Usage
1. Replace `execution_id` with your actual execution ID
2. The query returns errors with 5 seconds of context before and after
3. Use the context to understand what led to the error
```

---
File: proof_of_concept/logger_agent/prompts/guides/using_logger_agent.md
---
```markdown
# Using Logger Agent - Agent Guide

## Overview
The Logger Agent provides comprehensive logging and introspection capabilities for AI agents. This guide shows how to effectively use the system.

## Basic Usage

### 1. Import and Initialize
```python
from agent_log_manager import get_log_manager
from arango_log_sink import get_arango_sink
from loguru import logger
from datetime import datetime, timedelta # Often useful for queries
import sys # Needed for logger.add(sys.stderr)
from dotenv import load_dotenv # To load .env variables for DB config

# Load environment variables
load_dotenv()

# IMPORTANT: Remove default loguru handlers to avoid duplicate output.
# For standalone scripts, this ensures a clean slate. In a larger, long-running
# application, loguru configuration should be centralized and might not involve
# calling logger.remove() indiscriminately.
logger.remove() 

# Add console output (optional, but good for local debugging)
logger.add(
    sys.stderr, 
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Get and add ArangoDB sink to logger
# This step initializes the sink and starts its background tasks.
sink = get_arango_sink()
logger.add(sink.write, enqueue=True, level="DEBUG") # enqueue=True is critical for async

# Get manager instance
# This initializes the connection to ArangoDB and mock integration modules.
manager = await get_log_manager()

# You can now use the `logger` object and `manager` instance.
```

### 2. Script Execution Context
```python
# Always use execution context for tracking
# The context manager now yields the logger instance, bound with execution_id and script_name.
async with manager.script_execution("my_script", {"version": "1.0"}) as logger_ctx: 
    logger_ctx.info("Starting script operations")
    # Your code here. Use logger_ctx for all logging within this context.
    logger_ctx.debug("Performing sub-task A.")
    # If an exception occurs, it will automatically be logged and the run status updated.
    # raise ValueError("Something went wrong!") 
    logger_ctx.success("Script completed")
# Once the 'async with' block exits, the script run record is finalized.
```

### 3. Logging Best Practices
```python
# Use appropriate log levels (using the context-bound logger_ctx)
logger_ctx.debug("Detailed debugging information for developers.")
logger_ctx.info("General information about script progress.")
logger_ctx.warning("Warning conditions, e.g., low disk space or high resource usage.")
logger_ctx.error("Error conditions that prevent a part of the script from completing.")
logger_ctx.critical("Critical failures that cause the entire script to halt.")

# Bind context data using `logger.bind()`
# This attaches extra key-value pairs to the log record, making it searchable.
logger_ctx.bind(user_id="123", action="process_data", data_size=1000).info("Processing user request")

# Log structured data - directly include objects in bind()
response_data = {"status": "success", "items_processed": 42, "elapsed_time_ms": 150}
logger_ctx.bind(response=response_data).info("API response received.")

# For sensitive data, use truncation or avoid logging directly
sensitive_data = "data:image/png;base64,VERYLONGSENSITIVEDATAGOESHERE..."
logger_ctx.bind(image_data=sensitive_data).debug("Image data preview (truncated if too long).") 
# The ArangoLogSink's `write` method uses `log_safe_results` internally to truncate large values.
```

### 4. Recording Agent Learnings
```python
# Record insights and patterns your agent discovers during its execution.
# This creates a separate `agent_learnings` record in ArangoDB.
await manager.log_agent_learning(
    "Discovered that batch size of 100 is optimal for this dataset type, reducing memory peaks.",
    "process_data_module", # The function or module where the learning occurred
    {"dataset_size_mb": 1000, "optimal_batch_size": 100, "observed_memory_peak_mb": 500},
    confidence=0.9 # How confident is the agent in this learning?
)

# Example for an error learning:
await manager.log_agent_learning(
    "Identified a recurring 'Connection Timeout' error when connecting to ExternalAPI. Recommend increasing timeout to 30s.",
    "external_api_call",
    {"error_type": "ConnectionTimeout", "recommended_action": "Increase timeout"},
    confidence=0.95
)
```

## Advanced Queries

### Find Recent Errors
```python
# Requires 'datetime' and 'timedelta' imports (from datetime import datetime, timedelta)
errors = await manager.search_logs(
    "timeout OR connection failed", # Search for messages containing these keywords
    level="ERROR",                 # Filter by log level
    time_range={"start": datetime.utcnow() - timedelta(hours=1)}, # Logs from the last hour
    limit=20                       # Limit results
)

print(f"Found {len(errors)} errors in the last hour.")
for error in errors:
    print(f"[{error['timestamp']}] {error['level']}: {error['message']} (Execution: {error['execution_id']})")
```

### Analyze Performance Patterns
```python
# Query `script_runs` collection for overall script performance
aql = """
FOR run IN script_runs
FILTER run.script_name == @script_name
SORT run.start_time DESC

COLLECT status = run.status WITH COUNT INTO count
RETURN {status: status, count: count}
"""

results = await manager.query_logs(aql, {"script_name": "my_script"})

print(f"Performance summary for 'my_script': {results}")

# Example: Get average duration for successful runs
aql_duration = """
FOR run IN script_runs
FILTER run.script_name == @script_name AND run.status == "success" AND run.duration_seconds != null
RETURN run.duration_seconds
"""
successful_durations = await manager.query_logs(aql_duration, {"script_name": "my_script"})
if successful_durations:
    avg_duration = sum(successful_durations) / len(successful_durations)
    print(f"Average successful duration for 'my_script': {avg_duration:.2f} seconds")
```

### Extract Learnings Across Executions
```python
aql = """
FOR learning IN agent_learnings
FILTER learning.confidence >= 0.8
SORT learning.timestamp DESC
LIMIT 20
RETURN learning
"""

learnings = await manager.query_logs(aql)

print(f"Found {len(learnings)} recent high-confidence learnings:")
for learning in learnings:
    print(f"- [{learning['timestamp']}] Learning: {learning['learning'][:80]}... (Confidence: {learning['confidence']})")
```

## Tips for Effective Logging

1.  **Always use execution context** (`async with manager.script_execution(...)`) - It automatically groups related logs, making it easy to trace an entire operation.
2.  **Log at appropriate levels** - Avoid logging everything as `INFO`. Use `DEBUG` for verbose details, `INFO` for significant milestones, `WARNING` for potential issues, `ERROR` for failures, and `CRITICAL` for system-threatening problems.
3.  **Include structured data** - Use `logger_ctx.bind()` to add searchable key-value pairs (e.g., `user_id`, `item_id`, `status`). This is far more powerful than parsing messages.
4.  **Record learnings** (`manager.log_agent_learning()`) - When your agent identifies a pattern, a solution, or an important insight, log it as a learning. This builds a knowledge base.
5.  **Query your history** - Regularly query `log_events`, `script_runs`, and `agent_learnings` to understand past behavior, diagnose recurring issues, and validate improvements.
6.  **Monitor performance** - Log key metrics like duration, processed item counts, etc., and use them in AQL queries to track performance trends over time.

## Common Patterns

### Error Recovery Pattern
```python
import random # For simulated error
from tenacity import retry, stop_after_attempt, wait_fixed # Example for retry logic

async def risky_operation():
    # Simulate an operation that might fail
    if random.random() < 0.3: 
        raise ConnectionError("Simulated connection timeout")
    return "Operation successful"

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def resilient_operation(manager_instance, logger_ctx): # Pass manager and logger_ctx
    try:
        result = await risky_operation()
        logger_ctx.info("Resilient operation successful.")
        return result
    except ConnectionError as e:
        logger_ctx.error(f"Attempt failed, retrying: {e}")
        # Log learning about this specific error type
        await manager_instance.log_agent_learning( # Use manager_instance
            f"Encountered and retrying connection error: {e}",
            "resilient_operation",
            {"error_type": "ConnectionError", "attempt": resilient_operation.retry.statistics['attempt_number']},
            confidence=0.7 # Lower confidence for retryable errors
        )
        raise # Re-raise to trigger tenacity retry


# In your main script logic:
# manager = await get_log_manager() # Ensure manager is available
# async with manager.script_execution("error_handling_demo") as logger_ctx:
#     try:
#         await resilient_operation(manager, logger_ctx) # Pass manager and logger_ctx
#     except Exception as e:
#         logger_ctx.critical(f"Resilient operation failed after multiple retries: {e}")
#         # Search for similar historical issues to inform further action
#         similar_errors = await manager.search_logs(
#             "ConnectionError",
#             level="ERROR",
#             time_range={"start": datetime.utcnow() - timedelta(days=7)},
#             limit=5
#         )
#         if similar_errors:
#             logger_ctx.info(f"Found {len(similar_errors)} similar past errors.")
#             # Use the information to adapt strategy (e.g., alert human, switch endpoint)
```

### Performance Monitoring
```python
async def important_data_processing_task(logger_ctx, data_to_process: int):
    start_time = datetime.utcnow()
    # Simulate data processing
    await asyncio.sleep(data_to_process / 10000.0) 
    end_time = datetime.utcnow()
    duration_seconds = (end_time - start_time).total_seconds()

    logger_ctx.bind(
        data_processed=data_to_process,
        duration_seconds=duration_seconds,
        items_per_second=data_to_process / duration_seconds if duration_seconds > 0 else 0
    ).info("Important data processing task completed.")

# In your main script logic:
# manager = await get_log_manager() # Ensure manager is available
# async with manager.script_execution("performance_monitor_demo") as logger_ctx:
#     await important_data_processing_task(logger_ctx, 5000)
#     await important_data_processing_task(logger_ctx, 15000)

# Later, analyze performance:
aql = """
FOR log IN log_events
FILTER log.script_name == @script_name AND log.extra_data.duration_seconds != null
SORT log.timestamp DESC
LIMIT 100 # Look at recent 100 relevant logs

COLLECT 
    day = DATE_FORMAT(log.timestamp, "%Y-%m-%d")
WITH INTO daily_logs = { 
    avg_duration: AVG(log.extra_data.duration_seconds),
    avg_items_per_second: AVG(log.extra_data.items_per_second),
    total_processed: SUM(log.extra_data.data_processed)
}
SORT day DESC
RETURN {
    day: day,
    stats: daily_logs
}
"""
performance_trends = await manager.query_logs(aql, {"script_name": "performance_monitor_demo"})
print("Daily Performance Trends:")
for trend in performance_trends:
    print(f"- Day: {trend['day']}, Avg Duration: {trend['stats']['avg_duration']:.2f}s, Avg Items/Sec: {trend['stats']['avg_items_per_second']:.2f}, Total Processed: {trend['stats']['total_processed']}")
```

## Remember
- Logs are automatically batched and sent asynchronously to ArangoDB.
- Failed logs are buffered to disk and retried when the database becomes available.
- Use ArangoDB's AQL for complex and powerful queries across executions.
- The system is designed to be non-blocking and minimize impact on your main application's performance.
```