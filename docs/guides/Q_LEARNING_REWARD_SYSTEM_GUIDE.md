# Q-Learning Reward System Guide

## Overview

The Q-Learning reward system is designed to help AI agents learn optimal tool sequences for completing tasks. It uses reinforcement learning principles to track which tool combinations work best for different types of problems, learning from both successes and failures.

## Core Components

### 1. State Representation

The system represents the agent's current state using these key attributes:

```python
# From mcp_tool_journey.py (lines 132-139)
state = {
    "current_tool": current_tool,
    "tools_used": tools_used,  # List of previously used tools
    "context": {
        "error_type": error_type,  # e.g., "ModuleNotFoundError"
        "category": category,      # e.g., "import_error"
        "file_path": file_path
    },
    "task_type": task_type
}
```

States are hashed using MD5 for efficient storage:

```python
# From mcp_tool_journey.py (lines 141-152)
def _hash_state(state: Dict[str, Any]) -> str:
    """Create a hash for state representation."""
    state_str = json.dumps({
        "current_tool": state.get("current_tool", ""),
        "tools_used": sorted(state.get("tools_used", [])),
        "error_type": state.get("context", {}).get("error_type", ""),
        "category": state.get("context", {}).get("category", ""),
        "task_type": state.get("task_type", "")
    }, sort_keys=True)
    return hashlib.md5(state_str.encode()).hexdigest()[:16]
```

### 2. Reward Structure

The system uses carefully calibrated rewards to encourage efficient problem-solving:

```python
# From mcp_tool_journey.py (lines 51-62)
REWARDS = {
    "optimal_completion": 10.0,      # Completed in ≤3 steps
    "suboptimal_completion": 5.0,    # Completed but took more steps
    "per_extra_step": -0.5,          # Penalty for each step beyond optimal
    "per_tool_call": -0.1,           # Small cost per tool use
    "failed_tool_call": -1.0,        # Tool execution failed
    "task_failure": -5.0,            # Couldn't complete the task
    "timeout_penalty": -3.0,         # Task took too long
    "novel_success": 2.0             # Bonus for discovering new solutions
}
```

### 3. Q-Learning Algorithm

Q-values represent the expected future reward for taking an action in a given state:

```python
# From mcp_tool_journey.py (lines 45-49)
LEARNING_RATE = 0.1        # How quickly to update Q-values
DISCOUNT_FACTOR = 0.9      # How much to value future rewards
EXPLORATION_RATE = 0.3     # Initial exploration vs exploitation
MIN_EXPLORATION_RATE = 0.05
EXPLORATION_DECAY = 0.995  # Reduce exploration over time
```

Q-value update formula (implemented in `record_tool_step`):
```
Q(s,a) = Q(s,a) + α[r + γ·max(Q(s',a')) - Q(s,a)]
```

Where:
- α = learning rate
- r = immediate reward
- γ = discount factor
- s' = next state
- a' = possible actions in next state

### 4. Thompson Sampling

Thompson Sampling balances exploration vs exploitation using Beta distributions:

```python
# From mcp_tool_journey.py (lines 222-234)
# Sample from Beta distribution for each action
samples = {}
for action in possible_actions:
    params = thompson_params.get(action, {"alpha": 1.0, "beta": 1.0})
    # Higher alpha = more successes, higher beta = more failures
    samples[action] = np.random.beta(params["alpha"], params["beta"])

# Select action with highest sampled value
best_action = max(samples.items(), key=lambda x: x[1])
```

## Usage Scenarios

### Scenario 1: Starting a New Journey

When an agent begins a task, it queries for optimal tool sequences:

