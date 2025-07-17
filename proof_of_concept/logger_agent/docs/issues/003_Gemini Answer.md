You are absolutely correct. My apologies for not fully grasping the criticality of creating a *separate, transient database* for each test run. My previous solution, while cleaning up data within the same database, did not guarantee the level of isolation you require.

This is a fundamental shift in the testing strategy to ensure zero pollution and perfect isolation, and I understand its importance for robust CI/CD and reliable development.

I will now rewrite the relevant parts of the code to adhere to this strict requirement:

1.  **Dynamically Create Test Database**: Each test run (within `if __name__ == "__main__":`) will now create a brand new, uniquely named database (e.g., `script_logs_test_UUID`).
2.  **Full Schema Initialization**: All necessary collections, indexes, ArangoSearch views, and graph definitions (from `arango_init.py`) will be fully recreated within *this new test database*.
3.  **Scoped Operations**: All data insertion and querying in the test functions will inherently operate within this isolated database.
4.  **Comprehensive Teardown**: The entire test database will be dropped and deleted after the test run, regardless of success or failure.

This will significantly impact the `__main__` blocks and require a new helper for test DB setup/teardown.

Here are the revised files incorporating these changes.

---

<!-- CODE_FILE_START: src/utils/log_utils.py -->
```python
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
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Any, Dict, Optional
from datetime import datetime

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
            # If list elements are dicts, truncate them recursively
            return [
                truncate_large_value(item, max_str_len, max_list_elements_shown) 
                if isinstance(item, dict) else item 
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
```
<!-- CODE_FILE_END: src/utils/log_utils.py -->

