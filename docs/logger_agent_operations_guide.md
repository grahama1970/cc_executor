# Logger Agent Operations Guide - Query, Insert, Update

## Overview
This guide demonstrates concrete usage of logger.query, logger.insert, logger.update operations in debugging workflows. Each operation maps to specific debugging scenarios as described by the user.

## Core Operations Reference

### 1. logger.query() - Finding Similar Bugs

```python
# Basic query structure
async def query_similar_errors(manager, error_type, error_message, file_path):
    """Find similar bugs that are close to the current debugging context."""
    
    # Method 1: BM25 Text Search
    results = await manager.search.search_agent_activity(
        query=f"{error_type} {error_message} {file_path}",
        filters={
            "event_types": ["error", "fix", "resolution"],
            "tags": [error_type.lower()]
        },
        limit=10
    )
    
    # Method 2: Direct AQL Query with scoring
    aql = """
    FOR doc IN agent_activity_search
    SEARCH ANALYZER(
        doc.message IN TOKENS(@query, 'text_en') OR
        doc.error_type == @error_type,
        'text_en'
    )
    LET score = BM25(doc)
    FILTER score > 0.5
    SORT score DESC
    LIMIT 10
    RETURN {
        document: doc,
        score: score,
        fix: doc.fix_description
    }
    """
    
    results = await manager.db.aql.execute(
        aql,
        bind_vars={
            "query": error_message,
            "error_type": error_type
        }
    )
    
    return list(results)
```

### 2. logger.insert() - Creating New Log Entries

```python
# Insert error assessment
async def insert_error_assessment(manager, error, file_path, complexity_metrics):
    """Insert a new error assessment into the knowledge graph."""
    
    execution_id = f"debug_{datetime.utcnow().timestamp()}"
    
    # Insert the error document
    error_doc = await manager.log_event(
        level="ERROR",
        message=str(error),
        script_name=Path(file_path).name,
        execution_id=execution_id,
        extra_data={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "file_path": file_path,
            "stack_trace": traceback.format_exc(),
            "complexity_metrics": complexity_metrics,
            "assessed_at": datetime.utcnow().isoformat()
        },
        tags=["error", "assessment", type(error).__name__.lower()]
    )
    
    # Insert assessment results
    assessment_doc = await manager.log_event(
        level="INFO",
        message=f"Complexity assessment for {type(error).__name__}",
        script_name="assess_complexity",
        execution_id=execution_id,
        extra_data={
            "error_id": error_doc["_id"],
            "complexity_score": complexity_metrics.get("score", 0),
            "recommended_approach": complexity_metrics.get("approach"),
            "confidence": complexity_metrics.get("confidence")
        },
        tags=["assessment", "complexity"]
    )
    
    # Insert edge relationship
    edge_collection = manager.db.collection("error_causality")
    edge_doc = {
        "_from": error_doc["_id"],
        "_to": assessment_doc["_id"],
        "relationship_type": "ASSESSED_BY",
        "confidence": 1.0,
        "created_at": datetime.utcnow().isoformat()
    }
    edge_collection.insert(edge_doc)
    
    return error_doc["_id"], assessment_doc["_id"]
```

### 3. logger.update() - Marking Issues as Resolved

```python
# Update error status when fixed
async def update_error_resolved(manager, error_id, fix_description, fix_details):
    """Update an error document to mark it as resolved."""
    
    # Get the collection
    collection = manager.db.collection("log_events")
    
    # Update the error document
    collection.update({
        "_key": error_id.split("/")[1],  # Extract key from ID
        "resolved": True,
        "resolved_at": datetime.utcnow().isoformat(),
        "resolution_time_seconds": fix_details.get("duration", 0),
        "fix_description": fix_description,
        "fix_verified": fix_details.get("verified", False)
    })
    
    # Insert fix document
    fix_doc = await manager.log_event(
        level="SUCCESS",
        message=f"Fixed: {fix_description}",
        script_name=fix_details.get("script_name", "unknown"),
        execution_id=fix_details.get("execution_id"),
        extra_data={
            "original_error_id": error_id,
            "fix_description": fix_description,
            "fix_command": fix_details.get("command"),
            "fix_details": fix_details
        },
        tags=["fix", "success", "resolution"]
    )
    
    # Create FIXED_BY edge
    edge_collection = manager.db.collection("error_causality")
    edge_doc = {
        "_from": error_id,
        "_to": fix_doc["_id"],
        "relationship_type": "FIXED_BY",
        "confidence": 0.95,
        "rationale": fix_description,
        "created_at": datetime.utcnow().isoformat()
    }
    edge_collection.insert(edge_doc)
    
    return fix_doc["_id"]
```

## Complete Debugging Workflow Examples

### Scenario 1: "Where have I seen this bug before?"

