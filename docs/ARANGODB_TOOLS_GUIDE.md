# ArangoDB Tools Guide for Agents

## Overview
We have created a suite of tools to make ArangoDB interaction extremely simple for agents. These tools work together to provide CRUD operations, schema inspection, and natural language query support.

## Tools Available

### 1. **arango_crud_simple.py** - The Main Tool
The simplest interface for database operations.

```python
from cc_executor.tools.arango_crud_simple import log, error, aql, ask, collections

# Write to database
log("Something happened")
error("Failed to process", error_type="ImportError")

# Query with raw AQL
results = aql("FOR doc IN log_events LIMIT 10 RETURN doc")

# Get help with natural language
help_info = ask("show me recent errors")
# Returns: {'suggested_aql': '...', 'usage': '...'}

# List collections
cols = collections()  # ['log_events', 'agent_sessions', ...]
```

### 2. **inspect_arangodb_schema.py** - Schema Explorer
Provides detailed schema information about the database.

```python
# Run directly to get full schema report
python inspect_arangodb_schema.py

# Or import and use
from inspect_arangodb_schema import inspect_logger_agent_schema
schema = await inspect_logger_agent_schema()
```

### 3. **query_converter.py** - Natural Language to AQL
Converts natural language questions into AQL query examples.

```python
# Run directly for examples
python query_converter.py

# Or import and use  
from query_converter import generate_agent_prompt
prompt = await generate_agent_prompt("find similar errors")
```

## Quick Reference

### Writing Data
```python
# Simple logging
log("Processing started")
log("Task completed", task_id="123", duration=5.2)

# Error logging
error("Connection failed", error_type="NetworkError", host="api.example.com")

# With custom fields
log("User action", user_id="456", action="login", ip="192.168.1.1")
```

### Reading Data
```python
# Recent logs
results = aql("FOR doc IN log_events SORT doc.timestamp DESC LIMIT 10 RETURN doc")

# Filter by level
errors = aql("""
    FOR doc IN log_events 
    FILTER doc.level == "ERROR"
    SORT doc.timestamp DESC
    LIMIT 20
    RETURN doc
""")

# Count by type
counts = aql("""
    FOR doc IN log_events
    COLLECT level = doc.level WITH COUNT INTO count
    RETURN {level: level, count: count}
""")

# Search text
results = aql("""
    FOR doc IN log_events
    FILTER CONTAINS(LOWER(doc.message), LOWER(@search))
    RETURN doc
""", {"search": "timeout"})

# Time-based queries (last hour)
recent = aql("""
    FOR doc IN log_events
    FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 3600000)
    RETURN doc
""")
```

### Error Recovery
When a query fails, you get helpful information:

```python
result = aql("FOR doc IN nonexistent RETURN doc")
if isinstance(result, dict) and result.get("error"):
    print(result["message"])      # Error message
    print(result["suggestions"])  # Helpful suggestions
    print(result["examples"])     # Example queries
```

### Natural Language Help
```python
# Get AQL suggestions
help_info = ask("show me errors from the last hour")
print(help_info["suggested_aql"])  # The AQL query
print(help_info["usage"])          # How to use it
```

## Common Patterns

### 1. Log and Search Pattern
```python
# Log an event
log_id = log("Starting data import", source="api", records=1000)

# Later, search for it
results = aql("""
    FOR doc IN log_events
    FILTER doc.source == "api"
    FILTER doc.message LIKE "Starting%"
    RETURN doc
""")
```

### 2. Error Tracking Pattern
```python
# Log error
error("Import failed", error_type="ValidationError", line=42, file="data.csv")

# Find all validation errors
validation_errors = aql("""
    FOR doc IN log_events
    FILTER doc.error_type == "ValidationError"
    RETURN {
        message: doc.message,
        file: doc.file,
        line: doc.line,
        time: doc.timestamp
    }
""")
```

### 3. Performance Monitoring Pattern
```python
# Log with timing
log("Task started", task="process_data", start_time=datetime.now().isoformat())
# ... do work ...
log("Task completed", task="process_data", duration_ms=1234)

# Analyze performance
stats = aql("""
    FOR doc IN log_events
    FILTER doc.task == "process_data"
    FILTER doc.duration_ms != null
    COLLECT WITH
        avg_duration = AVG(doc.duration_ms),
        max_duration = MAX(doc.duration_ms),
        count = COUNT(1)
    RETURN {
        average_ms: avg_duration,
        max_ms: max_duration,
        total_runs: count
    }
""")
```

## Best Practices

1. **Always check query results type**:
   - `list` = success
   - `dict` with `error` key = failure

2. **Use bind variables for dynamic values**:
   ```python
   # Good
   aql("FOR doc IN @@col RETURN doc", {"@col": "log_events"})
   
   # Bad (SQL injection risk)
   aql(f"FOR doc IN {collection} RETURN doc")
   ```

3. **Start simple, then expand**:
   ```python
   # Start with
   aql("FOR doc IN log_events LIMIT 5 RETURN doc")
   
   # Then add filters
   aql("FOR doc IN log_events FILTER doc.level == 'ERROR' LIMIT 5 RETURN doc")
   ```

4. **Use ask() when unsure**:
   ```python
   help_info = ask("how do I count errors by type?")
   # Then use the suggested AQL
   ```

## Troubleshooting

### Collection not found
```python
# List available collections
print(collections())

# Common collections:
# - log_events (main log storage)
# - agent_sessions
# - errors_and_failures
# - script_runs
```

### Bind parameter errors
```python
# Collection names need @@
{"@collection": "log_events"}  # Correct
{"collection": "log_events"}   # Wrong

# Regular values need @
{"level": "ERROR"}    # Correct  
{"@level": "ERROR"}   # Wrong
```

### No results
```python
# Check if collection has data
count = aql("FOR doc IN log_events COLLECT WITH COUNT INTO c RETURN c")
print(f"Total documents: {count[0] if count else 0}")

# Get sample to see structure
samples = aql("FOR doc IN log_events SORT RAND() LIMIT 3 RETURN doc")
```

## Summary
- Use `arango_crud_simple.py` for all database operations
- It's as simple as: `log()`, `error()`, `aql()`, `ask()`
- Check result type to detect errors
- Use `ask()` to get help with queries
- All tools return helpful prompts when things go wrong