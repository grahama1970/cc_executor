# Debugging with Logger Agent - Complete Scenarios

## Overview

This document provides clear scenarios demonstrating how to use the logger agent tool to solve debugging problems. It shows how natural language queries are converted to AQL and executed against the knowledge graph.

## Scenario 1: Finding Similar Bugs That Were Fixed

### Context
You're debugging a `ModuleNotFoundError` in `data_processor.py`:
```python
ModuleNotFoundError: No module named 'pandas'
```

### Natural Language Query
"Find all similar functions to the one I'm debugging that were actually resolved"

### Using Query Converter Tool

```python
# As an agent, I would use the query converter tool:
prompt = generate_agent_prompt(
    natural_query="Find all similar functions to the one I'm debugging that were actually resolved",
    error_type="ModuleNotFoundError",
    error_message="No module named 'pandas'",
    file_path="data_processor.py",
    error_id="log_events/12345"
)
```

### Generated AQL Query
```aql
FOR doc IN agent_activity_search
SEARCH ANALYZER(
    doc.message IN TOKENS(@query, 'text_en') OR
    doc.error_type IN @error_types,
    'text_en'
)
LET score = BM25(doc)
FILTER score > 0.5
FILTER doc.resolved == true
SORT score DESC
LIMIT 10
RETURN {
    document: doc,
    score: score,
    type: SPLIT(doc._id, '/')[0]
}
```

### Execution Code
```python
# Get logger manager
manager = await get_log_manager()

# Execute the query
bind_vars = {
    "query": "ModuleNotFoundError pandas",
    "error_types": ["ModuleNotFoundError"]
}

results = await manager.db.aql.execute(aql_query, bind_vars=bind_vars)
results_list = list(results)

# Process results
for result in results_list:
    doc = result['document']
    score = result['score']
    
    if score > 0.8:
        logger.info(f"HIGH relevance ({score:.2f}): {doc['message'][:80]}...")
        
        # Find how it was fixed
        fix_aql = """
        FOR fix IN 1..1 OUTBOUND @error_id error_causality
        FILTER fix.relationship_type == 'FIXED_BY'
        RETURN fix
        """
        
        fixes = await manager.db.aql.execute(
            fix_aql, 
            bind_vars={"error_id": doc['_id']}
        )
        
        for fix in fixes:
            logger.info(f"  Fixed by: {fix.get('fix_description', 'Unknown')}")
```

### Expected Results
```
HIGH relevance (0.92): ModuleNotFoundError: No module named 'pandas' in analyzer.py...
  Fixed by: Installed pandas with 'uv add pandas==2.0.1'
  
HIGH relevance (0.87): ModuleNotFoundError: No module named 'pandas' in etl_pipeline.py...
  Fixed by: Added pandas to pyproject.toml dependencies
```

## Scenario 2: Multi-Hop Graph Traversal

### Context
You want to understand what other functions are related to your current error.

### Natural Language Query
"What functions are related to data_processor.py by 2 hops?"

### Generated AQL Query
```aql
FOR v, e, p IN 1..2 ANY @start_id 
    error_causality, agent_flow
OPTIONS {uniqueVertices: 'path', bfs: true}
RETURN {
    vertex: v,
    path_length: LENGTH(p.edges),
    relationships: p.edges[*].relationship_type
}
```

### Execution Code
```python
# Starting from current error
bind_vars = {"start_id": "log_events/12345"}

results = await manager.db.aql.execute(aql_query, bind_vars=bind_vars)
results_list = list(results)

# Group by relationship path
paths_by_type = {}
for result in results_list:
    path_key = " -> ".join(result['relationships'])
    if path_key not in paths_by_type:
        paths_by_type[path_key] = []
    paths_by_type[path_key].append(result['vertex'])

# Display grouped results
for path_type, vertices in paths_by_type.items():
    logger.info(f"\nPath type: {path_type}")
    for vertex in vertices[:3]:  # Show first 3
        logger.info(f"  - {vertex.get('message', '')[:60]}...")
```

