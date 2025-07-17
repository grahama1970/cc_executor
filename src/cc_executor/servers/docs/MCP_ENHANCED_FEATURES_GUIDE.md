# MCP Enhanced Features Guide

## Advanced Graph Intelligence for Debugging

This guide covers the enhanced features incorporated from ArangoDB's graph and memory modules into our MCP tools.

## 1. Temporal Metadata (Bi-Temporal Model)

### Why It Matters
- **Reference Time**: When the error actually occurred
- **Valid Time**: When the information about the error is valid
- **Current State**: Track what we know now vs. what we knew then

### Usage Pattern

```python
# Insert with temporal metadata
await mcp__arango-tools__insert_temporal(
    document={
        "error_type": "APITimeout",
        "error_message": "Request timed out after 30s",
        "occurred_at": "2024-01-15T10:30:00",  # When it happened
        "resolved": True,
        "resolution": "Increased timeout to 60s"
    },
    reference_time="2024-01-15T10:30:00",  # When error occurred
    valid_until="2024-02-15T10:30:00"      # When fix expires (API update)
)
```

### Query Historical State

```aql
// Find what we knew about timeouts on a specific date
FOR doc IN log_events
    FILTER doc.error_type == "APITimeout"
    FILTER doc._valid_from <= "2024-01-20"
    FILTER doc._valid_until >= "2024-01-20" OR doc._valid_until == null
    RETURN doc
```

## 2. Smart Edge Creation with Contradiction Handling

### Automatic Contradiction Detection

```python
# Create edge that auto-invalidates contradictions
await mcp__arango-tools__create_smart_edge(
    from_id="log_events/new_solution",
    to_id="log_events/old_solution",
    collection="error_relationships",
    relationship_type="supersedes",
    check_contradictions=True,  # Auto-invalidate conflicting edges
    confidence_score=0.95,
    metadata=json.dumps({
        "reason": "New solution handles edge cases",
        "tested": True
    })
)
```

### Relationship Types with Semantics

```python
RELATIONSHIP_TYPES = {
    # Learning relationships
    "inspired_by": "Solution inspired by another fix",
    "similar_to": "Same pattern, different context",
    "uses_technique": "Borrowed specific approach",
    
    # Contradiction relationships  
    "supersedes": "Replaces previous solution",
    "contradicts": "Mutually exclusive approaches",
    "partially_contradicts": "Works in some cases",
    
    # Dependency relationships
    "depends_on": "Requires another fix first",
    "enables": "Makes another solution possible",
    "prerequisite_for": "Must exist before",
    
    # Causal relationships
    "causes": "Directly leads to",
    "triggered_by": "Caused by",
    "correlates_with": "Often occurs together"
}
```

## 3. Semantic Search with Embeddings

### Find Similar Errors Using Natural Language

```python
# Search semantically similar errors
results = await mcp__arango-tools__semantic_search(
    query="subprocess hangs when output buffer fills up",
    error_type="SubprocessTimeout",  # Optional filter
    days_back=90,  # Search last 90 days
    limit=5
)

# Results include similarity scores
for result in results["results"]:
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Error: {result['error_message']}")
    print(f"Fix: {result['resolution']}")
```

### Fallback Strategy
If vector search fails, automatically falls back to BM25 text search.

## 4. Error Community Detection

### Find Clusters of Related Errors

```python
# Discover error communities
communities = await mcp__arango-tools__find_communities()

# Example output:
{
    "communities": [
        {
            "error_type": "FileNotFoundError",
            "size": 15,
            "resolved_ratio": 0.8,
            "members": ["err_123", "err_456", ...]
        },
        {
            "error_type": "ModuleNotFoundError", 
            "size": 8,
            "resolved_ratio": 0.625,
            "members": ["err_789", "err_012", ...]
        }
    ]
}
```

Use communities to:
- Find patterns in error types
- Identify systemic issues
- Apply bulk fixes to related errors

## 5. Debugging Session Storage

### Capture Complete Debugging Context

