# MCP Server Documentation

This directory contains documentation for all MCP (Model Context Protocol) tools and servers.

## Quick Start Guides

### Essential References
- [MCP ArangoDB & D3 Comprehensive Guide](MCP_ARANGO_D3_COMPREHENSIVE_GUIDE.md) - Complete guide for both visualization and database tools
- [MCP ArangoDB Tools Quick Reference](MCP_ARANGO_TOOLS_QUICK_REFERENCE.md) - Quick lookup for ArangoDB operations
- [MCP Debugging Guide](MCP_DEBUGGING_GUIDE.md) - Troubleshooting MCP tools
- [MCP Logger Agent Quick Reference](MCP_LOGGER_AGENT_QUICK_REFERENCE.md) - Logger integration guide

### Creating New Tools
- [MCP Tool Creation Guide](MCP_TOOL_CREATION_GUIDE.md) - Step-by-step guide for creating new MCP tools

## Feature Documentation

### Search and Query
- [Natural Language to AQL Workflow](natural_language_to_aql_workflow.md) - Convert natural language to ArangoDB queries
- [Semantic Search Guide](SEMANTIC_SEARCH_GUIDE.md) - AI-powered semantic search
- [Vector Search Quick Start](VECTOR_SEARCH_QUICK_START.md) - Vector similarity search

### Advanced Features
- [MCP Enhanced Features Guide](MCP_ENHANCED_FEATURES_GUIDE.md) - Graph intelligence and advanced features
- [MCP Knowledge Evolution Guide](MCP_KNOWLEDGE_EVOLUTION_GUIDE.md) - Evolving knowledge graphs
- [MCP Verification Tool](MCP_VERIFICATION_TOOL.md) - Anti-hallucination verification

## Implementation Details

### Query Converter
- [Query Converter Final Implementation](query_converter_final_implementation.md) - Complete implementation
- [Query Converter Simplification](query_converter_simplification.md) - Design philosophy
- [Schema Query Implementation](schema_query_implementation.md) - Schema-aware queries

### Technical Guides
- [Python ArangoDB Async Conversion Guide](python_arango_async_conversion_guide.md) - Async migration guide
- [MCP Tools Comprehensive Test Report](MCP_TOOLS_COMPREHENSIVE_TEST_REPORT.md) - Latest test results

## Available MCP Servers

### Active Servers
1. **arango-tools** - Full ArangoDB CRUD + advanced features (17+ tools)
2. **d3-visualizer** - D3.js graph visualization (3 tools)
3. **logger-tools** - Logger agent integration (15+ tools)

### Tool Categories

#### ArangoDB Tools (`mcp__arango-tools__*`)
- Database Operations: `execute_aql`, `insert`, `update`, `delete`, `upsert`, `get`
- Graph Analytics: `analyze_graph` (centrality, shortest_path, components, neighbors)
- Learning System: `track_solution_outcome`, `discover_patterns`, `extract_lesson`
- Glossary: `add_glossary_term`, `link_glossary_terms`, `link_term_to_log`
- Search: `advanced_search`, `research_database_issue`

#### D3 Visualizer (`mcp__d3-visualizer__*`)
- `generate_graph_visualization` - Create interactive visualizations
- `list_visualizations` - List generated files
- `visualize_arango_graph` - Direct ArangoDB visualization

#### Logger Tools (`mcp__logger-tools__*`)
- Error Assessment: `assess_complexity`
- Code Extraction: `extract_gemini_code`
- Query Assistance: `query_converter`, `cache_db_schema`
- Performance Analysis: `analyze_agent_performance`
- Log Queries: `query_agent_logs`

## Quick Examples

### Visualize Error Network
```python
result = await mcp__d3-visualizer__visualize_arango_graph(
    graph_name="claude_agent_observatory",
    collection="errors_and_failures",
    layout="force",
    title="Error Network"
)
```

### Find Similar Errors
```python
result = await mcp__arango-tools__discover_patterns(
    problem_id="log_events/12345",
    search_depth=2,
    min_similarity=0.7
)
```

### Track Solution Success
```python
result = await mcp__arango-tools__track_solution_outcome(
    solution_id="fix_import_123",
    outcome="success",
    key_reason="Added missing __init__.py",
    category="import_error"
)
```