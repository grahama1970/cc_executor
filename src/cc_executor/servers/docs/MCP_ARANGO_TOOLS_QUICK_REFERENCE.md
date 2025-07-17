# MCP ArangoDB Tools Quick Reference

## Overview
The `arango-tools` MCP server provides complete ArangoDB functionality including all CRUD operations, graph management, indexing, and natural language query support.

## Available Tools

### Database Operations

#### 1. `mcp__arango-tools__schema`
Get database schema information.

```python
# Get complete schema
schema = await mcp__arango-tools__schema()

# Returns:
{
    "success": true,
    "database": "script_logs",
    "collections": {
        "log_events": {
            "type": 2,
            "count": 1234,
            "sample_fields": {"timestamp": "str", "level": "str", ...}
        },
        ...
    },
    "views": [...],
    "graphs": [...],
    "common_queries": {...}
}
```

#### 2. `mcp__arango-tools__query`
Execute AQL queries directly.

```python
# Simple query
result = await mcp__arango-tools__query({
    "aql": "FOR doc IN log_events LIMIT 5 RETURN doc"
})

# With bind variables
result = await mcp__arango-tools__query({
    "aql": "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
    "bind_vars": {"@col": "log_events", "level": "ERROR"}
})
```

### Document Operations

#### 3. `mcp__arango-tools__insert`
Insert new documents.

```python
# Log event
await mcp__arango-tools__insert({
    "message": "Task completed",
    "level": "INFO",
    "task_id": "123",
    "duration": 5.2
})
```

#### 4. `mcp__arango-tools__get`
Retrieve a single document.

```python
result = await mcp__arango-tools__get({
    "collection": "log_events",
    "key": "123"  # or "log_events/123"
})
```

#### 5. `mcp__arango-tools__update`
Update specific fields in a document.

```python
await mcp__arango-tools__update({
    "collection": "log_events",
    "key": "123",
    "fields": {
        "resolved": true,
        "fix_description": "Added missing import"
    }
})
```

#### 6. `mcp__arango-tools__upsert`
Update if exists, create if not.

```python
await mcp__arango-tools__upsert({
    "collection": "script_runs",
    "search": {"script_name": "test.py"},
    "update": {
        "last_run": "2024-01-15",
        "run_count": 5
    },
    "create": {
        "first_run": "2024-01-01"
    }
})
```

#### 7. `mcp__arango-tools__delete`
Delete a document.

```python
await mcp__arango-tools__delete({
    "collection": "log_events",
    "key": "123"
})
```

### Graph Operations

#### 8. `mcp__arango-tools__edge`
Create edges between documents.

```python
# Link error to its fix
await mcp__arango-tools__edge({
    "from": "log_events/123",
    "to": "log_events/456",
    "collection": "error_causality",
    "relationship_type": "fixed_by",
    "fix_time_minutes": 30
})
```

#### 9. `mcp__arango-tools__create_graph`
Create a named graph.

```python
await mcp__arango-tools__create_graph({
    "name": "error_resolution_graph",
    "edge_definitions": [{
        "collection": "error_causality",
        "from_collections": ["log_events", "scripts"],
        "to_collections": ["log_events", "fixes"]
    }]
})
```

### Collection Management

#### 10. `mcp__arango-tools__create_collection`
Create new collections.

```python
# Document collection
await mcp__arango-tools__create_collection({
    "name": "my_logs"
})

# Edge collection
await mcp__arango-tools__create_collection({
    "name": "relationships",
    "edge": true
})
```

#### 11. `mcp__arango-tools__create_index`
Create indexes for performance.

```python
# Create unique index
await mcp__arango-tools__create_index({
    "collection": "users",
    "fields": ["email"],
    "type": "persistent",
    "unique": true
})

# Fulltext search index
await mcp__arango-tools__create_index({
    "collection": "log_events",
    "fields": ["message"],
    "type": "fulltext"
})
```

#### 12. `mcp__arango-tools__truncate`
Empty a collection.

```python
await mcp__arango-tools__truncate({
    "collection": "temp_data"
})
```

### Query Assistance

#### 13. `mcp__arango-tools__english_to_aql`
Convert natural language to AQL patterns.

```python
# Get AQL for natural language query
help_info = await mcp__arango-tools__english_to_aql({
    "query": "find similar resolved scripts",
    "context": {
        "script_name": "my_script.py",
        "error_type": "ImportError"
    }
})

# Returns:
{
    "success": true,
    "aql": "FOR doc IN agent_activity_search...",
    "bind_vars": {"query": "your search terms"},
    "usage": "Execute with query() using the AQL and bind_vars above"
}
```

## Common Workflows

### Finding Similar Resolved Scripts
```python
# Step 1: Get AQL pattern
pattern = await mcp__arango-tools__english_to_aql({
    "query": "find similar resolved scripts with ImportError"
})

# Step 2: Execute the query
results = await mcp__arango-tools__query({
    "aql": pattern["aql"],
    "bind_vars": pattern["bind_vars"]
})
```

### Logging a Fix
```python
# Log the error and fix
await mcp__arango-tools__insert({
    "message": "Fixed module import issue",
    "level": "INFO",
    "error_type": "ModuleNotFoundError",
    "script_name": "processor.py",
    "resolved": true,
    "fix_description": "Added sys.path manipulation",
    "fix_rationale": "Script runs as __main__ and needs parent directory in path",
    "resolution_time_minutes": 15
})
```

