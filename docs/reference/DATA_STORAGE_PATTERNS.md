# Data Storage Patterns for CC Executor

## Overview

This template provides standard patterns for data storage in CC Executor, covering Redis for quick/simple storage, ArangoDB for complex data, and file-based storage for results and logs.

## Storage Decision Matrix

| Use Case | Storage Solution | Reason |
|----------|-----------------|---------|
| Temporary cache (<1 hour) | Redis with TTL | Fast, auto-expires |
| Task results | JSON files in tmp/responses/ | Permanent, debuggable |
| Configuration | JSON/YAML files | Version controlled |
| Metrics/counters | Redis hashes | Atomic operations |
| Complex relationships | ArangoDB | Graph capabilities |
| Time-series data | Redis sorted sets | Efficient range queries |
| Large binary data | File system + Redis keys | Redis stores metadata only |

## Redis Patterns

### Pattern 1: Simple Key-Value with TTL

```python
import redis
import json
from typing import Any, Optional
from datetime import datetime

# Global Redis client with availability check
try:
    redis_client = redis.Redis(decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False

def cache_result(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    Cache a result in Redis with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds
        
    Returns:
        True if cached successfully
    """
    if not REDIS_AVAILABLE:
        return False
        
    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
        return True
    except Exception as e:
        logger.error(f"Redis cache failed: {e}")
        return False

def get_cached(key: str, default: Any = None) -> Any:
    """Get cached value with fallback."""
    if not REDIS_AVAILABLE:
        return default
        
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else default
    except Exception as e:
        logger.error(f"Redis get failed: {e}")
        return default
```

### Pattern 2: Task Metrics with Hashes

```python
class TaskMetrics:
    """Track task execution metrics in Redis."""
    
    def __init__(self, prefix: str = "metrics"):
        self.prefix = prefix
        self.client = redis_client if REDIS_AVAILABLE else None
        
    def increment(self, task_id: str, metric: str, amount: int = 1):
        """Increment a metric counter."""
        if not self.client:
            return
            
        key = f"{self.prefix}:{task_id}"
        try:
            self.client.hincrby(key, metric, amount)
            # Set expiry on first write
            if self.client.ttl(key) == -1:
                self.client.expire(key, 86400)  # 24 hours
        except Exception as e:
            logger.debug(f"Metric increment failed: {e}")
            
    def record_execution(self, task_id: str, success: bool, duration: float):
        """Record task execution metrics."""
        if not self.client:
            return
            
        self.increment(task_id, "total_executions")
        if success:
            self.increment(task_id, "successful_executions")
        else:
            self.increment(task_id, "failed_executions")
            
        # Store duration stats
        key = f"{self.prefix}:{task_id}"
        try:
            self.client.hset(key, "last_duration", duration)
            self.client.hset(key, "last_execution", datetime.now().isoformat())
        except:
            pass
            
    def get_stats(self, task_id: str) -> Dict[str, Any]:
        """Get task statistics."""
        if not self.client:
            return {}
            
        key = f"{self.prefix}:{task_id}"
        try:
            stats = self.client.hgetall(key)
            # Convert numeric strings
            for field in ["total_executions", "successful_executions", "failed_executions"]:
                if field in stats:
                    stats[field] = int(stats[field])
            if "last_duration" in stats:
                stats["last_duration"] = float(stats["last_duration"])
            return stats
        except:
            return {}
```

### Pattern 3: Distributed Locking

```python
import uuid
import time

class RedisLock:
    """Distributed lock using Redis."""
    
    def __init__(self, key: str, timeout: int = 30):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.identifier = str(uuid.uuid4())
        self.client = redis_client
        
    async def acquire(self, block: bool = True, block_timeout: int = 10) -> bool:
        """Acquire lock with optional blocking."""
        if not self.client:
            return True  # No Redis, no locking needed
            
        end_time = time.time() + block_timeout
        
        while True:
            # Try to acquire lock
            if self.client.set(self.key, self.identifier, nx=True, ex=self.timeout):
                return True
                
            if not block:
                return False
                
            if time.time() > end_time:
                return False
                
            await asyncio.sleep(0.1)
            
    async def release(self):
        """Release lock if we own it."""
        if not self.client:
            return
            
        # Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            self.client.eval(lua_script, 1, self.key, self.identifier)
        except Exception as e:
            logger.error(f"Lock release failed: {e}")
            
    async def __aenter__(self):
        if not await self.acquire():
            raise RuntimeError(f"Could not acquire lock: {self.key}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
```

