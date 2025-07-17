# Loguru ArangoDB Integration Guide

## Overview

This guide shows how to integrate Loguru with ArangoDB so that all `logger.info()`, `logger.error()`, etc. calls automatically log to ArangoDB collections, creating a unified logging system where everything flows into the knowledge graph.

## Current Architecture

The logger agent project already provides:
- `ArangoLogSink` - Custom Loguru sink that batches and writes logs to ArangoDB
- `AgentLogManager` - Singleton manager for logging operations
- Automatic execution context tracking
- Integration with search, graph traversal, and memory systems

## Basic Setup

### 1. Initialize the Logger with ArangoDB Sink

```python
import asyncio
from loguru import logger
from agent_log_manager import get_log_manager
from arango_log_sink import ArangoLogSink

async def setup_logging():
    """Set up Loguru to write to ArangoDB."""
    
    # Get the log manager instance
    manager = await get_log_manager()
    
    # Create ArangoDB sink
    db_config = {
        "url": "http://localhost:8529",
        "database": "logger_agent",
        "username": "root",
        "password": ""
    }
    
    sink = ArangoLogSink(
        db_config=db_config,
        collection_name="log_events",
        batch_size=100,
        flush_interval=5.0
    )
    
    # Start the sink (important for async operation)
    await sink.start()
    
    # Remove default handlers
    logger.remove()
    
    # Add console output (optional)
    logger.add(sys.stderr, level="INFO")
    
    # Add ArangoDB sink with enqueue=True for thread safety
    logger.add(sink.write, enqueue=True, level="DEBUG")
    
    # Connect sink to manager for context tracking
    manager.set_sink(sink)
    
    return sink
```

### 2. Using the Logger in Your Application

```python
async def main():
    # Set up logging
    sink = await setup_logging()
    
    # Get log manager for advanced features
    manager = await get_log_manager()
    
    # Use script execution context for automatic tracking
    async with manager.script_execution("my_script", {"version": "1.0"}) as ctx_logger:
        ctx_logger.info("Starting script execution")
        
        # All logs within this context are automatically tagged
        # with execution_id and script_name
        ctx_logger.debug("Processing data...")
        
        try:
            result = await process_data()
            ctx_logger.success(f"Processed {result} items")
        except Exception as e:
            ctx_logger.error(f"Processing failed: {e}")
            raise
    
    # Logs outside context still work but without execution tracking
    logger.info("Script completed")
```

### 3. Structured Logging with Extra Data

```python
# Log with structured data
logger.bind(
    user_id="user123",
    action="file_upload",
    file_size=1024
).info("File uploaded successfully")

# Log errors with full context
try:
    result = risky_operation()
except Exception as e:
    logger.bind(
        error_type=type(e).__name__,
        error_message=str(e),
        stack_trace=traceback.format_exc(),
        operation="risky_operation"
    ).error("Operation failed")
```

## Integration with CC Executor

### 1. Update Tool Scripts

For each tool in `src/cc_executor/tools/`, add ArangoDB logging:

```python
#!/usr/bin/env python3
"""
Tool with integrated ArangoDB logging.
"""

import asyncio
from loguru import logger
from pathlib import Path
import sys

# Add logger agent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"))

from agent_log_manager import get_log_manager
from arango_log_sink import ArangoLogSink

async def setup_tool_logging(tool_name: str):
    """Set up logging for a tool."""
    manager = await get_log_manager()
    
    # Check if sink already configured
    if not manager.sink:
        sink = ArangoLogSink(
            db_config={
                "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
                "database": os.getenv("ARANGO_DB", "logger_agent"),
                "username": os.getenv("ARANGO_USER", "root"),
                "password": os.getenv("ARANGO_PASS", "")
            }
        )
        await sink.start()
        logger.add(sink.write, enqueue=True, level="DEBUG")
        manager.set_sink(sink)
    
    return manager

async def assess_complexity(error_info: dict):
    """Assess error complexity with logging."""
    
    # Set up logging
    manager = await setup_tool_logging("assess_complexity")
    
    # Use execution context
    async with manager.script_execution("assess_complexity", error_info) as log:
        log.info("Starting complexity assessment")
        
        # Log the error being assessed
        await manager.log_event(
            level="INFO",
            message=f"Assessing error: {error_info['error_type']}",
            script_name="assess_complexity",
            execution_id=manager.current_execution_id,
            extra_data={
                "error_type": error_info['error_type'],
                "error_message": error_info['error_message'],
                "file_path": error_info.get('file_path'),
                "assessment_type": "complexity"
            },
            tags=["assessment", "complexity", error_info['error_type'].lower()]
        )
        
        # Search for similar errors
        similar_errors = await manager.search.search_agent_activity(
            query=f"{error_info['error_type']} {error_info['error_message']}",
            filters={"event_types": ["error", "fix"]},
            limit=10
        )
        
        log.info(f"Found {len(similar_errors)} similar errors")
        
        # Generate assessment
        assessment = generate_assessment(error_info, similar_errors)
        
        # Log assessment result
        await manager.log_event(
            level="SUCCESS",
            message="Assessment completed",
            script_name="assess_complexity",
            execution_id=manager.current_execution_id,
            extra_data={
                "complexity_score": assessment['score'],
                "recommended_approach": assessment['approach'],
                "similar_errors_found": len(similar_errors)
            },
            tags=["assessment", "completed"]
        )
        
        return assessment
```