### Error Analysis
```python
# Count errors by type
result = await mcp__arango-tools__query({
    "aql": """
        FOR doc IN log_events
        FILTER doc.level == "ERROR"
        COLLECT error_type = doc.error_type WITH COUNT INTO count
        SORT count DESC
        RETURN {type: error_type, count: count}
    """
})
```

## Quick Patterns

### Recent Logs
```python
await mcp__arango-tools__query({
    "aql": "FOR doc IN log_events SORT doc.timestamp DESC LIMIT 20 RETURN doc"
})
```

### Search Text
```python
await mcp__arango-tools__query({
    "aql": "FOR doc IN log_events FILTER CONTAINS(LOWER(doc.message), LOWER(@search)) RETURN doc",
    "bind_vars": {"search": "timeout"}
})
```

### Time-based Query
```python
# Last hour (3600000 ms)
await mcp__arango-tools__query({
    "aql": "FOR doc IN log_events FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 3600000) RETURN doc"
})
```

## Important Notes

1. **Bind Variables**:
   - Collection names need `@@`: `{"@col": "log_events"}`
   - Regular values need `@`: `{"level": "ERROR"}`

2. **BM25 Search**:
   - Only works with search views (e.g., `agent_activity_search`)
   - Cannot use FILTER with APPROX_NEAR_COSINE

3. **Error Handling**:
   - Check `result["success"]` to detect failures
   - Failed queries include `suggestions` for common issues

4. **Natural Language**:
   - Use `english_to_aql` first to get query patterns
   - Then execute with `query` using the returned AQL

## Complete Workflow Examples

### Error Resolution Workflow

```python
# 1. Log the error
error_doc = await mcp__arango-tools__insert({
    "message": "ModuleNotFoundError: No module named 'utils'",
    "level": "ERROR",
    "error_type": "ModuleNotFoundError",
    "script_name": "processor.py",
    "line": 42
})

# 2. Find similar resolved errors
pattern = await mcp__arango-tools__english_to_aql({
    "query": "find similar ModuleNotFoundError that were fixed"
})

similar = await mcp__arango-tools__query({
    "aql": pattern["aql"],
    "bind_vars": {"error_type": "ModuleNotFoundError"}
})

# 3. Fix the error and update the document
await mcp__arango-tools__update({
    "collection": "log_events",
    "key": error_doc["id"].split("/")[1],
    "fields": {
        "resolved": true,
        "fix_description": "Added sys.path manipulation",
        "resolution_time_minutes": 15
    }
})

# 4. Create edge to link error to solution
fix_doc = await mcp__arango-tools__insert({
    "message": "Fixed import by adding parent to sys.path",
    "level": "INFO",
    "script_name": "processor.py"
})

await mcp__arango-tools__edge({
    "from": error_doc["id"],
    "to": fix_doc["id"],
    "collection": "error_causality",
    "relationship_type": "resolved_by"
})
```

### Script Performance Tracking

```python
# Track script execution with upsert
await mcp__arango-tools__upsert({
    "collection": "script_performance",
    "search": {"script_name": "data_processor.py"},
    "update": {
        "last_run": datetime.now().isoformat(),
        "total_runs": {"$inc": 1},
        "avg_duration": 45.3
    },
    "create": {
        "first_run": datetime.now().isoformat(),
        "total_runs": 1
    }
})

# Query performance history
results = await mcp__arango-tools__query({
    "aql": """
        FOR doc IN script_performance
        FILTER doc.avg_duration > 60
        SORT doc.avg_duration DESC
        RETURN {
            script: doc.script_name,
            avg_time: doc.avg_duration,
            runs: doc.total_runs
        }
    """
})
```

### Graph Analysis

```python
# Find all errors caused by a specific change
await mcp__arango-tools__query({
    "aql": """
        FOR v, e, p IN 1..3 OUTBOUND @start_id error_causality
        FILTER e.relationship_type IN ["caused_by", "related_to"]
        RETURN DISTINCT {
            error: v.message,
            type: v.error_type,
            distance: LENGTH(p.edges)
        }
    """,
    "bind_vars": {"start_id": "changes/123"}
})
```

## Tool Summary

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `schema` | Get DB structure | None |
| `query` | Execute AQL | `aql`, `bind_vars` |
| `insert` | Create document | `message`, `level`, `...` |
| `get` | Read document | `collection`, `key` |
| `update` | Modify document | `collection`, `key`, `fields` |
| `upsert` | Update or create | `collection`, `search`, `update` |
| `delete` | Remove document | `collection`, `key` |
| `edge` | Create relationship | `from`, `to`, `collection` |
| `create_collection` | New collection | `name`, `edge` |
| `create_index` | Add index | `collection`, `fields`, `type` |
| `create_graph` | Define graph | `name`, `edge_definitions` |
| `truncate` | Empty collection | `collection` |
| `english_to_aql` | NL to AQL | `query`, `context` |

## Best Practices

1. **Always check success**: Every operation returns `{"success": true/false}`
2. **Use bind variables**: Prevents injection and improves performance
3. **Create indexes**: For frequently queried fields
4. **Use upsert**: For idempotent operations
5. **Link with edges**: To track relationships and causality