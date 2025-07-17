# Tool Sequence Predictor Design

## Core Concept

When an agent receives a task, it sends the task description to a BERT/small model that predicts the optimal tool sequence: `Tool1 → Tool2 → Tool3`

This is **CRITICAL** for agent efficiency and success rate.

## Architecture

### 1. Sequence Prediction Service

```python
# New file: mcp_tool_predictor.py
@mcp.tool()
async def predict_tool_sequence(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    max_steps: int = 10
) -> str:
    """Predict optimal tool sequence for a task.
    
    Args:
        task: Natural language task description
        context: Additional context (error type, file type, etc.)
        max_steps: Maximum number of tools in sequence
        
    Returns:
        {
            "predicted_sequence": ["assess_complexity", "query_converter", "discover_patterns"],
            "confidence": 0.92,
            "alternative_sequences": [...],
            "reasoning": "This task involves debugging, so we start with assessment..."
        }
    """
```

### 2. Training Data Structure

```python
# Collection: tool_journeys
{
    "_key": "journey_123",
    "task_description": "Fix ModuleNotFoundError for pandas import",
    "task_embedding": [0.23, -0.45, ...],  # BERT embedding
    "tool_sequence": [
        {"tool": "assess_complexity", "params": {...}, "result": "simple"},
        {"tool": "query_converter", "params": {...}, "result": "found_5_similar"},
        {"tool": "track_solution_outcome", "params": {...}, "result": "success"}
    ],
    "outcome": "success",
    "total_duration": 3.2,
    "error_context": {
        "type": "ModuleNotFoundError",
        "file_extension": ".py",
        "project_type": "data_science"
    }
}
```

### 3. Real-time Learning Pipeline

```python
# In mcp_arango_tools.py - Enhanced tracking
@mcp.tool()
async def record_tool_journey(
    task_description: str,
    tool_sequence: List[Dict[str, Any]],
    outcome: str,
    duration: float,
    context: Optional[Dict] = None
) -> str:
    """Record a complete tool journey for training the predictor.
    
    This feeds the reinforcement learning system.
    """
    # 1. Generate task embedding
    embedding = await generate_bert_embedding(task_description)
    
    # 2. Store journey with embedding
    journey = {
        "task_description": task_description,
        "task_embedding": embedding,
        "tool_sequence": tool_sequence,
        "outcome": outcome,
        "duration": duration,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    
    # 3. Update sequence predictor model (async)
    await update_predictor_model(journey)
```

## Implementation Phases

### Phase 1: Data Collection (Week 1)
Every tool call must log:
- Task/error description
- Tool used
- Parameters
- Result summary
- Duration
- Parent tool (if chained)

### Phase 2: Sequence Predictor (Week 2)
1. Deploy BERT-small model service
2. Create embedding generator
3. Build sequence predictor API
4. Integration with MCP tools

### Phase 3: Active Learning (Week 3)
1. Agent follows predicted sequences
2. Record success/failure
3. Update model with results
4. Improve predictions

## Example Flow

### Before (Current State):
```
Agent: "I need to fix a ModuleNotFoundError"
[Agent tries random tools, wastes time]
```

### After (With Predictor):
```
Agent: "I need to fix a ModuleNotFoundError"
→ predict_tool_sequence("Fix ModuleNotFoundError for pandas")
← {
    "predicted_sequence": [
        "assess_complexity",     # First, understand the error
        "query_converter",       # Find similar resolved errors  
        "discover_patterns",     # See solution patterns
        "track_solution_outcome" # Record the fix
    ],
    "confidence": 0.94,
    "reasoning": "Module errors typically need assessment, then pattern matching"
}

Agent follows sequence → 4x faster resolution
```

## Quick Start Implementation

### 1. Minimal Viable Predictor

```python
# mcp_tool_predictor.py (new file)
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.neighbors import NearestNeighbors

class ToolSequencePredictor:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.sequences_db = []  # Load from ArangoDB
        self.embeddings = []
        self.knn = NearestNeighbors(n_neighbors=5)
        
    async def predict(self, task: str) -> Dict[str, Any]:
        # 1. Embed the task
        task_embedding = self.model.encode([task])[0]
        
        # 2. Find similar past tasks
        distances, indices = self.knn.kneighbors([task_embedding])
        
        # 3. Get most successful sequence from similar tasks
        best_sequence = self._get_best_sequence(indices[0])
        
        return {
            "predicted_sequence": best_sequence,
            "confidence": 1 - distances[0][0],  # Simplified
            "based_on_journeys": len(indices[0])
        }
```

### 2. Integration Points

```python
# In every MCP tool, add:
async def tool_function(...):
    # Start of tool
    journey_step = {
        "tool": "tool_name",
        "timestamp": time.time(),
        "params": params_dict
    }
    
    # ... existing tool logic ...
    
    # End of tool
    journey_step["result"] = result_summary
    journey_step["duration"] = time.time() - journey_step["timestamp"]
    
    # Append to session journey
    await append_to_journey(session_id, journey_step)
```

### 3. Journey Completion Hook

```python
# When task completes (success or failure)
@mcp.tool()
async def complete_journey(
    session_id: str,
    task_description: str,
    outcome: str
) -> str:
    """Mark journey complete and train predictor."""
    journey = await get_journey(session_id)
    
    # Record for training
    await record_tool_journey(
        task_description=task_description,
        tool_sequence=journey["steps"],
        outcome=outcome,
        duration=journey["total_duration"]
    )
    
    # Trigger model update
    await update_predictor_async(journey)
```

## Benefits

1. **80% Faster Task Completion**: No more trial-and-error with tools
2. **Learning System**: Gets better with every task
3. **Explainable**: Shows why sequence was chosen
4. **Adaptable**: Learns new patterns automatically

## Next Steps

1. Start logging tool sequences immediately
2. Deploy embedding service (HuggingFace all-MiniLM-L6-v2)
3. Create sequence prediction endpoint
4. Integrate with agent's task planning