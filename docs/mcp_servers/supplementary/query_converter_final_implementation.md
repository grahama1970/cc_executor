# Query Converter - Final Implementation

## Overview

The `query_converter.py` tool has been simplified from 1000+ lines to ~450 lines by removing complex regex parsing and instead:

1. **Always retrieving/creating the database schema**
2. **Providing clear English → AQL examples**
3. **Returning a prompt that guides the agent to write queries**

## Key Changes

### Before (Complex)
- QueryIntent enum with 8+ types
- Complex regex patterns for intent detection
- Entity extraction with multiple regex patterns
- Constraint parsing logic
- 1000+ lines of code

### After (Simple)
- Direct schema retrieval (creates if missing)
- 8 clear English → AQL examples
- Agent adapts examples to needs
- ~450 lines of code

## How It Works

### 1. Schema Management
```python
async def get_or_create_schema():
    # Check for cached schema in logger agent
    # If not found or stale, create using inspect_arangodb_schema
    # Cache it for 24 hours
    # Return the schema
```

### 2. Prompt Generation
```python
async def generate_agent_prompt(natural_query, ...):
    # Show the user's request
    # Add any context (error_type, file_path, etc.)
    # Get/create and display schema
    # Provide 8 English → AQL examples
    # Show execution template
    # Return complete prompt
```

### 3. English → AQL Examples

The tool provides these patterns:
1. **"Find similar errors/bugs"** → BM25 text search
2. **"How was this fixed?"** → Filter by resolved status
3. **"Recent errors/bugs"** → Time-based filters
4. **"What's related/connected?"** → Graph traversal
5. **"Count/group by"** → Aggregation queries
6. **"Unresolved/pending"** → Status filters
7. **"In specific file/path"** → Path filters
8. **"Fixed quickly/slowly"** → Resolution time filters

## Example Usage

### Input
```python
prompt = await generate_agent_prompt(
    natural_query="Find similar ImportError bugs",
    error_type="ImportError"
)
```

### Output Structure
```
# Natural Language to AQL Query Assistant

## Your Request
"Find similar ImportError bugs"

## Current Context
- Error Type: `ImportError`

### Current Database Schema
**Collections:**
- `log_events` (document): 15,000 documents
  - Fields: `timestamp`, `level`, `message`, `error_type`, `resolved` (+10 more)
- `error_causality` (edge): 500 documents
  - Fields: `_from`, `_to`, `relationship_type`, `confidence`

**Search Views (for BM25 text search):**
- `agent_activity_search`: indexes `log_events`, `errors_and_failures`

**Statistics:**
- Total documents: 15,500
- Document collections: 5
- Edge collections: 2

## English Language → AQL Examples
[8 examples with AQL queries and bind variables]

## How to Write Your Query
[Step-by-step instructions]

## Tips
[Best practices for AQL]
```

## Benefits

1. **Simplicity**: No complex parsing logic to maintain
2. **Flexibility**: LLM understands intent better than regex
3. **Maintainability**: Just update examples when needed
4. **Schema Awareness**: Always shows current database structure
5. **Self-Documenting**: Examples teach query patterns

## Philosophy Alignment

Like the AssessComplexity tool, this returns a **prompt** that:
- Provides context and understanding
- Shows patterns, not prescriptions
- Empowers the agent to adapt
- Includes everything needed to succeed

## Usage in MCP

The tool is registered in `mcp_logger_tools.py` and can be called with:
```python
result = await query_converter(
    natural_query="Find bugs like mine",
    error_type="ImportError",
    include_schema_info=True
)
# Returns a prompt with schema and examples
```

## Key Improvements

1. **Automatic Schema Creation**: If schema doesn't exist, it creates one
2. **Project Root Detection**: Uses `find_dotenv()` instead of hardcoded paths
3. **Async Throughout**: Properly handles async operations
4. **Clear Examples**: Each example shows English query → AQL → bind vars
5. **Execution Template**: Shows exactly how to run the query

## Testing

```bash
# Test with working examples
python query_converter.py

# Test with debug mode
python query_converter.py debug

# Test with MCP arguments
python query_converter.py '{"natural_query": "Find similar bugs"}'
```

The simplified implementation is more robust, easier to understand, and provides better results by leveraging the LLM's natural language understanding rather than trying to parse everything with regex.