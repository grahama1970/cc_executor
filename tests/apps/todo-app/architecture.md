# Todo App Architecture

## Overview
A modern todo application built with a REST API backend and reactive frontend, featuring user authentication, task management, and real-time updates.

## Database Schema

### PostgreSQL Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Todo lists/projects
CREATE TABLE lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, is_default) WHERE is_default = true
);

-- Todo items
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 3),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'archived')),
    completed_at TIMESTAMP,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',
    UNIQUE(user_id, name)
);

-- Todo-tag relationship
CREATE TABLE todo_tags (
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, tag_id)
);

-- Indexes for performance
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_list_id ON todos(list_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_due_date ON todos(due_date);
CREATE INDEX idx_lists_user_id ON lists(user_id);
```

## REST API Design

### Authentication Endpoints

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
GET    /api/auth/me
```

### User Endpoints

```
GET    /api/users/profile
PUT    /api/users/profile
DELETE /api/users/account
PUT    /api/users/password
```

### List Endpoints

```
GET    /api/lists              # Get all user's lists
POST   /api/lists              # Create new list
GET    /api/lists/:id          # Get specific list
PUT    /api/lists/:id          # Update list
DELETE /api/lists/:id          # Delete list
GET    /api/lists/:id/todos    # Get todos in list
```

### Todo Endpoints

```
GET    /api/todos              # Get all todos (with filters)
POST   /api/todos              # Create new todo
GET    /api/todos/:id          # Get specific todo
PUT    /api/todos/:id          # Update todo
DELETE /api/todos/:id          # Delete todo
PATCH  /api/todos/:id/status   # Update todo status
PATCH  /api/todos/:id/position # Update todo position
POST   /api/todos/bulk         # Bulk operations
```

### Tag Endpoints

```
GET    /api/tags               # Get all user's tags
POST   /api/tags               # Create new tag
PUT    /api/tags/:id           # Update tag
DELETE /api/tags/:id           # Delete tag
```

### API Response Format

```json
// Success response
{
    "success": true,
    "data": { ... },
    "meta": {
        "page": 1,
        "limit": 20,
        "total": 100
    }
}

// Error response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": { ... }
    }
}
```

### Query Parameters

```
GET /api/todos?list_id=xxx&status=pending&tag=work&due_before=2024-12-31&sort=due_date&order=asc&page=1&limit=20
```

## Backend Architecture

### Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy (async)
- **Authentication**: JWT with refresh tokens
- **Validation**: Pydantic
- **Task Queue**: Celery with Redis
- **Caching**: Redis
- **WebSockets**: For real-time updates

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── lists.py
│   │   │   ├── todos.py
│   │   │   └── tags.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── user.py
│   │   ├── list.py
│   │   ├── todo.py
│   │   └── tag.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── list.py
│   │   ├── todo.py
│   │   └── tag.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── todo.py
│   │   └── notification.py
│   └── main.py
├── alembic/
├── tests/
├── requirements.txt
└── .env
```

## Frontend Architecture

### Tech Stack
- **Framework**: React 18 with TypeScript
- **State Management**: Zustand or Redux Toolkit
- **Routing**: React Router v6
- **UI Components**: Tailwind CSS + Headless UI
- **Forms**: React Hook Form + Zod
- **API Client**: Axios with interceptors
- **Real-time**: Socket.io-client
- **Build Tool**: Vite

### Component Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Dropdown.tsx
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── todo/
│   │   │   ├── TodoItem.tsx
│   │   │   ├── TodoList.tsx
│   │   │   ├── TodoForm.tsx
│   │   │   └── TodoFilters.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Layout.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ListDetail.tsx
│   │   ├── Login.tsx
│   │   └── Register.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTodos.ts
│   │   └── useWebSocket.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── todos.ts
│   ├── store/
│   │   ├── authStore.ts
│   │   ├── todoStore.ts
│   │   └── uiStore.ts
│   ├── types/
│   │   └── index.ts
│   └── App.tsx
```

### Key Features

1. **Authentication**
   - JWT token management
   - Auto-refresh tokens
   - Persistent sessions
   - OAuth integration (Google, GitHub)

2. **Todo Management**
   - Drag-and-drop reordering
   - Inline editing
   - Bulk operations
   - Keyboard shortcuts
   - Undo/redo functionality

3. **Real-time Updates**
   - WebSocket connection for live updates
   - Optimistic UI updates
   - Conflict resolution

4. **Offline Support**
   - Service worker for offline functionality
   - Local storage sync
   - Queue operations when offline

5. **Search & Filter**
   - Full-text search
   - Filter by status, date, tags
   - Smart lists (Today, Upcoming, Overdue)

## Deployment Architecture

### Docker Compose Setup

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: todoapp
      POSTGRES_USER: todouser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}

  backend:
    build: ./backend
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://todouser:${DB_PASSWORD}@postgres/todoapp
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:80"

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
```

### Production Considerations

1. **Security**
   - HTTPS everywhere
   - Rate limiting
   - Input validation
   - SQL injection prevention
   - XSS protection
   - CORS configuration

2. **Performance**
   - Database indexing
   - Query optimization
   - Redis caching
   - CDN for static assets
   - Lazy loading
   - Code splitting

3. **Monitoring**
   - Application metrics (Prometheus)
   - Error tracking (Sentry)
   - Logging (ELK stack)
   - Uptime monitoring

4. **Scalability**
   - Horizontal scaling with load balancer
   - Database read replicas
   - Redis cluster
   - Microservices architecture (future)

## API Examples

### Create Todo
```bash
POST /api/todos
Authorization: Bearer <token>

{
    "title": "Complete project documentation",
    "description": "Write comprehensive docs for the todo app",
    "list_id": "123e4567-e89b-12d3-a456-426614174000",
    "due_date": "2024-12-31T23:59:59Z",
    "priority": 2,
    "tags": ["work", "important"]
}
```

### Update Todo Status
```bash
PATCH /api/todos/456e7890-e89b-12d3-a456-426614174000/status
Authorization: Bearer <token>

{
    "status": "completed"
}
```

This architecture provides a solid foundation for a scalable, maintainable todo application with room for growth and additional features.