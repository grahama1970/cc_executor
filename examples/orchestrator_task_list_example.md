# Example: Orchestrator Using CC-Orchestration MCP Tools

This shows how a Claude orchestrator would use the cc-orchestration tools in a real task list.

## Multi-Step Project: Build a Secure Web API

### Task 1: Check Infrastructure
```python
# First, verify our execution infrastructure is ready
status = mcp__cc-orchestration__check_websocket_status()
# Returns: {"status": "running", "port": "8003", "health": {"uptime": 1234, "active_sessions": 0}}
```

✅ WebSocket server is running on port 8003

### Task 2: Validate Task List
```python
tasks = [
    "Create a FastAPI application with SQLAlchemy models for a blog system",
    "Implement JWT authentication with secure password hashing", 
    "Add rate limiting and CORS protection",
    "Write comprehensive pytest tests with 90% coverage",
    "Create API documentation with interactive examples"
]

validation = mcp__cc-orchestration__validate_task_list(tasks)
# Returns validation results with warnings about dependencies
```

⚠️ Warning: Task 4 depends on tasks 1-3, recommend cc_execute.md for isolation

### Task 3: Get Execution Strategy
```python
strategy = mcp__cc-orchestration__suggest_execution_strategy(tasks)
```

Recommended execution plan:
- Task 1: 🔄 cc_execute.md (Complex: creates project structure)
- Task 2: 🔄 cc_execute.md (Complex: security implementation)  
- Task 3: 🔄 cc_execute.md (Medium: needs fresh context)
- Task 4: 🔄 cc_execute.md (Complex: needs all previous code)
- Task 5: ➡️ Direct (Simple: documentation generation)

### Task 4: Execute Task 1 with cc_execute.md

Using cc_execute.md: Create a FastAPI application with SQLAlchemy models for a blog system. Include:
- User model with id, username, email, password_hash, created_at
- Post model with id, title, content, author_id, created_at, updated_at
- Comment model with id, content, post_id, author_id, created_at
- Proper relationships between models
- Database initialization script
- Basic CRUD endpoints for posts

### Task 5: Monitor Execution
```python
# While task is running, monitor progress
monitor = mcp__cc-orchestration__monitor_execution()
# Returns: {"active_sessions": 1, "recent_activity": [...]}
```

### Task 6: Check Task Complexity Before Next Step
```python
complexity = mcp__cc-orchestration__get_task_complexity(
    "Implement JWT authentication with secure password hashing"
)
# Returns: {"score": 8, "level": "high", "recommended_timeout": 600}
```

### Task 7: Execute Task 2 with cc_execute.md

Using cc_execute.md: Implement JWT authentication with secure password hashing. Include:
- Bcrypt for password hashing
- JWT token generation and validation
- Login/register endpoints
- Protected route decorators
- Token refresh mechanism
- Proper error handling

### Task 8: Continue Pattern...

The orchestrator continues this pattern:
1. Use MCP tools to analyze and plan
2. Execute complex tasks with cc_execute.md
3. Monitor progress via logs
4. Learn from execution history

### Task 9: Review Execution History
```python
history = mcp__cc-orchestration__get_execution_history(limit=10)
# Use this to improve future task planning
```

## Key Benefits

1. **Intelligence Before Action**: Tools provide insights without executing
2. **Fresh Context**: Each cc_execute.md gets 200K tokens
3. **Sequential Guarantee**: WebSocket ensures proper ordering
4. **Monitoring**: Real-time progress tracking via logs
5. **Learning**: History helps optimize future workflows

## What NOT to Do

❌ DON'T try to execute directly:
```python
# WRONG - This tool doesn't exist anymore!
result = mcp__cc-execute__execute("Build API")
```

✅ DO use orchestration tools + cc_execute.md:
```python
# RIGHT - Analyze first
complexity = mcp__cc-orchestration__get_task_complexity("Build API")
# Then use cc_execute.md prompt for actual execution
```