```python
# Store entire debugging session
await mcp__arango-tools__store_debug_session(
    session_id="debug_12345",
    messages=json.dumps([
        {"role": "user", "content": "Getting FileNotFoundError"},
        {"role": "assistant", "content": "Let me check the path..."},
        {"role": "assistant", "content": "Found issue - using relative path"},
        {"role": "user", "content": "That fixed it!"}
    ]),
    resolved=True,
    metadata=json.dumps({
        "error_type": "FileNotFoundError",
        "resolution": "Changed to absolute path with Path.resolve()",
        "tools_used": ["grep", "read", "edit"],
        "helpful_resources": [
            {"id": "log_events/err_old_similar", "score": 0.9},
            {"id": "scripts/path_utils.py", "score": 0.8}
        ],
        "start_time": "2024-01-15T10:00:00"
    })
)
```

### Search Past Debugging Sessions

```aql
// Find similar debugging sessions
FOR session IN debugging_sessions
    SEARCH APPROX_NEAR_COSINE(session.embedding, @query_embedding, 5)
    FILTER session.error_resolved == true
    RETURN {
        session_id: session.session_id,
        error_type: session.error_type,
        resolution: session.resolution,
        duration: session.duration,
        similarity: SIMILARITY
    }
```

## 6. Advanced Query Patterns

### Multi-Temporal Queries

```aql
// Find solutions that were valid at a specific time
FOR doc IN log_events
    FILTER doc._reference_time <= @point_in_time
    FILTER doc._valid_from <= @point_in_time
    FILTER doc._valid_until >= @point_in_time OR doc._valid_until == null
    FILTER doc.resolved == true
    RETURN doc
```

### Contradiction Chains

```aql
// Trace contradiction history
FOR v, e, p IN 1..5 OUTBOUND @start_solution error_relationships
    FILTER e.relationship_type IN ["contradicts", "supersedes"]
    RETURN {
        path: p.vertices[*].resolution,
        reasons: p.edges[*].metadata.reason,
        confidence: p.edges[*].confidence_score
    }
```

### Knowledge Evolution

```aql
// See how understanding evolved over time
FOR doc IN log_events
    FILTER doc.error_type == @error_type
    SORT doc._created_at ASC
    RETURN {
        time: doc._created_at,
        understanding: doc.resolution,
        valid: doc._is_current,
        invalidated_reason: doc._invalidation_reason
    }
```

## 7. Caching and Performance

### Embedding Cache
- Automatically caches embeddings to avoid recomputation
- LRU eviction when cache exceeds 1000 entries
- Check cache hits in response metadata

### Query Optimization
- Use temporal indexes for time-based queries
- Leverage ArangoDB views for full-text and vector search
- Batch relationship creation for bulk operations

## 8. Best Practices

### 1. Always Use Temporal Metadata
```python
# Bad
await insert({"error": "timeout"})

# Good  
await insert_temporal(
    {"error": "timeout"},
    reference_time=when_it_happened,
    valid_until=when_fix_expires
)
```

### 2. Check Contradictions for Critical Fixes
```python
# For important solutions, always check contradictions
await create_smart_edge(
    from_id=new_fix,
    to_id=old_fix,
    relationship_type="supersedes",
    check_contradictions=True  # Important!
)
```

### 3. Combine Search Methods
```python
# Use semantic search first, fall back to keywords
semantic_results = await semantic_search("buffer overflow in subprocess")
if semantic_results["count"] == 0:
    keyword_results = await query("FOR doc IN log_events FILTER CONTAINS(doc.error_message, 'buffer')")
```

### 4. Store Complete Context
When debugging succeeds, always store the session for future learning.

## 9. Migration from Basic to Enhanced

### Gradual Enhancement
1. Start using `insert_temporal` instead of `insert`
2. Add `check_contradictions=True` to edge creation
3. Implement semantic search for complex queries
4. Store debugging sessions for pattern analysis

### Backward Compatibility
All enhanced functions gracefully degrade:
- Temporal queries work on non-temporal data
- Semantic search falls back to text search
- Edge creation works without contradiction checking