```python
async def find_similar_bugs_workflow(manager, current_error, current_file):
    """Complete workflow for finding similar bugs."""
    
    error_type = type(current_error).__name__
    error_message = str(current_error)
    
    # Step 1: Query for similar errors
    logger.info(f"Searching for similar {error_type} errors...")
    
    # Query by error pattern
    similar_errors = await manager.search.search_agent_activity(
        query=f"{error_type} {error_message}",
        filters={
            "event_types": ["error", "fix"],
            "tags": [error_type.lower()]
        },
        limit=20
    )
    
    # Step 2: Filter by file context similarity
    relevant_errors = []
    current_dir = Path(current_file).parent.name
    
    for result in similar_errors:
        doc = result["doc"]
        file_path = doc.get("extra_data", {}).get("file_path", "")
        
        # Score based on path similarity
        if current_dir in file_path:
            result["context_score"] = 1.0
        elif Path(file_path).suffix == Path(current_file).suffix:
            result["context_score"] = 0.5
        else:
            result["context_score"] = 0.1
        
        # Combined score
        result["total_score"] = result["score"] * 0.7 + result["context_score"] * 0.3
        relevant_errors.append(result)
    
    # Sort by combined score
    relevant_errors.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Step 3: Extract fixes for these errors
    fixes_found = []
    for error in relevant_errors[:5]:
        error_id = error["doc"]["_id"]
        
        # Query for fixes
        aql = """
        FOR fix IN 1..1 OUTBOUND @error_id error_causality
        FILTER fix.relationship_type == 'FIXED_BY'
        RETURN {
            fix_description: fix.fix_description,
            confidence: fix.confidence,
            command: fix.fix_details.command
        }
        """
        
        fix_results = await manager.db.aql.execute(
            aql,
            bind_vars={"error_id": error_id}
        )
        
        for fix in fix_results:
            fixes_found.append({
                "error": error["doc"]["message"],
                "fix": fix,
                "score": error["total_score"]
            })
    
    return fixes_found
```

### Scenario 2: "What other functions are related by 2 hops?"

```python
async def find_related_functions_2hop(manager, error_id, file_path):
    """Find functions related to current error by 2-hop traversal."""
    
    # Query for 2-hop relationships
    aql = """
    FOR v, e, p IN 2..2 ANY @start_id 
        error_causality, agent_flow, insight_applications
    OPTIONS {uniqueVertices: 'path', bfs: true}
    
    // Filter for relevant relationships
    FILTER p.edges[*].relationship_type ANY IN [
        'CAUSED_BY', 'FIXED_BY', 'DEPENDS_ON', 'SIMILAR_TO'
    ]
    
    // Extract file paths and functions
    LET file_paths = (
        FOR vertex IN p.vertices
        RETURN DISTINCT vertex.extra_data.file_path
    )
    
    RETURN DISTINCT {
        related_vertex: v,
        path_length: 2,
        relationships: p.edges[*].relationship_type,
        file_paths: file_paths,
        connection_strength: PRODUCT(p.edges[*].confidence)
    }
    """
    
    results = await manager.db.aql.execute(
        aql,
        bind_vars={"start_id": error_id}
    )
    
    # Group by file/function
    related_functions = {}
    for result in results:
        vertex = result["related_vertex"]
        file = vertex.get("extra_data", {}).get("file_path", "unknown")
        
        if file not in related_functions:
            related_functions[file] = []
        
        related_functions[file].append({
            "message": vertex.get("message", ""),
            "type": vertex.get("level", ""),
            "relationships": result["relationships"],
            "strength": result["connection_strength"]
        })
    
    return related_functions
```

### Scenario 3: "Which ones were resolved/fixed?"

```python
async def find_resolved_issues_workflow(manager, error_type=None, time_range="7d"):
    """Find which issues have been resolved and how."""
    
    # Step 1: Query for resolved errors
    aql = """
    FOR error IN log_events
    FILTER error.resolved == true
    FILTER error.resolved_at != null
    """
    
    # Add error type filter if specified
    if error_type:
        aql += """
        FILTER error.error_type == @error_type
        """
    
    # Add time filter
    aql += """
    FILTER DATE_DIFF(error.resolved_at, NOW(), 'd') <= @days
    
    // Get the fix details
    LET fixes = (
        FOR fix IN 1..1 OUTBOUND error._id error_causality
        FILTER fix.relationship_type == 'FIXED_BY'
        RETURN fix
    )
    
    SORT error.resolved_at DESC
    RETURN {
        error: error,
        fixes: fixes,
        resolution_time: error.resolution_time_seconds
    }
    """
    
    # Parse time range
    days = int(time_range.rstrip('d'))
    
    bind_vars = {"days": days}
    if error_type:
        bind_vars["error_type"] = error_type
    
    results = await manager.db.aql.execute(aql, bind_vars=bind_vars)
    
    # Step 2: Group by fix pattern
    fix_patterns = {}
    for result in results:
        error = result["error"]
        fixes = result["fixes"]
        
        for fix in fixes:
            pattern = fix.get("fix_description", "Unknown fix")
            if pattern not in fix_patterns:
                fix_patterns[pattern] = {
                    "count": 0,
                    "avg_resolution_time": 0,
                    "examples": []
                }
            
            fix_patterns[pattern]["count"] += 1
            fix_patterns[pattern]["examples"].append({
                "error_type": error.get("error_type"),
                "error_message": error.get("message"),
                "resolved_at": error.get("resolved_at")
            })
    
    # Step 3: Calculate success metrics
    for pattern, data in fix_patterns.items():
        if data["examples"]:
            # Calculate average resolution time
            total_time = sum(
                e.get("resolution_time_seconds", 0) 
                for e in data["examples"]
            )
            data["avg_resolution_time"] = total_time / len(data["examples"])
    
    return fix_patterns
```

