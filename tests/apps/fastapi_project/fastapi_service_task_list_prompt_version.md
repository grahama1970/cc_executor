# FastAPI Complex Service - PROMPT VERSION (cc_execute.md)

## Test Configuration
- **Test Type**: Prompt Reference Pattern
- **Purpose**: Test reliability of cc_execute.md prompt references
- **Complexity**: High (to test WebSocket timeouts and Redis predictions)

## Task List for Sequential Execution

### Task 1: Complex Project Setup with Database Models
**Execution**: Using cc_execute.md
**Command**: Create a comprehensive FastAPI project structure with SQLAlchemy models, Alembic migrations, and proper separation of concerns. Include models for User, Post, and Comment with relationships. Create the following structure:
- fastapi_service/
  - app/
    - __init__.py
    - main.py
    - models/
      - __init__.py
      - user.py
      - post.py
      - comment.py
    - schemas/
      - __init__.py
      - user.py
      - post.py
      - comment.py
    - database/
      - __init__.py
      - connection.py
      - session.py
    - api/
      - __init__.py
      - endpoints/
        - __init__.py
        - users.py
        - posts.py
        - comments.py
  - alembic/
    - alembic.ini
  - requirements.txt
  - .env.example

Include proper type hints, pydantic schemas, and database relationships. This is a complex task that should take significant time.

### Task 2: Authentication System Implementation
**Execution**: Using cc_execute.md
**Command**: Implement a complete JWT-based authentication system with the following features:
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

This should include comprehensive error handling, logging, and security best practices.

### Task 3: Complex CRUD Operations with Advanced Queries
**Execution**: Using cc_execute.md
**Command**: Create advanced CRUD operations for all models with:
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
- Export functionality (CSV, JSON, Excel)

Include comprehensive error handling and performance optimizations.

### Task 4: Real-time Features with WebSockets
**Execution**: Using cc_execute.md
**Command**: Implement real-time features using WebSockets:
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

This should handle edge cases like connection drops, duplicate messages, and scaling considerations.

### Task 5: Advanced API Features and Middleware
**Execution**: Using cc_execute.md
**Command**: Add advanced API features:
- Custom middleware for request/response logging
- Rate limiting with Redis backend
- API versioning (v1, v2)
- Request ID tracking
- Compression middleware
- CORS with dynamic origins
- API key authentication as alternative to JWT
- GraphQL endpoint alongside REST
- OpenAPI schema customization
- Response caching with ETags
- Request validation middleware
- Circuit breaker pattern for external services
- Metrics collection (Prometheus format)
- Health checks with dependency status

### Task 6: Background Tasks and Scheduling
**Execution**: Using cc_execute.md
**Command**: Implement background task processing:
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
- Dead letter queue for failed tasks

### Task 7: Comprehensive Testing Suite
**Execution**: Using cc_execute.md
**Command**: Create a comprehensive testing suite:
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
- Contract testing for API compatibility

### Task 8: Production Deployment Configuration
**Execution**: Using cc_execute.md
**Command**: Create production-ready deployment configuration:
- Multi-stage Dockerfile with minimal image
- Docker Compose for local development
- Kubernetes manifests (Deployment, Service, Ingress)
- Helm chart with configurable values
- GitHub Actions CI/CD pipeline
- Database migration automation
- Secret management with Vault
- Monitoring with Prometheus and Grafana
- Log aggregation with ELK stack
- Distributed tracing with Jaeger
- Auto-scaling configuration
- Blue-green deployment strategy
- Backup and disaster recovery procedures

### Task 9: Performance Optimization and Caching
**Execution**: Using cc_execute.md
**Command**: Implement comprehensive performance optimizations:
- Redis caching layer for all endpoints
- Database query optimization with EXPLAIN analysis
- Lazy loading strategies
- CDN integration for static assets
- Response compression
- Database connection pooling optimization
- Async operations for I/O bound tasks
- Batch processing for bulk operations
- Materialized views for complex queries
- Query result caching with invalidation
- API response streaming for large datasets
- Memory profiling and optimization
- JIT compilation with Numba for compute-intensive operations

### Task 10: Documentation and API Client Generation
**Execution**: Using cc_execute.md
**Command**: Create comprehensive documentation:
- API documentation with ReDoc and Swagger UI
- Developer guide with architecture diagrams
- Deployment guide for multiple environments
- API client SDK generation (Python, JavaScript, Go)
- Postman collection with examples
- Database schema documentation
- WebSocket protocol documentation
- Performance tuning guide
- Security best practices document
- Troubleshooting guide with common issues
- Change log generation from git commits
- Interactive API tutorial
- Video tutorials for complex features

## Expected Outcomes
Each task should:
1. Take 2-5 minutes to complete (testing timeout predictions)
2. Generate substantial code/documentation
3. Build upon previous tasks
4. Test the WebSocket's ability to maintain long connections
5. Exercise Redis timeout prediction and adjustment

## Success Criteria
- All 10 tasks complete successfully
- No WebSocket timeouts despite long-running tasks
- Redis correctly predicts and adjusts timeouts
- Each task output is comprehensive and functional
- Total execution time: 20-50 minutes