### Pattern 4: Time-Series Data with Sorted Sets

```python
class TimeSeriesStore:
    """Store time-series data in Redis sorted sets."""
    
    def __init__(self, key_prefix: str):
        self.prefix = key_prefix
        self.client = redis_client
        
    def add_point(self, series: str, value: float, timestamp: Optional[float] = None):
        """Add a data point to time series."""
        if not self.client:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        key = f"{self.prefix}:{series}"
        
        # Store as JSON with timestamp as score
        data = json.dumps({"value": value, "ts": timestamp})
        
        try:
            self.client.zadd(key, {data: timestamp})
            # Keep only last 1000 points
            self.client.zremrangebyrank(key, 0, -1001)
            # Expire after 7 days
            self.client.expire(key, 604800)
        except Exception as e:
            logger.debug(f"Time series add failed: {e}")
            
    def get_range(self, series: str, start: float, end: float) -> List[Dict[str, float]]:
        """Get data points in time range."""
        if not self.client:
            return []
            
        key = f"{self.prefix}:{series}"
        
        try:
            results = self.client.zrangebyscore(key, start, end)
            return [json.loads(r) for r in results]
        except:
            return []
            
    def get_latest(self, series: str, count: int = 10) -> List[Dict[str, float]]:
        """Get latest N data points."""
        if not self.client:
            return []
            
        key = f"{self.prefix}:{series}"
        
        try:
            results = self.client.zrevrange(key, 0, count - 1)
            return [json.loads(r) for r in results]
        except:
            return []
```

## File Storage Patterns

### Pattern 1: JSON Results with Metadata

```python
from pathlib import Path
from datetime import datetime

def save_json_result(
    data: Dict[str, Any],
    category: str = "results",
    metadata: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Save JSON results with metadata and timestamp.
    
    Args:
        data: Data to save
        category: Subdirectory category
        metadata: Optional metadata to include
        
    Returns:
        Path to saved file
    """
    # Create directory structure
    base_dir = Path(__file__).parent / "tmp" / "responses" / category
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
    script_name = Path(__file__).stem
    filename = f"{script_name}_{category}_{timestamp}.json"
    filepath = base_dir / filename
    
    # Prepare data with metadata
    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "script": script_name,
            "category": category,
            "version": "1.0",
            **(metadata or {})
        },
        "data": data
    }
    
    # Save with pretty formatting
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=True, default=str)
    
    logger.info(f"Results saved to: {filepath}")
    
    # Also save latest symlink for easy access
    latest_link = base_dir / f"{script_name}_{category}_latest.json"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(filename)
    
    return filepath
```

### Pattern 2: CSV Export with Buffering

```python
import csv
from typing import Iterator

class CSVExporter:
    """Export data to CSV with buffering for large datasets."""
    
    def __init__(self, filepath: Path, headers: List[str], buffer_size: int = 1000):
        self.filepath = filepath
        self.headers = headers
        self.buffer_size = buffer_size
        self.buffer = []
        self.file = None
        self.writer = None
        
    def __enter__(self):
        self.file = open(self.filepath, 'w', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=self.headers)
        self.writer.writeheader()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Flush any remaining buffer
        if self.buffer:
            self._flush()
        if self.file:
            self.file.close()
            
    def _flush(self):
        """Flush buffer to disk."""
        if self.buffer and self.writer:
            self.writer.writerows(self.buffer)
            self.buffer = []
            
    def write_row(self, row: Dict[str, Any]):
        """Write a single row, buffering for performance."""
        self.buffer.append(row)
        if len(self.buffer) >= self.buffer_size:
            self._flush()
            
    def write_many(self, rows: Iterator[Dict[str, Any]]):
        """Write multiple rows efficiently."""
        for row in rows:
            self.write_row(row)
```

## ArangoDB Patterns

### Pattern 1: Document Store with Relationships

