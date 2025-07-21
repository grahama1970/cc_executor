#!/usr/bin/env python3
"""
Setup logger with CRUD capabilities via ArangoDB sink.

This module demonstrates how to configure loguru to use the ArangoDB sink
from logger_agent, enabling CRUD operations through standard logging calls.

Usage:
    from setup_crud_logger import setup_crud_logger
    
    logger = setup_crud_logger("my_script")
    logger.info("This will be stored in ArangoDB!")
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

def setup_crud_logger(
    script_name: str,
    execution_id: Optional[str] = None,
    db_config: Optional[Dict[str, Any]] = None
) -> logger:
    """
    Setup logger with ArangoDB CRUD capabilities.
    
    Args:
        script_name: Name of the script for tracking
        execution_id: Optional execution ID (auto-generated if not provided)
        db_config: Optional database config (uses env vars if not provided)
        
    Returns:
        Configured logger instance with CRUD capabilities
    """
        logger_agent_path = Path(__file__).parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
    if str(logger_agent_path) not in sys.path:
            
    try:
        # Import ArangoDB sink
        from arango_log_sink import ArangoLogSink
        
        # Use provided config or environment variables
        if db_config is None:
            db_config = {
                "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
                "database": os.getenv("ARANGO_DATABASE", "script_logs"),
                "username": os.getenv("ARANGO_USERNAME", "root"),
                "password": os.getenv("ARANGO_PASSWORD", "openSesame")
            }
        
        # Create and configure sink
        sink = ArangoLogSink(
            db_config=db_config,
            collection_name="log_events",
            batch_size=50,
            flush_interval=5.0
        )
        
        # Set execution context
        if execution_id:
            sink.set_execution_context(execution_id, script_name)
        else:
            # Auto-generate execution ID
            from datetime import datetime
            import uuid
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            execution_id = f"{script_name}_{timestamp}_{unique_id}"
            sink.set_execution_context(execution_id, script_name)
        
        # Start the sink
        sink.start()
        
        # Configure logger
        logger.remove()  # Remove default handlers
        logger.add(sys.stderr, level="INFO")  # Console output
        
        # Add ArangoDB sink
        logger.add(
            sink,
            level="DEBUG",
            enqueue=True,  # Thread-safe
            serialize=False  # Sink handles serialization
        )
        
        # Bind execution context to all logs
        contextualized_logger = logger.bind(
            execution_id=execution_id,
            script_name=script_name
        )
        
        logger.info(f"Logger configured with ArangoDB CRUD capabilities for {script_name}")
        return contextualized_logger
        
    except ImportError as e:
        logger.warning(f"Failed to setup ArangoDB sink: {e}")
        logger.warning("Falling back to standard logging without CRUD capabilities")
        
        # Return standard logger
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
        )
        return logger


def get_crud_functions():
    """
    Get CRUD functions from the logger_agent.
    
    Returns:
        Dict of CRUD functions or None if not available
    """
    try:
        from agent_log_manager import AgentLogManager
        
        # Get singleton instance
        manager = AgentLogManager()
        
        return {
            "query_logs": manager.query_logs,
            "search_bm25_logs": manager.search_bm25_logs,
            "prune_logs": manager.prune_logs,
            "get_latest_response": manager.get_latest_response,
            "log_agent_learning": manager.log_agent_learning,
            "build_execution_graph": manager.build_execution_graph
        }
        
    except ImportError:
        return None


# Example usage
if __name__ == "__main__":
    # Setup logger with CRUD
    logger = setup_crud_logger("test_crud_setup")
    
    # These will be stored in ArangoDB
    logger.info("Testing CRUD logger setup")
    logger.debug("Debug message with details", extra={"key": "value"})
    logger.warning("Warning message")
    logger.error("Error message for testing")
    
    # Get CRUD functions
    crud_funcs = get_crud_functions()
    if crud_funcs:
        print("\nAvailable CRUD functions:")
        for func_name in crud_funcs:
            print(f"  - {func_name}")
    else:
        print("\nCRUD functions not available")