#!/usr/bin/env python3
"""
Simple Natural Language to AQL Query Converter.

This tool:
1. Gets the latest schema (creates one if it doesn't exist)
2. Provides clear English language to AQL examples
3. Returns a prompt that guides the agent to write AQL queries

Instead of complex regex parsing, we provide examples and let the LLM understand intent.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python query_converter.py          # Runs working_usage() - stable, known to work
  python query_converter.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
==="""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from loguru import logger
from dotenv import find_dotenv, load_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Import the ArangoDB-backed logger that provides CRUD capabilities
# All logger.info() calls will now be stored in the database
# Add logger agent path FIRST before any imports
logger_agent_path = Path(__file__).parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
if str(logger_agent_path) not in sys.path:
    
# Now we can import from logger_agent
try:
    # Import with full module path
    import arango_log_sink
    import agent_log_manager
    from arango_log_sink import ArangoLogSink
    from agent_log_manager import AgentLogManager
    LOGGER_AGENT_AVAILABLE = True
except ImportError as e:
    logger.error(f"CRITICAL: Cannot import logger_agent components: {e}")
    logger.error("This tool REQUIRES logger_agent for CRUD functionality!")
    LOGGER_AGENT_AVAILABLE = False

# Configure logger with ArangoDB sink immediately
if LOGGER_AGENT_AVAILABLE:
    # Database configuration
    db_config = {
        "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
        "database": os.getenv("ARANGO_DATABASE", "script_logs"),
        "username": os.getenv("ARANGO_USERNAME", "root"),
        "password": os.getenv("ARANGO_PASSWORD", "openSesame")
    }
    
    # Create and configure the sink
    sink = ArangoLogSink(
        db_config=db_config,
        collection_name="log_events",
        batch_size=50,
        flush_interval=5.0
    )
    
    # Generate execution ID
    script_name = Path(__file__).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    execution_id = f"{script_name}_{timestamp}_{unique_id}"
    
    # Set execution context
    sink.set_execution_context(execution_id, script_name)
    
    # Start the sink SYNCHRONOUSLY (critical!)
    # Create event loop if needed for sync start
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Already in async context, create task
        asyncio.create_task(sink.start())
    except RuntimeError:
        # No event loop, create one
        loop = asyncio.new_event_loop()
        loop.run_until_complete(sink.start())
        loop.close()
    
    # Configure loguru with BOTH console and ArangoDB sink
    logger.remove()  # Remove default handlers
    
    # Console sink - always active
    logger.add(
        sys.stderr, 
        level="INFO", 
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    
    # ArangoDB sink with filter - only logs with db_store=True or specific levels
    def should_store_in_db(record):
        """Filter function to determine if log should go to database."""
        # Always store errors and above
        if record["level"].no >= logger.level("ERROR").no:
            return True
        
        # Store if explicitly marked
        if record.get("extra", {}).get("db_store", False):
            return True
        
        # Store specific log categories
        log_category = record.get("extra", {}).get("log_category", "")
        if log_category in ["AGENT_LEARNING", "SCRIPT_FINAL_RESPONSE", "SCHEMA_INSPECTION"]:
            return True
        
        # Default: don't store routine logs in DB
        return False
    
    logger.add(
        sink.write,  # Use the sink's write method
        level="DEBUG",
        enqueue=True,  # Thread-safe
        serialize=False,  # Sink handles serialization
        filter=should_store_in_db  # Selective storage
    )
    
    # Create manager instance for CRUD operations
    manager = AgentLogManager()
    
    # Initialize manager synchronously
    def init_manager():
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.initialize(db_config))
        loop.close()
    
    init_manager()
    
    # Set the sink in manager
    manager.set_sink(sink)
    
    logger.bind(db_store=True).success(f"Logger configured with ArangoDB CRUD! Execution ID: {execution_id}")
    logger.info("Logger configured with selective ArangoDB storage (errors + marked logs)")
    
    # Define CRUD functions
    def log_agent_learning(msg: str, function_name: str = "", **kwargs):
        """Log agent learning to ArangoDB."""
        logger.bind(
            db_store=True,  # Explicitly store in database
            log_category="AGENT_LEARNING",
            function_name=function_name,
            execution_id=execution_id,
            **kwargs
        ).info(msg)
    
    def start_run(name: str, mode: str) -> str:
        """Start tracking a script run."""
        logger.info(f"Starting script run: {name} in {mode} mode")
        # Also track in script_runs collection
        if hasattr(manager, 'start_run'):
            manager.start_run(name, mode)
        return execution_id
    
    def end_run(exec_id: str, success: bool):
        """End tracking a script run."""
        logger.info(f"Script run completed: {exec_id}, success={success}")
        if hasattr(manager, 'end_run'):
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(manager.end_run(exec_id, success))
            loop.close()
    
    # Async CRUD functions that actually query the database
    async def query_logs(aql_query: str, bind_vars: Dict = None):
        """Execute AQL query against log database."""
        if hasattr(manager, 'query_logs'):
            return await manager.query_logs(aql_query, bind_vars)
        return []
    
    async def search_bm25_logs(query: str, limit: int = 10):
        """Search logs using BM25 text search."""
        if hasattr(manager, 'search_bm25_logs'):
            return await manager.search_bm25_logs(query, limit)
        return []
    
    async def prune_logs(older_than_days: int = 30, dry_run: bool = False):
        """Prune old logs from database."""
        if hasattr(manager, 'prune_logs'):
            return await manager.prune_logs(older_than_days, dry_run)
        return 0
    
    async def get_latest_response(script_name: str, execution_id: str = None):
        """Get latest response from a script."""
        if hasattr(manager, 'get_latest_response'):
            return await manager.get_latest_response(script_name, execution_id)
        return None
    
    CRUD_LOGGER_AVAILABLE = True
    