## 10. Comprehensive Logging Infrastructure

### Centralized MCP Logger Utility

Based on production testing, we've created a reusable logging infrastructure that provides:

#### Features
- **Multi-destination logging**: Console (stderr) and file outputs
- **Automatic startup capture**: PID, Python version, environment
- **Call timing and metrics**: Duration tracking for all operations
- **Error context preservation**: Full traceback with context
- **Graceful error handling**: Prevents server crashes
- **Debug decorator**: Automatic logging wrapper

#### Implementation Pattern

```python
# At the top of your MCP server
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Initialize logger
mcp_logger = MCPLogger("your-tool-name")

# Use decorator on all tools
@mcp.tool()
@debug_tool(mcp_logger)
async def your_function(param: str) -> str:
    # Your code here - logging is automatic!
    return result
```

#### Log File Structure

```
~/.claude/mcp_logs/
├── {tool_name}_startup.log    # Server initialization info
├── {tool_name}_errors.log     # Error details with context
├── {tool_name}_calls.jsonl    # Tool call metrics
└── {tool_name}_debug.log      # Comprehensive debug output
```

#### Startup Logging

The logger automatically captures:
```json
{
  "timestamp": "2025-07-17T14:30:00",
  "tool_name": "arango-tools",
  "pid": 12345,
  "python": "/usr/bin/python3",
  "python_version": "3.10.11",
  "working_dir": "/home/user/project",
  "sys_path": [...],
  "env": {
    "MCP_DEBUG": "true",
    "ANTHROPIC_DEBUG": "true",
    "PYTHONPATH": "/home/user/project"
  }
}
```

#### Call Logging

Each tool call is logged with:
```json
{
  "timestamp": "2025-07-17T14:30:00",
  "function": "semantic_search",
  "args": {"query": "subprocess timeout"},
  "success": true,
  "duration_ms": 125.5,
  "result_preview": "Found 5 results..."
}
```

### Best Practices for MCP Logging

1. **Always use the centralized logger**
   ```python
   # Import once at the top
   from utils.mcp_logger import MCPLogger, debug_tool
   mcp_logger = MCPLogger("your-tool")
   ```

2. **Apply decorator to all tools**
   ```python
   @mcp.tool()
   @debug_tool(mcp_logger)  # Order matters!
   async def tool_function():
   ```

3. **Enable debug mode persistently**
   ```bash
   # Add to ~/.zshrc or ~/.bashrc
   export MCP_DEBUG=true
   export ANTHROPIC_DEBUG=true
   ```

4. **Monitor logs in real-time**
   ```bash
   # Watch all MCP logs
   tail -f ~/.claude/mcp_logs/*.log
   
   # Watch specific tool
   tail -f ~/.claude/mcp_logs/arango-tools_debug.log
   ```

5. **Return errors gracefully**
   The debug decorator automatically converts exceptions to JSON responses, preventing server crashes.

### Debugging Workflow with Logs

1. **Check startup succeeded**
   ```bash
   cat ~/.claude/mcp_logs/{tool}_startup.log
   ```

2. **Monitor call patterns**
   ```bash
   # See all calls with timing
   jq . ~/.claude/mcp_logs/{tool}_calls.jsonl
   ```

3. **Investigate errors**
   ```bash
   # View error details
   jq . ~/.claude/mcp_logs/{tool}_errors.log
   ```

4. **Real-time debugging**
   ```bash
   # Watch debug output
   tail -f ~/.claude/mcp_logs/{tool}_debug.log
   ```

## Summary

These enhanced features transform the MCP tool from a simple logger to an intelligent debugging assistant that:
- Tracks how knowledge evolves over time
- Automatically handles contradicting information
- Finds solutions using semantic understanding
- Learns from debugging patterns
- Builds a navigable knowledge graph
- **Provides comprehensive visibility through centralized logging**

The key is to use these features consistently so the system becomes smarter with every debugging session. The logging infrastructure ensures you can always trace what happened, when it happened, and why it happened.