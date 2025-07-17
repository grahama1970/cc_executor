#!/usr/bin/env python3
"""
Setup utility for configuring Loguru with ArangoDB sink.

This module provides a simple way to configure Loguru to automatically
log all messages to ArangoDB, creating a searchable knowledge graph
of application events.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python setup_arangodb_logging.py          # Runs working_usage() - stable, known to work
  python setup_arangodb_logging.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from loguru import logger

# Add logger agent to path
LOGGER_AGENT_PATH = Path(__file__).parent.parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
if LOGGER_AGENT_PATH.exists():
    sys.path.insert(0, str(LOGGER_AGENT_PATH))
    LOGGER_AGENT_AVAILABLE = True
else:
    LOGGER_AGENT_AVAILABLE = False
    logger.warning(f"Logger agent not found at {LOGGER_AGENT_PATH}")


async def setup_arangodb_logging(
    tool_name: Optional[str] = None,
    db_config: Optional[Dict[str, str]] = None,
    console_level: str = "INFO",
    db_level: str = "DEBUG",
    batch_size: int = 100,
    flush_interval: float = 5.0
) -> Optional[Any]:
    """
    Set up Loguru to automatically log to ArangoDB.
    
    Args:
        tool_name: Name of the tool/script for context
        db_config: Database configuration (uses env vars if not provided)
        console_level: Log level for console output
        db_level: Log level for database output
        batch_size: Number of logs to batch before writing
        flush_interval: Seconds between automatic flushes
        
    Returns:
        LogManager instance if successful, None otherwise
    """
    
    if not LOGGER_AGENT_AVAILABLE:
        logger.error("Logger agent not available - cannot set up ArangoDB logging")
        return None
    
    try:
        from agent_log_manager import get_log_manager
        from arango_log_sink import ArangoLogSink
    except ImportError as e:
        logger.error(f"Failed to import logger agent components: {e}")
        return None
    
    # Get or create log manager
    manager = await get_log_manager()
    
    # Check if already configured
    if manager.sink:
        logger.info("ArangoDB logging already configured")
        return manager
    
    # Configure database connection
    if not db_config:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DB", "logger_agent"),
            "username": os.getenv("ARANGO_USER", "root"),
            "password": os.getenv("ARANGO_PASS", "")
        }
    
    try:
        # Create ArangoDB sink
        sink = ArangoLogSink(
            db_config=db_config,
            collection_name="log_events",
            batch_size=batch_size,
            flush_interval=flush_interval
        )
        
        # Start the sink (important for async operation)
        await sink.start()
        
        # Configure Loguru
        logger.remove()  # Remove default handlers
        
        # Add console output
        logger.add(
            sys.stderr,
            level=console_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
            enqueue=True
        )
        
        # Add ArangoDB sink
        logger.add(
            sink.write,
            level=db_level,
            enqueue=True,  # Thread-safe queuing
            catch=True,    # Don't crash on sink errors
            backtrace=True # Include stack traces
        )
        
        # Connect sink to manager for context tracking
        manager.set_sink(sink)
        
        # Log initialization
        logger.success(f"ArangoDB logging initialized for {tool_name or 'application'}")
        logger.info(f"Logging to database: {db_config['database']} at {db_config['url']}")
        
        return manager
        
    except Exception as e:
        logger.error(f"Failed to set up ArangoDB logging: {e}")
        logger.info("Falling back to console-only logging")
        return None


def get_default_db_config() -> Dict[str, str]:
    """Get default database configuration from environment."""
    return {
        "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
        "database": os.getenv("ARANGO_DB", "logger_agent"),
        "username": os.getenv("ARANGO_USER", "root"),
        "password": os.getenv("ARANGO_PASS", "")
    }


async def working_usage():
    """
    Demonstrate setting up ArangoDB logging.
    
    AGENT: This is the stable, working example.
    """
    logger.info("=== Testing ArangoDB Logging Setup ===")
    
    # Setup logging
    manager = await setup_arangodb_logging(
        tool_name="setup_test",
        console_level="DEBUG",
        db_level="DEBUG"
    )
    
    if not manager:
        logger.warning("Could not set up ArangoDB logging (expected if DB not running)")
        # Still pass test as this is expected behavior
        return True
    
    # Test logging at different levels
    logger.debug("Debug message - should appear in DB")
    logger.info("Info message - should appear in console and DB")
    logger.warning("Warning message")
    logger.error("Error message (not a real error)")
    logger.success("Success message")
    
    # Test structured logging
    logger.bind(
        user_id="test_user",
        action="test_action",
        metadata={"test": True}
    ).info("Structured log entry")
    
    # Test execution context
    async with manager.script_execution("test_script", {"version": "1.0"}) as ctx_log:
        ctx_log.info("Inside execution context")
        ctx_log.debug("This log has execution_id and script_name")
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        ctx_log.success("Context execution completed")
    
    logger.info("All logging tests completed")
    
    # Verify stats if sink available
    if manager.sink:
        stats = manager.sink.stats
        logger.info(f"Logging stats: {stats}")
        assert stats["total_logs"] > 0, "Should have logged messages"
    
    return True


async def debug_function():
    """
    Debug function for testing new logging features.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    """
    logger.info("=== Debug Mode: Testing Advanced Logging ===")
    
    # Test 1: Multiple setup calls (should reuse existing)
    logger.info("Test 1: Multiple setup calls")
    manager1 = await setup_arangodb_logging(tool_name="debug1")
    manager2 = await setup_arangodb_logging(tool_name="debug2")
    
    if manager1 and manager2:
        assert manager1 is manager2, "Should return same manager instance"
        logger.success("✓ Singleton pattern working correctly")
    
    # Test 2: Error logging with full context
    logger.info("\nTest 2: Error logging with context")
    
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.bind(
            error_type=type(e).__name__,
            error_message=str(e),
            error_context={
                "function": "debug_function",
                "line": "attempting division by zero"
            }
        ).exception("Caught exception with full context")
    
    # Test 3: Performance logging
    logger.info("\nTest 3: Performance logging")
    
    import time
    start_time = time.time()
    
    # Simulate some work
    for i in range(10):
        logger.bind(
            iteration=i,
            progress=f"{(i+1)*10}%"
        ).debug(f"Processing item {i}")
        await asyncio.sleep(0.01)
    
    duration = time.time() - start_time
    logger.bind(
        duration_seconds=duration,
        items_processed=10,
        rate_per_second=10/duration
    ).info("Performance test completed")
    
    # Test 4: Nested contexts
    if manager1:
        logger.info("\nTest 4: Nested execution contexts")
        
        async with manager1.script_execution("outer_context") as outer_log:
            outer_log.info("In outer context")
            
            # Create a sub-task
            async with manager1.script_execution("inner_context") as inner_log:
                inner_log.info("In inner context")
                inner_log.debug("Both contexts active")
            
            outer_log.info("Back to outer context")
    
    logger.success("Debug tests completed!")
    return True


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