# ArangoDB Tools MCP Server

## Overview

The `mcp_arango_tools.py` server provides comprehensive ArangoDB integration for the cc_executor ecosystem. It has evolved from a simple query tool to a sophisticated graph database interface with visualization support, pattern analysis, and intelligent error handling.

## Core Features

### 1. Basic Operations
- **schema()** - Get database schema with collections, views, graphs
- **query()** - Execute AQL queries with bind variables
- **insert()** - Insert log events and documents
- **edge()** - Create graph edges between documents
- **upsert()** - Update or insert documents

### 2. Visualization Support (NEW)
- **get_visualization_data()** - Get D3-ready data for different visualization types
- **prepare_graph_for_d3()** - Convert ArangoDB graphs to D3 format
- **get_graph_metrics()** - Calculate graph metrics for visualization decisions
- **analyze_graph_patterns()** - Detect patterns for optimal layout selection

### 3. Pattern Analysis (NEW)
- **find_clusters()** - Detect communities in graphs
- **detect_anomalies()** - Find unusual patterns in data
- **analyze_time_series()** - Temporal pattern analysis
- **track_pattern_evolution()** - Monitor how patterns change over time

### 4. English to AQL (NEW)
- **english_to_aql()** - Convert natural language to AQL queries
- Uses 400+ training examples for accurate conversion
- Provides query explanations and bind variables
- Suggests similar successful queries

### 5. Advanced Graph Operations (NEW)
- **get_node_centrality()** - Calculate various centrality measures
- **find_shortest_paths()** - Path finding between nodes
- **detect_cycles()** - Find cycles in directed graphs
- **calculate_page_rank()** - PageRank algorithm implementation

## Architecture

```
mcp_arango_tools.py
├── Core Functions
│   ├── schema() - Database introspection
│   ├── query() - Query execution with error handling
│   ├── insert() - Document insertion
│   ├── edge() - Edge creation
│   └── upsert() - Document upsert
├── Visualization Support
│   ├── get_visualization_data() - Query types for D3
│   ├── prepare_graph_for_d3() - Format conversion
│   └── get_graph_metrics() - Metrics calculation
├── Pattern Analysis
│   ├── find_clusters() - Community detection
│   ├── detect_anomalies() - Anomaly detection
│   ├── analyze_time_series() - Time analysis
│   └── track_pattern_evolution() - Evolution tracking
├── Query Translation
│   ├── english_to_aql() - NLP to AQL
│   └── _load_query_patterns() - Pattern loading
└── Error Handling
    ├── Smart suggestions on query failures
    ├── Perplexity integration for AQL help
    └── Cached solutions from previous errors
```

## Usage Examples

### Basic Query
```python
# Simple query
result = await query("FOR doc IN log_events LIMIT 5 RETURN doc")

# With bind variables
result = await query(
    "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
    '{"@col": "log_events", "level": "ERROR"}'
)
```

### Visualization Data
```python
# Get network data for D3 force layout
data = await get_visualization_data(
    query_type="network",
    collection="log_events",
    limit=100,
    filters='{"level": "ERROR"}'
)

# Get hierarchy for tree visualization
data = await get_visualization_data(
    query_type="hierarchy",
    collection="script_dependencies"
)
```

### Pattern Analysis
```python
# Find clusters in error relationships
clusters = await find_clusters(
    graph_name="error_causality",
    algorithm="louvain"
)

# Detect anomalies in metrics
anomalies = await detect_anomalies(
    collection="performance_metrics",
    metric_field="response_time",
    method="isolation_forest"
)
```

### English to AQL
```python
# Natural language query
result = await english_to_aql(
    "Find all errors from the last week that were resolved"
)
# Returns AQL query with explanation
```

## Integration with Other MCP Servers

### D3 Visualizer Integration
```python
# 1. Fetch data from ArangoDB
viz_data = await mcp__arango_tools__get_visualization_data(
    query_type="network",
    collection="error_causality"
)

# 2. Analyze with advisor
analysis = await mcp__d3_visualization_advisor__analyze_data(
    data=viz_data,
    goal="explore_error_patterns"
)

# 3. Generate visualization
result = await mcp__d3_visualizer__generate_graph_visualization(
    graph_data=viz_data,
    layout=analysis["recommended_layout"],
    config=analysis["layout_config"]
)
```