### Expected Results
```
Path type: ASSESSED_BY -> FIXED_BY
  - Assessment: High complexity due to missing dependencies...
  - Fix: Installed all required packages via requirements.txt...

Path type: CAUSED_BY -> LED_TO
  - ImportError: cannot import name 'DataFrame' from 'pandas'...
  - AttributeError: 'NoneType' object has no attribute 'read_csv'...
```

## Scenario 3: Time-Based Fix History

### Natural Language Query
"Show me all TypeError fixes from the last week"

### Generated AQL Query
```aql
FOR doc IN log_events
FILTER doc.level == 'ERROR'
FILTER doc.error_type IN ["TypeError"]
FILTER DATE_DIFF(doc.timestamp, NOW(), 'd') <= 7
FILTER doc.resolved == true

// Get fix details
LET fixes = (
    FOR fix IN 1..1 OUTBOUND doc._id error_causality
    FILTER fix.relationship_type == 'FIXED_BY'
    RETURN fix
)

SORT doc.resolved_at DESC
LIMIT 10
RETURN {
    error: doc,
    fixes: fixes,
    resolution_time: doc.resolution_time_seconds
}
```

### Processing Pattern
```python
# Execute query
results = await manager.db.aql.execute(aql_query, bind_vars={})
results_list = list(results)

# Group by fix pattern
fix_patterns = {}
for result in results_list:
    error = result['error']
    for fix in result.get('fixes', []):
        pattern = fix.get('fix_description', 'Unknown')
        if pattern not in fix_patterns:
            fix_patterns[pattern] = {
                'count': 0,
                'avg_resolution_time': 0,
                'examples': []
            }
        fix_patterns[pattern]['count'] += 1
        fix_patterns[pattern]['examples'].append({
            'error': error['message'][:50],
            'time': result.get('resolution_time', 0)
        })

# Show most common fixes
for pattern, data in sorted(fix_patterns.items(), 
                          key=lambda x: x[1]['count'], 
                          reverse=True)[:5]:
    logger.info(f"\nFix pattern: {pattern}")
    logger.info(f"  Used {data['count']} times")
    logger.info(f"  Examples:")
    for ex in data['examples'][:2]:
        logger.info(f"    - {ex['error']}... (fixed in {ex['time']}s)")
```

## Scenario 4: Building Knowledge After Fixing

### After Successfully Fixing an Error

```python
# Log the successful fix
error_id = "log_events/12345"
fix_description = "Installed pandas with 'uv add pandas==2.0.1'"

# Create fix document
fix_doc = await manager.log_event(
    level="SUCCESS",
    message=f"Fixed ModuleNotFoundError: {fix_description}",
    script_name="data_processor.py",
    execution_id="debug_session_123",
    extra_data={
        "fix_description": fix_description,
        "original_error_id": error_id,
        "fix_command": "uv add pandas==2.0.1",
        "fix_verified": True
    },
    tags=["fix", "success", "modulenotfounderror", "resolved"]
)

# Create FIXED_BY relationship
edge_collection = manager.db.collection("error_causality")
edge_doc = {
    "_from": error_id,
    "_to": fix_doc["_id"],
    "relationship_type": "FIXED_BY",
    "confidence": 0.95,
    "rationale": "Standard fix for missing pandas module",
    "created_at": datetime.utcnow().isoformat()
}
edge_collection.insert(edge_doc)

# Update original error as resolved
log_collection = manager.db.collection("log_events")
log_collection.update({
    "_key": error_id.split("/")[1],
    "resolved": True,
    "resolved_at": datetime.utcnow().isoformat(),
    "resolution_time_seconds": 120,
    "fix_description": fix_description
})

logger.success("✅ Fix logged to knowledge graph for future reference")
```

## Scenario 5: Complex Investigation Flow

### Complete Workflow Example