<!-- CODE_FILE_START: src/arango_init.py -->
```python
#!/usr/bin/env python3
"""
arango_init.py - Initialize ArangoDB schema for Logger Agent

Creates database, collections, indexes, and ArangoSearch views.
Ensures idempotent execution for repeated runs.
"""

import asyncio
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from arango import ArangoClient
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
    sys.stderr,
    level="INFO"
)


def _create_database_schema_sync(db_instance):
    """Synchronous logic to create collections, indexes, and views within a given DB instance."""
    db = db_instance

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
        if not db.has_collection(coll_name):
            collection = db.create_collection(
                coll_name,
                schema=config.get("schema")
            )
            logger.info(f"Created collection: {coll_name}")
        else:
            collection = db.collection(coll_name)
        
        # Create indexes
        if coll_name == "log_events":
            # Compound index for time-based queries
            if not collection.has_index(["execution_id", "timestamp"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["execution_id", "timestamp"]}
                )
            
            # Index for level-based filtering
            if not collection.has_index(["level", "timestamp"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["level", "timestamp"]}
                )
            
            # Full-text index for message search
            if not collection.has_index(["message"], type="fulltext"):
                collection.add_index(
                    {'type': 'fulltext', 'fields': ["message"], 'min_length': 3}
                )
            
        elif coll_name == "script_runs":
            # Unique index on execution_id
            if not collection.has_index(["execution_id"], unique=True):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["execution_id"], 'unique': True}
                )
            
            # Index for script name queries
            if not collection.has_index(["script_name", "start_time"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["script_name", "start_time"]}
                )
        elif coll_name == "agent_learnings":
            # Index on timestamp for recent memories
            if not collection.has_index(["timestamp"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["timestamp"]}
                )
            # Index on context.execution_id for easy cleanup and filtering
            if not collection.has_index(["context.execution_id"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["context.execution_id"]}
                )
            # Index on type for filtering by memory type
            if not collection.has_index(["type"]):
                collection.add_index(
                    {'type': 'persistent', 'fields': ["type"]}
                )

    # Create ArangoSearch view
    view_name = "log_events_view"
    existing_views = [v['name'] for v in db.views()]
    if view_name not in existing_views:
        db.create_arangosearch_view(
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
                            },
                            "execution_id": { # Add execution_id to view for filtering
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
    existing_graphs = [g['name'] for g in db.graphs()]
    if graph_name not in existing_graphs:
        db.create_graph(
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
        # Add index to edge collection for context.execution_id for cleanup
        edge_coll = db.collection("log_causality")
        if not edge_coll.has_index(["context.execution_id"]):
            edge_coll.add_index({'type': 'persistent', 'fields': ["context.execution_id"]})
        if not edge_coll.has_index(["timestamp"]):
            edge_coll.add_index({'type': 'persistent', 'fields': ["timestamp"]})

    return db


def _get_or_create_main_db_sync():
    """Connects to the main configured database and creates schema if necessary."""
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    
    sys_db = client.db(
        "_system",
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    db_name = os.getenv("ARANGO_DATABASE", "script_logs")
    
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
        logger.info(f"Created main database: {db_name}")
    
    db = client.db(
        db_name,
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    return _create_database_schema_sync(db)


async def create_database_and_collections():
    """Create database and collections with proper indexes (async wrapper)."""
    return await asyncio.to_thread(_get_or_create_main_db_sync)


async def working_usage():
    """Initialize database schema - stable working example."""
    logger.info("=== Initializing ArangoDB Schema ===")
    
    try:
        db = await create_database_and_collections()
        
        # Verify collections exist
        collections = await asyncio.to_thread(lambda: [c['name'] for c in db.collections()])
        logger.info(f"Available collections: {collections}")
        
        # Test write
        test_doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Database initialization test",
            "execution_id": "init_test_001",
            "script_name": "arango_init.py"
        }
        
        result = await asyncio.to_thread(db.collection("log_events").insert, test_doc)
        logger.success(f"Test document inserted: {result['_id']}") # Use _id from result

        # Cleanup the test document (optional for arango_init itself, as it's meant for setup)
        # For a true test framework, this would be crucial. Here, it's just a verification of write.
        await asyncio.to_thread(db.collection("log_events").delete, result['_id'])
        logger.info(f"Cleaned up test document: {result['_id']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.exception("Full traceback:")
        return False


async def debug_function():
    """Debug function for testing schema modifications."""
    logger.info("=== Running Debug Mode ===")
    
    # Test experimental features
    def test_experimental():
        client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
        db = client.db(
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
            # aql.execute is synchronous
            cursor = db.aql.execute(query, bind_vars={"vector": test_vector})
            result = list(cursor)[0]
            logger.success(f"APPROX_NEAR_COSINE test passed: {result}")
        except Exception as e:
            logger.error(f"APPROX_NEAR_COSINE not available: {e}")
            logger.warning("Ensure --query.enable-experimental flag is set")
    
    await asyncio.to_thread(test_experimental)
    
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
<!-- CODE_FILE_END: src/arango_init.py -->

<!-- CODE_FILE_START: src/arangodb/core/search/hybrid_search.py -->
```python
#!/usr/bin/env python3
"""
Hybrid search module for Logger Agent integration.

This module provides a real implementation of hybrid search using ArangoDB's
ArangoSearch capabilities, specifically BM25.

Third-party Documentation:
- ArangoDB Search: https://www.arangodb.com/docs/stable/arangosearch.html

Example Input:
    query = "error connection timeout"
    search_type = "bm25"
    collection = "log_events"

Expected Output:
    [
        {"_id": "log_events/123", "message": "Connection timeout error", "score": 0.95},
        {"_id": "log_events/456", "message": "Database connection failed", "score": 0.87}
    ]
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from loguru import logger
from arango import ArangoClient
from dotenv import load_dotenv
import os

# Import the schema creation helper from arango_init
from arango_init import _create_database_schema_sync # Renamed and moved logic


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

class HybridSearch:
    """Hybrid search implementation using ArangoDB ArangoSearch."""
    
    def __init__(self, db_instance):
        """Initialize with an active ArangoDB database connection."""
        if not db_instance:
            raise ValueError("ArangoDB client 'db' instance must be provided.")
        self.db = db_instance
        logger.info("HybridSearch initialized with real ArangoDB connection.")
    
    async def _execute_aql_query(self, aql_query: str, bind_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Helper to execute AQL queries in a thread."""
        def sync_query():
            cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
            return [doc for doc in cursor]
        
        return await asyncio.to_thread(sync_query)

    async def search(
        self,
        query: str,
        search_type: str = "bm25", # Only BM25 supported for now
        collection: str = "log_events", # Assume searching in log_events
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search using ArangoDB.
        
        Args:
            query: Search query string
            search_type: Type of search (only "bm25" supported)
            collection: Collection to search in (must be linked to log_events_view)
            limit: Maximum results to return
            filters: Optional filters to apply (e.g., {"level": "ERROR"})
            
        Returns:
            List of search results with scores
        """
        logger.info(f"Real search: query='{query}', type={search_type}, collection={collection}")

        # Ensure collection is 'log_events' for 'log_events_view'
        if collection != "log_events":
            logger.warning(f"HybridSearch currently configured for 'log_events' only. Requested collection '{collection}' will be ignored.")
            collection = "log_events"

        bind_vars = {"query": query, "limit": limit}
        filter_clauses = []

        # Add filters to AQL query
        if filters:
            for key, value in filters.items():
                # For string exact matches on fields configured with 'identity' analyzer in view
                # This assumes 'level', 'script_name', 'execution_id' fields are configured as identity in log_events_view
                if key in ["level", "script_name", "execution_id"]: # Add other identity fields as needed
                    filter_clauses.append(f"doc.{key} == @filter_{key}")
                    bind_vars[f"filter_{key}"] = value
                elif key == "tags" and isinstance(value, list):
                    # Search for any of the tags
                    tag_filters = [f"'{tag}' IN doc.tags" for tag in value]
                    filter_clauses.append(f"({' OR '.join(tag_filters)})")
                else:
                    logger.warning(f"Filter for key '{key}' is not yet fully supported in HybridSearch. Skipping this filter.")

        filter_aql = f"FILTER {' AND '.join(filter_clauses)}" if filter_clauses else ""

        # AQL query for BM25 search
        aql_query = f"""
        FOR doc IN log_events_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        {filter_aql}
        SORT BM25(doc) DESC
        LIMIT @limit
        RETURN {{
            _id: doc._id,
            _key: doc._key,
            message: doc.message,
            level: doc.level,
            timestamp: doc.timestamp,
            score: BM25(doc)
        }}
        """
        
        try:
            results = await self._execute_aql_query(aql_query, bind_vars)
            logger.info(f"Returning {len(results)} real results from ArangoDB")
            return results
        except Exception as e:
            logger.error(f"ArangoDB search failed: {e}")
            return []


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """Save results to JSON file."""
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
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database object and its name.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return test_db_instance

    try:
        db = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db, unique_db_name
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error


# ============================================
# USAGE EXAMPLES (Inside __main__ block)
# ============================================

async def working_usage(db):
    """
    Demonstrate HybridSearch functionality using a real, isolated DB.
    
    This shows how the Logger Agent will use the search module.
    It will seed temporary data and clean it up afterwards (via DB teardown).
    """
    logger.info("=== Running Working Usage Examples (Real, Isolated DB) ===")
    
    log_collection = db.collection("log_events")

    # --- Data Seeding ---
    test_run_id = f"test_hs_w_{datetime.utcnow().strftime('%H%M%S')}" # Simplified ID as DB is isolated
    test_logs_data = [
        {"message": "Connection timeout error occurred on server 1", "level": "ERROR", "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w"},
        {"message": "Database connection error on process 2", "level": "ERROR", "timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w"},
        {"message": "Memory usage warning: 85% utilized on host A", "level": "WARNING", "timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w"},
        {"message": "Informational log message for search functionality", "level": "INFO", "timestamp": (datetime.utcnow() - timedelta(minutes=2)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w"},
        {"message": "Another error message encountered during API call", "level": "ERROR", "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w"},
        {"message": "Successful operation, everything fine", "level": "INFO", "timestamp": datetime.utcnow().isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_w", "tags": ["success", "api"]},
    ]
    
    logger.info(f"Seeding {len(test_logs_data)} test logs into isolated DB.")
    await asyncio.to_thread(log_collection.insert_many, test_logs_data)
    # Give ArangoSearch view a moment to index newly inserted data
    await asyncio.sleep(2) 

    # Initialize search with the real database
    search = HybridSearch(db)
    
    # Test 1: Search for errors
    logger.info("\nTest 1: Searching for errors...")
    # No need for execution_id filter here as the DB itself is isolated
    error_results = await search.search(
        query="error connection",
        search_type="bm25",
        limit=10,
    )
    
    logger.info(f"Found {len(error_results)} error results")
    for result in error_results:
        logger.info(f"  - {result['message'][:50]}... (score: {result['score']:.2f})")
    
    assert len(error_results) > 0, "Should find error results from isolated DB"
    
    # Test 2: Search with filters
    logger.info("\nTest 2: Searching with filters (level: ERROR)...")
    filtered_results = await search.search(
        query="error",
        filters={"level": "ERROR"}, # Filters on specific fields
        limit=5
    )
    
    logger.info(f"Found {len(filtered_results)} filtered results")
    assert all(r["level"] == "ERROR" for r in filtered_results), "All results should be ERROR level"
    assert len(filtered_results) > 0, "Expected filtered results for errors"

    # Test 3: Search for warnings
    logger.info("\nTest 3: Searching for warnings...")
    warning_results = await search.search(
        query="warning",
        filters={"level": "WARNING"},
        limit=3
    )
    logger.info(f"Found {len(warning_results)} warning results")
    assert len(warning_results) > 0, "Expected warning results"

    # Save test results
    save_results({
        "error_search": error_results,
        "filtered_search": filtered_results,
        "warning_search": warning_results,
        "test_timestamp": datetime.utcnow().isoformat()
    })
    
    logger.success("✓ All search tests passed using real isolated ArangoDB")

    return True


async def debug_function(db):
    """
    Debug function for testing search edge cases with real, isolated DB.
    
    Use this to test specific search scenarios or debug issues.
    """
    logger.info("=== Running Debug Function (Real, Isolated DB) ===")
    
    log_collection = db.collection("log_events")

    # --- Data Seeding ---
    test_run_id = f"test_hs_d_{datetime.utcnow().strftime('%H%M%S')}" # Simplified ID
    test_logs_data = [
        {"message": "Log with special characters: @#$%^&*()_+-=", "level": "INFO", "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_d"},
        {"message": "Long query test message " * 50, "level": "DEBUG", "timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_d"},
        {"message": "Another test message about an error", "level": "ERROR", "timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat(), "execution_id": test_run_id, "script_name": "test_script_hs_d"},
    ]
    await asyncio.to_thread(log_collection.insert_many, test_logs_data)
    await asyncio.sleep(2) # Give ArangoSearch view time to index

    search = HybridSearch(db)
    
    # Test empty query (should return based on default limit, without specific keywords)
    logger.info("Testing empty query...")
    empty_results = await search.search(query="", limit=5)
    logger.info(f"Empty query returned {len(empty_results)} results")
    assert len(empty_results) > 0, "Expected results for empty query"

    # Test very long query
    logger.info("\nTesting very long query...")
    long_query = " ".join(["message"] * 10) # Using words present in test_logs_data for actual hits
    long_results = await search.search(query=long_query, limit=5)
    logger.info(f"Long query returned {len(long_results)} results")
    assert len(long_results) > 0, "Expected results for long query"

    # Test special characters (ArangoSearch tokenizes these, so direct match might be low)
    logger.info("\nTesting special characters...")
    special_query = "@#$%^&*()" # Query based on the test log message
    special_results = await search.search(query=special_query, limit=5)
    logger.info(f"Special char query returned {len(special_results)} results")
    assert len(special_results) > 0, "Expected results for special char query (due to 'characters' keyword in log)"
    
    # Test collection variations (will warn and default to log_events, as handled in search method)
    logger.info("\nTesting different collections (expect warnings/defaulting)...")
    for collection in ["log_events", "non_existent_collection"]:
        results = await search.search(
            query="message", # General query to ensure some results
            collection=collection,
            limit=2,
        )
        logger.info(f"  {collection}: {len(results)} results")
        if collection == "log_events":
            assert len(results) > 0, "Expected results for valid collection"
        else:
            assert len(results) == 0, "Expected no results for non-existent collection link"

    return True


async def stress_test(db):
    """
    Stress test the search functionality with real, isolated DB.
    
    Tests high-volume and concurrent search operations.
    """
    logger.info("=== Running Stress Tests (Real, Isolated DB) ===")
    
    log_collection = db.collection("log_events")

    # --- Data Seeding (large volume) ---
    test_run_id = f"test_hs_s_{datetime.utcnow().strftime('%H%M%S')}" # Simplified ID
    logger.info(f"Seeding large volume of test logs into isolated DB.")
    stress_logs_data = []
    num_logs = 1000
    for i in range(num_logs):
        stress_logs_data.append({
            "message": f"Stress test log {i}: An error occurred with component {i % 10}",
            "level": "ERROR" if i % 5 == 0 else ("WARNING" if i % 5 == 1 else "INFO"),
            "timestamp": (datetime.utcnow() - timedelta(seconds=num_logs - i)).isoformat(), # Ensure distinct timestamps
            "execution_id": test_run_id,
            "script_name": "test_script_hs_s"
        })
    await asyncio.to_thread(log_collection.insert_many, stress_logs_data)
    await asyncio.sleep(5) # Give ample time for ArangoSearch indexing

    search = HybridSearch(db)
    
    # Test 1: Many sequential searches
    logger.info("Test 1: Sequential search performance...")
    start_time = datetime.utcnow()
    
    for i in range(100):
        await search.search(f"error component {i % 10}", limit=10)
        if i % 20 == 0:
            logger.info(f"  Completed {i} searches")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ 100 sequential searches in {duration:.2f} seconds")
    
    # Test 2: Concurrent searches
    logger.info("\nTest 2: Concurrent search performance...")
    
    async def concurrent_search(worker_id: int, count: int):
        """Run multiple searches concurrently."""
        for i in range(count):
            await search.search(f"warning component {worker_id}", limit=5)
    
    start_time = datetime.utcnow()
    workers = [concurrent_search(i, 10) for i in range(10)]
    await asyncio.gather(*workers)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ 100 concurrent searches (10x10) in {duration:.2f} seconds")
    
    # Test 3: Large result sets
    logger.info("\nTest 3: Large result set handling...")
    large_results = await search.search("log", limit=num_logs + 100) # Request more than available
    logger.success(f"✓ Handled large result request (got {len(large_results)} results)")
    assert len(large_results) == num_logs, f"Expected all {num_logs} logs to be found for general query"
    
    logger.info("\n📊 Stress Test Summary: All tests passed using real isolated ArangoDB")

    return True


if __name__ == "__main__":
    """
    Script entry point with triple-mode execution.
    
    IMPORTANT: This script requires a running ArangoDB instance.
               Environment variables (ARANGO_URL, ARANGO_USERNAME, ARANGO_PASSWORD)
               must be configured (e.g., via a .env file).
    
    Usage:
        python hybrid_search.py          # Runs working_usage() - stable tests
        python hybrid_search.py debug    # Runs debug_function() - experimental
        python hybrid_search.py stress   # Runs stress_test() - performance tests
    """
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_instance = None
        test_db_name = None
        success = False
        try:
            test_db_instance, test_db_name = await setup_test_database()
            
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function(test_db_instance)
            elif mode == "stress":
                logger.info("Running in STRESS TEST mode...")
                success = await stress_test(test_db_instance)
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage(test_db_instance)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)
```
<!-- CODE_FILE_END: src/arangodb/core/search/hybrid_search.py -->

<!-- CODE_FILE_START: src/arangodb/core/graph/relationship_extraction.py -->
```python
#!/usr/bin/env python3
"""
Relationship extraction module for Logger Agent integration.

Provides an interface for extracting and storing relationships between
log events in an ArangoDB graph database.

Third-party Documentation:
- ArangoDB Graphs: https://www.arangodb.com/docs/stable/graphs.html

Example Input:
    text1 = "Database connection failed"
    text2 = "Retrying database connection"

Expected Output (Stored in DB):
    An edge in 'log_causality' collection, linking two 'log_events' documents.
    e.g., {"_from": "log_events/123", "_to": "log_events/456", "type": "RETRY_OF", "confidence": 0.85}
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from loguru import logger
from arango import ArangoClient
from dotenv import load_dotenv
import os

# Import the schema creation helper from arango_init
from arango_init import _create_database_schema_sync # Renamed and moved logic


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

class RelationshipExtractor:
    """Relationship extractor for ArangoDB."""
    
    def __init__(self, db_instance):
        """Initialize with an active ArangoDB database connection."""
        if not db_instance:
            raise ValueError("ArangoDB client 'db' instance must be provided.")
        self.db = db_instance
        self.graph_name = "log_relationships"
        self.edge_collection_name = "log_causality"
        self.log_events_collection_name = "log_events"

        try:
            # Synchronously check and get graph/collection objects
            if not self.db.has_graph(self.graph_name):
                # In the test setup, _create_database_schema_sync is called.
                # If this warning appears, it means that setup failed or was skipped.
                logger.warning(f"Graph '{self.graph_name}' not found. Please ensure test DB setup is correct.")
                self.graph = None
                self.edge_collection = None
            else:
                self.graph = self.db.graph(self.graph_name)
                # Check if edge collection exists within the graph context
                if not self.graph.has_edge_collection(self.edge_collection_name):
                     logger.warning(f"Edge collection '{self.edge_collection_name}' not found in graph '{self.graph_name}'. Please ensure test DB setup is correct.")
                     self.edge_collection = None
                else:
                    self.edge_collection = self.graph.edge_collection(self.edge_collection_name)
            
            logger.info("RelationshipExtractor initialized with real ArangoDB connection.")

        except Exception as e:
            logger.error(f"Failed to initialize RelationshipExtractor DB connection: {e}")
            self.graph = None
            self.edge_collection = None
            raise # Re-raise to indicate critical failure
    
    async def _insert_relationship_edge(self, from_doc_id: str, to_doc_id: str, relationship_type: str, confidence: float, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Helper to insert an edge into the log_causality collection."""
        if not self.edge_collection:
            logger.error("Edge collection not initialized, cannot insert relationship.")
            return None

        edge_data = {
            "_from": from_doc_id,
            "_to": to_doc_id,
            "type": relationship_type,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        try:
            def sync_insert():
                return self.edge_collection.insert(edge_data)
            
            result = await asyncio.to_thread(sync_insert)
            logger.info(f"Stored relationship: {relationship_type} from {from_doc_id} to {to_doc_id}. Edge ID: {result['_id']}")
            return result
        except Exception as e:
            logger.error(f"Failed to insert relationship edge into DB: {e}")
            return None

    async def extract_relationships(
        self,
        log1_doc_id: str, # Expecting actual document IDs now
        log2_doc_id: str,
        log1_message: str, # Also pass messages for extraction logic
        log2_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract and store relationships between two log events.
        
        Args:
            log1_doc_id: The _id of the first log document (e.g., "log_events/123").
            log2_doc_id: The _id of the second log document (e.g., "log_events/456").
            log1_message: The message content of the first log.
            log2_message: The message content of the second log.
            context: Optional context information to store with the relationship.
            
        Returns:
            List of relationships found and attempted to be stored (includes metadata, not just boolean success).
        """
        extracted_rels_meta = [] # To return metadata about the created relationships
        
        # Simple pattern matching for demonstration
        text1_lower = log1_message.lower()
        text2_lower = log2_message.lower()
        
        # Check for retry patterns
        if "failed" in text1_lower and "retry" in text2_lower:
            rel_type = "RETRY_OF"
            confidence = 0.85
            inserted_edge = await self._insert_relationship_edge(log1_doc_id, log2_doc_id, rel_type, confidence, context)
            if inserted_edge:
                extracted_rels_meta.append({"type": rel_type, "confidence": confidence, "from_id": log1_doc_id, "to_id": log2_doc_id, "edge_id": inserted_edge["_id"]})
        
        # Check for error-fix patterns
        if "error" in text1_lower and ("fix" in text2_lower or "resolved" in text2_lower):
            rel_type = "FIXED_BY"
            confidence = 0.90
            inserted_edge = await self._insert_relationship_edge(log1_doc_id, log2_doc_id, rel_type, confidence, context)
            if inserted_edge:
                extracted_rels_meta.append({"type": rel_type, "confidence": confidence, "from_id": log1_doc_id, "to_id": log2_doc_id, "edge_id": inserted_edge["_id"]})
        
        # Check for cause-effect patterns (simplified)
        if "caused" in text2_lower or "because" in text2_lower:
            rel_type = "CAUSED_BY"
            confidence = 0.75
            # Note: direction changed for CAUSED_BY (log2 causes log1)
            inserted_edge = await self._insert_relationship_edge(log2_doc_id, log1_doc_id, rel_type, confidence, context)
            if inserted_edge:
                extracted_rels_meta.append({"type": rel_type, "confidence": confidence, "from_id": log2_doc_id, "to_id": log1_doc_id, "edge_id": inserted_edge["_id"]})
        
        # Temporal relationship (always exists between sequential logs)
        rel_type = "FOLLOWED_BY"
        confidence = 1.0
        inserted_edge = await self._insert_relationship_edge(log1_doc_id, log2_doc_id, rel_type, confidence, context)
        if inserted_edge:
            extracted_rels_meta.append({"type": rel_type, "confidence": confidence, "from_id": log1_doc_id, "to_id": log2_doc_id, "edge_id": inserted_edge["_id"]})

        return extracted_rels_meta


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """Save results to JSON file."""
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
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database object and its name.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return test_db_instance

    try:
        db = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db, unique_db_name
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error

# ============================================
# USAGE EXAMPLES (Inside __main__ block)
# ============================================

async def working_usage(db):
    """
    Demonstrate RelationshipExtractor functionality using a real, isolated DB.
    
    Shows how to extract relationships between log messages and store them.
    It will seed temporary data and clean it up afterwards (via DB teardown).
    """
    logger.info("=== Running Working Usage Examples (Real, Isolated DB) ===")
    
    log_events_collection = db.collection("log_events")
    
    # --- Data Seeding ---
    # In a real scenario, these log events would already exist from arango_log_sink.
    # For testing this module directly, we insert them.
    test_execution_id = f"test_re_w_{datetime.utcnow().strftime('%H%M%S')}" # Simplified ID as DB is isolated
    log_data_pairs = [
        ({"message": "Database connection failed with timeout", "level": "ERROR"}, 
         {"message": "Retrying database connection attempt 1", "level": "INFO"}),
        ({"message": "Critical error: Memory overflow detected", "level": "CRITICAL"}, 
         {"message": "Memory issue fixed by clearing cache", "level": "INFO"}),
        ({"message": "Service crashed unexpectedly because of high load", "level": "ERROR"}, 
         {"message": "Service restarted automatically", "level": "INFO"}),
        ({"message": "High CPU usage detected", "level": "WARNING"}, 
         {"message": "Process killed due to high CPU", "level": "CRITICAL"}),
        ({"message": "Configuration error found", "level": "ERROR"}, 
         {"message": "Configuration error resolved", "level": "INFO"})
    ]

    inserted_log_docs = []
    for log_data1, log_data2 in log_data_pairs:
        # Add test_execution_id for context on edges (if needed for later debugging, though DB is transient)
        log_data1_full = {**log_data1, "execution_id": test_execution_id, "script_name": "test_script_re_w", "timestamp": (datetime.utcnow() + timedelta(seconds=len(inserted_log_docs)*2)).isoformat()}
        log_data2_full = {**log_data2, "execution_id": test_execution_id, "script_name": "test_script_re_w", "timestamp": (datetime.utcnow() + timedelta(seconds=len(inserted_log_docs)*2+1)).isoformat()}
        
        inserted_log_docs.append(await asyncio.to_thread(log_events_collection.insert, log_data1_full))
        inserted_log_docs.append(await asyncio.to_thread(log_events_collection.insert, log_data2_full))
    
    logger.info(f"Seeded {len(inserted_log_docs)} log events into isolated DB.")
    await asyncio.sleep(1) # Give a moment for DB consistency

    extractor = RelationshipExtractor(db)
    
    all_relationships_meta = []

    # Test 1: Error and retry relationship
    logger.info("\nTest 1: Error-Retry relationship...")
    log1_doc_full = inserted_log_docs[0]
    log2_doc_full = inserted_log_docs[1]
    
    rels = await extractor.extract_relationships(
        log1_doc_full["_id"], log2_doc_full["_id"], 
        log1_doc_full["message"], log2_doc_full["message"], 
        {"execution_id": test_execution_id}
    )
    all_relationships_meta.extend(rels)
    logger.info(f"Found {len(rels)} relationships (and stored):")
    for rel in rels:
        logger.info(f"  - {rel['type']} (confidence: {rel['confidence']:.2f}) from {rel['from_id']} to {rel['to_id']}")
    assert any(r["type"] == "RETRY_OF" for r in rels), "Should find RETRY_OF relationship"
    
    # Test 2: Error and fix relationship
    logger.info("\nTest 2: Error-Fix relationship...")
    log3_doc_full = inserted_log_docs[2]
    log4_doc_full = inserted_log_docs[3]

    rels = await extractor.extract_relationships(
        log3_doc_full["_id"], log4_doc_full["_id"], 
        log3_doc_full["message"], log4_doc_full["message"],
        {"execution_id": test_execution_id}
    )
    all_relationships_meta.extend(rels)
    fix_rels = [r for r in rels if r["type"] == "FIXED_BY"]
    assert len(fix_rels) > 0, "Should find FIXED_BY relationship"
    logger.success(f"✓ Found FIXED_BY relationship with confidence {fix_rels[0]['confidence']:.2f}")
    
    # Test 3: Complex relationship extraction
    logger.info("\nTest 3: Complex relationship extraction for multiple pairs...")
    
    # Process remaining pairs from seeded data (from index 2 onwards)
    for i in range(2, len(log_data_pairs)):
        log_a_doc_full = inserted_log_docs[i*2]
        log_b_doc_full = inserted_log_docs[i*2+1]
        
        rels = await extractor.extract_relationships(
            log_a_doc_full["_id"], log_b_doc_full["_id"], 
            log_a_doc_full["message"], log_b_doc_full["message"],
            {"execution_id": test_execution_id}
        )
        all_relationships_meta.extend(rels)
        logger.info(f"  {log_a_doc_full['message'][:30]}... -> {log_b_doc_full['message'][:30]}... : {len(rels)} relationships")
    
    # Save results
    save_results({
        "total_extracted_relationships": len(all_relationships_meta),
        "relationships_details": all_relationships_meta,
        "test_execution_id": test_execution_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    logger.success("✓ All relationship extraction tests passed using real isolated ArangoDB")

    return True


async def debug_function(db):
    """
    Debug function for testing edge cases in relationship extraction with real, isolated DB.
    """
    logger.info("=== Running Debug Function (Real, Isolated DB) ===")
    
    log_events_collection = db.collection("log_events")

    # --- Data Seeding ---
    test_execution_id = f"test_re_d_{datetime.utcnow().strftime('%H%M%S')}" # Simplified ID
    log_data = [
        {"message": "", "level": "INFO", "ts_offset": 0}, # Empty strings
        {"message": "", "level": "INFO", "ts_offset": 1},
        {"message": "Same message repeated", "level": "INFO", "ts_offset": 2}, # Identical strings
        {"message": "Same message repeated", "level": "INFO", "ts_offset": 3},
        {"message": "Error: " + "A" * 1000, "level": "ERROR", "ts_offset": 4}, # Very long strings
        {"message": "Fixed: " + "B" * 1000, "level": "INFO", "ts_offset": 5},
        {"message": "Error: @#$%^&*() failed", "level": "ERROR", "ts_offset": 6}, # Special characters
        {"message": "Retry: !@#$%^&*() attempt", "level": "INFO", "ts_offset": 7},
        {"message": "Operation failed", "level": "ERROR", "ts_offset": 8}, # With context
        {"message": "Operation retried", "level": "INFO", "ts_offset": 9}
    ]

    inserted_log_docs = []
    for data in log_data:
        log_doc = {
            "message": data["message"],
            "level": data["level"],
            "timestamp": (datetime.utcnow() + timedelta(seconds=data["ts_offset"])).isoformat(),
            "execution_id": test_execution_id,
            "script_name": "test_script_re_d"
        }
        inserted_log_docs.append(await asyncio.to_thread(log_events_collection.insert, log_doc))
    
    logger.info(f"Seeded {len(inserted_log_docs)} log events into isolated DB.")
    await asyncio.sleep(1)

    extractor = RelationshipExtractor(db)

    all_debug_rels = []

    # Test empty strings
    logger.info("Testing empty strings...")
    rels = await extractor.extract_relationships(
        inserted_log_docs[0]["_id"], inserted_log_docs[1]["_id"], 
        inserted_log_docs[0]["message"], inserted_log_docs[1]["message"], 
        {"execution_id": test_execution_id, "test_case": "empty_strings"}
    )
    all_debug_rels.extend(rels)
    logger.info(f"Empty strings: {len(rels)} relationships (expected 'FOLLOWED_BY')")
    assert any(r["type"] == "FOLLOWED_BY" for r in rels)

    # Test identical strings
    logger.info("\nTesting identical strings...")
    rels = await extractor.extract_relationships(
        inserted_log_docs[2]["_id"], inserted_log_docs[3]["_id"], 
        inserted_log_docs[2]["message"], inserted_log_docs[3]["message"],
        {"execution_id": test_execution_id, "test_case": "identical_strings"}
    )
    all_debug_rels.extend(rels)
    logger.info(f"Identical strings: {len(rels)} relationships (expected 'FOLLOWED_BY')")
    assert any(r["type"] == "FOLLOWED_BY" for r in rels)

    # Test very long strings
    logger.info("\nTesting very long strings...")
    rels = await extractor.extract_relationships(
        inserted_log_docs[4]["_id"], inserted_log_docs[5]["_id"], 
        inserted_log_docs[4]["message"], inserted_log_docs[5]["message"],
        {"execution_id": test_execution_id, "test_case": "long_strings"}
    )
    all_debug_rels.extend(rels)
    logger.info(f"Long strings: {len(rels)} relationships")
    assert any(r["type"] == "FIXED_BY" for r in rels)

    # Test special characters
    logger.info("\nTesting special characters...")
    rels = await extractor.extract_relationships(
        inserted_log_docs[6]["_id"], inserted_log_docs[7]["_id"], 
        inserted_log_docs[6]["message"], inserted_log_docs[7]["message"],
        {"execution_id": test_execution_id, "test_case": "special_chars"}
    )
    all_debug_rels.extend(rels)
    logger.info(f"Special chars: {len(rels)} relationships")
    assert any(r["type"] == "RETRY_OF" for r in rels)

    # Test with context
    logger.info("\nTesting with context...")
    context = {"execution_id": test_execution_id, "timestamp_diff": 5.2, "test_case": "with_context"}
    rels = await extractor.extract_relationships(
        inserted_log_docs[8]["_id"], inserted_log_docs[9]["_id"], 
        inserted_log_docs[8]["message"], inserted_log_docs[9]["message"],
        context=context
    )
    all_debug_rels.extend(rels)
    logger.info(f"With context: {len(rels)} relationships")
    assert any(r["type"] == "RETRY_OF" for r in rels)
    
    return True


async def stress_test(db):
    """
    Stress test relationship extraction with real, isolated DB and high volume.
    """
    logger.info("=== Running Stress Tests (Real, Isolated DB) ===")
    
    log_events_collection = db.collection("log_events")

    # Test 1: Many sequential extractions
    logger.info("Test 1: Sequential extraction performance...")
    start_time = datetime.utcnow()
    
    total_relationships = 0
    num_pairs = 500
    test_execution_id_seq = f"test_re_s_seq_{datetime.utcnow().strftime('%H%M%S')}"

    for i in range(num_pairs):
        log_a_data = {"message": f"Log message {i}: Operation in progress", "level": "INFO", "execution_id": test_execution_id_seq, "script_name": "test_script_re_s", "timestamp": (datetime.utcnow() + timedelta(seconds=i*2)).isoformat()}
        log_b_data = {"message": f"Log message {i+1}: Operation completed", "level": "INFO", "execution_id": test_execution_id_seq, "script_name": "test_script_re_s", "timestamp": (datetime.utcnow() + timedelta(seconds=i*2+1)).isoformat()}

        log_a = await asyncio.to_thread(log_events_collection.insert, log_a_data)
        log_b = await asyncio.to_thread(log_events_collection.insert, log_b_data)

        extractor = RelationshipExtractor(db) # Re-initialize for each loop (optional, for safety)
        rels = await extractor.extract_relationships(
            log_a["_id"], log_b["_id"], log_a["message"], log_b["message"],
            {"execution_id": test_execution_id_seq, "test_case": "sequential_stress"}
        )
        total_relationships += len(rels)
        
        if i % 100 == 0:
            logger.info(f"  Processed {i} pairs")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Extracted {total_relationships} relationships from {num_pairs} pairs "
        f"in {duration:.2f} seconds"
    )
    
    # Test 2: Concurrent extractions
    logger.info("\nTest 2: Concurrent extraction performance...")
    
    async def extract_batch(batch_id: int, count: int, current_test_execution_id: str, db_instance):
        """Extract relationships for a batch of log pairs."""
        batch_rels = 0
        extractor_batch = RelationshipExtractor(db_instance) # Each worker gets its own extractor
        for i in range(count):
            log_a_data = {"message": f"Batch {batch_id} error {i}", "level": "ERROR", "execution_id": current_test_execution_id, "script_name": "test_script_re_s_concurrent", "timestamp": (datetime.utcnow() + timedelta(seconds=batch_id*1000 + i*2)).isoformat()}
            log_b_data = {"message": f"Batch {batch_id} recovery {i}", "level": "INFO", "execution_id": current_test_execution_id, "script_name": "test_script_re_s_concurrent", "timestamp": (datetime.utcnow() + timedelta(seconds=batch_id*1000 + i*2 + 1)).isoformat()}

            log_a = await asyncio.to_thread(log_events_collection.insert, log_a_data)
            log_b = await asyncio.to_thread(log_events_collection.insert, log_b_data)

            rels = await extractor_batch.extract_relationships(
                log_a["_id"], log_b["_id"], log_a["message"], log_b["message"],
                {"execution_id": current_test_execution_id, "test_case": f"concurrent_stress_batch_{batch_id}"}
            )
            batch_rels += len(rels)
        return batch_rels
    
    start_time = datetime.utcnow()
    test_execution_id_conc = f"test_re_s_conc_{datetime.utcnow().strftime('%H%M%S')}"
    tasks = [extract_batch(i, 50, test_execution_id_conc, db) for i in range(10)] # 10 batches of 50 pairs = 500 pairs
    batch_results = await asyncio.gather(*tasks)
    total_concurrent = sum(batch_results)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Extracted {total_concurrent} relationships concurrently "
        f"(10 batches x 50 pairs) in {duration:.2f} seconds"
    )
    
    # Test 3: Complex pattern matching
    logger.info("\nTest 3: Complex pattern performance...")
    complex_patterns = [
        ("System error: Database connection pool exhausted after 300 attempts",
         "Recovery initiated: Restarting connection pool and clearing stale connections"),
        ("Performance degradation: Response time increased from 100ms to 5000ms",
         "Optimization applied: Enabled query caching, response time reduced to 150ms"),
        ("Security alert: Multiple failed authentication attempts from IP 192.168.1.100",
         "Security response: IP blocked and alert sent to administrators")
    ]
    
    start_time = datetime.utcnow()
    test_execution_id_complex = f"test_re_s_complex_{datetime.utcnow().strftime('%H%M%S')}"

    for j in range(100): # Repeat 100 times
        for idx, (text1, text2) in enumerate(complex_patterns):
            log_a_data = {"message": text1, "level": "ERROR", "execution_id": test_execution_id_complex, "script_name": "test_script_re_s_complex", "timestamp": (datetime.utcnow() + timedelta(seconds=j*10000 + idx*2)).isoformat()}
            log_b_data = {"message": text2, "level": "INFO", "execution_id": test_execution_id_complex, "script_name": "test_script_re_s_complex", "timestamp": (datetime.utcnow() + timedelta(seconds=j*10000 + idx*2 + 1)).isoformat()}
            log_a = await asyncio.to_thread(log_events_collection.insert, log_a_data)
            log_b = await asyncio.to_thread(log_events_collection.insert, log_b_data)
            
            extractor_complex = RelationshipExtractor(db)
            await extractor_complex.extract_relationships(log_a["_id"], log_b["_id"], log_a["message"], log_b["message"], {"execution_id": test_execution_id_complex, "test_case": "complex_stress"})
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ Complex pattern extraction (300 ops) in {duration:.2f} seconds")
    
    logger.info("\n📊 Stress Test Summary: All tests passed using real isolated ArangoDB")

    return True


if __name__ == "__main__":
    """
    Script entry point with triple-mode execution.
    
    IMPORTANT: This script requires a running ArangoDB instance.
               Environment variables (ARANGO_URL, ARANGO_USERNAME, ARANGO_PASSWORD)
               must be configured (e.g., via a .env file).
    
    Usage:
        python relationship_extraction.py          # Runs working_usage()
        python relationship_extraction.py debug    # Runs debug_function()
        python relationship_extraction.py stress   # Runs stress_test()
    """
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_instance = None
        test_db_name = None
        success = False
        try:
            test_db_instance, test_db_name = await setup_test_database()
            
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function(test_db_instance)
            elif mode == "stress":
                logger.info("Running in STRESS TEST mode...")
                success = await stress_test(test_db_instance)
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage(test_db_instance)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)
```
<!-- CODE_FILE_END: src/arangodb/core/graph/relationship_extraction.py -->

<!-- CODE_FILE_START: src/arangodb/core/memory/memory_agent.py -->
```python
#!/usr/bin/env python3
"""
Memory agent module for Logger Agent integration.

Provides an interface for storing and retrieving memories from ArangoDB.

Third-party Documentation:
- ArangoDB Documents: https://www.arangodb.com/docs/stable/data-modeling-documents.html

Example Input:
    content = "Discovered optimal batch size is 100"
    memory_type = "learning"
    metadata = {"confidence": 0.9, "context": "data_processing"}

Expected Output (Stored in DB):
    {"_id": "agent_learnings/123", "content": "...", "type": "learning", "timestamp": "..."}
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from loguru import logger
from arango import ArangoClient
from dotenv import load_dotenv
import os

# Import the schema creation helper from arango_init
from arango_init import _create_database_schema_sync # Renamed and moved logic


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

class MemoryAgent:
    """Memory agent for storing and retrieving agent learnings in ArangoDB."""
    
    def __init__(self, db_instance):
        """Initialize with an active ArangoDB database connection."""
        if not db_instance:
            raise ValueError("ArangoDB client 'db' instance must be provided.")
        self.db = db_instance
        self.collection_name = "agent_learnings"
        self.collection = None

        try:
            # Check if collection exists (synchronous check in __init__)
            if not self.db.has_collection(self.collection_name):
                logger.warning(f"Collection '{self.collection_name}' not found. Please ensure test DB setup is correct.")
                self.collection = None # Mark as uninitialized if not found
            else:
                self.collection = self.db.collection(self.collection_name)
            
            logger.info("MemoryAgent initialized with real ArangoDB connection.")

        except Exception as e:
            logger.error(f"Failed to initialize MemoryAgent DB connection: {e}")
            self.collection = None
            raise # Re-raise to indicate critical failure
    
    async def add_memory(
        self,
        content: str,
        memory_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a new memory entry to ArangoDB.
        
        Args:
            content: Memory content
            memory_type: Type of memory (learning, observation, etc.)
            metadata: Additional metadata
            
        Returns:
            Created memory document (with _id, _key, _rev)
        """
        if not self.collection:
            logger.error("Memory collection not initialized, cannot add memory.")
            return {}

        memory_doc = {
            "content": content,
            "type": memory_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        try:
            def sync_insert():
                return self.collection.insert(memory_doc)
            
            result = await asyncio.to_thread(sync_insert)
            logger.info(f"Added {memory_type} memory: {result['_id']} - {content[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Failed to add memory to DB: {e}")
            return {}
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for memories in ArangoDB matching query.
        
        Args:
            query: Search query
            memory_type: Optional filter by type
            limit: Maximum results
            
        Returns:
            List of matching memories
        """
        if not self.collection:
            logger.error("Memory collection not initialized, cannot search memories.")
            return []

        # AQL query to search for memories
        bind_vars = {"query": query, "limit": limit}
        filter_clause = ""
        if memory_type:
            filter_clause = "FILTER doc.type == @memory_type"
            bind_vars["memory_type"] = memory_type

        # This query uses basic string matching (CONTAINS). For more advanced text search,
        # an ArangoSearch view linked to 'agent_learnings' would be needed.
        # We assume 'agent_learnings' has a persistent index on 'content' for performance.
        aql_query = f"""
        FOR doc IN {self.collection_name}
        FILTER CONTAINS(LOWER(doc.content), LOWER(@query))
        {filter_clause}
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        try:
            def sync_query():
                cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
                return [doc for doc in cursor]
            
            results = await asyncio.to_thread(sync_query)
            logger.info(f"Found {len(results)} memories matching '{query}'")
            return results
        except Exception as e:
            logger.error(f"Failed to search memories in DB: {e}")
            return []
    
    async def get_recent_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories from ArangoDB, optionally filtered by type.
        
        Args:
            memory_type: Optional filter by type
            limit: Maximum results
            
        Returns:
            List of recent memories
        """
        if not self.collection:
            logger.error("Memory collection not initialized, cannot get recent memories.")
            return []

        bind_vars = {"limit": limit}
        filter_clause = ""
        if memory_type:
            filter_clause = "FILTER doc.type == @memory_type"
            bind_vars["memory_type"] = memory_type

        aql_query = f"""
        FOR doc IN {self.collection_name}
        {filter_clause}
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        try:
            def sync_query():
                cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
                return [doc for doc in cursor]
            
            results = await asyncio.to_thread(sync_query)
            logger.info(f"Retrieved {len(results)} recent memories (type: {memory_type if memory_type else 'all'})")
            return results
        except Exception as e:
            logger.error(f"Failed to get recent memories from DB: {e}")
            return []


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """Save results to JSON file."""
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
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database object and its name.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return test_db_instance

    try:
        db = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db, unique_db_name
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error


# ============================================
# USAGE EXAMPLES (Inside __main__ block)
# ============================================

async def working_usage(db):
    """
    Demonstrate MemoryAgent functionality using a real, isolated DB.
    
    Shows how to store and retrieve various types of memories.
    It will seed temporary data and clean it up afterwards (via DB teardown).
    """
    logger.info("=== Running Working Usage Examples (Real, Isolated DB) ===")
    
    agent = MemoryAgent(db)
    
    # Test 1: Add different types of memories
    logger.info("\nTest 1: Adding various memory types...")
    
    # Add a learning
    learning = await agent.add_memory(
        "Batch size of 100 is optimal for datasets under 10GB",
        memory_type="learning",
        metadata={"confidence": 0.9, "context": "optimization"}
    )
    assert learning.get("_id"), "Learning memory should have been added and have an _id."
    logger.success(f"✓ Added learning: {learning['_id']}")
    
    # Add an observation
    observation = await agent.add_memory(
        "System performance degrades when memory usage exceeds 80%",
        memory_type="observation",
        metadata={"severity": "warning", "threshold": 0.8}
    )
    assert observation.get("_id"), "Observation memory should have been added and have an _id."
    logger.success(f"✓ Added observation: {observation['_id']}")
    
    # Add an error pattern
    error_pattern = await agent.add_memory(
        "ConnectionError often occurs after 5 minutes of idle time",
        memory_type="error_pattern",
        metadata={"frequency": "common", "timeout": 300}
    )
    assert error_pattern.get("_id"), "Error pattern memory should have been added and have an _id."
    logger.success(f"✓ Added error pattern: {error_pattern['_id']}")
    
    # Give ArangoDB a moment to ensure new documents are available for search
    await asyncio.sleep(1)

    # Test 2: Search memories
    logger.info("\nTest 2: Searching memories...")
    
    # Search for batch-related memories
    batch_memories = await agent.search_memories("batch size", limit=5)
    assert len(batch_memories) > 0, "Should find batch-related memories from real isolated DB"
    logger.info(f"Found {len(batch_memories)} memories about 'batch'")
    
    # Search for specific type
    learnings = await agent.search_memories("optimal", memory_type="learning", limit=10)
    assert len(learnings) > 0, "Should find learning memories from real isolated DB"
    logger.info(f"Found {len(learnings)} learning memories")
    
    # Test 3: Get recent memories
    logger.info("\nTest 3: Getting recent memories...")
    
    recent_all = await agent.get_recent_memories(limit=5)
    assert len(recent_all) > 0, "Should find recent memories from real isolated DB"
    logger.info(f"Got {len(recent_all)} recent memories (all types)")
    
    recent_observations = await agent.get_recent_memories(
        memory_type="observation",
        limit=3
    )
    assert len(recent_observations) > 0, "Should find recent observations from real isolated DB"
    logger.info(f"Got {len(recent_observations)} recent observations")
    
    # Save results
    save_results({
        "sample_learning": learning,
        "search_results": batch_memories,
        "recent_memories": recent_all
    })
    
    logger.success("✓ All memory tests passed using real isolated ArangoDB")

    return True


async def debug_function(db):
    """
    Debug function for testing memory edge cases with real, isolated DB.
    """
    logger.info("=== Running Debug Function (Real, Isolated DB) ===")
    
    agent = MemoryAgent(db)
    
    # Test empty content
    logger.info("Testing empty content...")
    empty_memory = await agent.add_memory("", memory_type="test", metadata={"case": "empty"})
    logger.info(f"Empty memory created: {empty_memory.get('_id')}")
    assert empty_memory.get("_id") is not None, "Expected empty memory to be created"
    
    # Test very long content
    logger.info("\nTesting very long content...")
    long_content = "A" * 10000
    long_memory = await agent.add_memory(
        long_content,
        memory_type="stress_test",
        metadata={"size": len(long_content), "case": "long"}
    )
    logger.info(f"Long memory created: {long_memory.get('_id')}")
    assert long_memory.get("_id") is not None, "Expected long memory to be created"

    # Test special characters
    logger.info("\nTesting special characters...")
    special_content = "Special chars: @#$%^&*()_+{}[]|\\:;\"'<>,.?/"
    special_memory = await agent.add_memory(special_content, memory_type="special", metadata={"case": "special"})
    logger.info(f"Special memory created: {special_memory.get('_id')}")
    assert special_memory.get("_id") is not None, "Expected special memory to be created"

    # Test Unicode
    logger.info("\nTesting Unicode content...")
    unicode_content = "Unicode test: 你好世界 🌍 مرحبا بالعالم"
    unicode_memory = await agent.add_memory(unicode_content, memory_type="unicode", metadata={"case": "unicode"})
    logger.info(f"Unicode memory created: {unicode_memory.get('_id')}")
    assert unicode_memory.get("_id") is not None, "Expected unicode memory to be created"

    await asyncio.sleep(1) # Give DB time to index

    # Test search with special queries
    logger.info("\nTesting special search queries...")
    
    # Empty search
    empty_results = await agent.search_memories("")
    logger.info(f"Empty search returned {len(empty_results)} results")
    assert len(empty_results) >= 4, "Expected at least 4 memories for specific run_id"
    
    # Special char search
    special_results = await agent.search_memories("@#$%")
    logger.info(f"Special char search returned {len(special_results)} results")
    assert len(special_results) >= 1, "Expected special char memory to be found"

    # Case sensitivity
    await agent.add_memory("UPPERCASE content", memory_type="case_test", metadata={"case": "case_test"})
    await asyncio.sleep(1)
    case_results = await agent.search_memories("uppercase")
    logger.info(f"Case-insensitive search returned {len(case_results)} results")
    assert len(case_results) >= 1, "Expected case-insensitive search to find memory"
    
    return True


async def stress_test(db):
    """
    Stress test memory operations with high volume on a real, isolated DB.
    """
    logger.info("=== Running Stress Tests (Real, Isolated DB) ===")
    
    agent = MemoryAgent(db)
    
    # Test 1: Add many memories
    logger.info("Test 1: Adding many memories...")
    start_time = datetime.utcnow()
    
    memory_types = ["learning", "observation", "error_pattern", "optimization", "debug"]
    
    num_memories_to_add = 1000
    for i in range(num_memories_to_add):
        await agent.add_memory(
            f"Memory {i}: Important information about process {i % 10}",
            memory_type=memory_types[i % len(memory_types)],
            metadata={"index": i, "batch": i // 100}
        )
        
        if i % 200 == 0:
            logger.info(f"  Added {i} memories")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ Added {num_memories_to_add} memories in {duration:.2f} seconds")
    # Verify count directly in the isolated DB
    def get_collection_count():
        return db.collection("agent_learnings").count()
    current_memory_count = await asyncio.to_thread(get_collection_count)
    assert current_memory_count >= num_memories_to_add, "Expected memories to be in DB"

    await asyncio.sleep(2) # Give DB time to index

    # Test 2: Search performance
    logger.info("\nTest 2: Search performance...")
    
    search_terms = ["process", "information", "important", "0", "memory"]
    total_results = 0
    
    start_time = datetime.utcnow()
    for term in search_terms:
        results = await agent.search_memories(term, limit=num_memories_to_add + 100) # Request more than available to get all
        total_results += len(results)
        logger.info(f"  '{term}': {len(results)} results")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Searched {len(search_terms)} terms, found {total_results} total results "
        f"in {duration:.2f} seconds"
    )
    
    # Test 3: Concurrent operations
    logger.info("\nTest 3: Concurrent memory operations...")
    
    async def memory_worker(worker_id: int, operation_count: int, db_instance):
        """Perform memory operations concurrently."""
        agent_worker = MemoryAgent(db_instance) # Each worker gets its own agent instance
        for i in range(operation_count):
            if i % 2 == 0:
                # Add memory
                await agent_worker.add_memory(
                    f"Worker {worker_id} memory {i} for concurrent test",
                    memory_type="concurrent_test"
                )
            else:
                # Search memory
                await agent_worker.search_memories(f"Worker {worker_id}", limit=1, memory_type="concurrent_test")
    
    start_time = datetime.utcnow()
    workers = [memory_worker(i, 20, db) for i in range(10)] # 10 workers, 20 ops each = 200 ops
    await asyncio.gather(*workers)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Completed 200 concurrent operations (10 workers x 20 ops) "
        f"in {duration:.2f} seconds"
    )
    
    # Final statistics (querying directly from DB)
    def get_db_counts():
        total_count = db.collection("agent_learnings").count()
        type_counts_cursor = db.aql.execute(f"""
            FOR doc IN agent_learnings
            COLLECT type = doc.type INTO count_group
            RETURN {{type: type, count: LENGTH(count_group)}}
        """)
        return total_count, {t['type']: t['count'] for t in type_counts_cursor}

    total_memories_in_db, type_counts = await asyncio.to_thread(get_db_counts)
    
    logger.info(f"\nFinal memory count in isolated DB: {total_memories_in_db}")
    
    logger.info("Memory type distribution in isolated DB:")
    for mem_type, count in type_counts.items():
        logger.info(f"  {mem_type}: {count}")
    
    logger.info("\n📊 Stress Test Summary: All tests passed using real isolated ArangoDB")

    return True


if __name__ == "__main__":
    """
    Script entry point with triple-mode execution.
    
    IMPORTANT: This script requires a running ArangoDB instance.
               Environment variables (ARANGO_URL, ARANGO_USERNAME, ARANGO_PASSWORD)
               must be configured (e.g., via a .env file).
    
    Usage:
        python memory_agent.py          # Runs working_usage() - stable tests
        python memory_agent.py debug    # Runs debug_function() - experimental
        python memory_agent.py stress   # Runs stress_test() - performance tests
    """
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_instance = None
        test_db_name = None
        success = False
        try:
            test_db_instance, test_db_name = await setup_test_database()
            
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function(test_db_instance)
            elif mode == "stress":
                logger.info("Running in STRESS TEST mode...")
                success = await stress_test(test_db_instance)
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage(test_db_instance)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)
```
<!-- CODE_FILE_END: src/arangodb/core/memory/memory_agent.py -->

<!-- CODE_FILE_START: src/arango_log_sink.py -->
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
import uuid # For unique test database names

from arango import ArangoClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import psutil
from dotenv import load_dotenv

from utils.log_utils import log_safe_results
from arango_init import _create_database_schema_sync # Import the schema creation helper


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
        self.client: Optional[ArangoClient] = None
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
            # ArangoClient is synchronous, so instantiate directly
            self.client = ArangoClient(hosts=self.db_config["url"])
            
            # DB operations are synchronous, must use asyncio.to_thread
            def sync_connect():
                db_instance = self.client.db(
                    self.db_config["database"],
                    username=self.db_config["username"],
                    password=self.db_config["password"]
                )
                # Test connection by getting version (synchronous)
                db_instance.version()
                return db_instance
            
            self.db = await asyncio.to_thread(sync_connect)
            self.collection = await asyncio.to_thread(self.db.collection, "log_events")
            
            self.connected = True
            logger.info(f"Connected to ArangoDB database: {self.db_config['database']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB (database: {self.db_config.get('database', 'N/A')}): {e}")
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
        
        if not self.collection:
            logger.error("ArangoDB collection is not initialized. Cannot write batch.")
            self.connected = False # Mark as disconnected to retry connection
            raise Exception("ArangoDB collection not ready")

        try:
            safe_batch = log_safe_results(batch) # Use log_safe_results here
            
            # insert_many is synchronous
            def sync_insert_many():
                return self.collection.insert_many(safe_batch)

            result = await asyncio.to_thread(sync_insert_many)
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
                            # This needs careful consideration to avoid infinite loops if DB is truly broken
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
        
        # Close database connection (client.close() is synchronous)
        if self.client:
            await asyncio.to_thread(self.client.close)
            logger.info("ArangoDB client closed.")
    
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


# Global sink instance (for main application usage, NOT for isolated tests)
_main_sink_instance: Optional[ArangoLogSink] = None

def get_main_arango_sink() -> ArangoLogSink:
    """
    Get or create the global ArangoDB sink instance for the MAIN configured database.
    This should be used by the application, not for isolated tests.
    """
    global _main_sink_instance
    
    if _main_sink_instance is None:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"), # Use the main configured database
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        _main_sink_instance = ArangoLogSink(
            db_config=db_config,
            batch_size=int(os.getenv("LOG_BATCH_SIZE", "200")),
            flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "2")),
            buffer_dir=Path(os.getenv("LOG_BUFFER_DIR", "/tmp/logger_agent_buffer")),
            max_buffer_size_mb=int(os.getenv("LOG_MAX_BUFFER_SIZE_MB", "1000"))
        )
        
        asyncio.create_task(_main_sink_instance.start())
    
    return _main_sink_instance


# ============================================
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database config dictionary and its name.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return {
            "url": arango_url,
            "database": unique_db_name,
            "username": arango_username,
            "password": arango_password
        }

    try:
        db_config = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db_config, unique_db_name
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error


# ============================================
# MAIN EXECUTION FOR TESTING SINK
# ============================================

async def _test_sink_usage(test_db_config: Dict[str, str]):
    """Internal helper to run sink tests with a given DB config."""
    logger.info(f"=== Testing ArangoDB Sink against isolated DB: {test_db_config['database']} ===")
    
    # Create a new sink instance specifically for this test database
    sink = ArangoLogSink(
        db_config=test_db_config,
        batch_size=int(os.getenv("LOG_BATCH_SIZE", "20")), # Smaller batch for faster testing
        flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "1")), # Faster flush
        buffer_dir=Path(f"/tmp/logger_agent_buffer_test_{test_db_config['database']}"),
        max_buffer_size_mb=100 # Smaller buffer limit for tests
    )
    # Start this specific sink instance
    await sink.start()

    # Configure logger with our sink (temporarily remove existing handlers if any from root logger)
    logger.remove() 
    logger.add(sys.stderr, level="INFO") # Keep console output for test results
    logger.add(sink.write, enqueue=True, level="DEBUG") # Add the test sink

    # Generate test logs
    execution_id = f"test_run_sink_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    logger.bind(execution_id=execution_id, tags=["test", "sink"]).info("Test log 1")
    logger.bind(execution_id=execution_id, tags=["test"]).warning("Test warning")
    logger.bind(execution_id=execution_id).error("Test error")
    
    # Wait for logs to be written
    await asyncio.sleep(sink.flush_interval * 2 + 1) # Ensure logs are flushed and processed

    # Verify logs in DB by connecting directly to the test DB
    client_test = ArangoClient(hosts=test_db_config['url'])
    db_test = client_test.db(
        test_db_config['database'],
        username=test_db_config['username'],
        password=test_db_config['password']
    )
    
    def count_logs_sync():
        try:
            coll = db_test.collection("log_events")
            aql = "FOR doc IN @collection FILTER doc.execution_id == @exec_id RETURN doc"
            cursor = db_test.aql.execute(aql, bind_vars={"collection": coll.name, "exec_id": execution_id})
            return len(list(cursor))
        except Exception as e:
            logger.error(f"Failed to query logs for verification: {e}")
            return 0
    
    logged_count = await asyncio.to_thread(count_logs_sync)

    # Check stats
    logger.info(f"Sink stats: {sink.stats}")
    logger.info(f"Logs found in isolated DB for {execution_id}: {logged_count}")
    
    # Basic assertions
    assert sink.stats["total_logs"] >= 3, "Expected at least 3 logs to be processed."
    assert sink.stats["successful_writes"] >= 3, "Expected at least 3 successful writes."
    assert logged_count >= 3, "Expected at least 3 logs to be found in the isolated database."

    # Cleanup this specific sink instance
    await sink.stop()
    return True


async def _test_sink_debug_usage(test_db_config: Dict[str, str]):
    """Internal helper to run sink debug tests with a given DB config."""
    logger.info(f"=== Debug Mode: Testing Sink Edge Cases against isolated DB: {test_db_config['database']} ===")
    
    sink = ArangoLogSink(
        db_config=test_db_config,
        batch_size=int(os.getenv("LOG_BATCH_SIZE", "5")), # Very small batch for debug
        flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "0.5")), # Very fast flush
        buffer_dir=Path(f"/tmp/logger_agent_buffer_debug_{test_db_config['database']}"),
        max_buffer_size_mb=10 # Smaller buffer limit for tests
    )
    await sink.start()

    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(sink.write, enqueue=True, level="DEBUG")

    # Test 1: High volume logging
    logger.info("Test 1: High volume")
    initial_total_logs = sink.stats["total_logs"]
    for i in range(100): # Reduced count for faster debug
        logger.bind(test_id=f"volume_{i}").debug(f"High volume test {i}")
    
    await asyncio.sleep(sink.flush_interval * 3 + 1)
    logger.info(f"After high volume: {sink.stats}")
    assert sink.stats["total_logs"] >= initial_total_logs + 100, "Expected all high volume logs to be queued."
    
    # Test 2: Large messages
    logger.info("Test 2: Large messages")
    initial_total_logs = sink.stats["total_logs"]
    large_data = {"data": "x" * 1000, "array": list(range(100))} # Reduced size for faster debug
    logger.bind(extra_data=large_data).info("Large message test")
    
    await asyncio.sleep(sink.flush_interval + 1)
    logger.info(f"After large message: {sink.stats}")
    assert sink.stats["total_logs"] >= initial_total_logs + 1, "Expected large message to be queued."

    # Test 3: Connection failure simulation (logs will buffer to disk)
    logger.info("Test 3: Simulating connection failure (logs will buffer to disk)")
    
    sink.connected = False
    sink.db = None # Invalidate current DB object
    
    initial_buffered_logs = sink.stats["buffered_logs"]
    for i in range(5): # Reduced count for faster debug
        logger.bind(test="failover").error(f"Failover test {i}")
    
    await asyncio.sleep(sink.flush_interval * 2 + 1)
    logger.info(f"After failover (buffered logs might not show up immediately in DB): {sink.stats}")
    assert sink.stats["buffered_logs"] >= initial_buffered_logs + 5, "Expected logs to be buffered to disk."
    
    logger.info("Re-enabling connection to process buffered logs...")
    await sink.connect()
    await asyncio.sleep(sink.flush_interval * 3 + 1)
    
    logger.info(f"After reconnect and processing: {sink.stats}")

    buffer_files = list(sink.buffer_dir.glob("*.jsonl"))
    failed_buffer_files = list((sink.buffer_dir / "_failed").glob("*.jsonl"))
    logger.info(f"Remaining buffer files: {len(buffer_files)}")
    logger.info(f"Failed buffer files (quarantined): {len(failed_buffer_files)}")
    
    assert len(buffer_files) == 0, "Expected all non-problematic buffer files to be processed and removed."
    
    await sink.stop()
    return True


if __name__ == "__main__":
    import sys
    load_dotenv()
    
    # Ensure a basic console logger is always present for script output
    logger.remove() 
    logger.add(sys.stderr, level="INFO")

    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_config = None
        test_db_name = None
        current_sink = None
        success = False
        try:
            test_db_config, test_db_name = await setup_test_database()
            
            if mode == "debug":
                success = await _test_sink_debug_usage(test_db_config)
            else:
                success = await _test_sink_usage(test_db_config)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            # Explicitly remove the test sink from loguru's handlers
            # to prevent it trying to log during test DB teardown.
            logger.remove(sink_id=current_sink.write if current_sink else None)
            
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    asyncio.run(main())
    exit(0 if success else 1)
```
<!-- CODE_FILE_END: src/arango_log_sink.py -->

