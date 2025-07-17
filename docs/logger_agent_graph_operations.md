# Logger Agent Graph Operations Guide

## Overview
The Logger Agent uses ArangoDB's graph capabilities to create relationships between errors, fixes, and insights. This guide shows you how to create edge documents and perform graph traversal.

## Creating Edge Documents

### Basic Edge Structure
```python
edge_doc = {
    "_from": "log_events/123",  # Source document ID
    "_to": "log_events/456",     # Target document ID
    "relationship_type": "CAUSED_BY",
    "confidence": 0.85,
    "rationale": "Import error led to undefined function error",
    "created_at": datetime.utcnow().isoformat(),
    "context": {
        "session_id": "session_789",
        "execution_id": "exec_123"
    }
}
```

### Relationship Types
- **CAUSED_BY**: Error A caused Error B
- **FIXED_BY**: Error A was fixed by Solution B
- **RETRY_OF**: Action B is a retry of Action A
- **FOLLOWED_BY**: Temporal sequence
- **DEPENDS_ON**: Code A depends on Code B
- **SIMILAR_TO**: Error A is similar to Error B

### Creating Edges Programmatically

#### Method 1: Direct Edge Creation
```python
# Get logger manager
manager = await get_log_manager()

# Create edge collection reference
edge_collection = manager.db.collection("error_causality")

# Create edge document
edge_doc = {
    "_from": "errors_and_failures/error_123",
    "_to": "log_events/fix_456",
    "relationship_type": "FIXED_BY",
    "confidence": 0.95,
    "rationale": "Applied uv add to install missing package",
    "fix_description": "Installed pandas with 'uv add pandas'",
    "created_at": datetime.utcnow().isoformat(),
    "created_by": "assess_complexity_tool"
}

# Insert edge
result = edge_collection.insert(edge_doc)
logger.info(f"Created edge: {result['_id']}")
```

#### Method 2: Using Relationship Extractor
```python
# Use the relationship extractor
extractor = manager.relationships  # or RelationshipExtractor(manager.db)

# Extract relationships between two texts
relationships = await extractor.extract_relationships(
    text1="ModuleNotFoundError: No module named 'requests'",
    text2="Fixed by installing requests with uv add",
    context={
        "error_id": "errors_and_failures/123",
        "fix_id": "log_events/456",
        "session_id": "current_session"
    }
)

# Store the relationships
stored_edges = await extractor.store_relationships(
    doc1_id="errors_and_failures/123",
    doc2_id="log_events/456",
    relationships=relationships,
    context={"execution_id": "exec_123"}
)
```

#### Method 3: Creating Custom Edges
```python
async def create_fix_relationship(error_id: str, fix_id: str, rationale: str):
    """Create a FIXED_BY relationship between error and fix."""
    
    edge_doc = {
        "_from": error_id,
        "_to": fix_id,
        "relationship_type": "FIXED_BY",
        "confidence": 0.9,
        "rationale": rationale,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {
            "tool": "assess_complexity",
            "verified": True
        }
    }
    
    # Get the appropriate edge collection
    edge_collection = manager.db.collection("error_causality")
    result = edge_collection.insert(edge_doc)
    
    return result["_id"]
```

## BM25 Full-Text Search

### Basic BM25 Search
```python
# Search across all agent activity
results = await manager.search.search_agent_activity(
    query="TypeError string concatenation",
    limit=20,
    sort_by_relevance=True  # Uses BM25 scoring
)

# Results include BM25 scores
for result in results:
    doc = result['doc']
    score = result['score']  # BM25 relevance score
    logger.info(f"Score: {score:.2f} - {doc['message']}")
```

### Advanced BM25 Search with Filters
```python
# Search with specific filters
results = await manager.search.search_agent_activity(
    query="import error pandas",
    filters={
        "source_apps": ["data_processor.py"],
        "event_types": ["error", "fix"],
        "time_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        }
    },
    limit=50
)
```

### Direct AQL Query with BM25
```python
# Custom BM25 search query
aql = """
FOR doc IN agent_activity_search
SEARCH ANALYZER(
    doc.message IN TOKENS(@query, 'text_en') OR
    doc.fix_description IN TOKENS(@query, 'text_en'),
    'text_en'
)
LET score = BM25(doc)
FILTER score > @min_score
SORT score DESC
LIMIT @limit
RETURN {
    doc: doc,
    score: score,
    highlights: {
        message: SUBSTRING(doc.message, 0, 200),
        fix: doc.fix_description
    }
}
"""

results = await manager.db.aql.execute(
    aql,
    bind_vars={
        "query": "ModuleNotFoundError requests",
        "min_score": 0.5,
        "limit": 10
    }
)
```

