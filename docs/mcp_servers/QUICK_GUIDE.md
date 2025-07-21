# MCP QUICK_GUIDE.md - Agent Task Reference

> **PURPOSE**: Concise reference for agents executing usage functions in `/src/cc_executor/servers/tests/usage_scenarios`  
> **USAGE**: Read this BEFORE each TODO task to understand tools, patterns, and common pitfalls

## 1. Critical Patterns - ALWAYS FOLLOW

### Tool Decorator Pattern (MANDATORY)
```python
@mcp.tool()
@debug_tool(mcp_logger)
async def your_tool_name(...) -> str:
    """Tool documentation."""
    # MUST return JSON string via response_utils
    return create_success_response(data=result)
```

### Response Format (NEVER DEVIATE)
```python
from utils.response_utils import create_success_response, create_error_response

# SUCCESS - even with empty results
return create_success_response(
    data={"count": 0, "results": []},  # Empty is still success!
    tool_name="schema"
)

# ERROR - only for actual failures
return create_error_response(
    error="Connection failed: timeout",
    tool_name="query"
)
```

### File Structure Requirements
```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "mcp>=1.1.0", 
#   "mcp-logger-utils>=0.1.5",
#   "python-arango>=8.1.4"
# ]
# ///
```

## 2. Core Tools Quick Reference

### ArangoDB Operations (mcp_arango_tools)
```python
# Get schema - ALWAYS start here
await mcp__arango_tools__schema()

# Query with bind variables (safer)
await mcp__arango_tools__query(
    aql="FOR doc IN @@collection FILTER doc.type == @type RETURN doc",
    bind_vars='{"@collection": "log_events", "type": "error"}'
)

# Insert document
await mcp__arango_tools__insert(
    message="ImportError in main.py",
    error_type="ImportError",
    metadata='{"file": "main.py", "line": 42}'
)

# Create edge relationship
await mcp__arango_tools__edge(
    from_id="errors/123",
    to_id="solutions/456", 
    collection="error_causality",
    relationship_type="solved_by"
)

# Natural language to AQL
await mcp__arango_tools__english_to_aql(
    query="Find all errors from yesterday"
)
```

### Visualization Preparation
```python
# Get D3-ready data
await mcp__arango_tools__get_visualization_data(
    query_type="network",  # or "timeline", "distribution", "hierarchy", "flow"
    collection="log_events",
    filters='{"error_type": "ImportError"}',
    limit=100
)

# Prepare graph for D3
await mcp__arango_tools__prepare_graph_for_d3(
    graph_name="error_causality",
    max_nodes=500,
    layout_hint="force"  # or "tree", "radial", "sankey"
)
```

### Pattern Analysis
```python
# Find similar errors
await mcp__arango_tools__find_similar_documents(
    document_id="errors/123",
    collection="errors_and_failures",
    similarity_method="vector",  # or "graph", "combined"
    top_k=5
)

# Detect anomalies
await mcp__arango_tools__detect_anomalies(
    collection="log_events",
    method="isolation_forest",
    contamination=0.1
)

# Find clusters
await mcp__arango_tools__find_clusters(
    edge_collection="pattern_similarity",
    algorithm="louvain",
    min_community_size=3
)
```

### Learning & Journey Tracking
```python
# Start a learning journey
journey = await mcp__tool_journey__start_journey(
    task_description="Debug ImportError in pandas import",
    context='{"error_type": "ImportError", "file": "analyzer.py"}'
)

# Record tool usage
await mcp__tool_journey__record_tool_step(
    journey_id=journey["data"]["journey_id"],
    tool_name="mcp_arango_tools.query",
    success=True,
    duration_ms=150
)

# Complete with outcome
await mcp__tool_journey__complete_journey(
    journey_id=journey["data"]["journey_id"],
    outcome="success",
    solution_description="Added pandas to requirements.txt"
)
```

## 3. Common Workflow Patterns

### Pattern 1: Error → Solution → Learn
```python
# 1. Find similar errors
similar = await mcp__arango_tools__find_similar_documents(
    document_id="current_error_id",
    similarity_method="combined"
)

# 2. If found, get solutions
if similar["data"]["count"] > 0:
    solutions = await mcp__arango_tools__query(
        aql="FOR s IN solutions FILTER s.error_id IN @ids RETURN s",
        bind_vars=json.dumps({"ids": [doc["_id"] for doc in similar["data"]["documents"]]})
    )

# 3. Record successful fix
await mcp__arango_tools__edge(
    from_id="errors/current",
    to_id="solutions/new",
    collection="error_causality",
    relationship_type="solved_by"
)
```

### Pattern 2: Visualize → Analyze → Optimize
```python
# 1. Get visualization recommendation
advice = await mcp__d3_visualization_advisor__analyze_and_recommend_visualization(
    data_description="Error frequency by type over time",
    data_sample='[{"type": "ImportError", "count": 45, "date": "2024-01-01"}]'
)

# 2. Prepare data for recommended type
viz_data = await mcp__arango_tools__get_visualization_data(
    query_type=advice["data"]["primary_recommendation"]["type"],
    collection="errors_and_failures"
)

# 3. Generate visualization
html = await mcp__d3_visualizer__generate_intelligent_visualization(
    data=json.dumps(viz_data["data"]),
    title="Error Pattern Analysis"
)
```