```python
# Agent code using mcp_tool_journey
result = await start_journey(
    task_description="Fix ModuleNotFoundError for pandas",
    context=json.dumps({
        "error_type": "ModuleNotFoundError",
        "module": "pandas",
        "file_path": "/app/data_processor.py"
    })
)

# Returns:
{
    "journey_id": "journey_abc123",
    "recommended_sequence": [
        {"tool": "assess_complexity", "q_value": 0.85, "confidence": 0.92},
        {"tool": "discover_patterns", "q_value": 0.78, "confidence": 0.88},
        {"tool": "track_solution_outcome", "q_value": 0.90, "confidence": 0.95}
    ],
    "alternatives": [...],
    "exploration_bonus": 0.1  # If trying new approaches
}
```

### Scenario 2: Recording Tool Usage

As the agent uses tools, it records each step:

```python
# After using a tool
result = await record_tool_step(
    journey_id="journey_abc123",
    tool_name="assess_complexity",
    success=True,
    duration_ms=1500,
    result_summary="Identified as simple import error"
)

# What happens internally:
# 1. Calculate immediate reward (-0.1 for tool use)
# 2. Update Q-value for (current_state, "assess_complexity")
# 3. Update Thompson parameters (alpha += 1 for success)
# 4. Get recommendation for next tool based on new state
```

### Scenario 3: Completing a Journey

When the task is complete, the system calculates final rewards:

```python
# Successful completion
result = await complete_journey(
    journey_id="journey_abc123",
    outcome="success",
    solution_description="Added pandas to requirements.txt"
)

# Internal process:
# 1. Calculate total reward:
#    - Base: 10.0 (optimal completion, used 3 tools)
#    - Tool costs: -0.3 (3 × -0.1)
#    - Novel bonus: +2.0 (if this solution path is new)
#    - Total: 11.7
#
# 2. Backpropagate rewards through the sequence:
#    - track_solution_outcome: Q += 0.1 × (11.7 - old_Q)
#    - discover_patterns: Q += 0.1 × (0.9 × next_Q - old_Q)
#    - assess_complexity: Q += 0.1 × (0.9 × next_Q - old_Q)
```

### Scenario 4: Learning from Failure

Failed attempts also update the system:

```python
# Failed attempt
result = await complete_journey(
    journey_id="journey_xyz789",
    outcome="failure",
    solution_description="Could not resolve dependency conflict"
)

# Internal process:
# 1. Calculate penalty: -5.0 (task failure) - 0.5 (5 tools used)
# 2. Update Q-values negatively for this sequence
# 3. Update Thompson beta parameters (failures) for each tool
# 4. System learns to avoid this sequence for similar problems
```

## Database Storage

### Q-Values Collection (mcp_arango_tools.py)

```python
# Structure in q_values collection
{
    "_key": "auto_generated",
    "state_hash": "a1b2c3d4e5f6",  # MD5 hash of state
    "action": "assess_complexity",
    "q_value": 0.85,
    "visit_count": 142,
    "created_at": "2024-01-15T10:00:00Z",
    "last_updated": "2024-01-15T15:30:00Z"
}
```

### Thompson Parameters Collection

```python
# Structure in thompson_params collection
{
    "_key": "auto_generated",
    "state_hash": "a1b2c3d4e5f6",
    "action": "assess_complexity",
    "alpha": 89.0,  # Successes
    "beta": 11.0,   # Failures
    "created_at": "2024-01-15T10:00:00Z",
    "last_updated": "2024-01-15T15:30:00Z"
}
```

### Tool Journey Edges

```python
# Structure in tool_journey_edges collection
{
    "_from": "tool_nodes/assess_complexity",
    "_to": "tool_nodes/discover_patterns",
    "context_type": "ModuleNotFoundError",
    "q_value": 0.82,
    "success_rate": 0.89,
    "total_uses": 142,
    "thompson_alpha": 126.0,
    "thompson_beta": 16.0
}
```

## Key Methods

### mcp_arango_tools.py

1. **get_q_value(state_hash, action)** (lines 1868-1899)
   - Retrieves Q-value for state-action pair
   - Returns 0.0 for new pairs

