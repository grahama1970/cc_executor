#!/usr/bin/env python3
"""
Simple Natural Language to AQL Query Converter.

This tool:
1. Gets the latest schema (creates one if it doesn't exist using inspect_arangodb_schema.py)
2. Provides clear English language to AQL examples
3. Returns a prompt that allows the agent to write the AQL query

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python simple_query_converter.py          # Runs working_usage() - stable, known to work
  python simple_query_converter.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
===
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
)


async def get_or_create_schema() -> Dict[str, Any]:
    """
    Get the latest schema from cache or create it using inspect_arangodb_schema.
    
    Returns:
        Dictionary containing the schema or error information
    """
    try:
        # First try to get from logger agent cache
                from agent_log_manager import get_log_manager
        
        manager = await get_log_manager()
        
        # Look for cached schema
        aql = """
        FOR doc IN log_events
        FILTER doc.extra_data.category == "db_schema"
        FILTER doc.timestamp > DATE_ADD(DATE_NOW(), -24, 'hour')
        SORT doc.timestamp DESC
        LIMIT 1
        RETURN doc.extra_data
        """
        
        cursor = await manager.db.aql.execute(aql)
        results = list(cursor)
        
        if results:
            logger.info("Found cached schema")
            return results[0]
        else:
            logger.info("No cached schema found - creating new one")
            
            # Use inspect_arangodb_schema to create it
            from inspect_arangodb_schema import inspect_logger_agent_schema
            schema_report = await inspect_logger_agent_schema()
            
            # Cache it using cache_db_schema
            from cache_db_schema import cache_schema_in_logger
            cache_result = await cache_schema_in_logger(
                force_refresh=True,
                cache_duration_hours=24
            )
            
            if cache_result.get('success'):
                logger.success("Schema created and cached successfully")
                return schema_report
            else:
                logger.error(f"Failed to cache schema: {cache_result.get('error')}")
                return schema_report  # Return uncached version
                
    except Exception as e:
        logger.error(f"Error getting/creating schema: {e}")
        return {"error": str(e)}


def format_schema_summary(schema: Dict[str, Any]) -> str:
    """Format schema into a readable summary."""
    if schema.get('error'):
        return f"⚠️ Schema Error: {schema['error']}"
    
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


def generate_agent_prompt(
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
        schema = asyncio.run(get_or_create_schema())
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
        
        prompt = generate_agent_prompt(
            natural_query=query,
            **context
        )
        
        # Verify the prompt has key sections
        assert "Natural Language to AQL Query Assistant" in prompt
        assert "Current Database Schema" in prompt or "Schema Error" in prompt
        assert "English Language → AQL Examples" in prompt
        assert "How to Write Your Query" in prompt
        
        logger.success("✓ Generated prompt with schema and examples")
        
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
    schema = await get_or_create_schema()
    
    if schema.get('error'):
        logger.error(f"Schema error: {schema['error']}")
    else:
        logger.success(f"Schema retrieved with {len(schema.get('collections', {}))} collections")
        
        # Print schema summary
        summary = format_schema_summary(schema)
        print("\n" + summary)
    
    # Test a specific query
    test_query = "Find all errors that were fixed within 5 minutes"
    logger.info(f"\nTesting query: {test_query}")
    
    prompt = generate_agent_prompt(
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
        prompt = generate_agent_prompt(
            natural_query=args.get("natural_query", ""),
            error_type=args.get("error_type"),
            error_message=args.get("error_message"),
            file_path=args.get("file_path"),
            error_id=args.get("error_id"),
            include_schema_info=args.get("include_schema_info", True)
        )
        
        # Return as JSON for MCP
        print(json.dumps({"prompt": prompt}))
    else:
        # Direct execution
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        if mode == "debug":
            asyncio.run(debug_function())
        else:
            asyncio.run(working_usage())