else:
    # CRITICAL: Without logger_agent, we can't provide CRUD functionality
    logger.error("RUNNING WITHOUT CRUD CAPABILITIES - This is NOT acceptable!")
    logger.error("Please ensure logger_agent is properly installed")
    
    # Dummy functions that warn about missing functionality
    def log_agent_learning(*args, **kwargs):
        logger.warning("log_agent_learning called but CRUD not available!")
    
    def start_run(*args, **kwargs):
        logger.warning("start_run called but CRUD not available!")
        return "no_crud_available"
    
    def end_run(*args, **kwargs):
        logger.warning("end_run called but CRUD not available!")
    
    async def query_logs(*args, **kwargs):
        logger.warning("query_logs called but CRUD not available!")
        return []
    
    async def search_bm25_logs(*args, **kwargs):
        logger.warning("search_bm25_logs called but CRUD not available!")
        return []
    
    async def prune_logs(*args, **kwargs):
        logger.warning("prune_logs called but CRUD not available!")
        return 0
    
    async def get_latest_response(*args, **kwargs):
        logger.warning("get_latest_response called but CRUD not available!")
        return None
    
    CRUD_LOGGER_AVAILABLE = False
    execution_id = "no_crud"

# Get project root from .env file location
PROJECT_ROOT = Path(find_dotenv()).parent


async def get_schema() -> Dict[str, Any]:
    """
    Get the current schema using inspect_arangodb_schema.
    Simple and direct - no caching needed.
    
    Returns:
        Dictionary containing the schema or error information
    """
    try:
        # Import and run schema inspection
        from inspect_arangodb_schema import inspect_logger_agent_schema
        
        logger.info("Inspecting database schema...")
        schema_report = await inspect_logger_agent_schema()
        
        return schema_report
                
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        return {"error": str(e)}




