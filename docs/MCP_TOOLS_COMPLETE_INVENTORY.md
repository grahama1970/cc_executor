# Complete MCP Tools Inventory vs Test Scenarios

## Executive Summary

The test scenarios reference many MCP tools correctly, but also expect functionality that doesn't exist. Here's the complete inventory of what's actually available versus what the scenarios expect.

## 1. Actually Available MCP Tools

### mcp_arango_tools (11 tools)
1. `schema()` - Get database schema
2. `query(aql, bind_vars)` - Execute AQL queries
3. `insert(...)` - Insert log events
4. `edge(...)` - Create graph edges
5. `upsert(...)` - Update or insert documents
6. `natural_language_to_aql(query, context)` - Convert English to AQL
7. `research_database_issue(error, aql, error_code, collection)` - Research errors
8. `add_glossary_term(term, definition, examples, related_errors, see_also)` - Manage glossary
9. `extract_lesson(solution_ids, lesson, category, applies_to)` - Extract lessons
10. `track_solution_outcome(solution_id, outcome, key_reason, category, gotchas, time_to_resolve, context)` - Track outcomes
11. `advanced_search(search_text, category, error_type, time_range, min_success_rate, resolved_only, limit)` - Multi-dimensional search

### mcp_d3_visualizer (4 tools)
1. `generate_graph_visualization(graph_data, layout, title, width, height, config)` - Create D3 visualizations
2. `list_visualizations()` - List generated visualizations
3. `visualize_arango_graph(graph_name, layout, limit, depth)` - Visualize from ArangoDB
4. `generate_intelligent_visualization(data, goal, config)` - Auto-select best visualization

### mcp_d3_visualization_advisor (1 tool)
1. `analyze_and_recommend_visualization(data, goal, constraints)` - Get visualization recommendations

### mcp_response_validator (1 tool)
1. `validate_llm_response(response, validation_type, expected_fields, expected_content, prompt, schema)` - Validate LLM responses

### mcp_universal_llm_executor (5 tools)
1. `execute_llm(llm, prompt, files, streaming, temperature, max_tokens, json_schema, timeout, api_key, model)` - Execute any LLM
2. `concatenate_files(files, max_tokens, format)` - Concatenate files intelligently
3. `detect_llms()` - Detect available LLMs
4. `estimate_tokens(text, file_path, model)` - Estimate token count
5. `parse_llm_output(content, output_file, validate_json)` - Parse LLM JSON output

### mcp_litellm_batch (1 tool)
1. `process_batch_requests(requests, concurrency)` - Process batch LLM requests

### mcp_litellm_request (1 tool)
1. `process_single_request(model, messages, temperature, max_tokens, cache, api_key)` - Single LLM request

### mcp_tool_journey (4 tools)
1. `start_journey(task_description, context)` - Start Q-learning journey
2. `record_tool_step(journey_id, tool_name, success, duration_ms, error)` - Record step
3. `complete_journey(journey_id, outcome, solution_description)` - Complete journey
4. `query_similar_journeys(task_description, limit, min_similarity)` - Find similar journeys

### mcp_tool_sequence_optimizer (5 tools)
1. `optimize_tool_sequence(task_description, error_context)` - Find optimal sequence
2. `record_sequence_step(journey_id, tool_name, success, duration_ms, result_summary)` - Record step
3. `complete_sequence_journey(journey_id, outcome, solution_description, category)` - Complete journey
4. `find_successful_sequences(task_pattern, min_success_rate, limit)` - Find patterns
5. `analyze_sequence_performance()` - Analyze performance metrics

### Other MCP servers (not referenced in scenarios but available)
- `mcp_code_analyzer` - AST analysis with tree-sitter
- `mcp_code_review` - Code review capabilities
- `mcp_crawler` - Web crawling and extraction
- `mcp_debugging_assistant` - Debugging help
- `mcp_outcome_adjudicator` - Decision making

## 2. Tools Referenced in Scenarios but NOT Available

### From mcp_arango_tools (expected but missing)
1. ❌ `get_visualization_data()` - Not implemented
2. ❌ `prepare_graph_for_d3()` - Not implemented  
3. ❌ `detect_anomalies()` - Not implemented
4. ❌ `find_clusters()` - Not implemented
5. ❌ `analyze_time_series()` - Not implemented
6. ❌ `track_pattern_evolution()` - Not implemented
7. ❌ `analyze_graph_patterns()` - Not implemented
8. ❌ `detect_cycles()` - Not implemented
9. ❌ `get_graph_metrics()` - Not implemented
10. ❌ `find_shortest_paths()` - Not implemented
11. ❌ `calculate_page_rank()` - Not implemented
12. ❌ `get_node_centrality()` - Not implemented
13. ❌ `find_communities()` - Not implemented
14. ❌ `build_similarity_graph()` - Not implemented
15. ❌ `find_similar_documents()` - Not implemented