<!-- CODE_FILE_START: src/agent_log_manager.py -->
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

from arango import ArangoClient
from loguru import logger
import numpy as np 
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Import from existing modules (now real implementations)
from arangodb.core.search.hybrid_search import HybridSearch
from arangodb.core.graph.relationship_extraction import RelationshipExtractor
from arangodb.core.memory.memory_agent import MemoryAgent
from utils.log_utils import truncate_large_value 

# Import schema creation helper for test database setup
from arango_init import _create_database_schema_sync 
# Import the ArangoLogSink for integration in testing
from arango_log_sink import ArangoLogSink # Use the class directly for test instance


class AgentLogManager:
    """Manager for agent logging operations. Can be used as a singleton in application,
    or as a regular class for isolated testing."""
    
    _instance = None # For potential singleton usage in a full application
    _initialized = False # To prevent re-initialization if used as a singleton

    # For testing purposes, we'll bypass the singleton pattern in __main__
    # to allow multiple isolated test runs against different databases.
    # In a deployed application, you'd typically just call get_log_manager().

    def __new__(cls, *args, **kwargs):
        # This part ensures singleton behavior when called without a specific test DB config
        if 'test_db_config' not in kwargs and cls._instance is not None:
            return cls._instance
        return super().__new__(cls)
    
    def __init__(self, test_db_config: Optional[Dict[str, str]] = None):
        """
        Initialize the AgentLogManager.
        
        Args:
            test_db_config: Optional dictionary for database connection if this is a
                            temporary instance for isolated testing. If None, it
                            will attempt to initialize for main application use.
        """
        # Prevent re-initialization if already a singleton instance
        if not test_db_config and self._initialized:
            return

        self.db = None
        self.client = None
        self.execution_context = {}
        self.current_execution_id = None
        
        # Integration modules
        self.hybrid_search = None
        self.relationship_extractor = None
        self.memory_agent = None

        self._initialized = True # Mark as initialized

        # Initialize immediately if test_db_config is provided, otherwise defer
        # to an explicit initialize() call or get_log_manager for main app.
        if test_db_config:
            # Use this specific config for the test instance
            self._db_config_override = test_db_config
            asyncio.create_task(self.initialize(test_db_config))
        else:
            # For potential main application usage, db_config will be loaded later
            self._db_config_override = None

    async def initialize(self, db_config: Dict[str, str]) -> None:
        """Initialize database connection and integration modules."""
        try:
            self.client = ArangoClient(hosts=db_config["url"])
            
            def sync_get_db():
                return self.client.db(
                    db_config["database"],
                    username=db_config["username"],
                    password=db_config["password"]
                )
            
            self.db = await asyncio.to_thread(sync_get_db)
            
            # Initialize integration modules with the actual DB instance
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
        # Ensure manager is initialized before starting an execution
        if not self.db:
            if self._db_config_override:
                await self.initialize(self._db_config_override)
            else:
                # This case should typically not happen if get_log_manager is used
                # or if the test_db_config is passed to the constructor.
                # Adding a fallback for main app singleton to ensure initialization.
                db_config = {
                    "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
                    "database": os.getenv("ARANGO_DATABASE", "script_logs"),
                    "username": os.getenv("ARANGO_USERNAME", "root"),
                    "password": os.getenv("ARANGO_PASSWORD", "openSesame")
                }
                await self.initialize(db_config)


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
            def sync_insert():
                return self.db.collection("script_runs").insert(doc)
            await asyncio.to_thread(sync_insert)
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
            # Get start time to calculate duration (synchronous operation)
            def sync_get_run_doc():
                return self.db.collection("script_runs").get({"execution_id": execution_id})

            run_doc = await asyncio.to_thread(sync_get_run_doc)
            
            if run_doc:
                start_time = datetime.fromisoformat(run_doc["start_time"])
                end_time = datetime.fromisoformat(update_doc["end_time"])
                update_doc["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Update the document (synchronous operation)
            def sync_update_match():
                return self.db.collection("script_runs").update_match(
                    {"execution_id": execution_id},
                    update_doc
                )
            await asyncio.to_thread(sync_update_match)
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
            # aql.execute is synchronous
            def sync_aql_execute():
                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars=bind_vars or {},
                    batch_size=100
                )
                return list(cursor) # Fetch all results
            
            results = await asyncio.to_thread(sync_aql_execute)
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
        # This function now primarily acts as a wrapper around HybridSearch
        # or can perform a basic AQL query if HybridSearch is not desired for a specific search.
        
        filters = {}
        if execution_id:
            filters["execution_id"] = execution_id
        if level:
            filters["level"] = level
        
        # Note: HybridSearch in core/search doesn't currently handle time_range directly
        # If time_range filtering is critical, it needs to be added to HybridSearch.
        if time_range:
            logger.warning("Time range filtering not implemented directly in core.search.HybridSearch. Ignoring time_range in HybridSearch call.")
            # If you need this, you'd add this logic to the `search` method in hybrid_search.py
            # and pass the time_range there.
        
        if self.hybrid_search:
            # Use the dedicated hybrid search module
            results = await self.hybrid_search.search(
                query=query,
                search_type="bm25", # Assuming BM25 by default for text search
                collection="log_events",
                limit=limit,
                filters=filters
            )
            return results
        else:
            logger.warning("HybridSearch module not initialized. Falling back to basic AQL text search (may be less efficient).")
            # Fallback to basic AQL if hybrid_search is not available
            bind_vars = {"query": query, "limit": limit}
            aql_filters = []
            
            if execution_id:
                aql_filters.append("doc.execution_id == @execution_id")
                bind_vars["execution_id"] = execution_id
            
            if level:
                aql_filters.append("doc.level == @level")
                bind_vars["level"] = level
            
            if time_range:
                if "start" in time_range:
                    aql_filters.append("doc.timestamp >= @start_time")
                    bind_vars["start_time"] = time_range["start"].isoformat()
                if "end" in time_range:
                    aql_filters.append("doc.timestamp <= @end_time")
                    bind_vars["end_time"] = time_range["end"].isoformat()
            
            where_clause = " AND ".join(aql_filters) if aql_filters else "true"
            
            aql = f"""
            FOR doc IN log_events_view
            SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
            FILTER {where_clause}
            SORT BM25(doc) DESC, doc.timestamp DESC
            LIMIT @limit
            RETURN {{
                _id: doc._id,
                message: doc.message,
                level: doc.level,
                timestamp: doc.timestamp,
                execution_id: doc.execution_id
            }}
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
                collection="log_events", # Fixed to log_events for now
                limit=limit,
                filters=filters
            )
            return results
        
        # Fallback to basic search if hybrid_search is not initialized/available
        logger.warning("HybridSearch module not initialized. Falling back to basic AQL text search (may be less efficient).")
        return await self.search_logs(text_query, limit=limit, filters=filters) # Pass filters to general search_logs
    
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
        # Ensure context includes current execution_id for easy cleanup in tests
        full_context = context.copy() if context else {}
        if self.current_execution_id:
            full_context["execution_id"] = self.current_execution_id
        
        try:
            # Use self.memory_agent to add the memory to DB
            if self.memory_agent:
                await self.memory_agent.add_memory(
                    content=message,
                    memory_type="learning",
                    metadata={
                        "function": function_name,
                        "confidence": confidence,
                        **(full_context) 
                    }
                )
                # The memory agent's add_memory logs its success internally.
                # Avoid duplicate logging here unless specific to manager.
            else:
                logger.warning("MemoryAgent not initialized. Agent learning not saved to DB.")
                # Fallback to direct DB insert if memory agent is not ready
                doc = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_id": self.current_execution_id or "manual",
                    "learning": message,
                    "function_name": function_name,
                    "context": full_context,
                    "confidence": confidence
                }
                def sync_insert_learning():
                    return self.db.collection("agent_learnings").insert(doc)
                await asyncio.to_thread(sync_insert_learning)
                logger.info(f"Recorded agent learning via fallback: {message[:100]}...")
                
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
                "id": log.get("_id", f"log_events/{log.get('_key', i)}"), # Ensure consistent ID
                "label": f"{log['level']}: {log['message'][:50]}...",
                "timestamp": log["timestamp"],
                "level": log["level"],
                "function": log.get("function_name", "unknown")
            }
            graph["nodes"].append(node)
        
        # Extract relationships if requested
        if include_relationships and self.relationship_extractor:
            # Analyze log messages for relationships
            for i in range(len(logs) - 1):
                log1 = logs[i]
                log2 = logs[i + 1]

                # Ensure logs have _id for graph edges
                log1_id = log1.get("_id", f"log_events/{log1.get('_key', i)}")
                log2_id = log2.get("_id", f"log_events/{log2.get('_key', i+1)}")

                # Define a context for the edge, including the execution_id for cleanup
                edge_context = {"execution_id": execution_id, "source_log_index": i, "target_log_index": i+1}

                # Extract semantic relationships using the real extractor
                # The extractor will also store them in the DB
                rels_from_extractor = await self.relationship_extractor.extract_relationships(
                    log1_id, log2_id, log1["message"], log2["message"], context=edge_context
                )
                
                # Add extracted relationships to the graph representation (for return value)
                for rel in rels_from_extractor:
                    # Rel contains 'from_id', 'to_id', 'type', 'confidence', 'edge_id'
                    graph["edges"].append({
                        "from": rel["from_id"], 
                        "to": rel["to_id"],     
                        "type": rel["type"],
                        "confidence": rel["confidence"],
                        "edge_id": rel["edge_id"] # Include the actual edge ID from DB
                    })
        
        return graph
    
    async def prune_logs(
        self,
        older_than_days: Optional[int] = None,
        execution_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Prune old logs based on criteria."""
        # For a truly isolated test DB, this function might not be strictly necessary
        # for cleanup, as the whole DB is dropped. However, it's good to keep it
        # for testing the pruning logic itself.
        
        stats = {"examined": 0, "deleted_log_events": 0, "deleted_script_runs": 0, "deleted_agent_learnings": 0, "deleted_log_causality_edges": 0}
        
        if not older_than_days and not execution_ids:
            logger.warning("No pruning criteria specified. No logs will be pruned.")
            return stats
        
        # --- Prune log_events collection ---
        log_events_filters = []
        log_events_bind_vars = {}

        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            log_events_filters.append("doc.timestamp < @cutoff_date")
            log_events_bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            log_events_filters.append("doc.execution_id IN @execution_ids")
            log_events_bind_vars["execution_ids"] = execution_ids
        
        if log_events_filters:
            log_events_where_clause = " AND ".join(log_events_filters)
            
            # Count matching documents in log_events
            count_aql = f"""
            FOR doc IN log_events
            FILTER {log_events_where_clause}
            COLLECT WITH COUNT INTO total
            RETURN total
            """
            count_result = await self.query_logs(count_aql, log_events_bind_vars)
            stats["examined"] = count_result[0] if count_result else 0
            
            if not dry_run and stats["examined"] > 0:
                delete_aql = f"""
                FOR doc IN log_events
                FILTER {log_events_where_clause}
                REMOVE doc IN log_events
                RETURN OLD
                """
                deleted = await self.query_logs(delete_aql, log_events_bind_vars)
                stats["deleted_log_events"] = len(deleted)
                logger.info(f"Pruned {stats['deleted_log_events']} log_events.")

        # --- Prune script_runs collection (only by execution_ids as it's the primary key) ---
        if execution_ids:
            script_runs_aql_filters = ["doc.execution_id IN @execution_ids"]
            script_runs_bind_vars = {"execution_ids": execution_ids}
            script_runs_where_clause = " AND ".join(script_runs_aql_filters)

            if not dry_run:
                delete_script_runs_aql = f"""
                FOR doc IN script_runs
                FILTER {script_runs_where_clause}
                REMOVE doc IN script_runs
                RETURN OLD
                """
                deleted_runs = await self.query_logs(delete_script_runs_aql, script_runs_bind_vars)
                stats["deleted_script_runs"] = len(deleted_runs)
                logger.info(f"Pruned {stats['deleted_script_runs']} script_runs.")

        # --- Prune agent_learnings collection ---
        agent_learnings_filters = []
        agent_learnings_bind_vars = {}

        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            agent_learnings_filters.append("doc.timestamp < @cutoff_date")
            agent_learnings_bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            # Assuming agent_learnings can also be filtered by execution_id in its metadata context
            agent_learnings_filters.append("doc.context.execution_id IN @execution_ids")
            agent_learnings_bind_vars["execution_ids"] = execution_ids
        
        if agent_learnings_filters:
            agent_learnings_where_clause = " AND ".join(agent_learnings_filters)
            if not dry_run:
                delete_learnings_aql = f"""
                FOR doc IN agent_learnings
                FILTER {agent_learnings_where_clause}
                REMOVE doc IN agent_learnings
                RETURN OLD
                """
                deleted_learnings = await self.query_logs(delete_learnings_aql, agent_learnings_bind_vars)
                stats["deleted_agent_learnings"] = len(deleted_learnings)
                logger.info(f"Pruned {stats['deleted_agent_learnings']} agent_learnings.")

        # --- Prune log_causality (edges) collection ---
        log_causality_filters = []
        log_causality_bind_vars = {}

        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            log_causality_filters.append("edge.timestamp < @cutoff_date")
            log_causality_bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            # Edges also store context.execution_id for easy cleanup
            log_causality_filters.append("edge.context.execution_id IN @execution_ids")
            log_causality_bind_vars["execution_ids"] = execution_ids
        
        if log_causality_filters:
            log_causality_where_clause = " AND ".join(log_causality_filters)
            if not dry_run:
                delete_edges_aql = f"""
                FOR edge IN log_causality
                FILTER {log_causality_where_clause}
                REMOVE edge IN log_causality
                RETURN OLD
                """
                deleted_edges = await self.query_logs(delete_edges_aql, log_causality_bind_vars)
                stats["deleted_log_causality_edges"] = len(deleted_edges)
                logger.info(f"Pruned {stats['deleted_log_causality_edges']} log_causality edges.")
        
        return stats
    
    async def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a script execution."""
        # Get run info (synchronous AQL execution)
        run_aql = """
        FOR doc IN script_runs
        FILTER doc.execution_id == @execution_id
        RETURN doc
        """
        
        run_info = await self.query_logs(run_aql, {"execution_id": execution_id})
        
        if not run_info:
            return {"error": "Execution not found"}
        
        # Get log statistics (synchronous AQL execution)
        stats_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        COLLECT level = doc.level WITH COUNT INTO count
        RETURN {level: level, count: count}
        """
        
        log_stats = await self.query_logs(stats_aql, {"execution_id": execution_id})
        
        # Get errors if any (synchronous AQL execution)
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
        
        # Get learnings (synchronous AQL execution)
        learnings_aql = """
        FOR doc IN agent_learnings
        FILTER doc.context.execution_id == @execution_id
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
            "log_statistics": {stat["level"]: stat["count"] for stat in log_stats} if log_stats else {},
            "errors": errors,
            "learnings": learnings,
            "total_logs": sum(stat["count"] for stat in log_stats) if log_stats else 0
        }
        
        return summary


# Global instance getter for MAIN application usage (NOT for isolated tests)
_main_manager_instance: Optional[AgentLogManager] = None

async def get_main_log_manager() -> AgentLogManager:
    """Get or create the global AgentLogManager instance for the MAIN configured database.
    This should be used by the application, not for isolated tests.
    """
    global _main_manager_instance
    
    if _main_manager_instance is None:
        _main_manager_instance = AgentLogManager()
        
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        await _main_manager_instance.initialize(db_config)
    
    return _main_manager_instance


# ============================================
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database object and its name, and the db_config for it.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return test_db_instance, {
            "url": arango_url,
            "database": unique_db_name,
            "username": arango_username,
            "password": arango_password
        }

    try:
        db, db_config = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db, unique_db_name, db_config
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error


# ============================================
# MAIN EXECUTION FOR TESTING MANAGER
# ============================================

async def working_usage_test(test_db_instance, test_db_config):
    """Demonstrate AgentLogManager functionality with an isolated DB."""
    logger.info(f"=== Testing AgentLogManager against isolated DB: {test_db_config['database']} ===")
    
    # Create a non-singleton instance for testing, passing the test DB config
    manager = AgentLogManager(test_db_config=test_db_config)
    # Ensure it's fully initialized before use (constructor runs this as a task)
    await asyncio.sleep(0.5) # Give it time to connect

    # Temporarily replace the default logger add for the test duration
    temp_sink = ArangoLogSink(test_db_config)
    await temp_sink.start()
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(temp_sink.write, enqueue=True, level="DEBUG")

    # Test 1: Script execution context
    script_name = "test_script_manager_usage"
    execution_id_tracker = {"id": None} 

    async with manager.script_execution(script_name, {"version": "1.0"}) as logger_ctx: 
        execution_id_tracker["id"] = manager.current_execution_id 

        logger_ctx.info("Starting test operations")
        logger_ctx.debug("Debug message from test_script_manager_usage")
        logger_ctx.info("Processing data in test_script_manager_usage")
        logger_ctx.warning("Resource usage high in test_script_manager_usage")
        
        # Log a learning
        await manager.log_agent_learning(
            "Discovered that batch size of 100 is optimal for this dataset",
            "process_data",
            {"batch_size": 100, "performance": "optimal"}
        )
        
        await asyncio.sleep(1) # Simulate some work
        logger_ctx.success("Operations completed in test_script_manager_usage")
    
    exec_id = execution_id_tracker["id"]
    if not exec_id:
        logger.error("Failed to capture execution ID from context manager.")
        return False

    # Wait a bit for logs to be flushed by the sink
    await asyncio.sleep(temp_sink.flush_interval * 2 + 1) 

    # Test 2: Query logs
    logger.info(f"\nQuerying recent logs for execution: {exec_id}...")
    recent_logs = await manager.search_logs(
        "test", 
        execution_id=exec_id,
        limit=5
    )
    logger.info(f"Found {len(recent_logs)} recent logs for execution ID {exec_id}")
    assert len(recent_logs) > 0, "Expected to find logs for the test execution."
    
    # Test 3: Get execution summary
    logger.info(f"\nGetting execution summary for {exec_id}...")
    summary = await manager.get_execution_summary(exec_id)
    logger.info(f"Summary: {json.dumps(summary, indent=2)}")
    assert "run_info" in summary and summary["run_info"]["status"] == "success", "Expected successful run summary."
    assert summary["total_logs"] >= 4, f"Expected at least 4 logs (info, debug, warning, success), got {summary['total_logs']}"
    assert summary["learnings"], "Expected at least one learning recorded"

    # Stop the temporary sink
    await temp_sink.stop()
    return True


async def debug_function_test(test_db_instance, test_db_config):
    """Debug advanced features of AgentLogManager with an isolated DB."""
    logger.info(f"=== Debug Mode: Advanced Features against isolated DB: {test_db_config['database']} ===")
    
    manager = AgentLogManager(test_db_config=test_db_config)
    await asyncio.sleep(0.5)

    temp_sink = ArangoLogSink(test_db_config)
    await temp_sink.start()
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(temp_sink.write, enqueue=True, level="DEBUG")

    # Test 1: Complex AQL query (on potentially empty DB or just setup data)
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
    logger.info(f"Error summary: {results}") # Might be empty if no errors seeded

    # Test 2: Build execution graph
    logger.info("\nTest 2: Building execution graph")
    
    script_name_graph = "graph_test_script"
    execution_id_graph_tracker = {"id": None}

    async with manager.script_execution(script_name_graph) as logger_ctx:
        execution_id_graph_tracker["id"] = manager.current_execution_id
        logger_ctx.info("Step 1: Initialize for graph test")
        logger_ctx.info("Step 2: Load data for graph test")
        logger_ctx.error("Step 3: Connection failed for graph test")
        logger_ctx.info("Step 4: Retrying connection for graph test")
        logger_ctx.success("Step 5: Connection restored for graph test")
        
        await asyncio.sleep(1) # Allow logs to be processed by sink

    exec_id_graph = execution_id_graph_tracker["id"]
    if not exec_id_graph:
        logger.error("Failed to capture graph test execution ID.")
        await temp_sink.stop()
        return False

    # Wait a bit for logs to be flushed by the sink and relationships to be created
    await asyncio.sleep(temp_sink.flush_interval * 2 + 1) 

    graph = await manager.build_execution_graph(exec_id_graph)
    logger.info(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    assert len(graph["nodes"]) > 0, "Expected graph to have nodes."
    assert len(graph["edges"]) > 0, "Expected graph to have edges (at least FOLLOWED_BY)."
    
    # Test 3: Prune logs (dry run) - targets specific execution_id in this isolated DB
    logger.info("\nTest 3: Pruning old logs (dry run)")
    prune_stats = await manager.prune_logs(
        older_than_days=1, # Set a very low number of days to pick up recent test data
        execution_ids=[exec_id_graph], 
        dry_run=True
    )
    logger.info(f"Would prune: {prune_stats}")
    assert prune_stats["examined"] > 0, "Expected some logs to be examined for pruning."
    assert prune_stats["deleted_log_events"] == 0, "Expected no deletions in dry run."
    
    # Stop the temporary sink
    await temp_sink.stop()
    return True


if __name__ == "__main__":
    import sys
    load_dotenv()
    
    logger.remove() 
    logger.add(sys.stderr, level="INFO") # Always keep a console logger

    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_instance = None
        test_db_name = None
        test_db_config = None
        success = False
        try:
            # Setup a new, isolated test database for this run
            test_db_instance, test_db_name, test_db_config = await setup_test_database()
            
            if mode == "debug":
                success = await debug_function_test(test_db_instance, test_db_config)
            else:
                success = await working_usage_test(test_db_instance, test_db_config)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            # Ensure the test database is torn down
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    asyncio.run(main())
    exit(0 if success else 1)
```
<!-- CODE_FILE_END: src/agent_log_manager.py -->