2. **update_q_value(state_hash, action, new_q_value)** (lines 1901-1948)
   - Updates Q-value with visit counting
   - Uses UPSERT for atomic operations

3. **get_thompson_params(state_hash, action)** (lines 1950-1981)
   - Gets Beta distribution parameters
   - Returns (1.0, 1.0) for new pairs

4. **update_thompson_params(state_hash, action, success)** (lines 1983-2027)
   - Increments alpha (success) or beta (failure)
   - Calculates success rate

5. **bootstrap_q_values(limit)** (lines 2029-2107)
   - Initializes Q-values from historical data
   - Processes past journeys to extract patterns

### mcp_tool_sequence_optimizer.py

1. **optimize_tool_sequence(task_description, error_context)** (lines 73-269)
   - Queries historical journeys and Q-values
   - Returns recommended sequence with confidence scores
   - Provides alternatives based on Q-values

2. **record_sequence_step(journey_id, tool_name, success, duration_ms)** (lines 271-319)
   - Tracks progress through sequences
   - Suggests next tool based on patterns

3. **complete_sequence_journey(journey_id, outcome, solution_description)** (lines 321-437)
   - Calculates performance metrics
   - Compares expected vs actual rewards
   - Extracts lessons for high-performance sequences

### mcp_tool_journey.py

1. **start_journey(task_description, context)** (lines 154-307)
   - Creates embeddings for task similarity
   - Queries Q-values and similar journeys
   - Uses Thompson Sampling for action selection

2. **record_tool_step(journey_id, tool_name, success, duration_ms)** (lines 309-397)
   - Updates journey state
   - Calculates immediate rewards
   - Updates Q-values in real-time
   - Updates Thompson parameters

3. **complete_journey(journey_id, outcome, solution_description)** (lines 399-520)
   - Calculates final rewards
   - Backpropagates Q-values through sequence
   - Stores journey for future learning

## How It All Works Together

1. **Task Arrival**: Agent describes task → System finds similar past tasks → Recommends tool sequence based on Q-values

2. **Exploration vs Exploitation**: Thompson Sampling occasionally suggests less-tested tools to discover better solutions

3. **Real-time Learning**: Each tool use immediately updates Q-values and success rates

4. **Backpropagation**: Journey completion triggers reverse updates through the entire sequence

5. **Pattern Recognition**: System learns that certain tools work well together for specific problem types

6. **Continuous Improvement**: More journeys = better Q-value estimates = more optimal recommendations

## Example: Complete Flow

```python
# 1. Agent encounters an error
error = "ModuleNotFoundError: No module named 'pandas'"

# 2. Start journey
journey = await start_journey(
    "Fix ModuleNotFoundError for pandas",
    {"error_type": "ModuleNotFoundError", "module": "pandas"}
)
# Recommended: [assess_complexity, discover_patterns, track_solution_outcome]

# 3. Execute first tool
await record_tool_step(journey["journey_id"], "assess_complexity", True, 1200)
# Q(state0, assess_complexity) updated
# Thompson α increased

# 4. Execute second tool  
await record_tool_step(journey["journey_id"], "discover_patterns", True, 3400)
# Q(state1, discover_patterns) updated

# 5. Execute final tool
await record_tool_step(journey["journey_id"], "track_solution_outcome", True, 500)
# Q(state2, track_solution_outcome) updated

# 6. Complete journey
await complete_journey(
    journey["journey_id"], 
    "success",
    "Added pandas to requirements.txt and ran pip install"
)
# Reward calculated: 10.0 - 0.3 = 9.7
# Backpropagation updates all Q-values in sequence
# Future similar errors will follow this proven path

# 7. Next time this error occurs
next_journey = await start_journey(
    "Fix ModuleNotFoundError for numpy",
    {"error_type": "ModuleNotFoundError", "module": "numpy"}  
)
# System recognizes similarity, recommends same successful sequence
# Confidence is higher due to previous success
```

This creates a self-improving system where the AI agent gets better at solving problems by learning from experience!