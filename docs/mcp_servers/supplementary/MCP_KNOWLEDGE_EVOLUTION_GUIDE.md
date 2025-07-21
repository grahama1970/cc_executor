# MCP Knowledge Evolution Guide

## The Problem: Knowledge Gets Stale

Solutions that worked yesterday might be:
- **Insecure** (e.g., `shell=True` in subprocess)
- **Deprecated** (API changes, better methods found)
- **Contradictory** (two solutions claim to work but one fails)
- **Incomplete** (missing edge cases discovered later)

## Knowledge Evolution Workflow

### 1. Test Contradicting Solutions

When you find multiple solutions for the same problem:

```python
# Example: Two solutions for handling subprocess timeout
solution_1 = "Use subprocess.run(timeout=30)"
solution_2 = "Use asyncio.create_subprocess_exec with wait_for()"

# Test both
test_results = {
    "err_123": {"success": False, "error": "Still hangs on large output"},
    "err_456": {"success": True, "output": "Handles large output correctly"}
}

# Update knowledge based on results
await resolve_contradiction(
    solutions=["err_123", "err_456"],
    test_results=test_results
)
```

### 2. Deprecate Dangerous Patterns

When you learn a pattern is dangerous:

```python
# Find all solutions using dangerous pattern
dangerous_query = """
FOR doc IN log_events
    FILTER doc.resolved == true
    FILTER CONTAINS(doc.resolution, "shell=True")
    RETURN doc
"""

# Deprecate them all
for doc in dangerous_solutions:
    await mcp__arango-tools__upsert(
        collection="log_events",
        search={"_key": doc["_key"]},
        update={
            "deprecated": True,
            "deprecation_reason": "shell=True is a security risk - use shlex.split()",
            "security_risk": True,
            "resolved": False  # No longer considered resolved!
        }
    )
```

### 3. Create Contradiction Edges

Document which solutions contradict each other:

```python
# Solution A contradicts Solution B
await mcp__arango-tools__edge(
    from_id="log_events/new_secure_solution",
    to_id="log_events/old_dangerous_solution",
    collection="error_relationships",
    relationship_type="contradicts",
    reason="Uses shlex.split() instead of shell=True",
    test_verified=True
)
```

### 4. Bulk Knowledge Updates

When you discover a new insight affecting many solutions:

```python
# Example: Learning that all FileNotFoundError with relative paths fail in MCP
bulk_update = """
FOR doc IN log_events
    FILTER doc.error_type == "FileNotFoundError"
    FILTER doc.resolved == true
    FILTER CONTAINS(doc.resolution, "relative path")
    UPDATE doc WITH {
        needs_review: true,
        review_reason: "MCP tools run from different directories - must use absolute paths",
        review_priority: "high"
    } IN log_events
"""

await mcp__arango-tools__query(bulk_update)
```

## Practical Examples

### Example 1: Subprocess Hanging Issue

```python
# Original solution (works sometimes)
error_1 = {
    "error_type": "SubprocessTimeout",
    "resolution": "Use subprocess.run(timeout=30)",
    "resolved": True
}

# Better solution discovered
error_2 = {
    "error_type": "SubprocessTimeout", 
    "resolution": "Use asyncio with stream draining to prevent buffer deadlock",
    "resolved": True
}

# After testing, update knowledge
# 1. Deprecate incomplete solution
await mcp__arango-tools__update(
    collection="log_events",
    key="error_1_key",
    fields={
        "deprecated": True,
        "deprecation_reason": "Doesn't handle full buffers - process still hangs",
        "replaced_by": "error_2_key"
    }
)

# 2. Create contradiction edge
await mcp__arango-tools__edge(
    from_id="log_events/error_2_key",
    to_id="log_events/error_1_key",
    collection="error_relationships",
    relationship_type="contradicts",
    buffer_size_tested="100MB",
    proven_superior=True
)
```

### Example 2: Security Pattern Evolution

```python
# Discover security issue in old solutions
security_audit = """
FOR doc IN log_events
    FILTER doc.resolved == true
    FILTER CONTAINS(LOWER(doc.resolution), "eval(")
       OR CONTAINS(LOWER(doc.resolution), "exec(")
       OR CONTAINS(LOWER(doc.resolution), "shell=true")
    UPDATE doc WITH {
        deprecated: true,
        security_risk: true,
        risk_level: "HIGH",
        deprecation_reason: "Security audit: dangerous code execution pattern"
    } IN log_events
    RETURN NEW
"""

results = await mcp__arango-tools__query(security_audit)
logger.critical(f"Deprecated {len(results)} insecure solutions")
```

### Example 3: API Version Migration

```python
# When an API changes
migration_update = """
// Find all solutions using old API
FOR doc IN log_events
    FILTER CONTAINS(doc.resolution, "client.query(")
    
    // Check if already migrated
    LET already_migrated = CONTAINS(doc.resolution, "client.execute_query(")
    
    UPDATE doc WITH {
        needs_review: NOT already_migrated,
        review_reason: "API changed: query() -> execute_query()",
        api_version: "v2.0",
        migration_required: NOT already_migrated
    } IN log_events
    RETURN {
        key: doc._key,
        migrated: already_migrated
    }
"""
```

## Query Patterns for Knowledge Maintenance

### Find Contradictions
```aql
// Find all contradiction chains
FOR v, e, p IN 1..3 ANY "log_events/current_error" error_relationships
    FILTER e.relationship_type == "contradicts"
    RETURN {
        path: p.vertices[*].resolution,
        reasons: p.edges[*].reason
    }
```

### Find Deprecated Solutions Still Being Referenced
```aql
FOR doc IN log_events
    FILTER doc.deprecated == true
    
    // Find incoming edges
    FOR e IN error_relationships
        FILTER e._to == doc._id
        FILTER e.deprecated != true
        
        LET source = DOCUMENT(e._from)
        RETURN {
            deprecated_solution: doc.resolution,
            still_referenced_by: source.resolution,
            edge_type: e.relationship_type
        }
```

### Knowledge Health Check
```aql
LET stats = {
    total_solutions: COUNT(FOR d IN log_events FILTER d.resolved == true RETURN 1),
    deprecated: COUNT(FOR d IN log_events FILTER d.deprecated == true RETURN 1),
    needs_review: COUNT(FOR d IN log_events FILTER d.needs_review == true RETURN 1),
    security_risks: COUNT(FOR d IN log_events FILTER d.security_risk == true RETURN 1),
    recently_confirmed: COUNT(
        FOR d IN log_events 
        FILTER d.confirmed_at > DATE_SUBTRACT(DATE_NOW(), 30, "days")
        RETURN 1
    )
}

RETURN {
    stats: stats,
    health_score: (stats.total_solutions - stats.deprecated - stats.security_risks) / stats.total_solutions * 100,
    review_urgency: stats.needs_review / stats.total_solutions * 100
}
```

## Best Practices

1. **Test Before Deprecating**: Always verify the new solution works before deprecating old ones

2. **Preserve History**: Don't delete - mark as deprecated with clear reasons

3. **Update Edges**: When deprecating, update or deprecate related edges

4. **Bulk Operations**: Use AQL for mass updates when patterns change

5. **Document Contradictions**: Use "contradicts" edges to show why one solution replaces another

6. **Regular Audits**: Run security and deprecation audits periodically

7. **Version Tracking**: Track which API/library versions solutions work with

## The Goal

Build a self-healing knowledge base where:
- Bad solutions get deprecated automatically
- Contradictions get resolved through testing  
- Security issues trigger bulk updates
- Knowledge improves over time
- Every fix makes the system smarter