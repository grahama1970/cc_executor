# Python-Arango-Async Conversion Guide

## Overview

This guide documents the conversion patterns for migrating the logger agent project from `asyncio.to_thread` with sync python-arango to fully async `python-arango-async`.

## Installation

```bash
uv add python-arango-async
```

## Key API Differences

### 1. Client Creation

**Sync (python-arango):**
```python
from arango import ArangoClient

client = ArangoClient(hosts="http://localhost:8529")
db = client.db("logger_agent", username="root", password="")
```

**Async (python-arango-async):**
```python
from arangoasync import ArangoClient
from arangoasync.auth import Auth

async with ArangoClient(hosts="http://localhost:8529") as client:
    auth = Auth(username="root", password="")
    db = await client.db("logger_agent", auth=auth)
```

### 2. Collection Operations

**Sync:**
```python
# List collections
for collection in db.collections():
    print(collection["name"])

# Get specific collection
col = db.collection("log_events")
doc = col.get("12345")
```

**Async:**
```python
# List collections
collections_cursor = await db.collections()
async for collection in collections_cursor:
    print(collection["name"])

# Get specific collection
col = await db.collection("log_events")
doc = await col.get("12345")
```

### 3. AQL Queries

**Sync:**
```python
cursor = db.aql.execute(
    "FOR doc IN log_events FILTER doc.level == @level RETURN doc",
    bind_vars={"level": "ERROR"}
)
for doc in cursor:
    process(doc)
```

**Async:**
```python
cursor = await db.aql.execute(
    "FOR doc IN log_events FILTER doc.level == @level RETURN doc",
    bind_vars={"level": "ERROR"}
)
async for doc in cursor:
    await process(doc)
```

### 4. Document Operations

**Sync:**
```python
# Insert
result = collection.insert({"name": "test"})

# Update
collection.update({"_key": "123", "name": "updated"})

# Delete
collection.delete("123")
```

**Async:**
```python
# Insert
result = await collection.insert({"name": "test"})

# Update
await collection.update({"_key": "123", "name": "updated"})

# Delete
await collection.delete("123")
```

### 5. Graph Operations

**Sync:**
```python
graph = db.graph("error_graph")
edge_collection = graph.edge_collection("error_causality")
edge_collection.insert({
    "_from": "errors/123",
    "_to": "fixes/456",
    "relationship_type": "FIXED_BY"
})
```

**Async:**
```python
graph = await db.graph("error_graph")
edge_collection = await graph.edge_collection("error_causality")
await edge_collection.insert({
    "_from": "errors/123",
    "_to": "fixes/456",
    "relationship_type": "FIXED_BY"
})
```

## Conversion Patterns for Logger Agent

### 1. LogManager Class

**Current (with asyncio.to_thread):**
```python
class LogManager:
    def __init__(self):
        self.client = ArangoClient(hosts=self.url)
        self.db = self.client.db(self.db_name, username=self.username, password=self.password)
    
    async def log_event(self, **kwargs):
        return await asyncio.to_thread(self._sync_log_event, **kwargs)
    
    def _sync_log_event(self, **kwargs):
        return self.collection.insert(document)
```

**Async version:**
```python
class AsyncLogManager:
    async def __init__(self):
        self.client = ArangoClient(hosts=self.url)
        self.auth = Auth(username=self.username, password=self.password)
        self.db = await self.client.db(self.db_name, auth=self.auth)
        self.collection = await self.db.collection("log_events")
    
    async def log_event(self, **kwargs):
        return await self.collection.insert(document)
```

### 2. Search Operations

**Current:**
```python
async def search_agent_activity(self, query: str):
    def _search():
        cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
        return list(cursor)
    
    return await asyncio.to_thread(_search)
```

**Async:**
```python
async def search_agent_activity(self, query: str):
    cursor = await self.db.aql.execute(aql_query, bind_vars=bind_vars)
    results = []
    async for doc in cursor:
        results.append(doc)
    return results
```

### 3. Context Manager Pattern

**Current:**
```python
async def get_log_manager():
    manager = LogManager()
    await manager.initialize()
    return manager
```

**Async:**
```python
@asynccontextmanager
async def get_log_manager():
    async with ArangoClient(hosts=url) as client:
        auth = Auth(username=username, password=password)
        db = await client.db(db_name, auth=auth)
        manager = AsyncLogManager(db)
        yield manager
```

## Migration Strategy

1. **Phase 1: Install and Test**
   - ✅ Install python-arango-async
   - ✅ Verify basic connectivity
   - ✅ Test async patterns

2. **Phase 2: Create Async Versions**
   - Create AsyncLogManager alongside LogManager
   - Implement async versions of key methods
   - Add compatibility layer for gradual migration

3. **Phase 3: Update Consumers**
   - Update MCP server to use async manager
   - Update query converter to use async operations
   - Update assessment tools to use async

4. **Phase 4: Remove Sync Code**
   - Remove asyncio.to_thread wrappers
   - Remove sync fallback code
   - Clean up imports

## Benefits of Migration

1. **Performance**: Native async operations without thread overhead
2. **Concurrency**: Better handling of concurrent database operations
3. **Resource Usage**: Lower memory footprint without thread pools
4. **Code Clarity**: Simpler async/await patterns throughout

## Testing Approach

```python
# Test async operations
async def test_async_operations():
    async with get_log_manager() as manager:
        # Test logging
        doc = await manager.log_event(
            level="INFO",
            message="Test async logging"
        )
        assert doc["_id"]
        
        # Test search
        results = await manager.search.search_agent_activity("test")
        assert isinstance(results, list)
        
        # Test graph traversal
        related = await manager.find_related_errors(doc["_id"], depth=2)
        assert isinstance(related, list)
```

## Current Status

- ✅ python-arango-async is installed and working
- ✅ Basic async patterns tested and verified
- ✅ API compatibility confirmed
- 🔄 Ready to begin conversion of logger agent project

## Next Steps

1. Create AsyncLogManager class with core functionality
2. Test with existing MCP server
3. Gradually migrate all database operations
4. Remove asyncio.to_thread usage
5. Update documentation and tests