async def generate_agent_prompt(
    natural_query: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    file_path: Optional[str] = None,
    error_id: Optional[str] = None,
    include_schema_info: bool = True
) -> str:
    """
    Generate a prompt that helps the agent write AQL queries.
    
    This function:
    1. Gets/creates the latest schema
    2. Provides English → AQL examples
    3. Returns a prompt for the agent to write queries
    
    Args:
        natural_query: What the user wants to find
        error_type: Current error type (optional)
        error_message: Current error message (optional)
        file_path: Current file (optional)
        error_id: Error ID in ArangoDB (optional)
        include_schema_info: Whether to include schema (default: True)
        
    Returns:
        Prompt with schema and examples to guide AQL query writing
    """
    
    prompt = f"""# Natural Language to AQL Query Assistant

## Your Request
"{natural_query}"
"""
    
    # Add context if provided
    if any([error_type, error_message, file_path, error_id]):
        prompt += "\n## Current Context\n"
        if error_type:
            prompt += f"- Error Type: `{error_type}`\n"
        if error_message:
            prompt += f"- Error Message: {error_message}\n"
        if file_path:
            prompt += f"- File: `{file_path}`\n"
        if error_id:
            prompt += f"- Error ID: `{error_id}`\n"
        prompt += "\n"
    
    # Get and show schema
    if include_schema_info:
        schema = await get_schema()
        if schema.get('error'):
            prompt += f"## Database Schema\n⚠️ Error: {schema['error']}\n\n"
        else:
            prompt += f"## Database Schema\n```json\n{json.dumps(schema, indent=2)}\n```\n\n"
    
    # Provide English → AQL examples
    prompt += """## English Language → AQL Examples

Here are common query patterns to help you write your AQL:

### 1. "Find similar errors/bugs"
**English**: "Find similar ImportError bugs", "errors like mine", "similar issues"
```aql
FOR doc IN agent_activity_search
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
SORT score DESC
LIMIT 10
RETURN {
    id: doc._id,
    message: doc.message,
    error_type: doc.error_type,
    resolved: doc.resolved,
    score: score
}
```
**Bind vars**: `{"query": "error message text"}`

### 2. "How was this fixed?"
**English**: "How was ImportError fixed?", "show me fixes", "what resolved this error?"
```aql
FOR error IN log_events
FILTER error.error_type == @error_type
FILTER error.resolved == true
SORT error.resolved_at DESC
LIMIT 10
RETURN {
    error: error.message,
    fix: error.fix_description,
    time_to_fix: error.resolution_time_minutes,
    fixed_at: error.resolved_at
}
```
**Bind vars**: `{"error_type": "ImportError"}`

### 3. "Recent errors/bugs"
**English**: "errors from last hour", "bugs today", "issues this week"
```aql
FOR doc IN log_events
FILTER doc.level == 'ERROR'
FILTER DATE_DIFF(doc.timestamp, DATE_NOW(), 'hour') <= @hours
SORT doc.timestamp DESC
LIMIT 50
RETURN doc
```
**Bind vars**: `{"hours": 24}` (1 hour = 1, 1 day = 24, 1 week = 168)

### 4. "What's related/connected?"
**English**: "what's related to main.py?", "find connections", "2 hops from this error"
```aql
FOR v, e, p IN 1..@depth ANY @start_id error_causality, agent_flow
RETURN DISTINCT {
    item: v,
    distance: LENGTH(p.edges),
    connection_type: p.edges[-1].relationship_type
}
```
**Bind vars**: `{"depth": 2, "start_id": "log_events/12345"}`

### 5. "Count/group by"
**English**: "count errors by type", "most common bugs", "error breakdown"
```aql
FOR doc IN log_events
FILTER doc.level == 'ERROR'
COLLECT error_type = doc.error_type WITH COUNT INTO count
SORT count DESC
RETURN {type: error_type, count: count}
```

### 6. "Unresolved/pending"
**English**: "unresolved errors", "pending bugs", "not fixed yet"
```aql
FOR doc IN log_events
FILTER doc.level == 'ERROR'
FILTER doc.resolved != true
SORT doc.timestamp DESC
RETURN doc
```

### 7. "In specific file/path"
**English**: "errors in main.py", "bugs in src/", "issues in tests"
```aql
FOR doc IN log_events
FILTER doc.extra_data.file_path == @file  // Exact match
// OR
FILTER doc.extra_data.file_path LIKE @pattern  // Pattern match
RETURN doc
```
**Bind vars**: `{"file": "main.py"}` or `{"pattern": "src/%.py"}`

### 8. "Fixed quickly/slowly"
**English**: "errors fixed in under 5 minutes", "quick fixes", "long-standing bugs"
```aql
FOR doc IN log_events
FILTER doc.resolved == true
FILTER doc.resolution_time_minutes <= @max_minutes
SORT doc.resolution_time_minutes ASC
RETURN {
    error: doc.message,
    fix_time: doc.resolution_time_minutes,
    fix: doc.fix_description
}
```
**Bind vars**: `{"max_minutes": 5}`

## How to Write Your Query

1. **Find the most similar example** above
2. **Adapt it** to your specific needs:
   - Change filters
   - Add/remove fields
   - Adjust limits
3. **Set bind variables** for your context
4. **Execute** using:

```python
from agent_log_manager import get_log_manager

async def run_your_query():
    manager = await get_log_manager()
    
    aql = '''
    <YOUR AQL HERE>
    '''
    
    bind_vars = {
        # Your variables
    }
    
    cursor = await manager.db.aql.execute(aql, bind_vars=bind_vars)
    results = list(cursor)
    
    for result in results:
        print(result)
    
    return results
```

## Tips
- Use `DATE_NOW()` not `NOW()` in ArangoDB
- BM25() requires a search view (like `agent_activity_search`)
- Use `DISTINCT` to avoid duplicates in graph queries
- Always use bind variables for user input (@variable)
- Start with small `LIMIT` values while testing

## ⚠️ Common AQL Mistakes

If your query returns None, Error, or incorrect results, check the **ARANGODB_RULES.md** document:
`/home/graham/workspace/experiments/cc_executor/src/cc_executor/tools/ARANGODB_RULES.md`

Key rules to remember:
- **NEVER use filters with APPROX_NEAR_COSINE** (Error 1554)
- **Cannot bind collection/view names** - use Python f-strings
- **Vector indexes need params as sub-object**
- **Always provide ALL bind parameters** (Error 1552)
- **Check the error quick reference table** in ARANGODB_RULES.md

When in doubt, keep queries simple and reference the rules document!
"""
    
    return prompt


