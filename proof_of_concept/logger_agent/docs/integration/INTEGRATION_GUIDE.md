# Logger Agent Dashboard Integration Guide

**Date**: 2025-01-14  
**Version**: 1.0.0  
**Purpose**: Complete guide for integrating the multi-agent observability dashboard

## Overview

This guide explains how to integrate the multi-agent observability dashboard from claude-code-hooks-multi-agent-observability into the logger_agent project, using ArangoDB for storage and leveraging graph relationships and BM25 search.

## Architecture Summary

```
Claude Code Agents
    ↓ (Hook Events)
.claude/hooks/send_event.py
    ↓ (HTTP POST)
FastAPI Dashboard Server (port 8000)
    ↓ (Store & Transform)
ArangoDB (Graph + BM25 Search)
    ↓ (WebSocket broadcast)
Vue.js Dashboard (port 5173)
```

## Installation Steps

### 1. Prerequisites

Ensure you have:
- ArangoDB running (via docker-compose)
- Python 3.10+ with uv installed
- Node.js 16+ and npm
- The observability repository cloned

### 2. Run Setup Script

```bash
cd /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent
./scripts/setup_dashboard.sh
```

This will:
- Copy the Vue dashboard from the observability repo
- Set up Claude hooks for event capture
- Configure API endpoints
- Create necessary __init__.py files

### 3. Install Dependencies

```bash
# Python dependencies
source .venv/bin/activate
uv add fastapi uvicorn websockets python-multipart

# Dashboard dependencies (handled by start script)
cd dashboard && npm install
```

### 4. Start the Dashboard

```bash
./scripts/start_dashboard.sh
```

This launches:
- FastAPI server on http://localhost:8000
- Vue dashboard on http://localhost:5173
- WebSocket connection for real-time updates

## Key Components

### 1. API Server (`src/api/dashboard_server.py`)

The FastAPI server provides:

**Endpoints:**
- `POST /events` - Receive events from Claude hooks
- `GET /events/recent` - Get recent events with filtering
- `POST /events/search` - BM25 search across all activity
- `GET /events/filter-options` - Available filter values
- `GET /sessions/{session_id}/flow` - Execution flow graph
- `GET /errors/patterns` - Common error patterns
- `WS /stream` - Real-time WebSocket updates

**Features:**
- Transforms hook events to ArangoDB log format
- Creates graph nodes and relationships
- Broadcasts events to connected clients
- Provides powerful search and analytics

### 2. Graph Builder (`src/arangodb/core/graph/agent_graph_builder.py`)

Creates and manages graph relationships:

**Node Types:**
- `agent_sessions` - Claude Code sessions
- `tool_executions` - Individual tool uses
- `code_artifacts` - Files created/modified
- `agent_insights` - Learnings and observations
- `errors_and_failures` - Errors encountered

**Edge Types:**
- `agent_flow` - Execution sequence
- `tool_dependencies` - Tool relationships
- `error_causality` - Error causes and fixes
- `artifact_lineage` - File modification history
- `insight_applications` - Where insights are applied

### 3. Search Engine (`src/arangodb/core/search/agent_search.py`)

Provides BM25 search capabilities:

**Features:**
- Full-text search across all agent activity
- Filter by app, session, event type, time range
- Find similar tool executions
- Discover error patterns and resolutions
- Get relevant insights based on context

**Example Searches:**
```python
# Search for errors related to imports
results = await search.search_agent_activity(
    "import error",
    filters={"event_types": ["PostToolUse"]},
    limit=20
)

# Find error patterns
patterns = await search.find_error_patterns(
    time_range="7d",
    min_occurrences=3
)

# Get insights for a context
insights = await search.get_insights_for_context(
    {"error_type": "ModuleNotFoundError"},
    min_confidence=0.8
)
```

### 4. Claude Hooks Integration

