# Comprehensive MCP Tools Guide: ArangoDB & D3 Visualizer

## Table of Contents
1. [Overview](#overview)
2. [D3 Visualizer Tools](#d3-visualizer-tools)
3. [ArangoDB Tools](#arangodb-tools)
4. [Usage Scenarios](#usage-scenarios)
5. [Error Recovery Patterns](#error-recovery-patterns)
6. [Tool Status](#tool-status)

---

## Overview

This guide covers all MCP tools available in:
- `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_d3_visualizer.py`
- `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_arango_tools.py`
- `/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_arango_crud.py` (not currently active)

### MCP Configuration
```json
{
  "arango-tools": {
    "command": "uv",
    "args": ["--directory", "/home/graham/workspace/experiments/cc_executor", "run", "--script", "src/cc_executor/servers/mcp_arango_tools.py"],
    "env": {
      "ARANGO_HOST": "localhost",
      "ARANGO_PORT": "8529",
      "ARANGO_DATABASE": "logger_agent"
    }
  },
  "d3-visualizer": {
    "command": "uv",
    "args": ["--directory", "/home/graham/workspace/experiments/cc_executor", "run", "--script", "src/cc_executor/servers/mcp_d3_visualizer.py"],
    "env": {
      "D3_OUTPUT_DIR": "/tmp/visualizations",
      "VIZ_SERVER_URL": "http://localhost:8000"
    }
  }
}
```

---

## D3 Visualizer Tools

### 1. generate_graph_visualization

**Purpose**: Generate interactive D3.js graph visualizations in HTML format.

**Parameters**:
- `graph_data` (string): JSON string with 'nodes' and 'links' keys
- `layout` (string): Visualization layout - "force", "tree", "radial", or "sankey"
- `title` (string): Title for the visualization
- `config` (string, optional): JSON string with configuration options

**Agent Call**:
```python
result = await mcp__d3-visualizer__generate_graph_visualization(
    graph_data=json.dumps({
        "nodes": [
            {"id": "error_1", "group": "error", "label": "ImportError"},
            {"id": "fix_1", "group": "fix", "label": "Add missing import"},
            {"id": "agent_1", "group": "agent", "label": "Debug Agent"}
        ],
        "links": [
            {"source": "agent_1", "target": "error_1", "value": 1, "type": "encounters"},
            {"source": "agent_1", "target": "fix_1", "value": 2, "type": "applies"},
            {"source": "fix_1", "target": "error_1", "value": 3, "type": "resolves"}
        ]
    }),
    layout="force",
    title="Error Resolution Graph",
    config=json.dumps({
        "width": 1200,
        "height": 800,
        "nodeRadius": 15,
        "linkDistance": 100,
        "chargeStrength": -300,
        "colors": {
            "error": "#ff6b6b",
            "fix": "#5f27cd",
            "agent": "#4ecdc4"
        }
    })
)
```

**Raw Response**:
```json
{
  "success": true,
  "filepath": "/tmp/visualizations/force_20250716_183833_18bcb6b2.html",
  "filename": "force_20250716_183833_18bcb6b2.html",
  "layout": "force",
  "title": "Error Resolution Graph",
  "server_generated": false,
  "url": "file:///tmp/visualizations/force_20250716_183833_18bcb6b2.html",
  "node_count": 3,
  "link_count": 3
}
```

**Self-Recovery**:
```python
# If visualization fails
if not result.get("success"):
    # Try with minimal config
    result = await mcp__d3-visualizer__generate_graph_visualization(
        graph_data=graph_data,
        layout="force",  # Default to force layout
        title="Fallback Visualization"
        # Omit config for defaults
    )
    
# If still failing, check data format
if not result.get("success"):
    # Validate JSON structure
    try:
        data = json.loads(graph_data)
        if "nodes" not in data or "links" not in data:
            # Fix structure
            graph_data = json.dumps({
                "nodes": data.get("nodes", []),
                "links": data.get("links", data.get("edges", []))
            })
    except:
        # Create minimal valid graph
        graph_data = json.dumps({
            "nodes": [{"id": "1", "label": "Node"}],
            "links": []
        })
```

### 2. list_visualizations

**Purpose**: List all generated visualization files.

**Parameters**: None

**Agent Call**:
```python
result = await mcp__d3-visualizer__list_visualizations()
```

**Raw Response**:
```json
{
  "success": true,
  "visualizations": [
    {
      "filename": "force_20250716_183833_18bcb6b2.html",
      "path": "/tmp/visualizations/force_20250716_183833_18bcb6b2.html",
      "size": 52453,
      "created": "2025-07-16T18:38:33",
      "layout": "force",
      "title": "Error Resolution Graph"
    },
    {
      "filename": "tree_20250716_184106_83c98b1e.html",
      "path": "/tmp/visualizations/tree_20250716_184106_83c98b1e.html",
      "size": 48221,
      "created": "2025-07-16T18:41:06",
      "layout": "tree",
      "title": "Hierarchy Visualization"
    }
  ],
  "count": 2,
  "total_size": 100674
}
```

### 3. visualize_arango_graph

**Purpose**: Visualize an ArangoDB graph directly.

**Parameters**:
- `graph_name` (string): Name of the ArangoDB graph
- `collection` (string): Collection to visualize nodes from (default: "log_events")
- `max_nodes` (integer): Maximum nodes to include (default: 50)
- `layout` (string): Visualization layout (default: "force")
- `title` (string, optional): Custom title

**Agent Call**:
```python
result = await mcp__d3-visualizer__visualize_arango_graph(
    graph_name="claude_agent_observatory",
    collection="errors_and_failures",
    max_nodes=30,
    layout="radial",
    title="Error Network Analysis"
)
```

**Raw Response**:
```json
{
  "success": true,
  "message": "Generated radial visualization of claude_agent_observatory",
  "filepath": "/tmp/visualizations/radial_20250716_190000_abc123.html",
  "node_count": 30,
  "edge_count": 45,
  "data_source": "ArangoDB"
}
```

---

## ArangoDB Tools

### 1. get_schema

**Purpose**: Retrieve database schema including collections, graphs, and views.

**Parameters**: None

**Agent Call**:
```python
result = await mcp__arango-tools__get_schema()
```

**Raw Response**:
```json
{
  "success": true,
  "database": "logger_agent",
  "collections": [
    {"name": "log_events", "type": "document", "count": 365410},
    {"name": "errors_and_failures", "type": "document", "count": 89},
    {"name": "agent_sessions", "type": "document", "count": 12},
    {"name": "error_causality", "type": "edge", "count": 134}
  ],
  "graphs": [
    {
      "name": "claude_agent_observatory",
      "edge_collections": [
        {
          "edge_collection": "error_causality",
          "from_vertex_collections": ["errors_and_failures"],
          "to_vertex_collections": ["agent_insights", "code_artifacts"]
        }
      ]
    }
  ],
  "views": ["agent_activity_search"],
  "summary": {
    "total_collections": 20,
    "document_collections": 11,
    "edge_collections": 9,
    "total_documents": 365632
  }
}
```

### 2. execute_aql

**Purpose**: Execute arbitrary AQL queries.

**Parameters**:
- `aql` (string): The AQL query to execute
- `bind_vars` (string, optional): JSON string of bind variables

**Agent Call**:
```python
result = await mcp__arango-tools__execute_aql(
    aql="""
    FOR doc IN log_events
        FILTER doc.level == @level
        FILTER doc.timestamp > DATE_SUBTRACT(DATE_NOW(), 1, "hour")
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN {
            id: doc._id,
            message: doc.message,
            error_type: doc.error_type,
            timestamp: doc.timestamp
        }
    """,
    bind_vars=json.dumps({
        "level": "ERROR",
        "limit": 10
    })
)
```

**Raw Response**:
```json
{
  "success": true,
  "results": [
    {
      "id": "log_events/365410",
      "message": "ModuleNotFoundError: No module named 'pandas'",
      "error_type": "ModuleNotFoundError",
      "timestamp": "2025-07-16T18:45:23.123Z"
    }
  ],
  "count": 10,
  "execution_time": 0.023,
  "cached": false
}
```

**Self-Recovery**:
```python
# If AQL syntax error
if not result.get("success") and "syntax error" in result.get("error", ""):
    # Try simpler query
    result = await mcp__arango-tools__execute_aql(
        aql="FOR doc IN log_events LIMIT 10 RETURN doc"
    )
    
# If collection not found
if "collection or view not found" in result.get("error", ""):
    # Get schema first
    schema = await mcp__arango-tools__get_schema()
    collections = [c["name"] for c in schema["collections"]]
    # Use valid collection
    result = await mcp__arango-tools__execute_aql(
        aql=f"FOR doc IN {collections[0]} LIMIT 10 RETURN doc"
    )
```

### 3. upsert_document

**Purpose**: Insert or update a document in a collection.

**Parameters**:
- `collection` (string): Collection name
- `document` (string): JSON string of the document
- `key` (string, optional): Document key for updates

**Agent Call**:
```python
result = await mcp__arango-tools__upsert_document(
    collection="agent_insights",
    document=json.dumps({
        "insight": "Always check for circular imports in ModuleNotFoundError",
        "category": "debugging",
        "confidence": 0.95,
        "derived_from": ["log_events/365410", "log_events/365320"],
        "created_at": datetime.now().isoformat()
    }),
    key="insight_circular_imports"
)
```

**Raw Response**:
```json
{
  "success": true,
  "operation": "insert",
  "id": "agent_insights/insight_circular_imports",
  "key": "insight_circular_imports",
  "rev": "_dKj3KPa--_"
}
```

### 4. search_logs

**Purpose**: Search log events with filters.

**Parameters**:
- `query` (string): Search query
- `level` (string, optional): Log level filter
- `start_time` (string, optional): ISO timestamp for start
- `end_time` (string, optional): ISO timestamp for end
- `limit` (integer, optional): Maximum results

**Note**: This method doesn't exist in the current implementation. Use execute_aql instead:

**Alternative Agent Call**:
```python
# Since search_logs doesn't exist, use execute_aql
result = await mcp__arango-tools__execute_aql(
    aql="""
    FOR doc IN log_events
        FILTER CONTAINS(LOWER(doc.message), LOWER(@query))
        FILTER doc.level == @level
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN doc
    """,
    bind_vars=json.dumps({
        "query": "import error",
        "level": "ERROR",
        "limit": 20
    })
)
```

### 5. add_glossary_term

**Purpose**: Add a technical term to the glossary.

**Parameters**:
- `term` (string): The term to add
- `definition` (string): Clear definition
- `category` (string, optional): Category like "errors", "patterns"
- `examples` (string, optional): JSON array of usage examples
- `related_terms` (string, optional): JSON array of related terms

**Agent Call**:
```python
result = await mcp__arango-tools__add_glossary_term(
    term="Circular Import",
    definition="When two or more modules import each other, creating a dependency loop",
    category="errors",
    examples=json.dumps([
        "module_a imports module_b, and module_b imports module_a",
        "from .models import User in views.py, and from .views import user_view in models.py"
    ]),
    related_terms=json.dumps(["ImportError", "ModuleNotFoundError", "dependency cycle"])
)
```

**Raw Response**:
```json
{
  "success": true,
  "term": "Circular Import",
  "normalized_term": "circular_import",
  "id": "glossary_terms/circular_import",
  "message": "Added term 'Circular Import' to glossary"
}
```

### 6. link_glossary_terms

**Purpose**: Create semantic relationships between glossary terms.

**Parameters**:
- `from_term` (string): Source term
- `to_term` (string): Target term
- `relationship` (string): Type of relationship
- `bidirectional` (boolean, optional): Create reverse link
- `context` (string, optional): Additional context

**Agent Call**:
```python
result = await mcp__arango-tools__link_glossary_terms(
    from_term="Circular Import",
    to_term="ImportError",
    relationship="causes",
    bidirectional=True,
    context="Circular imports often manifest as ImportError at runtime"
)
```

**Raw Response**:
```json
{
  "success": true,
  "from_term": "Circular Import",
  "to_term": "ImportError",
  "relationship": "causes",
  "message": "Linked 'Circular Import' --[causes]--> 'ImportError'"
}
```

### 7. link_term_to_log

**Purpose**: Link a glossary term to a specific log event.

**Parameters**:
- `term` (string): Glossary term
- `log_id` (string): Log event ID
- `relationship` (string, optional): Relationship type
- `context` (string, optional): Why this link exists

**Agent Call**:
```python
result = await mcp__arango-tools__link_term_to_log(
    term="Circular Import",
    log_id="log_events/365410",
    relationship="exemplifies",
    context="This error demonstrates a classic circular import pattern"
)
```

### 8. analyze_graph

**Purpose**: Run graph analysis algorithms.

**Parameters**:
- `graph_name` (string): Name of the graph
- `algorithm` (string): Algorithm to run
- `params` (string, optional): JSON string of algorithm parameters

**Supported Algorithms**:
1. **centrality** - Find most connected nodes
2. **shortest_path** - Find path between nodes
3. **connected_components** - Find graph clusters
4. **neighbors** - Explore node neighborhoods

**Agent Calls**:

```python
# 1. Centrality Analysis
result = await mcp__arango-tools__analyze_graph(
    graph_name="claude_agent_observatory",
    algorithm="centrality"
)

# 2. Shortest Path
result = await mcp__arango-tools__analyze_graph(
    graph_name="claude_agent_observatory",
    algorithm="shortest_path",
    params=json.dumps({
        "start_node": "errors_and_failures/error_123",
        "end_node": "agent_insights/insight_456"
    })
)

# 3. Connected Components
result = await mcp__arango-tools__analyze_graph(
    graph_name="claude_agent_observatory",
    algorithm="connected_components"
)

# 4. Neighbors
result = await mcp__arango-tools__analyze_graph(
    graph_name="claude_agent_observatory",
    algorithm="neighbors",
    params=json.dumps({
        "node": "tool_executions/exec_789",
        "depth": 2,
        "direction": "OUTBOUND"  # or "INBOUND", "ANY"
    })
)
```

**Raw Responses**:

```json
// Centrality
{
  "success": true,
  "algorithm": "centrality",
  "top_nodes": [
    {
      "vertex": "tool_executions/exec_123",
      "total_connections": 15,
      "in_degree": 5,
      "out_degree": 10
    }
  ]
}

// Shortest Path
{
  "success": true,
  "algorithm": "shortest_path",
  "path_found": true,
  "result": {
    "vertices": ["errors_and_failures/error_123", "tool_executions/exec_456", "agent_insights/insight_456"],
    "edges": ["error_causality/edge_1", "insight_applications/edge_2"],
    "length": 2
  }
}
```

### 9. track_solution_outcome

**Purpose**: Track the outcome of applying a solution.

**Parameters**:
- `solution_id` (string): ID of the solution
- `outcome` (string): "success", "partial", or "failed"
- `key_reason` (string): Key reason for outcome
- `category` (string): Category like "async_fix", "import_error"
- `gotchas` (string, optional): JSON array of gotchas
- `time_to_resolve` (integer, optional): Minutes to resolve
- `context` (string, optional): Additional context

**Agent Call**:
```python
result = await mcp__arango-tools__track_solution_outcome(
    solution_id="solution_fix_imports_123",
    outcome="success",
    key_reason="Added missing __init__.py file to package directory",
    category="import_error",
    gotchas=json.dumps([
        "Python requires __init__.py for package recognition",
        "Empty __init__.py is sufficient",
        "Check all parent directories need __init__.py"
    ]),
    time_to_resolve=15,
    context="User was trying to import from a directory without __init__.py"
)
```

**Raw Response**:
```json
{
  "success": true,
  "outcome_id": "solution_outcomes/outcome_xyz",
  "message": "Tracked success outcome for solution"
}
```

### 10. discover_patterns

**Purpose**: Find patterns in similar problems and solutions.

**Parameters**:
- `problem_id` (string): Problem document ID
- `search_depth` (integer, optional): Graph traversal depth
- `min_similarity` (number, optional): Minimum similarity threshold

**Agent Call**:
```python
result = await mcp__arango-tools__discover_patterns(
    problem_id="log_events/365410",
    search_depth=3,
    min_similarity=0.7
)
```

**Raw Response**:
```json
{
  "success": true,
  "patterns": [
    {
      "pattern": "Missing __init__.py",
      "frequency": 23,
      "success_rate": 0.95,
      "common_solutions": [
        "Create empty __init__.py",
        "Check parent directories"
      ]
    }
  ],
  "similar_problems": 5,
  "analyzed_solutions": 12
}
```

### 11. extract_lesson

**Purpose**: Extract general lessons from multiple solutions.

**Parameters**:
- `solution_ids` (string): JSON array of solution IDs
- `lesson` (string): The lesson learned
- `category` (string): Category like "best_practice"
- `applies_to` (string): JSON array of what it applies to

**Agent Call**:
```python
result = await mcp__arango-tools__extract_lesson(
    solution_ids=json.dumps([
        "solution_outcomes/outcome_123",
        "solution_outcomes/outcome_456"
    ]),
    lesson="Always check for __init__.py files when encountering ImportError in package imports",
    category="best_practice",
    applies_to=json.dumps([
        "import_errors",
        "package_structure",
        "python_modules"
    ])
)
```

**Raw Response**:
```json
{
  "success": true,
  "lesson_id": "agent_learnings/lesson_789",
  "message": "Extracted lesson from 2 solutions"
}
```

### 12. advanced_search

**Purpose**: Search across multiple collections with complex filters.

**Parameters**:
- `collections` (string): JSON array of collections
- `filters` (string): JSON object of filters
- `text_search` (string, optional): Full-text search
- `date_range` (string, optional): JSON object with start/end
- `limit` (integer, optional): Max results per collection
- `sort` (string, optional): Sort field

**Agent Call**:
```python
result = await mcp__arango-tools__advanced_search(
    collections=json.dumps(["log_events", "errors_and_failures"]),
    filters=json.dumps({
        "level": "ERROR",
        "error_type": "ImportError"
    }),
    text_search="circular import",
    date_range=json.dumps({
        "start": "2025-07-01T00:00:00Z",
        "end": "2025-07-16T23:59:59Z"
    }),
    limit=20,
    sort="timestamp DESC"
)
```

**Raw Response**:
```json
{
  "success": true,
  "results": [
    {
      "collection": "log_events",
      "document": {
        "_id": "log_events/365410",
        "message": "ImportError: circular import detected",
        "timestamp": "2025-07-16T18:45:23Z"
      }
    }
  ],
  "total_results": 15,
  "collections_searched": 2
}
```

### 13. research_database_issue

**Purpose**: Get research prompts for database errors.

**Parameters**:
- `error_info` (string): JSON string with error details

**Agent Call**:
```python
result = await mcp__arango-tools__research_database_issue(
    error_info=json.dumps({
        "error": "bind parameter 'level' was not declared in query",
        "error_code": 1552,
        "aql": "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
        "bind_vars": {"@col": "log_events"},
        "collection": "log_events"
    })
)
```

**Raw Response**:
```json
{
  "success": true,
  "cached": false,
  "research": {
    "error_summary": "bind parameter 'level' was not declared in query",
    "tool_suggestions": {
      "perplexity": {
        "action": "Research the specific error with perplexity-ask",
        "prompt": "ArangoDB Error: bind parameter 'level' was not declared...",
        "when": "For specific error codes"
      }
    },
    "recovery_workflow": [
      "1. Check bind_vars includes all parameters",
      "2. Verify @ vs @@ usage",
      "3. Test with execute_aql"
    ]
  },
  "message": "Research context prepared for error"
}
```

---

## Usage Scenarios

### Scenario 1: Debugging Import Errors

**Goal**: Find and visualize patterns in import errors.

```python
# 1. Search for recent import errors
errors = await mcp__arango-tools__execute_aql(
    aql="""
    FOR doc IN log_events
        FILTER doc.error_type IN ["ImportError", "ModuleNotFoundError"]
        FILTER doc.timestamp > DATE_SUBTRACT(DATE_NOW(), 7, "day")
        COLLECT error_type = doc.error_type INTO errors
        RETURN {
            error_type: error_type,
            count: LENGTH(errors),
            examples: errors[*].doc.message[0..3]
        }
    """
)

# 2. Find patterns
if errors["results"]:
    pattern_result = await mcp__arango-tools__discover_patterns(
        problem_id=errors["results"][0]["examples"][0]["_id"],
        search_depth=2
    )

# 3. Visualize error relationships
viz_data = {
    "nodes": [],
    "links": []
}

for error in errors["results"]:
    viz_data["nodes"].append({
        "id": error["error_type"],
        "group": "error",
        "label": f"{error['error_type']} ({error['count']})"
    })

# Add solutions
for pattern in pattern_result["patterns"]:
    solution_id = f"solution_{pattern['pattern'].replace(' ', '_')}"
    viz_data["nodes"].append({
        "id": solution_id,
        "group": "solution",
        "label": pattern["pattern"]
    })
    viz_data["links"].append({
        "source": error["error_type"],
        "target": solution_id,
        "value": pattern["success_rate"]
    })

visualization = await mcp__d3-visualizer__generate_graph_visualization(
    graph_data=json.dumps(viz_data),
    layout="force",
    title="Import Error Patterns"
)
```

### Scenario 2: Learning System Integration

**Goal**: Track solutions and extract lessons.

```python
# 1. Track a successful solution
outcome = await mcp__arango-tools__track_solution_outcome(
    solution_id="fix_circular_import_123",
    outcome="success",
    key_reason="Moved import inside function to break cycle",
    category="import_error",
    gotchas=json.dumps([
        "Function-level imports have performance impact",
        "Consider refactoring to avoid circular dependency"
    ])
)

# 2. Find similar successful solutions
similar = await mcp__arango-tools__execute_aql(
    aql="""
    FOR outcome IN solution_outcomes
        FILTER outcome.category == "import_error"
        FILTER outcome.outcome == "success"
        FILTER outcome.key_reason =~ "circular"
        RETURN outcome
    """
)

# 3. Extract lesson if enough evidence
if len(similar["results"]) >= 3:
    lesson = await mcp__arango-tools__extract_lesson(
        solution_ids=json.dumps([s["_id"] for s in similar["results"]]),
        lesson="Moving imports inside functions is a quick fix for circular imports",
        category="quick_fix",
        applies_to=json.dumps(["circular_imports", "import_errors"])
    )

# 4. Link to glossary
await mcp__arango-tools__add_glossary_term(
    term="Function-level Import",
    definition="Import statement inside a function to avoid circular dependencies",
    category="patterns",
    examples=json.dumps(["def get_user(): from .models import User"])
)
```

### Scenario 3: Graph Analysis for Root Cause

**Goal**: Find root cause of cascading errors.

```python
# 1. Find error cluster
components = await mcp__arango-tools__analyze_graph(
    graph_name="claude_agent_observatory",
    algorithm="connected_components"
)

# 2. For largest component, find central node
if components["success"] and components["components"]:
    largest = max(components["components"], key=lambda x: x["size"])
    
    # Get centrality within component
    centrality = await mcp__arango-tools__analyze_graph(
        graph_name="claude_agent_observatory",
        algorithm="centrality"
    )
    
    # Find root cause (most central error)
    root_cause = centrality["top_nodes"][0] if centrality["top_nodes"] else None

# 3. Trace paths from root cause
if root_cause:
    paths = await mcp__arango-tools__analyze_graph(
        graph_name="claude_agent_observatory",
        algorithm="neighbors",
        params=json.dumps({
            "node": root_cause["vertex"],
            "depth": 3,
            "direction": "OUTBOUND"
        })
    )

# 4. Visualize the error cascade
cascade_viz = await mcp__d3-visualizer__visualize_arango_graph(
    graph_name="claude_agent_observatory",
    collection="errors_and_failures",
    max_nodes=50,
    layout="tree",
    title=f"Error Cascade from {root_cause['vertex']}"
)
```

---

## Error Recovery Patterns

### Pattern 1: Handle Missing Collections

```python
try:
    result = await mcp__arango-tools__execute_aql(
        aql="FOR doc IN my_collection RETURN doc"
    )
except Exception as e:
    if "collection or view not found" in str(e):
        # Get available collections
        schema = await mcp__arango-tools__get_schema()
        collections = [c["name"] for c in schema["collections"]]
        print(f"Available collections: {collections}")
        
        # Use a valid collection
        result = await mcp__arango-tools__execute_aql(
            aql=f"FOR doc IN {collections[0]} LIMIT 10 RETURN doc"
        )
```

### Pattern 2: Fix AQL Syntax Errors

```python
# Common AQL mistakes and fixes
aql_fixes = {
    "GRAPH @graph_name": "GRAPH error_knowledge_graph",  # Use literal
    "COLLECTION(coll)": "FOR doc IN collection_name",    # Direct access
    "@@col": "@col",  # Fix double @
    "FILTER @undefined": "FILTER true"  # Remove undefined vars
}

def fix_aql_query(aql, error):
    """Attempt to fix common AQL errors."""
    for mistake, fix in aql_fixes.items():
        if mistake in aql:
            aql = aql.replace(mistake, fix)
    
    # Extract missing bind var from error
    if "bind parameter" in error and "was not declared" in error:
        import re
        match = re.search(r"'(\w+)' was not declared", error)
        if match:
            var_name = match.group(1)
            # Add to bind_vars or remove from query
            aql = aql.replace(f"@{var_name}", '""')  # Default to empty string
    
    return aql
```

### Pattern 3: Validate Graph Data

```python
def validate_graph_data(data):
    """Ensure graph data is properly formatted for D3."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return None
    
    # Ensure required keys
    if "nodes" not in data:
        data["nodes"] = []
    if "links" not in data and "edges" in data:
        data["links"] = data.pop("edges")
    elif "links" not in data:
        data["links"] = []
    
    # Ensure nodes have IDs
    for i, node in enumerate(data["nodes"]):
        if "id" not in node:
            node["id"] = str(i)
    
    # Validate links reference existing nodes
    node_ids = {n["id"] for n in data["nodes"]}
    data["links"] = [
        link for link in data["links"] 
        if link.get("source") in node_ids and link.get("target") in node_ids
    ]
    
    return data
```

### Pattern 4: Retry with Defaults

```python
async def safe_visualization(data, title="Visualization"):
    """Create visualization with fallback options."""
    layouts = ["force", "tree", "radial", "sankey"]
    
    for layout in layouts:
        try:
            result = await mcp__d3-visualizer__generate_graph_visualization(
                graph_data=json.dumps(data),
                layout=layout,
                title=title
            )
            if result.get("success"):
                return result
        except Exception as e:
            logger.warning(f"Layout {layout} failed: {e}")
            continue
    
    # Final fallback - minimal graph
    return await mcp__d3-visualizer__generate_graph_visualization(
        graph_data=json.dumps({
            "nodes": [{"id": "1", "label": "No data"}],
            "links": []
        }),
        layout="force",
        title="Fallback Visualization"
    )
```

---

## Tool Status

### Active Tools (In MCP Configuration)
- ✅ **mcp_d3_visualizer.py** - Fully functional, all tests passing
- ✅ **mcp_arango_tools.py** - Fully functional, all tests passing, handles ALL CRUD operations

### Archived Tools
- 📦 **mcp_arango_crud.py** - Archived on 2025-07-16
  - Location: `/archived/mcp_arango_crud.py.archived_20250716`
  - Reason: All functionality superseded by mcp_arango_tools.py
  - Original features: Only had 2 tools (query, log)
  - Migration: Use mcp_arango_tools.py for all database operations

### Confirmation: mcp_arango_tools.py Handles All CRUD
- **Create**: `insert`, `upsert`, `edge` tools
- **Read**: `query`/`execute_aql`, `get`, `advanced_search` tools  
- **Update**: `update`, `upsert` tools
- **Delete**: `delete` tool
- **Plus**: Schema inspection, graph analytics, glossary, learning system

---

## Best Practices

1. **Always validate JSON inputs** - Use json.dumps() for parameters
2. **Check operation success** - Look for `success: true` in responses
3. **Use appropriate error recovery** - Don't just retry, fix the issue
4. **Batch operations when possible** - Use advanced_search for multi-collection queries
5. **Cache results** - ArangoDB tools cache for 5 minutes by default
6. **Monitor visualization size** - Keep max_nodes reasonable for performance
7. **Use proper bind variables** - Prevent injection and improve caching
8. **Link related data** - Use glossary and graph edges for knowledge building