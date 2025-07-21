# MCP Logger Agent Quick Reference

## Why Logger Agent Integration is Critical

1. **Build Knowledge Base**: Every error becomes a learning opportunity
2. **Find Solutions Fast**: Query past fixes for similar errors  
3. **Track Patterns**: Identify recurring issues
4. **Self-Improving**: Tools get better over time

## Setup in Any MCP Tool

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastmcp", "python-dotenv", "loguru"]
# ///

from loguru import logger
import sys
from pathlib import Path

# 1. Import logger agent
LOGGER_AGENT_AVAILABLE = False
try:
    logger_agent_path = Path(__file__).parent.parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
    sys.path.insert(0, str(logger_agent_path))
    
    from logger_agent.sinks.arango_sink import ArangoLogSink
    from logger_agent.managers.agent_log_manager import AgentLogManager
    
    LOGGER_AGENT_AVAILABLE = True
except ImportError:
    pass

# 2. Configure if available
if LOGGER_AGENT_AVAILABLE:
    sink = ArangoLogSink({
        "url": "http://localhost:8529",
        "database": "script_logs",
        "username": "root",
        "password": ""
    })
    
    execution_id = f"mcp_{Path(__file__).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sink.set_execution_context(execution_id, Path(__file__).stem)
    
    # Start sink
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sink.start())
    loop.close()
    
    # Add with filter
    def should_store(record):
        return (
            record["level"].no >= logger.level("ERROR").no or
            record.get("extra", {}).get("log_category", "") in ["MCP_ERROR", "MCP_RESOLVED"]
        )
    
    logger.add(sink.write, filter=should_store)
```

## Logging Errors (Unresolved)

```python
@mcp.tool()
async def your_tool(param: str) -> str:
    try:
        result = do_something(param)
        return json.dumps({"success": True, "data": result})
    except Exception as e:
        error_id = f"err_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
        
        logger.error(
            f"Tool failed: {e}",
            extra={
                "log_category": "MCP_ERROR",
                "error_id": error_id,
                "tool_name": "your_tool",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "parameters": {"param": param},
                "resolved": False,  # CRITICAL!
                "resolution": None,
                "fix_rationale": None
            }
        )
        
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_id": error_id
        })
```

## Logging Resolutions

```python
# When you fix an error, ALWAYS log the resolution
logger.info(
    "Error resolved",
    extra={
        "log_category": "MCP_RESOLVED",
        "error_id": error_id,
        "resolution": "Added try/except for edge case",
        "fix_rationale": "API returns None when no data, not empty list as documented",
        "resolved": True
    }
)

# Or update existing error log
update_query = """
FOR doc IN log_events
    FILTER doc.error_id == @error_id
    UPDATE doc WITH {
        resolved: true,
        resolution: @fix,
        fix_rationale: @why,
        resolved_at: DATE_ISO8601(DATE_NOW())
    } IN log_events
"""
```

## Creating Edge Relationships

```python
# Link errors to helpful resources
await mcp__arango-tools__edge(
    from_id="log_events/err_current_123",
    to_id="log_events/err_helpful_456", 
    collection="error_relationships",
    relationship_type="inspired_by",
    helpfulness_score=0.9,
    context="Their async pattern fixed my timeout issue"
)

# Common relationship types:
# - "inspired_by" - Solution inspired by another fix
# - "similar_pattern" - Same pattern, different context
# - "uses_technique" - Borrowed specific technique
# - "references_script" - Script that shows the pattern
# - "depends_on_fix" - Requires another fix first
# - "caused_by_same" - Same root cause

# Link to scripts
await mcp__arango-tools__edge(
    from_id="log_events/err_123",
    to_id="scripts/working_example.py",
    collection="error_relationships",
    relationship_type="references_script"
)
```

## Query Patterns

### Basic Queries

```aql
// Find unresolved MCP errors
FOR doc IN log_events
    FILTER doc.log_category == "MCP_ERROR"
    FILTER doc.resolved == false
    RETURN doc

