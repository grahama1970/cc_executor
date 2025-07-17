# Redis Timeout Estimation System

## Overview

The CC Executor uses a sophisticated Redis-based timeout estimation system that learns from historical execution data to predict appropriate timeouts for Claude tasks.

## How It Works

### 1. Task Classification
When a task is submitted, the system classifies it based on:
- **Category**: calculation, code, writing, analysis, etc.
- **Complexity**: trivial, low, medium, high, extreme
- **Type**: More specific classification within category

### 2. Timeout Prediction
The Redis timer checks for:
1. **Exact History**: Previous executions of the same task
2. **Similar Tasks**: Tasks with same category and complexity
3. **Category Average**: Average time for the category
4. **Fallback**: Default estimation based on complexity

### 3. Safety Floor
The system applies a minimum 300-second safety floor to prevent premature timeouts.

## Usage

### Default Behavior (Recommended)
```python
# Let Redis estimate timeout automatically
result = await cc_execute(
    "Your task here",
    config=None,  # Uses Redis estimation
    stream=True
)
```

### Override with Custom Timeout
```python
# Force a specific timeout
result = await cc_execute(
    "Your task here", 
    config=CCExecutorConfig(timeout=600),  # 10 minutes
    stream=True
)
```

### Agent Prediction Mode
```python
# Use Claude to predict timeout based on task complexity
result = await cc_execute(
    "Complex multi-step task",
    agent_predict_timeout=True,  # Claude analyzes task
    stream=True
)
```

## Redis Data Structure

### Timing Keys
- `task:timing:{task_hash}` - Average execution time
- `task:last_run:{task_hash}` - Last execution timestamp
- `task:success_rate:{task_hash}` - Success rate (0-1)
- `task:category:{category}:avg` - Category average time
- `task:history` - Recent execution log

### Confidence Levels
- **1.00**: Exact task match found
- **0.80**: Similar tasks (same category/complexity)
- **0.50**: Category average only
- **0.30**: Fallback estimation

## Examples from Usage Tests

### Simple Calculation
```
Task: "What is 2+2?"
Category: calculation
Complexity: trivial
Redis Prediction: 17s (confidence: 1.00)
Applied Timeout: 300s (safety floor)
Actual Time: 10.1s
```

### Code Generation
```
Task: "Create a Python function..."
Category: code
Complexity: low
Redis Prediction: 96s (confidence: 1.00)
Applied Timeout: 300s (safety floor)
Actual Time: 39.0s
```

## Monitoring

### View Redis Predictions
```python
from cc_executor.prompts.redis_task_timing import RedisTaskTimer

timer = RedisTaskTimer()
estimation = await timer.estimate_complexity("Your task")
print(f"Predicted: {estimation['timeout']}s")
print(f"Category: {estimation['category']}")
print(f"Confidence: {estimation['confidence']}")
```

### Export History
```python
history = await export_execution_history(limit=100)
print(history)
```

## Best Practices

1. **Use Default Estimation**: Let Redis learn and improve over time
2. **Monitor Variances**: Check the variance percentages in logs
3. **Update on Failures**: Failed executions don't update timing data
4. **Category Patterns**: Similar tasks benefit from shared learning

## Troubleshooting

### Timeouts Too Short
- Check if safety floor is being applied
- Review task classification accuracy
- Consider using `agent_predict_timeout=True`

### Timeouts Too Long
- Redis will adjust downward as it learns
- Variance tracking helps identify overestimation
- Manual override available for known quick tasks

## Related Files
- `/src/cc_executor/prompts/redis_task_timing.py` - Core implementation
- `/src/cc_executor/client/cc_execute.py` - Integration point
- `/src/cc_executor/core/usage_cc_execute.py` - Usage examples