# Blog Platform with Hooks

This example demonstrates pre-flight assessment and post-execution reporting.

## Overview

Build a complete blog platform API with quality assurance through hooks.

## Tasks

### Task 1: Create Database Models
**Description**: What database models are needed for a blog platform? Create blog_platform/models.py with SQLAlchemy models for User (id, username, email, created_at) and Post (id, title, content, author_id, created_at, updated_at).

**Complexity**: 2.5
**Estimated Duration**: 30s

### Task 2: Create FastAPI Application  
**Description**: How do I create a FastAPI application for the blog? Read blog_platform/models.py and create blog_platform/main.py with FastAPI app initialization, database setup, and CORS middleware configuration.

**Complexity**: 2.8
**Estimated Duration**: 45s

### Task 3: Implement User Endpoints
**Description**: What REST endpoints are needed for user management? Read existing files in blog_platform/ and create blog_platform/routers/users.py with POST /users (create user), GET /users/{id} (get user), and GET /users (list users) endpoints.

**Complexity**: 3.2
**Estimated Duration**: 60s

### Task 4: Implement Post Endpoints
**Description**: How can I add blog post functionality? Read the models and existing routers, then create blog_platform/routers/posts.py with full CRUD endpoints: POST /posts, GET /posts, GET /posts/{id}, PUT /posts/{id}, DELETE /posts/{id}.

**Complexity**: 3.5
**Estimated Duration**: 75s

### Task 5: Write Integration Tests
**Description**: How do I test the blog API endpoints? Read all files in blog_platform/ and create blog_platform/tests/test_api.py with pytest tests covering user creation, post CRUD operations, and authentication flows.

**Complexity**: 3.8
**Estimated Duration**: 80s

## Pre-Flight Expectations

When hooks are enabled, expect:
- Total complexity: ~15.8 (MODERATE-HIGH)
- Risk assessment for each task
- Success rate prediction
- Timeout recommendations

## Post-Execution Expectations

The completion report will include:
- Execution metrics per task
- Files created verification  
- Cross-task dependency validation
- Overall quality assessment

## Benefits of Hooks

1. **Early Warning**: Know risks before execution
2. **Quality Gates**: Automated verification
3. **Transparency**: Full execution audit trail
4. **Continuous Improvement**: Learn from each run