```python
async def investigate_error(error: Exception, file_path: str):
    """Complete error investigation workflow."""
    
    manager = await get_log_manager()
    
    # Step 1: Log the error
    error_doc = await manager.log_event(
        level="ERROR",
        message=str(error),
        script_name=Path(file_path).name,
        execution_id=f"investigate_{datetime.now().timestamp()}",
        extra_data={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "file_path": file_path,
            "stack_trace": traceback.format_exc()
        },
        tags=["error", "investigation", type(error).__name__.lower()]
    )
    error_id = error_doc["_id"]
    
    # Step 2: Search for similar errors
    logger.info("Searching for similar errors...")
    
    similar_results = await manager.search.search_agent_activity(
        query=f"{type(error).__name__} {str(error)}",
        filters={
            "event_types": ["error", "fix"],
            "tags": ["resolved"]
        },
        limit=5
    )
    
    if similar_results:
        logger.info(f"Found {len(similar_results)} similar resolved errors")
        
        # Step 3: Find their fixes
        for result in similar_results[:3]:
            similar_error_id = result['doc']['_id']
            
            # Get fix details
            fix_aql = """
            FOR fix IN 1..1 OUTBOUND @error_id error_causality
            FILTER fix.relationship_type == 'FIXED_BY'
            RETURN fix
            """
            
            fixes = await manager.db.aql.execute(
                fix_aql,
                bind_vars={"error_id": similar_error_id}
            )
            
            for fix in fixes:
                logger.info(f"Previous fix: {fix.get('fix_description')}")
                logger.info(f"  Confidence: {fix.get('confidence', 0)}")
    
    # Step 4: Explore related errors (2-hop)
    logger.info("\nExploring related errors...")
    
    related_aql = """
    FOR v, e, p IN 2..2 ANY @start_id 
        error_causality, agent_flow
    FILTER v.error_type != null
    RETURN DISTINCT {
        error: v,
        path: p.edges[*].relationship_type,
        distance: LENGTH(p.edges)
    }
    LIMIT 10
    """
    
    related = await manager.db.aql.execute(
        related_aql,
        bind_vars={"start_id": error_id}
    )
    
    related_errors = list(related)
    if related_errors:
        logger.info(f"Found {len(related_errors)} related errors through graph")
        
    return {
        "error_id": error_id,
        "similar_count": len(similar_results),
        "related_count": len(related_errors),
        "suggested_fixes": [
            fix.get('fix_description') 
            for fix in fixes 
            if fix.get('confidence', 0) > 0.8
        ]
    }
```

## Best Practices

### 1. Always Log Context
```python
# When starting debugging
await manager.log_event(
    level="INFO",
    message="Starting debug session for ModuleNotFoundError",
    extra_data={
        "session_goal": "Fix pandas import",
        "initial_error": str(error),
        "approach": "Search similar fixes first"
    }
)
```

### 2. Use Confidence Scores
```python
# When creating relationships
edge_doc = {
    "_from": error_id,
    "_to": fix_id,
    "relationship_type": "FIXED_BY",
    "confidence": 0.95,  # High confidence = verified fix
    "rationale": "Fix verified through successful test run"
}
```

### 3. Build Causal Chains
```python
# Link related errors
if error_caused_by_previous:
    edge_doc = {
        "_from": previous_error_id,
        "_to": current_error_id,
        "relationship_type": "LED_TO",
        "confidence": 0.8,
        "rationale": "Missing import led to undefined variable"
    }
```

### 4. Query Optimization
```python
# Use indexes effectively
# Add time constraints for recent data
FILTER DATE_DIFF(doc.timestamp, NOW(), 'd') <= 30

# Limit traversal depth for performance
FOR v, e, p IN 1..2  # Not 1..5

# Use DISTINCT to avoid duplicates
RETURN DISTINCT v
```

## Summary

The logger agent provides powerful capabilities for debugging:

1. **Similarity Search**: Find errors like yours that were already fixed
2. **Graph Traversal**: Discover relationships between errors and fixes
3. **Pattern Recognition**: Identify common fix patterns
4. **Knowledge Building**: Every fix makes future debugging easier
5. **Time-based Analysis**: Track error trends and resolution times

By using natural language queries converted to AQL, you can effectively query the debugging knowledge graph without needing to master AQL syntax.