### 2. MCP Server Integration

Update the MCP server to use ArangoDB logging:

```python
# In mcp_logger_tools_enhanced.py

async def setup_mcp_logging():
    """Set up logging for MCP server."""
    
    # Initialize logger agent
    if LOGGER_AGENT_AVAILABLE:
        manager = await get_log_manager()
        
        # Create and configure sink
        sink = ArangoLogSink(
            db_config={
                "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
                "database": os.getenv("ARANGO_DB", "logger_agent"),
                "username": os.getenv("ARANGO_USER", "root"),
                "password": os.getenv("ARANGO_PASS", "")
            }
        )
        await sink.start()
        
        # Configure Loguru
        logger.remove()
        logger.add(sys.stderr, level="INFO")  # Console
        logger.add(sink.write, enqueue=True, level="DEBUG")  # ArangoDB
        
        # Connect to manager
        manager.set_sink(sink)
        
        logger.info("MCP server logging initialized with ArangoDB sink")
        return manager
    else:
        logger.warning("Logger agent not available - using console logging only")
        return None

# In server startup
@mcp.on_startup
async def startup():
    """Initialize MCP server."""
    global log_manager
    log_manager = await setup_mcp_logging()
    logger.info("MCP Logger Tools server started")
```

## Converting to python-arango-async

To use the async ArangoDB client with the sink:

```python
class AsyncArangoLogSink:
    """Async version of ArangoLogSink using python-arango-async."""
    
    def __init__(self, db_config: Dict[str, str], **kwargs):
        self.db_config = db_config
        self.client = None
        self.db = None
        self.collection = None
        # ... other init code ...
    
    async def connect(self):
        """Connect using async client."""
        from arangoasync import ArangoClient
        from arangoasync.auth import Auth
        
        async with ArangoClient(hosts=self.db_config["url"]) as client:
            auth = Auth(
                username=self.db_config["username"],
                password=self.db_config["password"]
            )
            self.db = await client.db(self.db_config["database"], auth=auth)
            self.collection = await self.db.collection(self.collection_name)
    
    async def write_batch(self, batch: List[Dict]):
        """Write a batch of logs asynchronously."""
        if not self.collection:
            await self.connect()
        
        try:
            # Insert multiple documents
            results = await self.collection.insert_many(batch)
            self.stats["successful_writes"] += len(results)
        except Exception as e:
            self.stats["failed_writes"] += len(batch)
            self.stats["last_error"] = str(e)
            # Add to retry queue
            self.failed_logs.extend(batch)
```

## Benefits of Integration

1. **Unified Logging**: All application logs automatically flow to ArangoDB
2. **Searchable History**: Use BM25 search to find similar errors and patterns
3. **Execution Tracking**: Automatic tracking of script runs and their outcomes
4. **Graph Relationships**: Build relationships between errors, fixes, and code
5. **Performance**: Batched writes minimize database overhead
6. **Reliability**: Failed logs are buffered and retried

## Query Examples

Once integrated, you can query logs using AQL:

```python
# Find all errors from a specific tool
aql = """
FOR log IN log_events
FILTER log.script_name == @tool_name
FILTER log.level == "ERROR"
SORT log.timestamp DESC
LIMIT 10
RETURN log
"""

results = await manager.db.aql.execute(
    aql,
    bind_vars={"tool_name": "assess_complexity"}
)

# Search for patterns
results = await manager.search.search_agent_activity(
    query="ModuleNotFoundError pandas",
    filters={"event_types": ["error", "fix"]},
    limit=20
)

# Find execution flows
async with manager.script_execution("analyze_logs") as log:
    flow = await manager.graph_builder.get_execution_flow(
        execution_id=manager.current_execution_id
    )
```

## Best Practices

1. **Always use enqueue=True** when adding the sink to Loguru
2. **Start the sink** before using it with `await sink.start()`
3. **Use execution contexts** for tracking related operations
4. **Add structured data** with `logger.bind()` for better searchability
5. **Tag appropriately** to enable filtering and categorization
6. **Handle shutdown gracefully** to ensure all logs are flushed

## Configuration

Environment variables for production:
```bash
export ARANGO_URL="http://localhost:8529"
export ARANGO_DB="logger_agent"
export ARANGO_USER="root"
export ARANGO_PASS="your_password"
export LOG_BATCH_SIZE="100"
export LOG_FLUSH_INTERVAL="5.0"
```

## Summary

By integrating Loguru with ArangoDB through the ArangoLogSink:
- Every `logger.info()` call becomes a searchable event in the knowledge graph
- Errors are automatically linked to their fixes
- Execution patterns emerge from the logged data
- The system learns from its own debugging history

This creates a self-improving debugging system where past experiences inform future problem-solving.