### Pattern 3: Multi-Step Solution Validation
```python
# 1. Query for resolved errors with solutions
errors = await mcp__arango_tools__query(
    aql="""FOR error IN errors_and_failures
      FILTER error.resolved == true
      LET solution = (
        FOR v IN 1..1 OUTBOUND error._id error_causality
          FILTER v.fix_description != null
          RETURN v
      )[0]
      RETURN {error: error, solution: solution}""",
)

# 2. Apply and track solution outcome
outcome = await mcp__arango_tools__upsert(
    collection="solution_outcomes",
    search='{"solution_id": "log_events/123", "error_id": "errors/456"}',
    update='{"outcome": "success", "success_score": 1.0, "time_to_fix_seconds": 45}',
    create='{"error_type": "ImportError", "solution_type": "package_install"}'
)

# 3. Calculate effectiveness metrics
metrics = await mcp__arango_tools__query(
    aql="""LET outcomes = (
      FOR o IN solution_outcomes
        FILTER o.error_type == @type
        COLLECT outcome = o.outcome WITH COUNT INTO count
        RETURN {outcome: outcome, count: count}
    )
    RETURN {
      success_rate: outcomes[?outcome == "success"][0].count / SUM(outcomes[*].count),
      total_applied: SUM(outcomes[*].count)
    }""",
    bind_vars='{"type": "ImportError"}'
)

# 4. Update lessons learned
await mcp__arango_tools__upsert(
    collection="lessons_learned",
    search='{"category": "solution_validation", "applies_to": ["ImportError"]}',
    update='{"lesson": "Package install solutions have high success rate", "confidence": 0.95}'
)
```

## 4. Critical Gotchas & Solutions

### Empty Results Are SUCCESS
```python
# WRONG ❌
if result["count"] == 0:
    return create_error_response(error="No data found")

# RIGHT ✅  
return create_success_response(
    data={"count": 0, "results": []},
    tool_name="query"
)
```

### Always Use Bind Variables
```python
# WRONG ❌ - SQL injection risk
aql = f"FOR doc IN {collection} FILTER doc.id == '{user_input}' RETURN doc"

# RIGHT ✅ - Safe parameterization
await mcp__arango_tools__query(
    aql="FOR doc IN @@col FILTER doc.id == @id RETURN doc",
    bind_vars='{"@col": "users", "id": "user123"}'
)
```

### Check Collection Existence
```python
# Get schema first
schema = await mcp__arango_tools__schema()
collections = [c["name"] for c in schema["data"]["collections"]]

if "my_collection" not in collections:
    # Collection doesn't exist - handle appropriately
    pass
```

### Handle Large Result Sets
```python
# Use LIMIT for large collections
await mcp__arango_tools__query(
    aql="FOR doc IN large_collection LIMIT 1000 RETURN doc"
)

# Or use streaming for visualization
await mcp__arango_tools__get_visualization_data(
    query_type="network",
    collection="huge_graph",
    limit=500  # D3 performance limit
)
```

## 5. Usage Scenario Execution Checklist

When executing scenarios from `/tests/usage_scenarios/`:

1. **Read scenario goal** - Understand what you're testing
2. **Check schema first** - Verify collections/graphs exist
3. **Plan tool sequence** - List exact MCP calls needed
4. **Execute with validation** - Verify each step succeeds
5. **Handle failures properly** - Empty results ≠ error
6. **Update journey** - Record what worked for future learning

## 6. Quick Debugging Commands

```python
# Check if ArangoDB is accessible
schema = await mcp__arango_tools__schema()
print(f"Collections: {len(schema['data']['collections'])}")

# Verify collection has data
result = await mcp__arango_tools__query(
    aql="FOR doc IN @@col COLLECT WITH COUNT INTO length RETURN length",
    bind_vars='{"@col": "log_events"}'
)

# Test natural language query
aql = await mcp__arango_tools__english_to_aql(
    query="Show me the last 5 errors"
)
print(f"Generated AQL: {aql['data']['aql']}")

# Check similarity search readiness
similar = await mcp__arango_tools__find_similar_documents(
    document_id="test_doc",
    collection="log_events"
)
```

## 7. Performance Tips

- **Lazy Loading**: Heavy ML models load on first use, not import
- **Use streaming**: For result sets > 10k documents  
- **Limit visualizations**: D3 performs poorly > 1000 nodes
- **Cache patterns**: Similar document searches are expensive
- **Batch operations**: Use upsert for bulk updates

## Remember: Tools Work Together

The MCP system is designed for **orchestration**. Don't use tools in isolation - combine them:

1. **mcp_tool_journey** → tracks your learning path
2. **mcp_arango_tools** → stores and queries knowledge  
3. **mcp_d3_visualizer** → visualizes patterns
4. **mcp_debugging_assistant** → orchestrates complex workflows
5. **mcp_outcome_adjudicator** → determines success/failure

---

**FINAL TIP**: When in doubt, check the schema first and use empty results as success!