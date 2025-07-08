# FastAPI Complex Service - MCP TOOL VERSION

## Test Configuration
- **Test Type**: MCP Tool Pattern
- **Purpose**: Test reliability of mcp__cc-execute__execute vs prompt references
- **Complexity**: Mixed (some tasks use MCP tool, some direct orchestrator)
- **WebSocket Timeout Testing**: Complex tasks designed to test timeout predictions

## Task List for Sequential Execution

### Task 1: Project Research and Planning
**Execution**: Direct (Orchestrator handles this)
**Command**: Use perplexity-ask to research the latest FastAPI best practices for 2025, including:
- Recommended project structure patterns
- Security best practices for authentication
- Performance optimization techniques
- WebSocket implementation patterns
- Testing strategies

Save the research findings to `research_findings.md`.

### Task 2: Complex Project Setup with Database Models
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Create a comprehensive FastAPI project structure with SQLAlchemy models, Alembic migrations, and proper separation of concerns. Include models for User, Post, and Comment with relationships. Create the following structure:
- fastapi_service/
  - app/
    - __init__.py
    - main.py
    - models/ (user.py, post.py, comment.py)
    - schemas/ (user.py, post.py, comment.py)
    - database/ (connection.py, session.py)
    - api/endpoints/ (users.py, posts.py, comments.py)
  - alembic/alembic.ini
  - requirements.txt
  - .env.example

Include proper type hints, pydantic schemas, and database relationships."

Set timeout to 300 seconds for this complex task.

### Task 3: Quick Configuration Check
**Execution**: Direct (Orchestrator)
**Command**: Read the generated .env.example and requirements.txt files to verify they contain appropriate configurations. Check that SQLAlchemy, Alembic, FastAPI, and other necessary dependencies are included.

### Task 4: Authentication System Implementation
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Implement a complete JWT-based authentication system with:
- Password hashing with bcrypt
- JWT token generation and validation
- OAuth2 with Password flow
- Protected endpoints decorator
- User registration endpoint with email validation
- Login endpoint with proper error handling
- Token refresh mechanism
- Role-based access control (RBAC) with admin, user, and guest roles
- Account lockout after failed attempts
- Password reset functionality with email tokens

Include comprehensive error handling, logging, and security best practices."

Set timeout to 300 seconds.

### Task 5: Run Database Migrations
**Execution**: Direct (Orchestrator)
**Command**: Execute the following commands to set up the database:
1. `cd fastapi_service && alembic init alembic` (if not already done)
2. `alembic revision --autogenerate -m "Initial models"`
3. `alembic upgrade head`

Report any errors or issues with the migration process.

### Task 6: Complex CRUD Operations with Advanced Queries
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Create advanced CRUD operations for all models with:
- Pagination with cursor-based and offset-based options
- Complex filtering (date ranges, text search, nested filters)
- Sorting by multiple fields
- Eager loading to prevent N+1 queries
- Bulk operations (bulk create, update, delete)
- Soft delete functionality
- Audit trails for all operations
- Transaction support with rollback
- Custom SQL queries for complex aggregations
- Full-text search implementation
- Export functionality (CSV, JSON, Excel)"

Set timeout to 300 seconds.

### Task 7: API Documentation Check
**Execution**: Direct (Orchestrator)
**Command**: Start the FastAPI application with `uvicorn app.main:app --reload` and check the auto-generated API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

Verify that all endpoints are properly documented with request/response schemas.

### Task 8: Real-time Features with WebSockets
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Implement real-time features using WebSockets:
- WebSocket connection manager with rooms
- Real-time notifications for new posts and comments
- Live typing indicators
- Online user presence tracking
- Message queuing for offline users
- Rate limiting for WebSocket messages
- Reconnection logic with exponential backoff
- Binary data support for file transfers
- Broadcasting to specific user groups
- WebSocket authentication and authorization
- Connection pooling and management

Handle edge cases like connection drops, duplicate messages, and scaling considerations."

Set timeout to 300 seconds.