## Multi-Hop Graph Traversal

### 1-Hop Traversal: Find Direct Relationships
```python
# Find all documents directly related to an error
doc_id = "errors_and_failures/error_123"

aql = """
FOR v, e IN 1..1 ANY @start_doc 
    error_causality, agent_flow, insight_applications
RETURN {
    vertex: v,
    edge: e,
    relationship: e.relationship_type,
    confidence: e.confidence
}
"""

results = await manager.db.aql.execute(
    aql,
    bind_vars={"start_doc": doc_id}
)
```

### Multi-Hop Traversal: Find Causal Chains
```python
# Find error chains up to 3 hops
aql = """
FOR v, e, p IN 1..3 ANY @start_doc 
    error_causality, agent_flow
    OPTIONS {uniqueVertices: 'path', bfs: true}
FILTER e.relationship_type IN ['CAUSED_BY', 'FIXED_BY', 'RETRY_OF']
RETURN {
    vertex: v,
    edge: e,
    path_length: LENGTH(p.edges),
    path: p.vertices[*].message,
    relationships: p.edges[*].relationship_type
}
"""

results = await manager.db.aql.execute(
    aql,
    bind_vars={"start_doc": "errors_and_failures/error_123"}
)

# Process results
for result in results:
    logger.info(f"Found at depth {result['path_length']}: {result['vertex']['message']}")
    logger.info(f"Path: {' -> '.join(result['relationships'])}")
```

### Finding Fix Patterns Through Graph Traversal
```python
async def find_fix_patterns(error_type: str, max_depth: int = 3):
    """Find common fix patterns for an error type using graph traversal."""
    
    aql = """
    // Find all errors of the given type
    FOR error IN errors_and_failures
    FILTER error.error_type == @error_type
    LIMIT 100
    
    // For each error, traverse to find fixes
    FOR v, e, p IN 1..@max_depth OUTBOUND error
        error_causality, agent_flow
    FILTER e.relationship_type == 'FIXED_BY'
    
    // Group by fix description
    COLLECT fix_desc = v.fix_description WITH COUNT INTO occurrences
    FILTER occurrences >= 2
    
    SORT occurrences DESC
    RETURN {
        fix_description: fix_desc,
        count: occurrences,
        confidence: occurrences / 100.0
    }
    """
    
    results = await manager.db.aql.execute(
        aql,
        bind_vars={
            "error_type": error_type,
            "max_depth": max_depth
        }
    )
    
    return list(results)
```

### Complex Graph Query: Error Resolution Paths
```python
async def find_resolution_paths(error_id: str):
    """Find all paths from an error to its resolutions."""
    
    aql = """
    // Find all paths from error to successful resolutions
    FOR path IN 1..5 OUTBOUND @error_id
        error_causality, agent_flow, insight_applications
        OPTIONS {uniqueVertices: 'global', bfs: false}
    
    // Only paths that end in success
    FILTER path.vertices[-1].level == 'SUCCESS' OR 
           path.vertices[-1].resolution != null
    
    // Return the full path with details
    RETURN {
        path_length: LENGTH(path.edges),
        steps: path.vertices[*].message,
        relationships: path.edges[*].relationship_type,
        final_resolution: path.vertices[-1].fix_description,
        total_time: DATE_DIFF(
            path.vertices[0].timestamp,
            path.vertices[-1].timestamp,
            's'
        )
    }
    """
    
    paths = await manager.db.aql.execute(
        aql,
        bind_vars={"error_id": error_id}
    )
    
    return list(paths)
```

## Practical Examples

### Example 1: Creating Error-Fix Relationship
```python
# After fixing an error
error_id = "errors_and_failures/import_error_123"
fix_id = "log_events/fix_456"

# Create the edge
edge_doc = {
    "_from": error_id,
    "_to": fix_id,
    "relationship_type": "FIXED_BY",
    "confidence": 0.95,
    "rationale": "Installed missing package resolved import error",
    "fix_details": {
        "command": "uv add pandas",
        "duration_seconds": 2.5,
        "verified": True
    },
    "created_at": datetime.utcnow().isoformat()
}

edge_collection = manager.db.collection("error_causality")
result = edge_collection.insert(edge_doc)
```

