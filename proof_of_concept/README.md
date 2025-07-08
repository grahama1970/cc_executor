# CC Executor - Proof of Concept

Simple async interface for executing complex Claude tasks.

## Features

- **Simple API**: Just like LiteLLM - `await cc_execute("task")`
- **Complex Task Support**: Handles multi-hour execution 
- **Streaming Output**: Real-time visibility into execution
- **Error Handling**: Timeouts, API errors, process management
- **Task Lists**: Execute multiple related tasks sequentially
- **Transcript Saving**: All outputs saved for debugging

## Installation

```python
# Add to your project
from cc_executor import cc_execute

# Set API key
export ANTHROPIC_API_KEY=your_key
```

## Basic Usage

```python
import asyncio
from cc_executor import cc_execute

async def main():
    # Simple task - string output
    result = await cc_execute("Write a hello world in Python")
    print(result)
    
    # Structured JSON output (recommended for programmatic use)
    result = await cc_execute(
        "Create a function to calculate factorial",
        return_json=True
    )
    print(result['result'])   # The actual code
    print(result['summary'])  # What was done
    print(result['files_created'])  # List of created files
    
    # Complex task with streaming
    result = await cc_execute(
        "Create a complete REST API with auth, database, and tests",
        stream=True  # See output in real-time
    )

asyncio.run(main())
```

### JSON Output Schema

When using `return_json=True`, responses follow this schema:

```json
{
    "result": "The main output/code/answer",
    "summary": "Brief summary of what was done",
    "files_created": ["list", "of", "created", "files"],
    "files_modified": ["list", "of", "modified", "files"],
    "execution_uuid": "uuid-for-verification"
}
```

## Task List Execution

```python
from cc_executor import cc_execute_list

tasks = [
    "1. Create project structure", 
    "2. Add database models",
    "3. Implement API endpoints",
    "4. Add authentication",
    "5. Write tests"
]

results = await cc_execute_list(tasks, sequential=True)
```

## Configuration

```python
from cc_executor import cc_execute, CCExecutorConfig

config = CCExecutorConfig(
    timeout=7200,  # 2 hours for complex tasks
    stream_output=True,
    save_transcript=True,
    transcript_dir=Path("/tmp/cc_executor_transcripts")
)

result = await cc_execute("complex task", config=config)
```

### Agent-Based Timeout Prediction

For complex or novel tasks, you can use Claude to predict the appropriate timeout:

```python
# Let Claude analyze the task and predict timeout
result = await cc_execute(
    "Build a complete e-commerce platform with microservices",
    agent_predict_timeout=True  # Claude will predict timeout
)
```

This is useful when:
- The task is novel or complex
- You're unsure how long it will take
- Redis doesn't have historical data for similar tasks

The agent considers:
- Task complexity and scope
- Number of files/operations needed
- MCP tool usage overhead
- Typical Claude processing patterns

## Why This Approach?

1. **No WebSocket Server**: Direct subprocess execution
2. **No Deployment**: Just import and use
3. **Streaming Support**: See progress on long tasks
4. **Simple Integration**: Works like any async library

## Advanced Examples

### Game Engine Algorithm Competition

Spawn multiple Claude instances to compete on creating better algorithms:

```python
from advanced_examples import game_engine_algorithm_competition

# Run 3 Claude instances concurrently to create better algorithms
# than the fast inverse square root
results = await game_engine_algorithm_competition()
```

### Distributed Web Scraper

Build a complete distributed scraper with concurrent components:

```python
from advanced_examples import distributed_web_scraper

# Each Claude instance handles a different component
# Results are combined into a working system
await distributed_web_scraper()
```

### Microservices Architecture

Generate a complete microservices system concurrently:

```python
from advanced_examples import microservices_architecture

# Creates auth, payment, notification services + API gateway
# Includes docker-compose.yml for deployment
await microservices_architecture()
```

### Machine Learning Pipeline

Build an ML pipeline with concurrent stage development:

```python
from advanced_examples import machine_learning_pipeline

# Preprocessing, training, and deployment stages built in parallel
await machine_learning_pipeline()
```

## Testing

Run the test suite:

```bash
python test_executor.py
```

Run advanced examples:

```bash
python advanced_examples.py
```

This will test:
- Basic execution
- Complex multi-file tasks
- Task list execution  
- Streaming output
- Error handling
- Concurrent execution
- Multi-Claude coordination

## Next Steps

To integrate into your project:

1. Copy the `cc_executor` module
2. Add to your `pyproject.toml`:
   ```toml
   dependencies = [
       "anthropic",  # If using API directly
   ]
   ```
3. Import and use:
   ```python
   from cc_executor import cc_execute
   result = await cc_execute("your complex task")
   ```

That's it! No servers, no WebSockets, just simple async execution.