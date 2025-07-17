# ArangoDB MCP Tools - Complete Usage Guide

This guide covers all functionality of the ArangoDB MCP tools including schema inspection, queries, CRUD operations, glossary management, and error recovery with research capabilities.

## Overview

The ArangoDB MCP tools (`mcp__arango-tools__*`) provide:
- Database schema inspection
- AQL query execution with error recovery
- Document and edge CRUD operations
- Technical glossary management
- Automatic research suggestions using context7 and perplexity
- Natural language to AQL conversion

## Core Tools

### 1. Schema Inspection

```python
# Get complete database schema
schema = await mcp__arango-tools__schema()

# Returns:
# - Collections (document and edge)
# - Views and their configurations
# - Graphs and relationships
# - Sample documents
# - Common query patterns
```

### 2. Query Execution with Error Recovery

```python
# Basic query
result = await mcp__arango-tools__query(
    "FOR doc IN log_events LIMIT 5 RETURN doc"
)

# Query with bind variables
result = await mcp__arango-tools__query(
    "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
    {"@col": "log_events", "level": "ERROR"}
)

# When queries fail, you automatically get:
# - Error-specific suggestions
# - Research recommendations using context7 for AQL docs
# - Perplexity-ask prompts for specific errors
# - Cached solutions from previous similar errors
```

**Error Recovery Example:**
```python
# If your query fails with an unknown function error:
result = await mcp__arango-tools__query(
    "FOR doc IN items RETURN APPROX_NEAR_COSINE(doc.vector, @target)"
)

# The result will include:
{
    "success": false,
    "error": "unknown function 'APPROX_NEAR_COSINE'",
    "use_these_tools": {
        "for_aql_syntax": "await mcp__context7__resolve-library-id('arangodb') then get-library-docs with topic='aql'",
        "for_error_research": "await mcp__perplexity-ask__perplexity_ask with the error context",
        "for_terms": "await mcp__arango-tools__query to search glossary_terms"
    },
    "recovery_steps": [
        "1. Check glossary for any unfamiliar terms in the error",
        "2. Use context7 to get official AQL documentation if syntax-related",
        "3. Use perplexity-ask for specific error code research if needed",
        "4. Update glossary with new terms discovered",
        "5. Link solution to this error for future reference"
    ]
}
```

### 3. Natural Language to AQL

```python
# Convert English to AQL
pattern = await mcp__arango-tools__english_to_aql(
    "find similar resolved scripts"
)

# Execute the generated query
result = await mcp__arango-tools__query(
    pattern["aql"],
    pattern["bind_vars"]
)

# Supported patterns:
# - "find similar errors/scripts/bugs"
# - "find resolved/fixed errors"
# - "recent errors from last hour/day"
# - "count by type/level/field"
# - "find related/connected items"
```

## CRUD Operations

### Document Operations

```python
# Insert a log event
doc = await mcp__arango-tools__insert(
    message="Process completed successfully",
    level="INFO",
    script_name="data_processor.py",
    execution_id="exec_12345",
    duration=45.3,
    metadata='{"rows_processed": 1000}'
)

# Update a document
await mcp__arango-tools__update(
    collection="log_events",
    key=doc["key"],
    fields={
        "resolved": True,
        "resolution": "Fixed by updating dependencies",
        "resolved_at": "2024-01-15T10:30:00Z"
    }
)

# Upsert (update or create)
await mcp__arango-tools__upsert(
    collection="script_runs",
    search={"script_name": "test.py"},
    update={"last_run": "2024-01-15", "run_count": 5},
    create={"first_run": "2024-01-01"}  # Used only if creating new
)

# Get a document
doc = await mcp__arango-tools__get("log_events", "12345")

# Delete a document
await mcp__arango-tools__delete("log_events", "12345")
```

### Edge Operations

```python
# Create an edge between documents
await mcp__arango-tools__edge(
    from_id="log_events/error_123",
    to_id="log_events/fix_456",
    collection="error_causality",
    relationship_type="fixed_by",
    fix_time_minutes=30,
    metadata='{"confidence": 0.95}'
)

# Common edge collections:
# - error_causality: Links errors to their fixes
# - agent_flow: Tracks agent execution flow
# - script_dependencies: Maps script relationships
# - term_relationships: Glossary term connections
```

## Glossary Management

### Adding Terms

```python
# Basic term
await mcp__arango-tools__add_glossary_term(
    term="BM25",
    definition="Best Match 25 - probabilistic ranking function used in information retrieval",
    category="algorithm"
)

# Term with full context
await mcp__arango-tools__add_glossary_term(
    term="subprocess.PIPE",
    definition="Python constant that creates a pipe for subprocess I/O. Has 64KB buffer limit.",
    category="python",
    context="Used with subprocess.run() to capture stdout/stderr",
    examples=[
        "proc = subprocess.run(['ls'], stdout=subprocess.PIPE)",
        "# WARNING: Can deadlock if buffer fills!"
    ],
    aliases=["PIPE", "subprocess pipe"],
    tags=["subprocess", "io", "buffer"],
    related_errors=["SubprocessDeadlock", "BufferOverflow"]
)
```

