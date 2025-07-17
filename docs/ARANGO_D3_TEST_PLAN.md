# ArangoDB & D3 Visualizer Test Plan

## Test Date: 2025-01-16

## Prerequisites
1. Reload Claude after MCP configuration updates
2. Ensure ArangoDB is running
3. Check collections exist (will be auto-created if not)

## Test Categories

### 1. Learning System Tests (New Features)

#### 1.1 Track Solution Outcome
```python
# Test tracking a successful solution
await mcp__arango-tools__track_solution_outcome(
    "log_events/365368",  # From previous test
    "success",
    "Used json.loads() to parse bind variables correctly",
    "parameter_parsing",
    '["Always use JSON strings with FastMCP", "Dict parameters fail validation"]',
    15,  # 15 minutes to resolve
    '{"tool": "arango-tools", "method": "query"}'
)
```

#### 1.2 Discover Patterns
```python
# Find patterns for a problem
await mcp__arango-tools__discover_patterns(
    "log_events/365368",
    2,  # search depth
    0.5  # min similarity
)
```

#### 1.3 Extract Lesson
```python
# Extract general lesson from multiple solutions
await mcp__arango-tools__extract_lesson(
    '["log_events/365368", "log_events/365417"]',
    "FastMCP requires JSON strings for all complex parameters - Dict and List types fail validation",
    "best_practice",
    '["fastmcp", "parameter_validation", "json_parsing"]'
)
```

#### 1.4 Advanced Search
```python
# Multi-dimensional search
await mcp__arango-tools__advanced_search(
    category="parameter_parsing",
    time_range="last_week",
    min_success_rate=0.8
)

# Text search with filters
await mcp__arango-tools__advanced_search(
    search_text="json validation error",
    category="fastmcp",
    limit=10
)
```

### 2. Graph Analytics Tests

#### 2.1 Shortest Path
```python
# Find path between two nodes
await mcp__arango-tools__analyze_graph(
    "error_knowledge_graph",
    "shortest_path",
    '{"start_node": "log_events/365368", "end_node": "log_events/365417"}'
)
```

#### 2.2 Find Neighbors
```python
# Find related nodes within 2 hops
await mcp__arango-tools__analyze_graph(
    "error_knowledge_graph",
    "neighbors",
    '{"node": "log_events/365368", "depth": 2, "direction": "ANY"}'
)
```

#### 2.3 Centrality Analysis
```python
# Find most connected nodes
await mcp__arango-tools__analyze_graph(
    "error_knowledge_graph",
    "centrality"
)
```

#### 2.4 Connected Components
```python
# Find clusters in the graph
await mcp__arango-tools__analyze_graph(
    "error_knowledge_graph",
    "connected_components"
)
```

### 3. D3 Visualizer Tests

#### 3.1 Generate Force-Directed Graph
```python
# Create a simple error-solution network
await mcp__d3-visualizer__generate_graph_visualization(
    '{
        "nodes": [
            {"id": "e1", "label": "ModuleNotFoundError", "type": "error", "color": "#ff6b6b"},
            {"id": "s1", "label": "Install module", "type": "solution", "color": "#51cf66"},
            {"id": "e2", "label": "ImportError", "type": "error", "color": "#ff6b6b"},
            {"id": "s2", "label": "Fix import path", "type": "solution", "color": "#51cf66"},
            {"id": "p1", "label": "Import Best Practices", "type": "pattern", "color": "#339af0"}
        ],
        "links": [
            {"source": "e1", "target": "s1", "value": 3},
            {"source": "e2", "target": "s2", "value": 2},
            {"source": "s1", "target": "p1", "value": 1},
            {"source": "s2", "target": "p1", "value": 1}
        ]
    }',
    "force",
    "Error Resolution Network"
)
```

#### 3.2 Test Tree Layout
```python
# Create hierarchical visualization
await mcp__d3-visualizer__generate_graph_visualization(
    '{
        "nodes": [
            {"id": "root", "label": "All Errors", "parent": null},
            {"id": "async", "label": "Async Errors", "parent": "root"},
            {"id": "import", "label": "Import Errors", "parent": "root"},
            {"id": "e1", "label": "Deadlock", "parent": "async"},
            {"id": "e2", "label": "ModuleNotFound", "parent": "import"}
        ],
        "links": []
    }',
    "tree",
    "Error Hierarchy"
)
```

#### 3.3 List Visualizations
```python
# Check what visualizations were created
await mcp__d3-visualizer__list_visualizations()
```

#### 3.4 Complex Knowledge Graph
```python
# Visualize actual data from ArangoDB
# First, query some data
result = await mcp__arango-tools__query(
    """
    FOR doc IN log_events
        FILTER doc.resolved == true
        LIMIT 20
        RETURN {
            id: doc._key,
            label: doc.message || doc.error_type,
            type: doc.resolved ? "solution" : "error",
            color: doc.resolved ? "#51cf66" : "#ff6b6b"
        }
    """
)

# Then create visualization from the results
# (Would need to format as proper graph data)
```

### 4. Integration Tests

#### 4.1 Learning Workflow
1. Insert a new error
2. Track failed solution attempt
3. Track successful solution with key reason
4. Discover patterns from this solution
5. Extract lesson learned
6. Search for similar problems

#### 4.2 Visualization Workflow
1. Query graph data from ArangoDB
2. Transform to D3 format
3. Generate visualization
4. List and verify output

## Expected Results

### Learning System
- Solution outcomes tracked with categories
- Patterns discovered across multiple dimensions
- Lessons extracted and linked to solutions
- Advanced search returns filtered results

### Graph Analytics
- Shortest paths found between nodes
- Neighbors identified at various depths
- Centrality shows most connected nodes
- Components reveal graph structure

### D3 Visualizer
- HTML files generated in /tmp/visualizations
- Multiple layouts work correctly
- Visualization URLs returned
- List shows all generated files

## Troubleshooting

1. **MCP Tools Not Found**
   - Reload Claude interface
   - Check ~/.claude/logs/mcp*.log

2. **Collection Errors**
   - Collections auto-create on first use
   - Check ArangoDB connection

3. **Visualization Errors**
   - Check D3_OUTPUT_DIR exists
   - Verify write permissions

4. **Graph Not Found**
   - Create graph first:
   ```aql
   // In ArangoDB
   CREATE GRAPH error_knowledge_graph {
       edge_definitions: [
           {
               collection: "error_causality",
               from: ["log_events"],
               to: ["log_events"]
           },
           {
               collection: "term_relationships",
               from: ["glossary_terms"],
               to: ["glossary_terms", "log_events"]
           }
       ]
   }
   ```

## Success Criteria
- [ ] All learning features return success
- [ ] Graph analytics provide meaningful results
- [ ] Visualizations generate valid HTML
- [ ] Integration workflows complete without errors
- [ ] No validation errors with JSON parameters