### Example 2: Finding Similar Errors via Graph
```python
async def find_similar_errors_via_graph(error_id: str):
    """Find errors similar to a given error through graph relationships."""
    
    aql = """
    // Start from the error
    LET start_error = DOCUMENT(@error_id)
    
    // Find errors with similar fixes
    FOR v, e, p IN 2..2 ANY @error_id
        error_causality
    FILTER p.edges[0].relationship_type == 'FIXED_BY'
        AND p.edges[1].relationship_type == 'FIXED_BY'
        AND v._id != @error_id
        AND v.error_type == start_error.error_type
    
    COLLECT similar_error = v WITH COUNT INTO similarity_count
    
    RETURN {
        error: similar_error,
        similarity_score: similarity_count / 10.0,
        common_fixes: (
            FOR fix_v, fix_e IN 1..1 OUTBOUND similar_error._id
                error_causality
            FILTER fix_e.relationship_type == 'FIXED_BY'
            RETURN fix_v.fix_description
        )
    }
    """
    
    results = await manager.db.aql.execute(
        aql,
        bind_vars={"error_id": error_id}
    )
    
    return list(results)
```

### Example 3: Complete Error Assessment Workflow
```python
async def complete_error_workflow(error: Exception, file_path: str):
    """Complete workflow with graph operations."""
    
    # 1. Create error document
    error_doc = await manager.log_event(
        level="ERROR",
        message=str(error),
        script_name=Path(file_path).name,
        execution_id="current_session",
        extra_data={
            "error_type": type(error).__name__,
            "stack_trace": traceback.format_exc()
        }
    )
    error_id = error_doc["_id"]
    
    # 2. Search for similar errors using BM25
    similar = await manager.search.search_agent_activity(
        query=f"{type(error).__name__} {str(error)}",
        filters={"tags": ["error", "fix"]},
        limit=10
    )
    
    # 3. Find fix patterns through graph traversal
    fix_patterns = await find_fix_patterns(type(error).__name__)
    
    # 4. Apply fix (example)
    fix_applied = "Installed missing module with uv add"
    
    # 5. Log the fix
    fix_doc = await manager.log_event(
        level="SUCCESS",
        message=f"Fixed: {fix_applied}",
        script_name=Path(file_path).name,
        execution_id="current_session",
        extra_data={
            "fix_description": fix_applied,
            "original_error_id": error_id
        }
    )
    fix_id = fix_doc["_id"]
    
    # 6. Create edge relationship
    edge_doc = {
        "_from": error_id,
        "_to": fix_id,
        "relationship_type": "FIXED_BY",
        "confidence": 0.95,
        "rationale": "Standard fix for missing module",
        "created_at": datetime.utcnow().isoformat()
    }
    
    edge_collection = manager.db.collection("error_causality")
    edge_result = edge_collection.insert(edge_doc)
    
    # 7. Find related errors through multi-hop traversal
    related = await find_resolution_paths(error_id)
    
    return {
        "error_id": error_id,
        "fix_id": fix_id,
        "edge_id": edge_result["_id"],
        "similar_errors": len(similar),
        "fix_patterns": fix_patterns,
        "related_paths": related
    }
```

## Best Practices

1. **Always Include Rationale**: Every edge should explain WHY the relationship exists
2. **Use Confidence Scores**: Rate how certain the relationship is (0.0 - 1.0)
3. **Add Context**: Include session_id, execution_id, timestamps
4. **Use Appropriate Edge Collections**:
   - `error_causality` for error relationships
   - `agent_flow` for execution flow
   - `insight_applications` for insights to actions
5. **Leverage Multi-Hop Queries**: Don't just look at direct relationships
6. **Combine BM25 and Graph**: Use text search to find candidates, then traverse graph for relationships

## Summary

The Logger Agent provides powerful graph capabilities:
- Create edges with `_from`, `_to`, `relationship_type`, `rationale`
- Use BM25 for full-text relevance search
- Perform multi-hop traversal to find complex relationships
- Combine both for comprehensive error analysis and fix discovery