### Creating Term Relationships

```python
# Link related terms
await mcp__arango-tools__link_glossary_terms(
    from_term="subprocess.PIPE",
    to_term="deadlock",
    relationship="can_cause",
    context="When output exceeds 64KB buffer and isn't drained"
)

# Common relationships:
# - "can_cause": X can lead to Y
# - "prevents": X prevents Y  
# - "part_of": X is component of Y
# - "alternative_to": X can be used instead of Y
# - "improves_upon": X is better version of Y
# - "related_to": General relationship
```

### Linking Terms to Logs

```python
# When you encounter a term in an error
error_id = await mcp__arango-tools__insert(
    message="subprocess.Popen hangs when output exceeds PIPE buffer",
    error_type="SubprocessHang"
)

# Link the technical terms
await mcp__arango-tools__link_term_to_log(
    term="subprocess.PIPE",
    log_id=error_id["key"],
    relationship="mentioned_in",
    context="The component causing the hang"
)
```

## Complete Usage Scenarios

### Scenario 1: Debugging Unknown AQL Function Error

```python
# 1. Query fails with unknown function
result = await mcp__arango-tools__query("""
    FOR doc IN vectors
    RETURN APPROX_NEAR_COSINE(doc.embedding, [0.1, 0.2, 0.3])
""")

# 2. Follow the recovery suggestions
# First, check context7 for AQL documentation
context7_id = await mcp__context7__resolve-library-id("arangodb")
docs = await mcp__context7__get-library-docs(
    context7_id, 
    topic="vector search functions"
)

# 3. Research with perplexity if needed
research = await mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"ArangoDB error: {result['error']}. How do I use vector search functions in ArangoDB 3.11?"
    }]
})

# 4. Add newfound knowledge to glossary
await mcp__arango-tools__add_glossary_term(
    term="APPROX_NEAR_COSINE",
    definition="ArangoDB function for approximate vector similarity search using cosine distance",
    category="algorithm",
    context="Requires ArangoSearch view with vector index. Available in 3.11+ with experimental features enabled",
    examples=["FOR doc IN myView SEARCH APPROX_NEAR_COSINE(doc.vector, @target, 10) RETURN doc"],
    related_errors=["FunctionNotFound", "ExperimentalFeature"]
)

# 5. Link to the original error for future reference
await mcp__arango-tools__link_term_to_log(
    term="APPROX_NEAR_COSINE",
    log_id=error_id,
    relationship="solution_for",
    context="The missing function that caused the error"
)
```

### Scenario 2: Building Knowledge Graph from Errors

```python
# 1. Log an error when it occurs
error_id = await mcp__arango-tools__insert(
    message="ModuleNotFoundError: No module named 'pandas'",
    level="ERROR",
    error_type="ModuleNotFoundError",
    script_name="data_analyzer.py",
    resolved=False
)

# 2. Search for similar resolved errors
similar_fixes = await mcp__arango-tools__query("""
    FOR doc IN log_events
        FILTER doc.error_type == "ModuleNotFoundError"
        FILTER doc.resolved == true
        RETURN {
            error: doc.message,
            fix: doc.resolution,
            rationale: doc.fix_rationale
        }
""")

# 3. Fix the error and update the log
await mcp__arango-tools__update(
    collection="log_events",
    key=error_id["key"],
    fields={
        "resolved": True,
        "resolution": "Added pandas to pyproject.toml dependencies and ran uv sync",
        "fix_rationale": "Module was missing from project dependencies"
    }
)

# 4. Create edges to helpful resources
if similar_fixes["data"]:
    helpful_fix = similar_fixes["data"][0]
    await mcp__arango-tools__edge(
        from_id=f"log_events/{error_id['key']}",
        to_id=helpful_fix["_id"],
        collection="error_causality",
        relationship_type="inspired_by",
        metadata='{"helpfulness": 0.9}'
    )

# 5. Add or update glossary terms
await mcp__arango-tools__add_glossary_term(
    term="uv sync",
    definition="Command to synchronize Python dependencies from pyproject.toml",
    category="tool",
    context="Resolves and installs all dependencies defined in the project",
    examples=["uv sync", "uv sync --dev"],
    related_errors=["ModuleNotFoundError", "ImportError"]
)
```

### Scenario 3: Analyzing Error Patterns

