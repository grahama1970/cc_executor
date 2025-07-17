#!/usr/bin/env python3
"""
Simple Natural Language to AQL Query Converter - No Caching Version.

This tool:
1. Gets the current schema directly (no caching)
2. Provides clear English language to AQL examples
3. Returns a prompt that guides the agent to write AQL queries

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python simple_query_converter_no_cache.py          # Runs working_usage()
  python simple_query_converter_no_cache.py debug    # Runs debug_function()

DO NOT create separate test files - use the debug_function() instead!
===
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from loguru import logger
from dotenv import find_dotenv

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
)

# Get project root from .env file location
env_path = find_dotenv()
if env_path:
    PROJECT_ROOT = Path(env_path).parent
else:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


async def get_schema() -> Dict[str, Any]:
    """
    Get the current schema using inspect_arangodb_schema.
    No caching - just get it fresh when needed.
    
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


def format_schema_summary(schema: Dict[str, Any]) -> str:
    """Format schema into a readable summary."""
    if schema.get('error'):
        return f"⚠️ Schema Error: {schema['error']}\n\nTo inspect manually:\n```python\nfrom inspect_arangodb_schema import inspect_logger_agent_schema\nschema = await inspect_logger_agent_schema()\n```"
    
    summary = "### Current Database Schema\n\n"
    
    # Collections
    collections = schema.get('collections', {})
    if collections:
        summary += "**Collections:**\n"
        for name, info in collections.items():
            summary += f"- `{name}` ({info['type']}): {info.get('count', 0):,} documents\n"
            # Show top 5 fields
            fields = list(info.get('schema', {}).keys())[:5]
            if fields:
                summary += f"  - Fields: {', '.join(f'`{f}`' for f in fields)}"
                if len(info.get('schema', {})) > 5:
                    summary += f" (+{len(info['schema']) - 5} more)"
                summary += "\n"
    
    # Views for search
    views = schema.get('views', {})
    if views:
        summary += "\n**Search Views (for BM25 text search):**\n"
        for name, info in views.items():
            summary += f"- `{name}`: "
            links = list(info.get('links', {}).keys())
            if links:
                summary += f"indexes {', '.join(f'`{l}`' for l in links)}\n"
    
    # Summary stats
    if 'summary' in schema:
        s = schema['summary']
        summary += f"\n**Statistics:**\n"
        summary += f"- Total documents: {s.get('total_documents', 0):,}\n"
        summary += f"- Document collections: {s.get('document_collections', 0)}\n"
        summary += f"- Edge collections: {s.get('edge_collections', 0)}\n"
    
    return summary


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
    1. Gets the current schema (no caching)
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
    
    # Get and show schema (no caching)
    if include_schema_info:
        schema = await get_schema()
        prompt += format_schema_summary(schema)
        prompt += "\n"
    
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
"""
    
    return prompt


async def working_usage():
    """
    Demonstrate proper usage of the tool.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    logger.info("=== Natural Language to AQL Converter (No Cache) ===")
    
    # Test different query types
    test_queries = [
        ("Find similar ImportError bugs", {"error_type": "ImportError"}),
        ("How was ModuleNotFoundError fixed?", {"error_type": "ModuleNotFoundError"}),
        ("Show me errors from the last 24 hours", {}),
    ]
    
    for query, context in test_queries:
        logger.info(f"\nProcessing: {query}")
        
        prompt = await generate_agent_prompt(
            natural_query=query,
            **context
        )
        
        # Verify the prompt has key sections
        assert "Natural Language to AQL Query Assistant" in prompt
        assert "Current Database Schema" in prompt or "Schema Error" in prompt
        assert "English Language → AQL Examples" in prompt
        assert "How to Write Your Query" in prompt
        
        logger.success("✓ Generated prompt with schema and examples")
    
    logger.success("✅ All tests passed!")
    return True


async def debug_function():
    """
    Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    """
    logger.info("=== Debug Mode (No Cache) ===")
    
    # Test direct schema retrieval
    logger.info("Testing direct schema retrieval...")
    schema = await get_schema()
    
    if schema.get('error'):
        logger.error(f"Schema error: {schema['error']}")
    else:
        logger.success(f"Schema retrieved with {len(schema.get('collections', {}))} collections")
        
        # Print schema summary
        summary = format_schema_summary(schema)
        print("\n" + summary)
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())