### Task 9: Performance Testing
**Execution**: Direct (Orchestrator)
**Command**: Run performance tests using Apache Bench (ab) or similar tools:
1. Test authentication endpoints: `ab -n 1000 -c 10 http://localhost:8000/api/v1/auth/login`
2. Test CRUD operations: `ab -n 1000 -c 10 http://localhost:8000/api/v1/users/`
3. Generate a performance report with response times and throughput

### Task 10: Background Tasks and Scheduling
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Implement background task processing:
- Celery integration with Redis as broker
- Scheduled tasks with Celery Beat
- Email sending queue (welcome emails, notifications)
- Image processing pipeline (thumbnails, optimization)
- Data export jobs
- Database cleanup tasks
- Report generation (PDF, Excel)
- Webhook delivery system with retries
- Long-running task progress tracking
- Task result storage and retrieval
- Priority queues for different task types
- Dead letter queue for failed tasks"

Set timeout to 300 seconds.

### Task 11: Security Audit
**Execution**: Direct (Orchestrator)
**Command**: Use MCP tools to perform a security audit:
1. Use ripgrep to search for hardcoded secrets: `rg -i "password|secret|key" --type py`
2. Check for SQL injection vulnerabilities in raw queries
3. Verify CORS configuration is properly restrictive
4. Check that all endpoints have appropriate authentication

### Task 12: Comprehensive Testing Suite
**Execution**: Using MCP tool
**Command**: Use mcp__cc-execute__execute with task: "Create a comprehensive testing suite:
- Unit tests for all models and schemas (100% coverage)
- Integration tests for all API endpoints
- WebSocket connection tests
- Authentication flow tests
- Database transaction tests
- Mocking external services
- Performance tests with locust
- Security tests (SQL injection, XSS, CSRF)
- Load testing scenarios
- End-to-end tests with Playwright
- Continuous integration setup
- Test data factories
- Mutation testing
- Contract testing for API compatibility"

Set timeout to 400 seconds (extra time for comprehensive test generation).

### Task 13: Final Integration Test
**Execution**: Direct (Orchestrator)
**Command**: Run the complete test suite and generate a coverage report:
1. `pytest --cov=app --cov-report=html --cov-report=term`
2. Check that coverage is above 80%
3. Review the HTML coverage report
4. Document any failing tests or areas needing improvement

## MCP Tool Usage Pattern

For each MCP tool invocation, the orchestrator should:
```python
# Example for Task 2
result = mcp__cc-execute__execute(
    task="Create a comprehensive FastAPI project structure...",
    timeout=300
)

# The tool will:
# 1. Spawn a fresh Claude instance with 200K context
# 2. Execute the task with full isolation
# 3. Return results via WebSocket
# 4. Block until completion (sequential execution guaranteed)
```

## Expected Outcomes
- **Direct tasks (5)**: Quick execution by orchestrator, typically < 30 seconds
- **MCP tool tasks (8)**: Complex generation requiring fresh context, 2-5 minutes each
- **Total execution time**: 20-40 minutes
- **WebSocket stability**: No timeouts despite long-running MCP executions
- **Sequential guarantee**: Each task waits for previous completion

## Success Criteria
- All 13 tasks complete successfully
- MCP tool provides same reliability as prompt references
- No WebSocket timeouts on long-running tasks
- Direct tasks provide quick feedback and validation
- MCP tool tasks produce comprehensive, high-quality code
- Final application is fully functional with tests passing

## Comparison Points vs Prompt Version
1. **Syntax**: MCP tool calls vs prompt references
2. **Error handling**: How each approach handles failures
3. **Timeout management**: MCP timeout parameter vs prompt-based
4. **Output format**: JSON responses vs markdown output
5. **Debugging**: Stack traces and error visibility
6. **Reliability**: Success rate comparison

## Failure Recovery
If any MCP tool task times out:
1. Check Redis timeout predictions
2. Increase timeout parameter for that specific task
3. Consider breaking complex tasks into smaller subtasks
4. Fall back to prompt reference if MCP consistently fails