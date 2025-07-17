# ArangoDB Working Scenarios - Expert Reference

## Table of Contents
1. [Basic CRUD Operations](#basic-crud-operations)
2. [Edge Document Operations](#edge-document-operations)
3. [Graph Traversal Queries](#graph-traversal-queries)
4. [BM25 Full-Text Search](#bm25-full-text-search)
5. [Complex Graph Patterns](#complex-graph-patterns)
6. [Logger Agent Integration Scenarios](#logger-agent-integration-scenarios)

## Basic CRUD Operations

### 1. Document Creation
```python
# Create a single document
async def create_error_document(manager, error_type, error_message, file_path):
    """Create an error document in log_events collection."""
    
    doc = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": "ERROR",
        "message": error_message,
        "error_type": error_type,
        "file_path": file_path,
        "execution_id": f"exec_{datetime.utcnow().timestamp()}",
        "tags": ["error", error_type.lower()],
        "resolved": False
    }
    
    collection = manager.db.collection("log_events")
    result = collection.insert(doc)
    
    # Result includes _id, _key, _rev
    return result
```

### 2. Document Read
```python
# Read by _key
doc = collection.get("12345")

# Read by _id
doc = manager.db.document("log_events/12345")

# Find documents with filters
cursor = collection.find({"error_type": "ModuleNotFoundError"}, limit=10)
results = list(cursor)
```

### 3. Document Update
```python
# Update by key
collection.update({
    "_key": "12345",
    "resolved": True,
    "resolution_time": datetime.utcnow().isoformat(),
    "fix_description": "Installed missing module"
})

# Update with match
collection.update_match(
    {"error_type": "ModuleNotFoundError", "resolved": False},
    {"resolved": True, "resolver": "auto_fix"}
)
```

### 4. Document Delete
```python
# Delete by key
collection.delete("12345")

# Delete multiple with filter
collection.delete_match({"timestamp": {"<": "2024-01-01"}})
```

## Edge Document Operations

### 1. Creating Edge Documents
```python
# Basic edge structure
edge_doc = {
    "_from": "log_events/error_123",    # Source vertex ID
    "_to": "log_events/fix_456",        # Target vertex ID
    "relationship_type": "FIXED_BY",
    "confidence": 0.95,
    "rationale": "Applied uv add to install missing package",
    "created_at": datetime.utcnow().isoformat(),
    "metadata": {
        "duration_seconds": 2.5,
        "attempts": 1,
        "tool_used": "assess_complexity"
    }
}

# Insert into edge collection
edge_collection = manager.db.collection("error_causality")
result = edge_collection.insert(edge_doc)
```

### 2. Complex Edge Creation for Logger Agent
```python
async def create_fix_relationship(manager, error_id, fix_id, assessment_id):
    """Create a complete fix relationship with all metadata."""
    
    # Create primary FIXED_BY edge
    fix_edge = {
        "_from": error_id,
        "_to": fix_id,
        "relationship_type": "FIXED_BY",
        "confidence": 0.95,
        "rationale": "Standard fix applied based on assessment",
        "assessment_id": assessment_id,
        "created_at": datetime.utcnow().isoformat(),
        "verified": True,
        "fix_details": {
            "method": "uv add",
            "package": "pandas",
            "version": "2.0.1"
        }
    }
    
    edge_coll = manager.db.collection("error_causality")
    result1 = edge_coll.insert(fix_edge)
    
    # Create ASSESSED_BY edge linking to assessment
    if assessment_id:
        assess_edge = {
            "_from": error_id,
            "_to": f"assessments/{assessment_id}",
            "relationship_type": "ASSESSED_BY",
            "confidence": 1.0,
            "created_at": datetime.utcnow().isoformat()
        }
        result2 = edge_coll.insert(assess_edge)
    
    # Create temporal edge
    temporal_edge = {
        "_from": error_id,
        "_to": fix_id,
        "relationship_type": "FOLLOWED_BY",
        "confidence": 1.0,
        "time_delta_seconds": 45,
        "created_at": datetime.utcnow().isoformat()
    }
    
    flow_coll = manager.db.collection("agent_flow")
    result3 = flow_coll.insert(temporal_edge)
    
    return [result1, result2, result3]
```

### 3. Edge Updates
```python
# Update edge properties
edge_collection.update({
    "_key": edge_key,
    "verified": True,
    "verification_time": datetime.utcnow().isoformat(),
    "verifier": "working_usage_test"
})
```

## Graph Traversal Queries

### 1. Single-Hop Traversal - Find Direct Relationships
```python
async def find_direct_fixes(manager, error_id):
    """Find all direct fixes for an error."""
    
    aql = """
    FOR v, e IN 1..1 OUTBOUND @error_id 
        error_causality
    FILTER e.relationship_type == 'FIXED_BY'
    RETURN {
        fix: v,
        edge: e,
        confidence: e.confidence,
        rationale: e.rationale
    }
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"error_id": error_id}
    )
    
    return list(cursor)
```

### 2. Multi-Hop Traversal - Find Causal Chains
```python
async def find_error_chain(manager, root_error_id):
    """Find the complete error chain from root cause."""
    
    aql = """
    FOR v, e, p IN 1..5 OUTBOUND @root_error 
        error_causality
    FILTER e.relationship_type IN ['CAUSED_BY', 'LED_TO', 'TRIGGERED']
    OPTIONS {uniqueVertices: 'path', bfs: true}
    RETURN {
        error: v,
        relationship: e.relationship_type,
        depth: LENGTH(p.edges),
        path: p.vertices[*].message,
        complete_path: p
    }
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"root_error": root_error_id}
    )
    
    return list(cursor)
```

### 3. Bidirectional Traversal - Find Related Errors
```python
async def find_related_errors(manager, error_id):
    """Find errors related through any path."""
    
    aql = """
    // Find errors with common fixes (share the same fix)
    LET common_fix_errors = (
        FOR fix IN 1..1 OUTBOUND @error_id error_causality
        FILTER fix.relationship_type == 'FIXED_BY'
        FOR related IN 1..1 INBOUND fix._id error_causality
        FILTER related._id != @error_id
        FILTER related.error_type == DOCUMENT(@error_id).error_type
        RETURN DISTINCT related
    )
    
    // Find errors that led to this error
    LET causing_errors = (
        FOR cause IN 1..2 INBOUND @error_id error_causality
        FILTER cause.relationship_type IN ['CAUSED_BY', 'LED_TO']
        RETURN cause
    )
    
    // Find errors caused by this error
    LET caused_errors = (
        FOR effect IN 1..2 OUTBOUND @error_id error_causality
        FILTER effect.relationship_type IN ['CAUSED_BY', 'LED_TO']
        RETURN effect
    )
    
    RETURN {
        common_fix_errors: common_fix_errors,
        causing_errors: causing_errors,
        caused_errors: caused_errors
    }
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"error_id": error_id}
    )
    
    return list(cursor)[0] if cursor else {}
```

## BM25 Full-Text Search

### 1. Basic BM25 Search
```python
async def search_logs_bm25(manager, query_text):
    """Search logs using BM25 scoring."""
    
    aql = """
    FOR doc IN agent_activity_search
    SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
    LET score = BM25(doc)
    SORT score DESC
    LIMIT 20
    RETURN {
        document: doc,
        score: score,
        type: SPLIT(doc._id, '/')[0]
    }
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"query": query_text}
    )
    
    return list(cursor)
```

### 2. Multi-Field BM25 Search
```python
async def search_comprehensive(manager, query_text, filters=None):
    """Search across multiple fields with filters."""
    
    # Build filter conditions
    filter_conditions = []
    if filters:
        if filters.get("error_type"):
            filter_conditions.append("doc.error_type == @error_type")
        if filters.get("time_range"):
            filter_conditions.append("doc.timestamp >= @start_time")
    
    filter_clause = f"FILTER {' AND '.join(filter_conditions)}" if filter_conditions else ""
    
    aql = f"""
    FOR doc IN agent_activity_search
    SEARCH ANALYZER(
        doc.message IN TOKENS(@query, 'text_en') OR
        doc.fix_description IN TOKENS(@query, 'text_en') OR
        doc.error_message IN TOKENS(@query, 'text_en') OR
        doc.stack_trace IN TOKENS(@query, 'text_en'),
        'text_en'
    )
    {filter_clause}
    LET score = BM25(doc)
    FILTER score > 0.1
    SORT score DESC
    LIMIT 50
    RETURN {{
        id: doc._id,
        score: score,
        message: doc.message,
        highlights: {{
            message: SUBSTRING(doc.message, 0, 200),
            fix: doc.fix_description
        }}
    }}
    """
    
    bind_vars = {"query": query_text}
    if filters:
        bind_vars.update(filters)
    
    cursor = manager.db.aql.execute(aql, bind_vars=bind_vars)
    return list(cursor)
```

## Complex Graph Patterns

### 1. Finding Fix Patterns
```python
async def find_successful_fix_patterns(manager, error_type):
    """Find the most successful fix patterns for an error type."""
    
    aql = """
    // Find all errors of this type
    FOR error IN errors_and_failures
    FILTER error.error_type == @error_type
    FILTER error.resolved == true
    
    // Find their fixes
    FOR fix IN 1..1 OUTBOUND error error_causality
    FILTER fix.relationship_type == 'FIXED_BY'
    
    // Group by fix pattern
    COLLECT 
        fix_pattern = fix.fix_description,
        fix_method = fix.fix_details.method
    WITH COUNT INTO success_count
    
    // Calculate success metrics
    LET total_errors = LENGTH(
        FOR e IN errors_and_failures
        FILTER e.error_type == @error_type
        RETURN 1
    )
    
    SORT success_count DESC
    RETURN {
        pattern: fix_pattern,
        method: fix_method,
        success_count: success_count,
        success_rate: success_count / total_errors,
        confidence: success_count > 5 ? 0.9 : 0.7
    }
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"error_type": error_type}
    )
    
    return list(cursor)
```

### 2. Graph-Based Similar Error Detection
```python
async def find_similar_errors_by_graph(manager, error_id):
    """Find similar errors using graph relationships."""
    
    aql = """
    LET source_error = DOCUMENT(@error_id)
    
    // Strategy 1: Errors fixed by similar methods
    LET similar_by_fix = (
        FOR my_fix IN 1..1 OUTBOUND @error_id error_causality
        FILTER my_fix.relationship_type == 'FIXED_BY'
        
        // Find other errors fixed the same way
        FOR other_error IN 1..1 INBOUND my_fix._id error_causality
        FILTER other_error._id != @error_id
        FILTER other_error.error_type == source_error.error_type
        RETURN {
            error: other_error,
            similarity_reason: 'same_fix_method',
            fix_method: my_fix.fix_description
        }
    )
    
    // Strategy 2: Errors in same causal chain
    LET similar_by_cause = (
        FOR related IN 2..3 ANY @error_id error_causality
        FILTER related._id != @error_id
        FILTER related.error_type == source_error.error_type
        RETURN {
            error: related,
            similarity_reason: 'causal_relationship',
            distance: LENGTH(SHORTEST_PATH(
                @error_id TO related._id 
                error_causality
            ))
        }
    )
    
    // Combine and deduplicate
    LET all_similar = UNION_DISTINCT(similar_by_fix, similar_by_cause)
    
    FOR item IN all_similar
    SORT item.error.timestamp DESC
    LIMIT 20
    RETURN item
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={"error_id": error_id}
    )
    
    return list(cursor)
```

## Logger Agent Integration Scenarios

### 1. Complete Error Assessment and Fix Workflow
```python
async def complete_error_workflow(manager, error, file_path):
    """Complete workflow from error to fix with full graph integration."""
    
    execution_id = f"workflow_{datetime.utcnow().timestamp()}"
    
    # Step 1: Log the error
    error_doc = await manager.log_event(
        level="ERROR",
        message=str(error),
        script_name=Path(file_path).name,
        execution_id=execution_id,
        extra_data={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "file_path": file_path,
            "stack_trace": traceback.format_exc()
        },
        tags=["error", type(error).__name__.lower()]
    )
    error_id = error_doc["_id"]
    
    # Step 2: Create assessment
    assessment_doc = await manager.log_event(
        level="INFO",
        message=f"Assessing {type(error).__name__}",
        script_name="assess_complexity",
        execution_id=execution_id,
        extra_data={
            "assessment_type": "error_analysis",
            "error_id": error_id,
            "complexity_indicators": ["import_missing"],
            "confidence": "HIGH"
        },
        tags=["assessment"]
    )
    assessment_id = assessment_doc["_id"]
    
    # Step 3: Create assessment edge
    assess_edge = {
        "_from": error_id,
        "_to": assessment_id,
        "relationship_type": "ASSESSED_BY",
        "confidence": 1.0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    edge_coll = manager.db.collection("error_causality")
    edge_coll.insert(assess_edge)
    
    # Step 4: Search for similar errors and fixes
    aql = """
    FOR doc IN agent_activity_search
    SEARCH ANALYZER(
        doc.message IN TOKENS(@query, 'text_en') AND
        doc.error_type == @error_type,
        'text_en'
    )
    LET score = BM25(doc)
    FILTER score > 0.5
    
    // Find fixes for these errors
    LET fixes = (
        FOR fix IN 1..1 OUTBOUND doc._id error_causality
        FILTER fix.relationship_type == 'FIXED_BY'
        RETURN fix
    )
    
    SORT score DESC
    LIMIT 5
    RETURN {
        error: doc,
        fixes: fixes,
        score: score
    }
    """
    
    similar_results = await manager.db.aql.execute(
        aql,
        bind_vars={
            "query": str(error),
            "error_type": type(error).__name__
        }
    )
    
    # Step 5: Apply fix
    fix_description = "Installed missing module with uv add"
    
    # Step 6: Log successful fix
    fix_doc = await manager.log_event(
        level="SUCCESS",
        message=f"Fixed: {fix_description}",
        script_name=Path(file_path).name,
        execution_id=execution_id,
        extra_data={
            "fix_description": fix_description,
            "original_error_id": error_id,
            "assessment_id": assessment_id
        },
        tags=["fix", "success", type(error).__name__.lower()]
    )
    fix_id = fix_doc["_id"]
    
    # Step 7: Create fix edges
    fix_edge = {
        "_from": error_id,
        "_to": fix_id,
        "relationship_type": "FIXED_BY",
        "confidence": 0.95,
        "rationale": "Applied standard fix from pattern database",
        "assessment_id": assessment_id,
        "created_at": datetime.utcnow().isoformat()
    }
    edge_coll.insert(fix_edge)
    
    # Step 8: Create temporal flow edge
    flow_edge = {
        "_from": assessment_id,
        "_to": fix_id,
        "relationship_type": "LED_TO",
        "confidence": 0.9,
        "created_at": datetime.utcnow().isoformat()
    }
    
    flow_coll = manager.db.collection("agent_flow")
    flow_coll.insert(flow_edge)
    
    # Step 9: Store as memory
    await manager.memory.add_memory(
        content=f"Fix for {type(error).__name__}: {fix_description}",
        memory_type="learning",
        metadata={
            "error_type": type(error).__name__,
            "fix_description": fix_description,
            "file_path": file_path,
            "confidence": 0.9,
            "error_id": error_id,
            "fix_id": fix_id
        }
    )
    
    return {
        "error_id": error_id,
        "assessment_id": assessment_id,
        "fix_id": fix_id,
        "workflow_complete": True
    }
```

### 2. Multi-Hop Search for Resolution Paths
```python
async def find_resolution_paths(manager, error_id, max_depth=5):
    """Find all paths from error to resolution using multi-hop traversal."""
    
    aql = """
    // Find all possible resolution paths
    FOR path IN 1..@max_depth OUTBOUND @error_id
        error_causality, agent_flow
    OPTIONS {uniqueVertices: 'none', bfs: false}
    
    // Only paths that end in success
    FILTER path.vertices[-1].level == 'SUCCESS' OR 
           path.vertices[-1].tags ANY == 'fix'
    
    // Extract the path details
    LET path_summary = {
        length: LENGTH(path.edges),
        start: path.vertices[0].message,
        end: path.vertices[-1].message,
        steps: (
            FOR i IN 0..LENGTH(path.edges)-1
            RETURN {
                from: path.vertices[i].message,
                to: path.vertices[i+1].message,
                relationship: path.edges[i].relationship_type,
                confidence: path.edges[i].confidence
            }
        ),
        total_confidence: PRODUCT(path.edges[*].confidence),
        time_taken: DATE_DIFF(
            path.vertices[0].timestamp,
            path.vertices[-1].timestamp,
            's'
        )
    }
    
    // Only return high-confidence paths
    FILTER path_summary.total_confidence > 0.5
    
    SORT path_summary.total_confidence DESC, path_summary.length ASC
    LIMIT 10
    
    RETURN path_summary
    """
    
    cursor = manager.db.aql.execute(
        aql,
        bind_vars={
            "error_id": error_id,
            "max_depth": max_depth
        }
    )
    
    return list(cursor)
```

## Best Practices Summary

1. **Always Include Metadata in Edges**:
   - `relationship_type`: Clear relationship name
   - `confidence`: 0.0-1.0 score
   - `rationale`: Human-readable explanation
   - `created_at`: ISO timestamp
   - `metadata`: Additional context

2. **Use Appropriate Collections**:
   - Documents: `log_events`, `errors_and_failures`, `agent_insights`
   - Edges: `error_causality`, `agent_flow`, `insight_applications`

3. **Leverage Indexes**:
   - Create indexes on frequently queried fields
   - Use compound indexes for complex queries

4. **Graph Traversal Tips**:
   - Use `OPTIONS {uniqueVertices: 'path'}` to avoid cycles
   - Specify edge collections explicitly
   - Use `FILTER` early to reduce traversal scope

5. **BM25 Search Tips**:
   - Use appropriate analyzers (`text_en` for English)
   - Score threshold filtering improves relevance
   - Combine with graph traversal for context