# MCP Integration Analysis: Logger, ArangoDB & D3 Tools

## Current State

### 1. mcp_arango_tools.py (17+ tools)
- **CRUD Operations**: execute_aql, insert, update, delete, upsert, get
- **Graph Analytics**: analyze_graph (centrality, shortest_path, components, neighbors)
- **Learning System**: track_solution_outcome, discover_patterns, extract_lesson
- **Glossary**: add_glossary_term, link_glossary_terms, link_term_to_log
- **Search**: advanced_search, research_database_issue

### 2. mcp_d3_visualizer.py (3 tools)
- generate_graph_visualization - Create interactive visualizations
- list_visualizations - List generated files  
- visualize_arango_graph - Direct ArangoDB visualization

### 3. mcp_logger_tools.py (9 tools)
- **Error Assessment**: assess_complexity
- **Code Extraction**: extract_gemini_code, send_to_gemini, send_to_gemini_batch
- **Query Assistance**: query_converter, cache_db_schema, inspect_arangodb_schema
- **Performance Analysis**: analyze_agent_performance, query_agent_logs

## Integration Opportunities

### 1. Tool Call Journey Tracking (User Request)
To enable reinforcement learning on optimal tool call paths:

```python
# In mcp_arango_tools.py - Add new collection for tool journeys
async def track_tool_journey(
    session_id: str,
    tool_sequence: List[Dict[str, Any]],  # [{tool: "assess_complexity", result: "success", timestamp: ...}]
    outcome: str,  # "resolved", "failed", "partial"
    total_time: float,
    error_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Track complete tool call journeys for reinforcement learning."""
    
# In mcp_logger_tools.py - Enhance logging to capture tool sequences
async def log_tool_call(
    session_id: str,
    tool_name: str,
    parameters: Dict,
    result: Any,
    duration: float,
    parent_tool: Optional[str] = None
) -> str:
    """Log individual tool calls with parent context for journey tracking."""
```

### 2. Unified Error Resolution Flow

Current gap: Each tool operates independently. We need a unified flow:

```python
# Unified workflow combining all three MCP servers:
1. assess_complexity (logger) → Determine strategy
2. query_converter (logger) → Find similar errors  
3. discover_patterns (arango) → Analyze error patterns
4. generate_graph_visualization (d3) → Visualize error network
5. track_solution_outcome (arango) → Record fix success
6. analyze_agent_performance (logger) → Learn from journey
```

### 3. Schema Synchronization

Logger tools use different schema than arango tools:
- Logger: `log_events`, `errors_and_failures` (separate DB)
- Arango: `claude_agent_observatory` graph

**Solution**: Add cross-database querying:

```python
# In mcp_arango_tools.py
async def sync_with_logger_db(
    logger_event_ids: List[str],
    import_to_graph: bool = True
) -> Dict[str, Any]:
    """Import logger events into the main knowledge graph."""

# In mcp_logger_tools.py  
async def export_to_knowledge_graph(
    event_ids: List[str],
    target_graph: str = "claude_agent_observatory"
) -> str:
    """Export logger events to the main ArangoDB graph."""
```

### 4. Visualization Integration

Current: D3 visualizer can't directly visualize logger data.

**Solution**: Add logger-specific visualizations:

```python
# In mcp_d3_visualizer.py
async def visualize_tool_journey(
    session_id: str,
    layout: str = "sankey"  # Sankey diagram for tool flow
) -> str:
    """Visualize the tool call journey for a session."""

async def visualize_error_resolution_path(
    error_id: str,
    include_attempts: bool = True
) -> str:
    """Visualize how an error was resolved across tools."""
```

## Recommended Implementation Priority

### Phase 1: Tool Journey Tracking (Immediate)
1. Add `tool_journeys` collection to ArangoDB
2. Modify each MCP tool to log its calls with session context
3. Create edges: `tool_called_by`, `tool_calls`, `resolves_error`

### Phase 2: Unified Workflows (Next Week)
1. Create meta-tools that orchestrate across MCP servers
2. Add cross-database query capabilities
3. Implement journey analysis tools

### Phase 3: Reinforcement Learning (Future)
1. Analyze successful vs failed journeys
2. Identify optimal tool sequences for error types
3. Generate recommendations for tool selection

## Example: Complete Tool Journey

```python
# Starting with an error
session_id = "debug_session_123"

# 1. Assess complexity (logger-tools)
assessment = await assess_complexity(
    error_type="ModuleNotFoundError",
    error_message="No module named 'pandas'",
    file_path="/app/analyzer.py"
)
# Log: {tool: "assess_complexity", duration: 0.5s, result: "simple"}

# 2. Query for similar errors (logger-tools)  
similar = await query_converter(
    natural_query="Find ModuleNotFoundError fixes for pandas"
)
# Log: {tool: "query_converter", duration: 0.3s, parent: "assess_complexity"}

# 3. Discover patterns (arango-tools)
patterns = await discover_patterns(
    problem_id="errors/module_not_found_123"
)
# Log: {tool: "discover_patterns", duration: 1.2s, parent: "query_converter"}

# 4. Visualize relationships (d3-visualizer)
viz = await generate_graph_visualization(
    graph_data=patterns["graph_data"],
    title="Module Import Error Network"
)
# Log: {tool: "generate_graph_visualization", duration: 0.8s}

# 5. Track outcome (arango-tools)
outcome = await track_solution_outcome(
    solution_id="fix_pandas_import",
    outcome="success",
    key_reason="Added pandas to requirements.txt"
)
# Log: {tool: "track_solution_outcome", duration: 0.4s, closes_session: true}

# Complete journey logged for reinforcement learning
```

## Minimal Changes Required

### 1. Add to each MCP tool:
```python
# At start of each tool function
journey_id = context.get("journey_id") or str(uuid.uuid4())
start_time = time.time()

# At end of each tool function  
await log_tool_journey_step(
    journey_id=journey_id,
    tool_name="tool_name",
    duration=time.time() - start_time,
    result_summary=result
)
```

### 2. Create journey analysis tool:
```python
@mcp.tool()
async def analyze_tool_journeys(
    error_type: Optional[str] = None,
    outcome_filter: Optional[str] = None,  # "success", "failure"
    limit: int = 100
) -> str:
    """Analyze tool call journeys to identify optimal paths."""
```

This integration would enable powerful reinforcement learning on tool usage patterns while keeping the tools loosely coupled and maintainable.