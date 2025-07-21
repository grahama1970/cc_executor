# Tool Journey Graph Architecture

## Overview

The Tool Journey Graph system uses ArangoDB to store and learn from tool usage patterns as a directed graph:

```
[Task] --starts_with--> [Tool1] --followed_by--> [Tool2] --leads_to--> [Outcome]
                            |                         |
                            +----- success_rate ------+
                                    duration
                                    total_uses
```

## Graph Structure

### Nodes (Collection: `tool_journey_nodes`)

1. **Task Nodes**
   ```json
   {
     "_key": "task_abc123",
     "type": "task",
     "description": "Fix ModuleNotFoundError for pandas",
     "task_type": "error_fix",
     "embeddings": [0.23, -0.45, ...],  // BERT embeddings
     "created_at": "2024-01-15T10:30:00Z"
   }
   ```

2. **Tool Nodes**
   ```json
   {
     "_key": "tool_assess_complexity",
     "type": "tool",
     "name": "assess_complexity",
     "total_uses": 1523,
     "success_count": 1420,
     "failure_count": 103
   }
   ```

3. **Outcome Nodes**
   ```json
   {
     "_key": "outcome_success_xyz",
     "type": "outcome",
     "outcome": "success",
     "details": "Added pandas to requirements.txt",
     "timestamp": "2024-01-15T10:35:00Z"
   }
   ```

### Edges (Collection: `tool_journey_edges`)

1. **starts_with** (Task → Tool)
   ```json
   {
     "_from": "tool_journey_nodes/task_abc123",
     "_to": "tool_journey_nodes/tool_assess_complexity",
     "type": "starts_with",
     "success": true,
     "duration": 523
   }
   ```

2. **followed_by** (Tool → Tool)
   ```json
   {
     "_from": "tool_journey_nodes/tool_assess_complexity",
     "_to": "tool_journey_nodes/tool_query_converter",
     "type": "followed_by",
     "success_rate": 0.85,
     "success_count": 342,
     "failure_count": 60,
     "total_uses": 402,
     "task_type": "error_fix",
     "avg_duration": 312
   }
   ```

3. **leads_to** (Tool → Outcome)
   ```json
   {
     "_from": "tool_journey_nodes/tool_track_solution_outcome",
     "_to": "tool_journey_nodes/outcome_success_xyz",
     "type": "leads_to",
     "task_id": "task_abc123",
     "total_duration": 2340
   }
   ```

## Key Algorithms

### 1. Finding Similar Tasks
```aql
// Find tasks with similar descriptions that succeeded
FOR task IN tool_journey_nodes
    FILTER task.type == "task"
    FILTER CONTAINS(LOWER(task.description), LOWER(@keyword))
    
    // Traverse to find successful outcomes
    FOR v, e, p IN 1..20 OUTBOUND task tool_journey_edges
        FILTER v.type == "outcome" AND v.outcome == "success"
        
        // Extract tool sequence
        LET tools = (
            FOR node IN p.vertices
                FILTER node.type == "tool"
                RETURN node.name
        )
        
        RETURN {
            task_description: task.description,
            tool_sequence: tools,
            success_rate: AVG(p.edges[*].success_rate)
        }
```

### 2. Optimal Path Finding
Uses ArangoDB's K_SHORTEST_PATHS with success_rate as weight:
```aql
FOR path IN K_SHORTEST_PATHS
    "tool_journey_nodes/tool_assess_complexity"
    TO
    tool_journey_nodes
    tool_journey_edges
    OPTIONS {
        weightAttribute: "success_rate",
        defaultWeight: 0.1
    }
    FILTER LAST(path.vertices).outcome == "success"
```

### 3. Edge Weight Updates
After each journey:
- Success: `success_count++`, recalculate `success_rate`
- Failure: `failure_count++`, recalculate `success_rate`
- Prune edges with `success_rate < 0.2` after 10+ uses

## Learning Process

### 1. Journey Start
```python
# Agent starts a task
result = await start_graph_journey(
    "Fix ModuleNotFoundError for pandas",
    task_type="error_fix"
)
# Returns: ["assess_complexity", "query_converter", "track_solution_outcome"]
```

### 2. Real-time Recording
```python
# As agent uses tools
await record_graph_tool_call(
    journey_id="abc123",
    tool_name="assess_complexity",
    success=True,
    duration_ms=523
)
# Returns next tool recommendations based on graph
```

### 3. Journey Completion
```python
# When task completes
await complete_graph_journey(
    journey_id="abc123",
    outcome="success"
)
# Updates all edge weights in the path
```

### 4. Continuous Improvement
- Successful paths get reinforced (higher success_rate)
- Failed paths get weakened (lower success_rate)
- New patterns emerge from accumulated data
- Unsuccessful edges pruned periodically

## Benefits

1. **Context-Aware Predictions**: Different tool sequences for different task types
2. **Self-Improving**: Every journey updates the graph
3. **Explainable**: Can show why a sequence was recommended
4. **Resilient**: Failed paths naturally fade away
5. **Scalable**: Graph structure handles complex tool relationships

## Example Query Results

### Finding Optimal Sequence for Error Fix:
```json
{
  "predicted_sequence": [
    "assess_complexity",
    "query_converter", 
    "discover_patterns",
    "track_solution_outcome"
  ],
  "confidence": 0.85,
  "based_on": {
    "task_description": "Fix ImportError for requests module",
    "success_rate": 0.92,
    "similar_tasks": 47
  }
}
```

### Tool Performance Analysis:
```json
{
  "tool": "assess_complexity",
  "total_uses": 1523,
  "avg_success_rate": 0.87,
  "incoming_connections": 15,  // 15 different tools lead here
  "outgoing_connections": 8    // Leads to 8 different tools
}
```

## Integration with Existing Tools

Each MCP tool needs minimal changes:
```python
# Get journey context
journey_id = context.get("journey_id")

# Record the call
if journey_id:
    await record_graph_tool_call(
        journey_id=journey_id,
        tool_name="my_tool",
        success=result["success"],
        duration_ms=elapsed_ms
    )
```

This creates a powerful, self-learning system that gets better with every use!