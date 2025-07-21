# Schema Query Implementation

## Overview

The natural language query converter now supports schema-related queries like:
- "Get me the latest db schema from arangodb for db X. If it doesn't exist, create it"
- "Show me the database schema"
- "Refresh the database schema"
- "What collections are in the database?"

## How It Works

### 1. Query Detection

The `generate_agent_prompt()` function detects schema-related queries by looking for keywords:
```python
schema_keywords = ["schema", "database structure", "collections", "db structure", "database schema"]
is_schema_query = any(keyword in natural_query.lower() for keyword in schema_keywords)
```

### 2. Schema Query Handler

When a schema query is detected, it's routed to `_handle_schema_query()` which:
- Parses the database name from the query
- Determines if the user wants to create/refresh or just retrieve
- Generates a comprehensive prompt with executable code

### 3. Generated Prompt Structure

The prompt returned includes:

1. **Query Understanding**
   - Parsed database name
   - Detected action (retrieve vs create/refresh)

2. **Step-by-Step Instructions**
   - Check for existing cached schema
   - Retrieve or create schema based on findings
   - Usage examples for the schema

3. **Complete Executable Code**
   - AQL query to check for cached schema
   - Python code to handle both cases (exists/doesn't exist)
   - Error handling and logging

4. **Key Features**
   - Schema cached with category "db_schema"
   - 24-hour cache duration (configurable)
   - Automatic refresh when stale
   - Force refresh option available

## Example Usage

### Natural Language Query
```
"Get me the latest db schema from arangodb for db logger_agent. If it doesn't exist, create it"
```

### Generated Response
The tool returns a prompt that guides the agent to:

1. Check if schema exists in cache:
```python
async def check_cached_schema(db_name="logger_agent"):
    manager = await get_log_manager()
    
    aql = """
    FOR doc IN log_events
    FILTER doc.extra_data.category == "db_schema"
    FILTER doc.extra_data.database == @db_name
    FILTER doc.timestamp > DATE_ISO8601(DATE_ADD(NOW(), -24, 'hour'))
    SORT doc.timestamp DESC
    LIMIT 1
    RETURN {
        schema: doc.extra_data,
        age_hours: DATE_DIFF(doc.timestamp, NOW(), 'hour', false)
    }
    """
    
    cursor = await manager.db.aql.execute(aql, bind_vars={"db_name": db_name})
    results = list(cursor)
    
    if results:
        return results[0]['schema']
    else:
        return None
```

2. Create schema if missing or stale:
```python
from cache_db_schema import cache_schema_in_logger

result = await cache_schema_in_logger(
    force_refresh=True,
    cache_duration_hours=24
)

if result.get('success'):
    print(f"Schema cached successfully!")
    return result['schema']
```

## Philosophy Alignment

This implementation follows the same philosophy as the AssessComplexity tool:

1. **Returns a Prompt, Not Just Data**
   - The tool returns a comprehensive prompt that guides the agent
   - Includes context, reasoning, and executable code
   - Empowers the agent to understand and execute

2. **Agent-Centric Design**
   - The agent receives everything needed to complete the task
   - No hidden logic or assumptions
   - Clear step-by-step guidance

3. **Flexibility**
   - Agent can check cache first
   - Agent decides whether to refresh
   - Agent controls execution flow

## Integration with Logger Agent

The schema is stored in the logger agent database with:
- **Category**: "db_schema"
- **Tags**: ["db_schema", "cache", "infrastructure", "agent_resource"]
- **Expiration**: Configurable (default 24 hours)
- **Content**: Full database schema including collections, views, graphs, and sample queries

## Benefits

1. **Natural Language Interface**: No need to remember specific commands
2. **Intelligent Caching**: Avoids repeated schema inspections
3. **Complete Guidance**: Agent gets full context and code
4. **Error Handling**: Built-in error handling and fallbacks
5. **Extensible**: Easy to add new schema-related query patterns

## Testing

Run the test scripts to see it in action:
```bash
python tmp/test_schema_query_direct.py
python tmp/demo_schema_query.py
```

These demonstrate:
- Schema query detection
- Database name parsing
- Action determination
- Complete prompt generation