The `.claude/settings.json` configures hooks to send events:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type PreToolUse"
      }]
    }],
    // ... other event types
  }
}
```

Events are sent to the dashboard API and stored in ArangoDB with full context.

## Using the Dashboard

### 1. Real-time Monitoring

- Open http://localhost:5173
- Watch events stream in as Claude Code executes
- Filter by app, session, or event type
- Click events to see full details

### 2. Search and Analytics

- Use the search bar for BM25 queries
- Examples:
  - `error AND import` - Find import errors
  - `"pytest" tool:Bash` - Find pytest executions
  - `insight confidence:>0.8` - High-confidence insights

### 3. Execution Flow Visualization

- Click on a session to see its execution graph
- Nodes show tools, errors, insights, artifacts
- Edges show relationships and dependencies
- Interactive graph with zoom and pan

### 4. Error Pattern Analysis

- View common error patterns
- See successful resolutions
- Track fix times and success rates
- Learn from past solutions

## Advanced Features

### 1. Graph Queries

Query execution flows and relationships:

```python
# Get all tools that led to errors
aql = """
FOR error IN errors_and_failures
FOR tool IN 1..3 INBOUND error error_causality
FILTER CONTAINS(tool._id, 'tool_executions')
RETURN DISTINCT tool.tool_name
"""
```

### 2. Semantic Search (Future)

With embeddings stored in ArangoDB:
```python
# Find similar errors using vector similarity
aql = """
FOR doc IN log_events
LET similarity = COSINE_SIMILARITY(doc.embeddings, @query_embedding)
FILTER similarity > 0.8
SORT similarity DESC
RETURN doc
"""
```

### 3. Custom Analytics

Build custom dashboards using the API:
```javascript
// Get agent productivity metrics
const response = await fetch('/api/analytics/agent-productivity?timeRange=7d')
const metrics = await response.json()

// Display in charts
showProductivityChart(metrics)
```

## Troubleshooting

### Dashboard Not Loading

1. Check API server is running: `curl http://localhost:8000/health`
2. Check WebSocket connection in browser console
3. Verify CORS settings in dashboard_server.py

### Events Not Appearing

1. Check Claude hooks are configured: `cat .claude/settings.json`
2. Verify API endpoint in send_event.py points to localhost:8000
3. Check API server logs for errors

### Database Connection Issues

1. Ensure ArangoDB is running: `docker-compose ps`
2. Check credentials in .env file
3. Verify database initialization: `python src/arango_init.py`

### Search Not Working

1. Check search view exists: `python -c "from agent_search import *; ..."`
2. Verify collections have data
3. Check AQL syntax in search queries

## Best Practices

1. **Session Management**: Always use consistent session IDs
2. **Error Handling**: Create error nodes for all failures
3. **Insights**: Record learnings with high confidence scores
4. **Graph Relationships**: Create meaningful edges between nodes
5. **Search Optimization**: Use appropriate analyzers for fields

## Future Enhancements

1. **ML-Powered Insights**: Use embeddings for semantic similarity
2. **Predictive Analytics**: Predict likely errors based on patterns
3. **Auto-Resolution**: Suggest fixes based on past solutions
4. **Performance Tracking**: Monitor agent efficiency over time
5. **Collaboration**: Share insights between team members

## API Examples

### Create Custom Event

```python
import httpx

event = {
    "source_app": "my-agent",
    "session_id": "session_123", 
    "hook_event_type": "CustomEvent",
    "payload": {
        "action": "data_processing",
        "status": "completed",
        "records_processed": 1000
    }
}

response = httpx.post("http://localhost:8000/events", json=event)
```

### Search with Complex Filters

```python
filters = {
    "source_apps": ["logger-agent", "cc-executor"],
    "session_ids": ["session_123", "session_456"],
    "event_types": ["PreToolUse", "PostToolUse"],
    "time_range": {
        "start": "2025-01-14T00:00:00Z",
        "end": "2025-01-14T23:59:59Z"
    },
    "search_query": "error handling"
}

response = httpx.post("http://localhost:8000/events/search", json=filters)
results = response.json()
```

### Get Session Graph

```python
session_id = "session_123"
response = httpx.get(f"http://localhost:8000/sessions/{session_id}/flow")
graph_data = response.json()

# Process nodes and edges
for node in graph_data["nodes"]:
    print(f"Node: {node['_id']}, Type: {node['_id'].split('/')[0]}")

for edge in graph_data["edges"]:
    print(f"Edge: {edge['_from']} -> {edge['_to']}")
```

## Conclusion

The Logger Agent Dashboard provides powerful observability for Claude Code agents by combining:
- Real-time event streaming
- Graph-based relationship tracking
- BM25 full-text search
- Error pattern analysis
- Execution flow visualization

This enables developers to understand, debug, and optimize their AI agent workflows effectively.