## Complete Integration Example

```python
async def complete_debugging_workflow(error: Exception, file_path: str):
    """
    Complete workflow demonstrating all operations:
    1. Query for similar bugs
    2. Insert assessment and error
    3. Apply fix and update status
    """
    
    manager = await get_log_manager()
    execution_id = f"debug_{datetime.utcnow().timestamp()}"
    
    logger.info("=== Starting Complete Debugging Workflow ===")
    
    # STEP 1: QUERY - Where have I seen this before?
    logger.info("Step 1: Searching for similar errors...")
    
    similar_bugs = await find_similar_bugs_workflow(
        manager, error, file_path
    )
    
    if similar_bugs:
        logger.info(f"Found {len(similar_bugs)} similar bugs:")
        for bug in similar_bugs[:3]:
            logger.info(f"  - {bug['error'][:50]}...")
            logger.info(f"    Fix: {bug['fix']['fix_description']}")
    
    # STEP 2: INSERT - Log the current error
    logger.info("\nStep 2: Inserting error assessment...")
    
    complexity_metrics = {
        "score": 0.7,
        "approach": "self-fix" if similar_bugs else "research",
        "confidence": 0.8 if similar_bugs else 0.3
    }
    
    error_id, assessment_id = await insert_error_assessment(
        manager, error, file_path, complexity_metrics
    )
    
    logger.info(f"Created error: {error_id}")
    logger.info(f"Created assessment: {assessment_id}")
    
    # STEP 3: QUERY - Find related functions (2-hop)
    logger.info("\nStep 3: Finding related functions...")
    
    related = await find_related_functions_2hop(
        manager, error_id, file_path
    )
    
    for file, functions in related.items():
        logger.info(f"  File: {file}")
        for func in functions[:2]:
            logger.info(f"    - {func['message'][:50]}...")
    
    # STEP 4: Apply fix (simulated)
    logger.info("\nStep 4: Applying fix...")
    
    # Simulate fixing based on similar bugs
    if similar_bugs:
        best_fix = similar_bugs[0]["fix"]
        fix_description = best_fix["fix_description"]
        fix_command = best_fix.get("command", "manual fix")
    else:
        fix_description = "Applied manual fix after research"
        fix_command = "manual intervention"
    
    logger.info(f"Applying: {fix_description}")
    
    # STEP 5: UPDATE - Mark as resolved
    logger.info("\nStep 5: Updating error as resolved...")
    
    fix_id = await update_error_resolved(
        manager,
        error_id,
        fix_description,
        {
            "duration": 45,
            "verified": True,
            "command": fix_command,
            "script_name": Path(file_path).name,
            "execution_id": execution_id
        }
    )
    
    logger.info(f"Created fix: {fix_id}")
    
    # STEP 6: QUERY - Verify resolution
    logger.info("\nStep 6: Verifying resolution...")
    
    resolved_patterns = await find_resolved_issues_workflow(
        manager,
        error_type=type(error).__name__,
        time_range="1d"
    )
    
    logger.success("✅ Workflow completed!")
    logger.info(f"Resolution patterns found: {len(resolved_patterns)}")
    
    return {
        "error_id": error_id,
        "assessment_id": assessment_id,
        "fix_id": fix_id,
        "similar_bugs_found": len(similar_bugs),
        "related_functions": len(related),
        "resolution_verified": True
    }
```

## Quick Reference

### Query Operations
```python
# Find similar errors
results = await manager.search.search_agent_activity(query, filters, limit)

# Graph traversal
results = await manager.db.aql.execute(aql_query, bind_vars)

# Get specific document
doc = await manager.db.document("collection/key")
```

### Insert Operations
```python
# Log event
doc = await manager.log_event(level, message, script_name, execution_id, extra_data, tags)

# Create edge
edge_collection.insert(edge_doc)

# Add memory
await manager.memory.add_memory(content, memory_type, metadata)
```

### Update Operations
```python
# Update document
collection.update({"_key": key, ...updates})

# Update by match
collection.update_match(filter, updates)
```

## Best Practices

1. **Always Include Context**: Every operation should include execution_id, file_path, and timestamp
2. **Use Appropriate Tags**: Help future queries by tagging consistently
3. **Create Relationships**: Don't just log events - connect them with edges
4. **Score and Rank Results**: Combine BM25 scores with context scores
5. **Verify Fixes**: Always mark errors as resolved and track resolution time

## Summary

Each debugging step maps to logger operations:
- "Where have I seen this bug before?" → **logger.query()**
- "Log this error and assessment" → **logger.insert()**
- "Mark this as fixed" → **logger.update()**

The combination of these operations creates a powerful debugging knowledge graph that improves over time.