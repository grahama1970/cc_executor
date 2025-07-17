# Technical Glossary Tool Guide

## Overview

The glossary functionality is integrated into the ArangoDB tools (`mcp__arango-tools__*`). It helps agents build a knowledge base of technical terms, concepts, and their relationships. It connects terms to real log events, creating a navigable knowledge graph.

## Why a Glossary?

1. **Term Disambiguation** - Know exactly what "BM25", "deadlock", or "event loop" means
2. **Context Building** - Link terms to real errors and solutions
3. **Knowledge Navigation** - Find related concepts through graph traversal
4. **Learning from Logs** - Connect abstract concepts to concrete examples

## Architecture

```
glossary_terms (document collection)
    ├── term: "subprocess.PIPE"
    ├── definition: "Python constant for capturing subprocess output"
    ├── category: "python"
    ├── examples: ["proc = subprocess.run(..., stdout=subprocess.PIPE)"]
    └── related_errors: ["BufferOverflow", "DeadlockError"]

term_relationships (edge collection)
    ├── glossary_term → glossary_term (concept relationships)
    └── glossary_term → log_event (real-world examples)
```

## Usage Examples

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

### Creating Relationships

```python
# Term to term relationships
await mcp__arango-tools__link_glossary_terms(
    from_term="subprocess.PIPE",
    to_term="deadlock",
    relationship="can_cause",
    context="When output exceeds 64KB buffer and isn't drained"
)

await mcp__arango-tools__link_glossary_terms(
    from_term="asyncio",
    to_term="event loop",
    relationship="implements",
    bidirectional=False
)

# Common relationships:
# - "can_cause" - X can lead to Y
# - "prevents" - X prevents Y  
# - "part_of" - X is component of Y
# - "alternative_to" - X can be used instead of Y
# - "improves_upon" - X is better version of Y
# - "related_to" - General relationship
```

### Linking to Log Events

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

await mcp__arango-tools__link_term_to_log(
    term="deadlock",
    log_id=error_id["key"],
    relationship="example_of",
    context="Classic deadlock scenario"
)
```

### Searching and Navigation

```python
# Search for terms (using standard query with appropriate AQL)
results = await mcp__arango-tools__query("""
    FOR doc IN glossary_terms
        FILTER CONTAINS(LOWER(doc.definition), LOWER(@search)) OR
               CONTAINS(LOWER(doc.term), LOWER(@search))
        LIMIT @limit
        RETURN doc
""", {"search": "buffer process", "limit": 5})

# Get term details
term_details = await mcp__arango-tools__query("""
    FOR doc IN glossary_terms
        FILTER doc.normalized_term == @term
        LIMIT 1
        RETURN doc
""", {"term": "subprocess.pipe"})

# Find related concepts through graph traversal
related = await mcp__arango-tools__query("""
    FOR term IN glossary_terms
        FILTER term.normalized_term == @term
        FOR v, e, p IN 1..@depth ANY term._id term_relationships
            RETURN DISTINCT {
                term: v.term,
                path: p.edges[*].relationship,
                distance: LENGTH(p.edges)
            }
""", {"term": "deadlock", "depth": 2})

# Find logs that mention a term
logs_with_term = await mcp__arango-tools__query("""
    FOR term IN glossary_terms
        FILTER term.normalized_term == @term
        FOR log IN 1..1 OUTBOUND term._id term_relationships
            FILTER log._id LIKE "log_events/%"
            RETURN log
""", {"term": "deadlock"})
```

## Best Practices

### 1. Add Terms as You Learn

When you encounter a new technical term:
```python
# First time seeing "BM25"
await mcp__arango-tools__add_glossary_term(
    term="BM25",
    definition="Probabilistic retrieval function that ranks documents by relevance",
    category="algorithm",
    context="Used in ArangoDB for text search ranking"
)
```

### 2. Link Terms When Solving Errors

```python
# You just fixed a subprocess hanging issue
await mcp__arango-tools__update(
    collection="log_events",
    key=error_id,
    fields={
        "resolved": True,
        "resolution": "Added stream draining to prevent buffer overflow"
    }
)

# Add/update the glossary
await mcp__arango-tools__add_glossary_term(
    term="stream draining",
    definition="Continuously reading from a stream to prevent buffer overflow",
    category="pattern",
    examples=["asyncio.create_task(_drain_stream(proc.stdout, 'STDOUT'))"]
)

# Link everything
await mcp__arango-tools__link_term_to_log("stream draining", error_id, "solution_uses")
await mcp__arango-tools__link_glossary_terms("stream draining", "buffer overflow", "prevents")
```

### 3. Build Concept Hierarchies

```python
# Create a hierarchy
await mcp__arango-tools__link_glossary_terms("Python", "subprocess", "contains")
await mcp__arango-tools__link_glossary_terms("subprocess", "subprocess.PIPE", "contains")
await mcp__arango-tools__link_glossary_terms("subprocess", "subprocess.run", "contains")
await mcp__arango-tools__link_glossary_terms("subprocess", "Popen", "contains")
```

### 4. Categories to Use

- **algorithm** - BM25, cosine similarity, graph traversal
- **python** - subprocess.PIPE, asyncio, pathlib
- **pattern** - stream draining, retry logic, circuit breaker
- **error** - deadlock, race condition, buffer overflow
- **concurrency** - async/await, threading, multiprocessing
- **architecture** - MCP, REST API, event-driven
- **tool** - ripgrep, ArangoDB, git

## Integration with Learning Flow

```python
# 1. Error occurs
error_id = await mcp__arango-tools__insert(
    message="APPROX_NEAR_COSINE function not found",
    error_type="ArangoError"
)

# 2. Research and learn
await mcp__glossary__add_term(
    term="APPROX_NEAR_COSINE",
    definition="ArangoDB function for approximate vector similarity search using cosine distance",
    category="algorithm",
    context="Requires --experimental-vector-index flag and vector index",
    related_errors=["FunctionNotFound", "ExperimentalFeature"]
)

# 3. Find solution
# ... resolve the error ...

# 4. Link everything
await mcp__glossary__link_term_to_log(
    term="APPROX_NEAR_COSINE",
    log_id=error_id,
    relationship="defines",
    context="The function that was missing"
)

# 5. Future searches benefit
# Next time someone searches "vector similarity", they'll find:
# - The term definition
# - The actual error
# - The solution
```

## Graph Queries

The glossary integrates with the knowledge graph:

```aql
// Find all logs that demonstrate a concept
FOR term IN glossary_terms
    FILTER term.term == "deadlock"
    FOR log IN 1..1 OUTBOUND term._id term_relationships
        FILTER log.resolved == true
        RETURN {
            example: log.message,
            solution: log.resolution,
            context: log.fix_rationale
        }

// Find learning path between concepts
FOR v, e, p IN 1..3 ANY "glossary_terms/deadlock" term_relationships
    FILTER v.category == "pattern"
    RETURN DISTINCT {
        concept: v.term,
        path: p.vertices[*].term,
        relationships: p.edges[*].relationship
    }
```

## Benefits

1. **Faster Learning** - Don't re-research the same terms
2. **Better Search** - Terms provide context for BM25 searches
3. **Knowledge Preservation** - Capture understanding as you learn
4. **Context Navigation** - Jump from concept to real examples
5. **Team Knowledge** - Shared understanding of technical terms

## Summary

The glossary tool transforms isolated technical terms into a connected knowledge graph. By linking terms to each other and to real log events, you build a navigable map of technical knowledge grounded in actual debugging experience.