```python
# 1. Find common error types
error_stats = await mcp__arango-tools__query("""
    FOR doc IN log_events
        FILTER doc.error_type != null
        COLLECT error_type = doc.error_type WITH COUNT INTO count
        SORT count DESC
        RETURN {
            error_type: error_type,
            count: count
        }
""")

# 2. Find unresolved errors of the most common type
if error_stats["data"]:
    most_common = error_stats["data"][0]["error_type"]
    
    unresolved = await mcp__arango-tools__query("""
        FOR doc IN log_events
            FILTER doc.error_type == @error_type
            FILTER doc.resolved != true
            RETURN doc
    """, {"error_type": most_common})

# 3. Find successful fix patterns using graph traversal
fix_patterns = await mcp__arango-tools__query("""
    FOR error IN log_events
        FILTER error.error_type == @error_type
        FILTER error.resolved == true
        
        // Find all related fixes within 2 hops
        FOR v, e, p IN 1..2 OUTBOUND error error_causality
            FILTER e.relationship_type IN ["fixed_by", "inspired_by", "similar_pattern"]
            RETURN DISTINCT {
                original_error: error.message,
                fix_approach: error.resolution,
                related_fixes: p.vertices[*].resolution,
                relationship_chain: p.edges[*].relationship_type
            }
""", {"error_type": most_common})
```

### Scenario 4: Research and Cache Pattern

```python
# 1. Encounter a complex error
error_info = {
    "error": "AQL: collection or view not found",
    "error_code": 1203,
    "aql": "FOR doc IN non_existent_view RETURN doc",
    "collection": "non_existent_view"
}

# 2. The query tool automatically provides research suggestions
result = await mcp__arango-tools__query(
    error_info["aql"]
)
# Result includes research_help with tool suggestions

# 3. Follow the research workflow
# Check glossary for terms
glossary_check = await mcp__arango-tools__query("""
    FOR term IN glossary_terms
        FILTER "view" IN term.tags OR CONTAINS(term.definition, "view")
        RETURN term
""")

# Use context7 for official docs
arangodb_id = await mcp__context7__resolve-library-id("arangodb")
view_docs = await mcp__context7__get-library-docs(
    arangodb_id,
    topic="arangosearch views"
)

# Research with perplexity for specific error
research_result = await mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"ArangoDB error code 1203: {error_info['error']}. How do I create and use ArangoSearch views?"
    }]
})

# 4. Solution found - create the view
create_view = await mcp__arango-tools__query("""
    // This would be the actual view creation AQL
    // Just showing the pattern here
""")

# 5. Document the solution in glossary
await mcp__arango-tools__add_glossary_term(
    term="ArangoSearch View",
    definition="Full-text search view that indexes documents for efficient text queries",
    category="database",
    context="Must be created before querying. Uses analyzers for text processing.",
    examples=[
        "CREATE VIEW myView TYPE 'arangosearch'",
        "FOR doc IN myView SEARCH ANALYZER(...)"
    ],
    related_errors=["CollectionNotFound", "ViewNotFound"]
)
```

## Advanced Patterns

### Finding Solutions Through Graph Traversal

```python
# Find non-obvious solutions through relationship chains
solutions = await mcp__arango-tools__query("""
    // Start from your specific error
    FOR error IN log_events
        FILTER error._key == @error_key
        
        // Traverse up to 3 hops through various relationships
        FOR v, e, p IN 1..3 ANY error 
            error_causality, term_relationships
            OPTIONS {uniqueVertices: 'global'}
            
            // Only follow helpful paths
            FILTER e.helpfulness_score == null OR e.helpfulness_score > 0.7
            
            // Get resolved errors or glossary terms
            FILTER (v.resolved == true) OR (v._id LIKE "glossary_terms/%")
            
            RETURN DISTINCT {
                type: v._id LIKE "glossary_terms/%" ? "term" : "solution",
                content: v._id LIKE "glossary_terms/%" ? v.definition : v.resolution,
                path: p.edges[*].relationship_type,
                distance: LENGTH(p.edges)
            }
""", {"error_key": "current_error_key"})
```

### Semantic Search with BM25

```python
# Use the agent_activity_search view for semantic search
semantic_results = await mcp__arango-tools__query("""
    FOR doc IN agent_activity_search
        SEARCH ANALYZER(doc.message IN TOKENS(@search_terms, 'text_en'), 'text_en')
        LET score = BM25(doc)
        FILTER score > @threshold
        SORT score DESC
        LIMIT @limit
        RETURN {
            message: doc.message,
            score: score,
            type: doc.error_type,
            resolved: doc.resolved,
            resolution: doc.resolution
        }
""", {
    "search_terms": "subprocess timeout hanging buffer",
    "threshold": 0.3,
    "limit": 10
})
```

## Best Practices

1. **Always Update Resolved Errors**: When you fix an error, update it with resolution details
2. **Create Edges**: Link errors to solutions, similar patterns, and helpful resources
3. **Build Glossary**: Add technical terms as you encounter them
4. **Use Graph Traversal**: Find non-obvious solutions through relationship chains
5. **Cache Research**: Research results are automatically cached for 7 days
6. **Follow Recovery Workflow**: Use the suggested tools when queries fail

## Summary

The ArangoDB MCP tools provide a complete solution for:
- Database operations and queries
- Building a knowledge graph of errors and solutions
- Managing technical glossary with relationships
- Automatic error recovery with research suggestions
- Finding solutions through graph traversal

By combining these tools with context7 for documentation and perplexity for research, you have a comprehensive system for learning from errors and building institutional knowledge.