### Tool Journey Integration
```python
# Track tool usage patterns
await mcp__arango_tools__insert(
    message="Tool sequence completed",
    metadata=json.dumps({
        "journey_id": journey_id,
        "tools_used": ["arango_tools", "d3_visualizer"],
        "success": True
    })
)
```

## Query Types for Visualization

### 1. Network (Force-directed graphs)
- Error relationships
- Dependency graphs
- Communication patterns

### 2. Hierarchy (Tree layouts)
- File system structure
- Organization charts
- Category hierarchies

### 3. Timeline (Time-based)
- Event sequences
- Error occurrence over time
- Performance trends

### 4. Distribution (Statistical)
- Error type frequency
- Performance distribution
- Resource usage patterns

### 5. Flow (Sankey diagrams)
- Data flow between systems
- State transitions
- Resource allocation

## Error Handling

The server provides intelligent error handling with:

1. **Syntax Error Detection**
   - Identifies common AQL syntax mistakes
   - Provides corrected query suggestions
   - Links to relevant documentation

2. **Schema Validation**
   - Checks if collections/attributes exist
   - Suggests valid alternatives
   - Shows example queries for the schema

3. **Performance Warnings**
   - Detects potentially slow queries
   - Suggests index creation
   - Recommends query optimization

4. **Fallback Strategies**
   - PyMuPDF fallback for graph operations
   - Cached query results
   - Progressive enhancement

## Performance Considerations

### Query Optimization
- Use indexes for frequent filters
- Limit results for visualization queries
- Use graph traversal options wisely

### Caching Strategy
- Schema cached for 24 hours
- Query patterns cached indefinitely
- Visualization data cached for 15 minutes

### Resource Management
- Lazy loading of analysis libraries
- Connection pooling
- Automatic cleanup of large results

## Testing

Run comprehensive tests:
```bash
# Run 20 scenario tests
python src/cc_executor/servers/tests/test_arango_tools_scenarios.py

# Test specific functionality
python src/cc_executor/servers/mcp_arango_tools.py test

# Test visualization integration
python src/cc_executor/servers/tests/test_visualization_pipeline.py
```

## Configuration

### Environment Variables
```bash
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=your_password
ARANGO_DATABASE=cc_executor
```

### Collections Setup
```python
# Required collections
collections = [
    "log_events",
    "script_runs", 
    "error_fixes",
    "tool_usage",
    "query_patterns"
]

# Required edge collections
edge_collections = [
    "error_causality",
    "script_dependencies",
    "tool_sequences"
]

# Required graphs
graphs = [
    {
        "name": "error_graph",
        "edge_definitions": [{
            "collection": "error_causality",
            "from": ["log_events"],
            "to": ["log_events"]
        }]
    }
]
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check ArangoDB is running: `sudo systemctl status arangodb3`
   - Verify port 8529 is accessible
   - Check credentials in .env

2. **Query Timeout**
   - Add indexes for filtered fields
   - Reduce result limit
   - Use query profiling

3. **Memory Issues**
   - Enable streaming for large results
   - Use pagination
   - Clear visualization cache

### Debug Mode
```python
# Enable debug logging
export ARANGO_DEBUG=true

# Test connection
python -c "from mcp_arango_tools import test_connection; test_connection()"
```

## Future Enhancements

1. **GraphML Export** - Export graphs in standard formats
2. **Real-time Subscriptions** - Live query updates
3. **ML Integration** - Graph neural networks for prediction
4. **Distributed Queries** - Multi-database federation
5. **Time-travel Queries** - Historical state reconstruction

## Contributing

When adding new features:
1. Add comprehensive docstrings
2. Include usage examples
3. Update schema documentation
4. Add test scenarios
5. Consider visualization compatibility

## Related Documentation

- [D3 Visualizer Integration](./mcp_d3_visualizer.py)
- [Query Pattern Dataset](./data/english_to_aql_patterns.json)
- [Test Scenarios](./tests/arango_tools_20_scenarios.md)
- [ArangoDB Best Practices](https://www.arangodb.com/docs/stable/aql/tutorial.html)