```python
from arango import ArangoClient
from typing import Optional

class ArangoStore:
    """ArangoDB store for complex data relationships."""
    
    def __init__(self, db_name: str = "cc_executor"):
        self.client = None
        self.db = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to ArangoDB."""
        try:
            self.client = ArangoClient()
            sys_db = self.client.db('_system', username='root', password='password')
            
            # Create database if not exists
            if not sys_db.has_database(self.db_name):
                sys_db.create_database(self.db_name)
                
            self.db = self.client.db(self.db_name, username='root', password='password')
            self.connected = True
            
            # Ensure collections exist
            self._ensure_collections()
            
            logger.info("ArangoDB connected")
            return True
            
        except Exception as e:
            logger.warning(f"ArangoDB connection failed: {e}")
            return False
            
    def _ensure_collections(self):
        """Ensure required collections exist."""
        collections = [
            ("tasks", False),  # Document collection
            ("results", False),  # Document collection
            ("relationships", True)  # Edge collection
        ]
        
        for name, is_edge in collections:
            if not self.db.has_collection(name):
                self.db.create_collection(name, edge=is_edge)
                
    def save_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Save task document and return ID."""
        if not self.connected:
            return None
            
        try:
            tasks = self.db.collection('tasks')
            doc = {
                **task_data,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            result = tasks.insert(doc)
            return result['_key']
        except Exception as e:
            logger.error(f"ArangoDB save failed: {e}")
            return None
            
    def link_result_to_task(self, task_id: str, result_id: str, relationship: str = "produced"):
        """Create edge between task and result."""
        if not self.connected:
            return
            
        try:
            edges = self.db.collection('relationships')
            edge = {
                "_from": f"tasks/{task_id}",
                "_to": f"results/{result_id}",
                "type": relationship,
                "created_at": datetime.now().isoformat()
            }
            edges.insert(edge)
        except Exception as e:
            logger.error(f"Edge creation failed: {e}")
            
    def query_task_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Query all results for a task using AQL."""
        if not self.connected:
            return []
            
        try:
            aql = """
            FOR v, e IN 1..1 OUTBOUND @task_id relationships
                FILTER e.type == 'produced'
                RETURN v
            """
            cursor = self.db.aql.execute(
                aql,
                bind_vars={'task_id': f'tasks/{task_id}'}
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
```

## Hybrid Storage Pattern

### Pattern: Redis + File System for Large Data

```python
class HybridStorage:
    """Use Redis for metadata and file system for large data."""
    
    def __init__(self, data_dir: Path = Path("tmp/data")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def store_large_result(self, task_id: str, data: Any, metadata: Dict[str, Any]) -> bool:
        """Store large result with metadata in Redis."""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id}_{timestamp}.json"
        filepath = self.data_dir / filename
        
        # Save data to file
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Store metadata in Redis
            redis_metadata = {
                **metadata,
                "filepath": str(filepath),
                "size_bytes": filepath.stat().st_size,
                "stored_at": datetime.now().isoformat()
            }
            
            cache_result(
                f"large_result:{task_id}",
                redis_metadata,
                ttl=86400  # 24 hours
            )
            
            logger.info(f"Stored large result: {filepath} ({redis_metadata['size_bytes']} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Hybrid storage failed: {e}")
            return False
            
    def retrieve_large_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve large result using metadata."""
        # Get metadata from Redis
        metadata = get_cached(f"large_result:{task_id}")
        if not metadata:
            return None
            
        # Load data from file
        filepath = Path(metadata.get("filepath", ""))
        if not filepath.exists():
            logger.error(f"Data file not found: {filepath}")
            return None
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            return {
                "metadata": metadata,
                "data": data
            }
        except Exception as e:
            logger.error(f"Data retrieval failed: {e}")
            return None
```

## Best Practices Summary

### Redis
1. **Always check availability** before operations
2. **Use TTL** to prevent memory bloat
3. **Handle failures gracefully** - Redis is optional
4. **Use appropriate data structures** (strings, hashes, sets)
5. **Batch operations** when possible (pipeline/multi)

### File Storage
1. **Use timestamps** in filenames
2. **Create directory structure** upfront
3. **Pretty-print JSON** for debugging
4. **Include metadata** in saved files
5. **Use symlinks** for "latest" versions

### ArangoDB
1. **Design schema** with relationships in mind
2. **Use AQL** for complex queries
3. **Create indexes** for performance
4. **Handle connection failures** gracefully
5. **Use transactions** for consistency

### General
1. **Choose the right tool** for each use case
2. **Plan for failures** - services may be unavailable
3. **Use async operations** where beneficial
4. **Clean up old data** with TTLs or cron jobs
5. **Monitor storage usage** to prevent issues

## Summary

These storage patterns provide:
- Flexibility to use the right storage for each use case
- Graceful degradation when services are unavailable
- Consistent interfaces across storage types
- Performance optimization through appropriate data structures
- Easy debugging through structured file storage

Always consider data lifecycle, access patterns, and failure scenarios when choosing storage solutions.