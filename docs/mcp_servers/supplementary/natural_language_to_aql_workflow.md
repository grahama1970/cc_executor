# Natural Language to AQL Workflow

## Overview

This document describes the complete workflow for converting natural language queries to AQL using cached database schema from the logger agent.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Query    │────▶│  Query Converter │────▶│   AQL Query     │
│ "Find similar   │     │     (MCP Tool)   │     │ FOR doc IN ...  │
│   bugs"         │     └──────────────────┘     └─────────────────┘
                                │                           │
                                ▼                           ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Cached Schema   │     │  Query Results  │
                        │  (Logger Agent)  │     │   (ArangoDB)    │
                        └──────────────────┘     └─────────────────┘
```

## Step 1: Cache Database Schema

First, run the `cache_db_schema` tool to store the schema in logger agent:

```bash
# Using MCP
mcp query cache_db_schema --force_refresh true --cache_duration_hours 24
```

This stores the schema with:
- Category: `db_schema`
- Tags: `["db_schema", "cache", "infrastructure", "agent_resource"]`
- Expiration: 24 hours (configurable)

### What Gets Cached

```json
{
  "category": "db_schema",
  "schema_version": "1.0",
  "database": "logger_agent",
  "collections": {
    "log_events": {
      "type": "document",
      "count": 15000,
      "schema": {
        "timestamp": ["str"],
        "level": ["str"],
        "message": ["str"],
        "error_type": ["str"],
        "execution_id": ["str"],
        "extra_data": ["dict"]
      }
    },
    "error_causality": {
      "type": "edge",
      "count": 500,
      "schema": {
        "_from": ["str"],
        "_to": ["str"],
        "relationship_type": ["str"],
        "confidence": ["float"]
      }
    }
  },
  "views": {
    "agent_activity_search": {
      "type": "arangosearch",
      "links": ["log_events", "errors_and_failures"]
    }
  },
  "sample_queries": [...],
  "agent_prompt": "..."
}
```

## Step 2: Use Query Converter

The `query_converter` tool automatically retrieves the cached schema:

```python
# Example natural language queries
queries = [
    "Find all similar functions to the one I'm debugging that were resolved",
    "Show me ModuleNotFoundError fixes from the last week",
    "What functions are related to data_processor.py by 2 hops?",
    "Find all errors caused by missing imports that got fixed"
]
```

### How It Works

1. **Query Parsing**: Natural language is parsed to identify:
   - Intent (FIND_SIMILAR, FIND_FIXES, FIND_RELATED, etc.)
   - Entities (error types, time ranges, file names)
   - Constraints (resolved, time filters, etc.)

2. **Schema Retrieval**: The tool queries logger agent for cached schema:
   ```aql
   FOR doc IN log_events
   FILTER doc.extra_data.category == "db_schema"
   FILTER doc.timestamp > DATE_ISO8601(DATE_ADD(NOW(), -24, 'hour'))
   SORT doc.timestamp DESC
   LIMIT 1
   RETURN doc.extra_data
   ```

3. **AQL Generation**: Based on intent and available collections/views:
   - Text search → Uses BM25 search view
   - Relationships → Uses graph traversal
   - Time-based → Uses DATE_DIFF functions

## Step 3: Execute Generated Query

The tool returns a prompt with the generated AQL and execution code:

```python
# Get logger manager
manager = await get_log_manager()

# Execute the generated query
aql_query = """
FOR doc IN agent_activity_search
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
SORT score DESC
LIMIT 10
RETURN {document: doc, score: score}
"""

bind_vars = {"query": "ModuleNotFoundError pandas"}
results = await manager.db.aql.execute(aql_query, bind_vars=bind_vars)
```

## Implementation Details

### Query Intent Mapping

| Natural Language Pattern | Intent | AQL Pattern |
|-------------------------|--------|-------------|
| "find similar", "like this" | FIND_SIMILAR | BM25 search with scoring |
| "how was X fixed", "fixes for" | FIND_FIXES | Graph traversal FIXED_BY |
| "related to", "connected" | FIND_RELATED | Multi-hop traversal |
| "caused by", "led to" | FIND_CAUSED_BY | Causal graph traversal |
| "last week", "recent" | TIME_BASED | DATE_DIFF filters |

### Schema-Aware Query Generation

The converter uses cached schema to:
1. **Validate collections exist** before generating queries
2. **Choose appropriate views** for text search
3. **Use correct edge collections** for traversals
4. **Apply proper field filters** based on schema

### Performance Optimization

1. **Schema Caching**: Avoids repeated schema inspection
2. **24-hour cache**: Balances freshness with performance
3. **Lightweight queries**: Only retrieves needed schema parts
4. **Index awareness**: Uses indexed fields when available

## Example Workflow

```python
import asyncio
from agent_log_manager import get_log_manager

async def debug_with_nl_queries():
    """Complete debugging workflow using natural language."""
    
    # 1. Ensure schema is cached (run once daily)
    # mcp query cache_db_schema
    
    # 2. Convert natural language to AQL
    # mcp query query_converter --natural_query "Find similar ImportError bugs"
    
    # 3. Execute the generated query
    manager = await get_log_manager()
    
    # The generated AQL from query_converter
    aql = """
    FOR doc IN agent_activity_search
    SEARCH ANALYZER(
        doc.message IN TOKENS(@query, 'text_en') OR
        doc.error_type == @error_type,
        'text_en'
    )
    LET score = BM25(doc)
    FILTER score > 0.5
    FILTER doc.resolved == true
    SORT score DESC
    LIMIT 10
    RETURN {
        error: doc.message,
        fixed_by: doc.fix_description,
        score: score
    }
    """
    
    results = await manager.db.aql.execute(
        aql,
        bind_vars={
            "query": "ImportError",
            "error_type": "ImportError"
        }
    )
    
    # 4. Process results
    for result in results:
        print(f"Similar error: {result['error']}")
        print(f"Fixed by: {result['fixed_by']}")
        print(f"Relevance: {result['score']:.2f}\n")
```

## Best Practices

1. **Cache Schema Daily**: Run `cache_db_schema` as part of daily maintenance
2. **Use Specific Queries**: More specific natural language = better AQL
3. **Include Context**: Provide error_type, file_path when available
4. **Verify Generated AQL**: Review the generated query before execution
5. **Monitor Cache Age**: Schema older than 24h may be stale

## Benefits

1. **No AQL Knowledge Required**: Natural language interface
2. **Schema Awareness**: Queries use actual database structure
3. **Performance**: Cached schema avoids repeated inspections
4. **Accuracy**: Schema validation prevents invalid queries
5. **Learning**: Generated AQL teaches query patterns

## Summary

The natural language to AQL workflow enables intuitive database queries by:
- Caching database schema in logger agent (category: `db_schema`)
- Converting natural language to AQL with schema awareness
- Providing executable code with proper bind variables
- Teaching AQL patterns through generated examples

This creates a self-documenting system where debugging queries become progressively easier as the agent learns common patterns.