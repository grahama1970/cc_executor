# Arango Tools Quick Reference Guide

## Available Tools

### 1. schema()
**Purpose**: Get database structure overview
**Parameters**: None
**Usage**: `mcp__arango-tools__schema()`
**Returns**: Collections, views, graphs, sample fields
**When to use**: Always first to understand what's available

### 2. query(aql, bind_vars)
**Purpose**: Execute AQL queries
**Parameters**: 
- `aql`: Query string (required)
- `bind_vars`: JSON string of variables (optional)
**Usage Examples**:
```python
# Simple query
mcp__arango-tools__query("FOR doc IN log_events LIMIT 5 RETURN doc")

# With filter
mcp__arango-tools__query("FOR e IN log_events FILTER e.level == 'ERROR' RETURN e")

# With bind variables
mcp__arango-tools__query(
    "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
    '{"@col": "log_events", "level": "ERROR"}'
)

# Graph traversal
mcp__arango-tools__query(
    "FOR e IN errors_and_failures FILTER e._key == '436414' FOR v IN 1..1 OUTBOUND e error_causality RETURN v"
)
```
**Remember**: 
- Empty results are SUCCESS: `{"success": true, "count": 0, "results": []}`
- Use FILTER not WHERE
- String matching: `=~` for regex, `==` for exact

### 3. insert(message, level, **kwargs)
**Purpose**: Add new log entries
**Parameters**:
- `message`: Log message (required)
- `level`: "INFO", "ERROR", "WARN", etc. (default: "INFO")
- Optional: `error_type`, `script_name`, `execution_id`, `task_id`
- `metadata`: JSON string for additional data
**Usage Examples**:
```python
# Basic log
mcp__arango-tools__insert("Task completed", "INFO")

# Error log
mcp__arango-tools__insert(
    "ModuleNotFoundError: No module named numpy",
    "ERROR",
    error_type="ModuleNotFoundError",
    script_name="test.py"
)

# With metadata (for booleans and extra fields)
mcp__arango-tools__insert(
    "Fixed error",
    "INFO",
    metadata='{"resolved": true, "fix_command": "uv add numpy"}'
)
```
**Returns**: `{"success": true, "id": "log_events/12345", "message": "Inserted successfully"}`
**Note**: Boolean parameters often fail - use metadata instead!

### 4. edge(from_id, to_id, collection, relationship_type, metadata)
**Purpose**: Create relationships between documents
**Parameters**:
- `from_id`: Source document ID (required)
- `to_id`: Target document ID (required) 
- `collection`: Edge collection name (required)
- `relationship_type`: Optional string (e.g., "fixed_by", "caused")
- `metadata`: JSON string for ALL numeric/boolean properties (REQUIRED for any numeric values!)

**⚠️ CRITICAL: Numeric parameters MUST go in metadata JSON!**

**Usage Examples**:
```python
# Link error to fix (simple, no numeric values)
mcp__arango-tools__edge(
    "log_events/436414",
    "log_events/436426",
    "error_causality",
    relationship_type="fixed_by"
)

# With timing (MUST use metadata for numeric values!)
mcp__arango-tools__edge(
    "errors/123",
    "fixes/456",
    "error_causality",
    relationship_type="fixed_by",
    metadata='{"fix_time_minutes": 5}'  # ← Numeric value in metadata!
)

# With sequence (MUST use metadata!)
mcp__arango-tools__edge(
    "sessions/1",
    "executions/2", 
    "agent_flow",
    relationship_type="executed",
    metadata='{"sequence": 1}'  # ← Numeric value in metadata!
)
```
**Common collections**: 
- `error_causality`: Links errors to fixes
- `agent_flow`: Execution flow
- `artifact_lineage`: Code evolution
**Returns**: `{"success": true, "id": "error_causality/789", "message": "Edge created from X to Y"}`

### 5. upsert(collection, search, update, create)
**Purpose**: Update existing or create new document
**Parameters** (ALL must be JSON strings!):
- `collection`: Collection name (required)
- `search`: JSON criteria to find document (required)
- `update`: JSON fields to update (required)
- `create`: JSON fields for new doc (optional)
**Usage Examples**:
```python
# Track script status
mcp__arango-tools__upsert(
    "script_runs",
    '{"script_name": "test.py"}',
    '{"last_run": "2024-01-15", "run_count": 5}'
)

# With create fields
mcp__arango-tools__upsert(
    "script_runs",
    '{"execution_id": "run_123"}',
    '{"status": "completed", "end_time": "2024-01-15T10:00:00Z"}',
    '{"start_time": "2024-01-15T09:00:00Z"}'
)
```
**Returns**: `{"success": true, "operation": "updated"/"created", "id": "collection/key"}`

## Common AQL Pitfalls

### COLLECT with AGGREGATE
**Wrong**: 
```aql
COLLECT solution = s.key_reason, score = s.success_score 
AGGREGATE avg_score = AVG(score)  -- ❌ Can't use 'score' here!
```

**Correct**:
```aql
COLLECT solution = s.key_reason 
AGGREGATE avg_score = AVG(s.success_score)  -- ✅ Use original document ref
```

### GROUP BY vs COLLECT
**Wrong**: 
```aql
GROUP BY solution_id = s.solution_id  -- ❌ AQL doesn't use GROUP BY!
```

**Correct**:
```aql
COLLECT solution_id = s.solution_id  -- ✅ AQL uses COLLECT, not GROUP BY
```

## Common Patterns

### Finding and Fixing Errors
```python
# 1. Find error
query("FOR e IN errors_and_failures FILTER e.error_type == 'ModuleNotFoundError' RETURN e")

# 2. If found, check for existing fix
query("FOR e IN errors_and_failures FILTER e._key == '12345' FOR v IN 1..1 OUTBOUND e error_causality RETURN v")

# 3. If no fix, insert one
fix_id = insert("Fixed by: uv add package", "INFO")

# 4. Link error to fix
edge(error_id, fix_id, "error_causality", relationship_type="fixed_by")
```

### Building Knowledge
```python
# 1. Search for patterns
query("FOR e IN errors_and_failures COLLECT type = e.error_type WITH COUNT INTO c RETURN {type: type, count: c}")

# 2. Create lesson
insert(
    "ModuleNotFoundError usually fixed with uv add",
    "INFO",
    metadata='{"lesson_type": "pattern", "confidence": 0.95}'
)

# 3. Update glossary
upsert(
    "glossary_terms",
    '{"term": "ModuleNotFoundError"}',
    '{"definition": "Python import error when module not installed", "usage_count": 10}'
)
```

## Key Reminders
1. **Always use schema() first** to verify collections exist
2. **Metadata parameter** must be valid JSON string
3. **Boolean values** often fail in direct params - use metadata
4. **Empty query results** are not errors
5. **All upsert params** must be JSON strings
6. **Document IDs** include collection: "log_events/12345"