### External tools referenced incorrectly
1. ❌ `mcp__pdf_extractor__extract_pdf_content()` - Different server name
2. ❌ `mcp__document_structurer__process_document_fully()` - Different server name
3. ❌ `mcp__cc_execute__execute_task()` - Not an MCP tool
4. ❌ `mcp__kilocode_review__review_match()` - Not found
5. ❌ `mcp__perplexity_ask__perplexity_ask()` - External service

## 3. Correct Usage Examples for Available Tools

### Visualization Pipeline (Correct)
```python
# Step 1: Query data from ArangoDB
data = await mcp__arango_tools__query(
    "FOR v, e IN 1..2 OUTBOUND 'start/node' GRAPH mygraph RETURN {node: v, edge: e}"
)

# Step 2: Generate visualization directly
viz = await mcp__d3_visualizer__generate_graph_visualization(
    graph_data=json.dumps({
        "nodes": [...],  # Format data from query
        "links": [...]
    }),
    layout="force",
    title="My Graph"
)

# OR use the convenience function
viz = await mcp__d3_visualizer__visualize_arango_graph(
    graph_name="mygraph",
    layout="force",
    limit=100
)
```

### LLM Validation Pipeline (Correct)
```python
# Step 1: Execute LLM
result = await mcp__universal_llm_executor__execute_llm(
    llm="gemini",
    prompt="Explain this error",
    json_schema='{"explanation": "string", "solution": "string"}'
)

# Step 2: Parse output
parsed = await mcp__universal_llm_executor__parse_llm_output(
    content=result.get("stdout", "")
)

# Step 3: Validate response
validation = await mcp__response_validator__validate_llm_response(
    response=json.dumps(parsed),
    validation_type="content",
    expected_content=["explanation", "solution"]
)
```

### Tool Learning Pipeline (Correct)
```python
# Step 1: Start journey
journey = await mcp__tool_journey__start_journey(
    task_description="Fix import error in Python",
    context='{"error_type": "ImportError"}'
)

# Step 2: Record steps
await mcp__tool_journey__record_tool_step(
    journey_id=journey["journey_id"],
    tool_name="arango_tools.query",
    success=True,
    duration_ms=150
)

# Step 3: Complete journey
await mcp__tool_journey__complete_journey(
    journey_id=journey["journey_id"],
    outcome="success",
    solution_description="Added missing import"
)
```

## 4. Recommendations for Test Scenarios

### High Priority Updates
1. Replace all `get_visualization_data()` calls with direct `generate_graph_visualization()`
2. Replace `detect_anomalies()` with custom AQL queries for outlier detection
3. Replace `find_clusters()` with graph traversal queries
4. Use `mcp__d3_visualization_advisor__analyze_and_recommend_visualization()` for intelligent viz

### Medium Priority Updates  
1. Replace pattern analysis with AQL aggregations
2. Use `advanced_search()` instead of similarity functions
3. Leverage `natural_language_to_aql()` for query generation

### Low Priority Updates
1. Remove references to ML-based features entirely
2. Simplify time series analysis to basic aggregations
3. Focus on graph traversal instead of advanced graph metrics

## 5. Test Scenario Rewrite Example

### Original (Won't Work)
```python
# Uses non-existent functions
viz_data = await mcp__arango_tools__get_visualization_data(
    query_type="network",
    collection="log_events"
)
clusters = await mcp__arango_tools__find_clusters(
    graph_name="error_causality"
)
```

### Corrected Version
```python
# Query data directly
graph_data = await mcp__arango_tools__query(
    "FOR v, e IN 1..2 ANY 'log_events/start' error_causality RETURN {node: v, edge: e}"
)

# Format for visualization
nodes = [{"id": r["node"]["_id"], "label": r["node"]["message"]} for r in graph_data["results"]]
links = [{"source": r["edge"]["_from"], "target": r["edge"]["_to"]} for r in graph_data["results"] if r["edge"]]

# Generate visualization
viz = await mcp__d3_visualizer__generate_graph_visualization(
    graph_data=json.dumps({"nodes": nodes, "links": links}),
    layout="force"
)

# For clustering, use graph traversal
clusters = await mcp__arango_tools__query("""
    FOR v IN log_events
    LET cluster = (
        FOR n IN 1..3 ANY v error_causality
        RETURN DISTINCT n._id
    )
    FILTER LENGTH(cluster) > 5
    RETURN {center: v, members: cluster}
""")
```

## Conclusion

The test scenarios need significant updates to match actual MCP tool availability. While we have powerful visualization, LLM execution, and learning tools, the advanced ML/analytics features expected by the scenarios don't exist. The scenarios should be rewritten to leverage the actual tools available, focusing on:

1. Direct D3 visualization generation
2. AQL-based analysis instead of ML algorithms
3. Tool journey learning capabilities
4. LLM validation pipelines
5. Natural language to AQL conversion

This will create realistic, executable test scenarios that properly exercise the actual MCP ecosystem.