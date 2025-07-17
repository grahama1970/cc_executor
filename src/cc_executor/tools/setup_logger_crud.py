#!/usr/bin/env python3
"""
Setup logger CRUD functionality for tools.

This module demonstrates how to make logger.info() calls CRUD-compatible
with the logger_agent by setting up the ArangoDB sink.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python setup_logger_crud.py          # Runs working_usage() - stable, known to work
  python setup_logger_crud.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
===
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import the setup utility
try:
    from utils.setup_arangodb_logging import setup_arangodb_logging
    SETUP_AVAILABLE = True
except ImportError:
    SETUP_AVAILABLE = False
    logger.warning("setup_arangodb_logging not available - logger.info() won't be CRUD-compatible")


async def setup_crud_logging(tool_name: str = "query_converter") -> Optional[Any]:
    """
    Set up CRUD-compatible logging for a tool.
    
    When this is set up, all logger.info(), logger.error(), etc. calls
    will automatically be stored in ArangoDB and can be queried.
    
    Args:
        tool_name: Name of the tool for context
        
    Returns:
        LogManager instance if successful, None otherwise
    """
    if not SETUP_AVAILABLE:
        logger.warning("Cannot set up CRUD logging - setup_arangodb_logging not available")
        return None
    
    # Set up ArangoDB logging
    manager = await setup_arangodb_logging(
        tool_name=tool_name,
        console_level="INFO",
        db_level="DEBUG"  # Store all log levels in DB
    )
    
    if manager:
        logger.success(f"CRUD logging enabled for {tool_name}")
        logger.info("All logger calls are now being stored in ArangoDB")
        
        # Example of how logs are now CRUD-compatible
        logger.bind(
            tool=tool_name,
            operation="setup",
            status="complete"
        ).info("Tool initialization complete")
    
    return manager


async def working_usage():
    """
    Demonstrate CRUD-compatible logging setup.
    
    AGENT: Run this for stable, production-ready example.
    """
    logger.info("=== Testing CRUD Logging Setup ===")
    
    # Set up CRUD logging
    manager = await setup_crud_logging("test_tool")
    
    if not manager:
        logger.warning("CRUD logging not available - continuing without it")
        return True
    
    # Now all these logs are stored in ArangoDB
    logger.info("This message is stored in ArangoDB")
    logger.debug("Debug messages are also stored")
    logger.warning("Warnings are tracked")
    logger.error("Errors are recorded (this is not a real error)")
    
    # Structured logging with extra fields
    logger.bind(
        query_type="similar_errors",
        error_type="ImportError",
        user_id="test_user"
    ).info("User searched for similar ImportError bugs")
    
    # You can query these logs later
    logger.info("Example queries you can run:")
    logger.info("- Find all errors: FOR doc IN log_events FILTER doc.level == 'ERROR' RETURN doc")
    logger.info("- Find by tool: FOR doc IN log_events FILTER doc.extra_data.tool == 'test_tool' RETURN doc")
    logger.info("- Search messages: FOR doc IN log_events FILTER CONTAINS(doc.message, 'ImportError') RETURN doc")
    
    logger.success("✅ CRUD logging demonstration complete!")
    return True


async def debug_function():
    """
    Debug function for testing advanced CRUD operations.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    """
    logger.info("=== Debug Mode: Testing CRUD Operations ===")
    
    # Set up CRUD logging
    manager = await setup_crud_logging("debug_tool")
    
    if not manager:
        logger.warning("Cannot test CRUD operations without manager")
        return True
    
    # Test 1: Log with complex metadata
    logger.bind(
        operation="schema_inspection",
        database="script_logs",
        collections=["log_events", "tool_executions", "errors_and_failures"],
        metadata={
            "version": "1.0",
            "timestamp": "2025-07-15T13:19:00Z",
            "user": "debug_user"
        }
    ).info("Completed schema inspection with 14 collections found")
    
    # Test 2: Log query execution
    logger.bind(
        query_type="BM25_search",
        query="Find similar ImportError bugs",
        aql_generated="""
        FOR doc IN agent_activity_search
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        LET score = BM25(doc)
        FILTER score > 0.5
        SORT score DESC
        LIMIT 10
        """,
        bind_vars={"query": "ImportError"}
    ).info("Generated AQL query for similarity search")
    
    # Test 3: Performance tracking
    import time
    start_time = time.time()
    
    # Simulate some work
    await asyncio.sleep(0.1)
    
    duration = time.time() - start_time
    logger.bind(
        operation="query_generation",
        duration_seconds=duration,
        performance={
            "schema_fetch_ms": 50,
            "prompt_generation_ms": 25,
            "total_ms": duration * 1000
        }
    ).info("Query generation completed")
    
    # Test 4: Error tracking with context
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.bind(
            error_type=type(e).__name__,
            error_context={
                "function": "debug_function", 
                "operation": "division",
                "recovery_action": "logged_and_continued"
            }
        ).exception("Handled exception during debug testing")
    
    logger.success("Debug CRUD operations completed!")
    return True


# Example of how to integrate into existing tools
def add_crud_to_tool_example():
    """
    Example of how to add CRUD logging to query_converter.py or inspect_arangodb_schema.py
    
    Add this to the top of the tool file after imports:
    
    ```python
    # Set up CRUD logging if available
    try:
        from setup_logger_crud import setup_crud_logging
        asyncio.create_task(setup_crud_logging("query_converter"))
    except ImportError:
        pass  # Continue without CRUD logging
    ```
    """
    pass


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
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())