// Find how FileNotFoundError was fixed before
FOR doc IN log_events
    FILTER doc.error_type == "FileNotFoundError"
    FILTER doc.resolved == true
    RETURN {
        error: doc.error_message,
        fix: doc.resolution,
        why: doc.fix_rationale
    }
```

### Graph Traversal Queries

```aql
// Find related fixes within 2 hops
FOR error IN log_events
    FILTER error._key == "err_current_problem"
    
    FOR v, e, p IN 1..2 OUTBOUND error error_relationships
        FILTER v.resolved == true
        RETURN {
            solution: v.resolution,
            rationale: v.fix_rationale,
            path: p.edges[*].relationship_type,
            helpfulness: p.edges[*].helpfulness_score
        }

// Find most helpful fixes (by incoming edges)
FOR fix IN log_events
    FILTER fix.resolved == true
    LET incoming = (
        FOR e IN error_relationships
            FILTER e._to == fix._id
            RETURN e
    )
    FILTER LENGTH(incoming) > 0
    SORT LENGTH(incoming) DESC
    LIMIT 10
    RETURN {
        fix: fix.resolution,
        error_type: fix.error_type,
        helped_count: LENGTH(incoming),
        average_helpfulness: AVG(incoming[*].helpfulness_score)
    }

// Find solution chains for specific error type
FOR start IN log_events
    FILTER start.error_type == @error_type
    FILTER start.resolved == true
    
    FOR v, e, p IN 1..3 ANY start error_relationships
        OPTIONS {uniqueVertices: 'path'}
        FILTER v.resolved == true
        
        RETURN DISTINCT {
            start_error: start.error_message,
            chain: p.vertices[*].error_type,
            relationships: p.edges[*].relationship_type,
            final_fix: v.resolution
        }

// Find scripts that helped solve the most errors
FOR script IN scripts
    LET helped_errors = (
        FOR e IN error_relationships
            FILTER e._to == script._id
            FILTER e.relationship_type == "references_script"
            RETURN e._from
    )
    FILTER LENGTH(helped_errors) > 0
    SORT LENGTH(helped_errors) DESC
    RETURN {
        script: script.name,
        helped_count: LENGTH(helped_errors),
        error_types: (
            FOR err_id IN helped_errors
                LET err = DOCUMENT(err_id)
                RETURN DISTINCT err.error_type
        )
    }
```

## Key Fields for Knowledge Building

| Field | Type | Purpose |
|-------|------|---------|
| `error_id` | string | Unique ID to track error lifecycle |
| `resolved` | boolean | **CRITICAL** - false when error occurs, true when fixed |
| `resolution` | string | How the error was fixed |
| `fix_rationale` | string | Why this fix works (context for future) |
| `error_type` | string | Exception class name |
| `tool_name` | string | Which MCP tool failed |
| `parameters` | object | Input that caused the error |
| `log_category` | string | "MCP_ERROR" or "MCP_RESOLVED" |

## Best Practices

1. **Always set `resolved: false`** when logging errors
2. **Always update with resolution** when you fix something
3. **Include detailed rationale** - future you will thank you
4. **Use error_id** to link problem and solution
5. **Query before debugging** - the fix might already exist

## Example Workflow

```python
# 1. Error happens
error_id = "err_1234567_abcd"
# Logged with resolved: false

# 2. You debug and find: "Oh, the API key was expired"

# 3. Log the fix
logger.info("Fixed API key error", extra={
    "log_category": "MCP_RESOLVED",
    "error_id": error_id,
    "resolution": "Regenerated API key and updated .env",
    "fix_rationale": "API keys expire after 90 days, need quarterly rotation"
})

# 4. Next time: Query finds this instantly!
# "API authentication failed" -> "Check if key expired (90 days)"
```

Remember: Every error is a chance to make the system smarter!