async def working_usage():
    """
    Demonstrate proper usage of the tool.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    logger.info("=== Natural Language to AQL Converter ===")
    
    # Test different query types
    test_queries = [
        ("Find similar ImportError bugs", {"error_type": "ImportError"}),
        ("How was ModuleNotFoundError fixed?", {"error_type": "ModuleNotFoundError"}),
        ("Show me errors from the last 24 hours", {}),
        ("What's related to main.py?", {"file_path": "main.py"})
    ]
    
    for query, context in test_queries:
        logger.info(f"\nProcessing: {query}")
        
        prompt = await generate_agent_prompt(
            natural_query=query,
            **context
        )
        
        # Verify the prompt has key sections
        assert "Natural Language to AQL Query Assistant" in prompt
        assert "Database Schema" in prompt or "Schema Error" in prompt
        assert "English Language → AQL Examples" in prompt
        assert "How to Write Your Query" in prompt
        
        logger.success("✓ Generated prompt with schema and examples")
        
        # Log the successful conversion to database
        if CRUD_LOGGER_AVAILABLE:
            log_agent_learning(
                f"Successfully converted natural language query '{query}' to AQL prompt",
                function_name="working_usage"
            )
            
            # Also store the prompt generation event
            logger.bind(
                db_store=True,
                log_category="PROMPT_GENERATION",
                query=query,
                context=context,
                execution_id=execution_id
            ).info(f"Generated AQL prompt for: {query}")
        
        # Save one example
        if "ImportError" in query:
            output_path = Path(__file__).parent / "tmp" / "example_query_prompt.md"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(prompt)
            logger.info(f"Example saved to: {output_path}")
    
    logger.success("✅ All tests passed!")
    return True


async def debug_function():
    """
    Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    logger.info("=== Debug Mode ===")
    
    # Test schema retrieval
    logger.info("Testing schema retrieval...")
    schema = await get_schema()
    
    if schema.get('error'):
        logger.error(f"Schema error: {schema['error']}")
    else:
        logger.success(f"Schema retrieved with {len(schema.get('collections', {}))} collections")
        
        # Print raw schema
        print(f"\nSchema (first 500 chars):\n{json.dumps(schema, indent=2)[:500]}...")
    
    # Test a specific query
    test_query = "Find all errors that were fixed within 5 minutes"
    logger.info(f"\nTesting query: {test_query}")
    
    prompt = await generate_agent_prompt(
        natural_query=test_query,
        include_schema_info=True
    )
    
    # Find the relevant example in the prompt
    lines = prompt.split('\n')
    in_relevant_section = False
    for line in lines:
        if "Fixed quickly/slowly" in line:
            in_relevant_section = True
        elif in_relevant_section and line.startswith("###"):
            break
        elif in_relevant_section:
            print(line)
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    # Handle JSON arguments from MCP server
    if len(sys.argv) > 1 and sys.argv[1].startswith('{'):
        args = json.loads(sys.argv[1])
        
        # Generate prompt with provided arguments
        async def run_mcp():
            prompt = await generate_agent_prompt(
                natural_query=args.get("natural_query", ""),
                error_type=args.get("error_type"),
                error_message=args.get("error_message"),
                file_path=args.get("file_path"),
                error_id=args.get("error_id"),
                include_schema_info=args.get("include_schema_info", True)
            )
            
            # Return as JSON for MCP
            print(json.dumps({"prompt": prompt}))
        
        asyncio.run(run_mcp())
    else:
        # Direct execution
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        # Start tracking this script execution in ArangoDB if available
        if CRUD_LOGGER_AVAILABLE:
            script_name = Path(__file__).stem
            exec_id = start_run(script_name, mode)
            # Log script start to database
            logger.bind(
                db_store=True,
                execution_id=exec_id,
                script_name=script_name,
                mode=mode
            ).info(f"Script '{script_name}' starting in '{mode.upper()}' mode")
            log_agent_learning(f"Query converter initiated in '{mode}' mode.", function_name="__main__")
        
        success = False
        try:
            if mode == "debug":
                success = asyncio.run(debug_function())
            else:
                success = asyncio.run(working_usage())
        except Exception as e:
            # Critical errors always go to database
            logger.critical(f"Unhandled error in query converter: {e}", exc_info=True)
            if CRUD_LOGGER_AVAILABLE:
                log_agent_learning(f"CRITICAL: Query converter failed with: {e}", function_name="__main__")
        
        # End the script run record in ArangoDB
        if CRUD_LOGGER_AVAILABLE:
            exit_code = 0 if success else 1
            # Log completion to database
            logger.bind(
                db_store=True,
                execution_id=execution_id,
                exit_code=exit_code,
                success=success
            ).info(f"Script finished with exit code {exit_code}")
            end_run(execution_id, success)
            exit(exit_code)
        else:
            exit(0 if success else 1)