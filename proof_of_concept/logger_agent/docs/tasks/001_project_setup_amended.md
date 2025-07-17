# Logger Agent - Comprehensive Implementation Plan (Amended)

## Overview

The Logger Agent is a centralized logging and introspection system for autonomous AI agents that leverages ArangoDB's multi-model capabilities. This amended plan includes all implementation details, code examples, and integration points based on the project requirements.

## System Architecture

### Core Components
1. **ArangoDB 3.12.4** - Multi-model database backend with experimental features enabled
2. **Loguru** - Python logging library with custom async sink
3. **Async Architecture** - Non-blocking log ingestion using asyncio and uvloop
4. **Agent API** - Unified interface for log queries and management
5. **Integration Modules** - Connections to existing graph, search, and memory systems

### Key Features
- Zero-blocking async logging with automatic buffering
- Full-text search via ArangoSearch with BM25 ranking
- Graph relationships between log events
- Automatic reconnection with exponential backoff
- Disk-based buffering for database downtime
- Rich metadata and execution context tracking
- Performance monitoring and alerting

## Phase 0: Environment Setup

### Docker Configuration for ArangoDB

```yaml
# docker-compose.yml
version: '3.8'

services:
  arangodb:
    image: arangodb:3.12.4
    container_name: logger_agent_arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=openSesame
    volumes:
      - arangodb_data:/var/lib/arangodb3
      - arangodb_apps:/var/lib/arangodb3-apps
    command: >
      arangod 
      --query.enable-experimental true
      --server.endpoint tcp://0.0.0.0:8529
      --log.level info
      --database.auto-upgrade true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  arangodb_data:
  arangodb_apps:
```

### Environment Variables (.env)

```bash
# ArangoDB Configuration
ARANGO_URL=http://localhost:8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=openSesame
ARANGO_DATABASE=script_logs

# Logger Agent Configuration
LOG_BATCH_SIZE=200
LOG_FLUSH_INTERVAL=2
LOG_BUFFER_DIR=/tmp/logger_agent_buffer
LOG_MAX_BUFFER_SIZE_MB=1000
LOG_RETENTION_DAYS=30

# Performance Monitoring
ENABLE_MONITORING=true
MONITORING_INTERVAL=60
ALERT_LOG_FAILURE_THRESHOLD=10

# Python Path
PYTHONPATH=./src
```

### Python Dependencies (requirements.txt)

```txt
# Core dependencies
loguru>=0.7.2
aioarango>=1.0.0
uvloop>=0.19.0
python-dotenv>=1.0.0
tenacity>=9.0.0

# Integration dependencies (from existing project)
numpy>=2.0.0
scipy>=1.10.0
pandas>=2.0.0
redis>=5.0.0

# Monitoring
psutil>=5.9.0
rich>=13.0.0
```

## Phase 1: ArangoDB Backend Setup

### Database Initialization Script

```python
#!/usr/bin/env python3
"""
arango_init.py - Initialize ArangoDB schema for Logger Agent

Creates database, collections, indexes, and ArangoSearch views.
Ensures idempotent execution for repeated runs.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from aioarango import ArangoClient
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()
logger.add(
    "logs/arango_init_{time}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)


async def create_database_and_collections():
    """Create database and collections with proper indexes."""
    
    # Connect to ArangoDB
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    
    # System database connection
    sys_db = await client.db(
        "_system",
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    db_name = os.getenv("ARANGO_DATABASE", "script_logs")
    
    # Create database if not exists
    if not await sys_db.has_database(db_name):
        await sys_db.create_database(db_name)
        logger.info(f"Created database: {db_name}")
    
    # Connect to our database
    db = await client.db(
        db_name,
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Create collections
    collections = {
        "log_events": {
            "schema": {
                "rule": {
                    "properties": {
                        "timestamp": {"type": "string"},
                        "level": {"type": "string"},
                        "message": {"type": "string"},
                        "execution_id": {"type": "string"},
                        "script_name": {"type": "string"},
                        "function_name": {"type": "string"},
                        "file_path": {"type": "string"},
                        "line_number": {"type": "integer"},
                        "extra_data": {"type": "object"},
                        "embeddings": {"type": "array"},
                        "tags": {"type": "array"}
                    },
                    "required": ["timestamp", "level", "message", "execution_id"]
                }
            }
        },
        "script_runs": {
            "schema": {
                "rule": {
                    "properties": {
                        "execution_id": {"type": "string"},
                        "script_name": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "status": {"type": "string"},
                        "metadata": {"type": "object"},
                        "error": {"type": "string"}
                    },
                    "required": ["execution_id", "script_name", "start_time"]
                }
            }
        },
        "agent_learnings": {
            "schema": {
                "rule": {
                    "properties": {
                        "timestamp": {"type": "string"},
                        "execution_id": {"type": "string"},
                        "learning": {"type": "string"},
                        "context": {"type": "object"},
                        "function_name": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["timestamp", "learning"]
                }
            }
        }
    }
    
    for coll_name, config in collections.items():
        if not await db.has_collection(coll_name):
            collection = await db.create_collection(
                coll_name,
                schema=config.get("schema")
            )
            logger.info(f"Created collection: {coll_name}")
        else:
            collection = db.collection(coll_name)
        
        # Create indexes
        if coll_name == "log_events":
            # Compound index for time-based queries
            await collection.add_persistent_index(
                fields=["execution_id", "timestamp"],
                unique=False,
                sparse=False
            )
            
            # Index for level-based filtering
            await collection.add_persistent_index(
                fields=["level", "timestamp"],
                unique=False,
                sparse=False
            )
            
            # Full-text index for message search
            await collection.add_fulltext_index(
                fields=["message"],
                min_length=3
            )
            
        elif coll_name == "script_runs":
            # Unique index on execution_id
            await collection.add_persistent_index(
                fields=["execution_id"],
                unique=True,
                sparse=False
            )
            
            # Index for script name queries
            await collection.add_persistent_index(
                fields=["script_name", "start_time"],
                unique=False,
                sparse=False
            )
    
    # Create ArangoSearch view
    view_name = "log_events_view"
    if not await db.has_view(view_name):
        await db.create_arangosearch_view(
            view_name,
            properties={
                "links": {
                    "log_events": {
                        "analyzers": ["text_en", "identity"],
                        "fields": {
                            "message": {
                                "analyzers": ["text_en"]
                            },
                            "level": {
                                "analyzers": ["identity"]
                            },
                            "script_name": {
                                "analyzers": ["identity"]
                            },
                            "tags": {
                                "analyzers": ["identity"]
                            }
                        },
                        "includeAllFields": False,
                        "storeValues": "id",
                        "trackListPositions": False
                    }
                }
            }
        )
        logger.info(f"Created ArangoSearch view: {view_name}")
    
    # Create graph for log relationships (optional)
    graph_name = "log_relationships"
    if not await db.has_graph(graph_name):
        await db.create_graph(
            graph_name,
            edge_definitions=[
                {
                    "edge_collection": "log_causality",
                    "from_vertex_collections": ["log_events"],
                    "to_vertex_collections": ["log_events", "agent_learnings"]
                }
            ]
        )
        logger.info(f"Created graph: {graph_name}")
    
    return db


async def working_usage():
    """Initialize database schema - stable working example."""
    logger.info("=== Initializing ArangoDB Schema ===")
    
    try:
        db = await create_database_and_collections()
        
        # Verify collections exist
        collections = await db.collections()
        logger.info(f"Available collections: {[c['name'] for c in collections]}")
        
        # Test write
        test_doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Database initialization test",
            "execution_id": "init_test_001",
            "script_name": "arango_init.py"
        }
        
        result = await db.collection("log_events").insert(test_doc)
        logger.success(f"Test document inserted: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.exception("Full traceback:")
        return False


async def debug_function():
    """Debug function for testing schema modifications."""
    logger.info("=== Running Debug Mode ===")
    
    # Test experimental features
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    db = await client.db(
        os.getenv("ARANGO_DATABASE", "script_logs"),
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Test APPROX_NEAR_COSINE availability
    test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    query = """
    RETURN APPROX_NEAR_COSINE(@vector, @vector, 1)
    """
    
    try:
        cursor = await db.aql.execute(query, bind_vars={"vector": test_vector})
        result = await cursor.next()
        logger.success(f"APPROX_NEAR_COSINE test passed: {result}")
    except Exception as e:
        logger.error(f"APPROX_NEAR_COSINE not available: {e}")
        logger.warning("Ensure --query.enable-experimental flag is set")
    
    return True


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

## Phase 2: Loguru Custom Sink Implementation

### Async ArangoDB Sink

```python
#!/usr/bin/env python3
"""
arango_log_sink.py - Custom loguru sink for async ArangoDB writes

Implements non-blocking log ingestion with batching, buffering,
and automatic retry mechanisms.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import aiofiles
import uvloop

from aioarango import ArangoClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import psutil

# Set uvloop as the event loop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class ArangoLogSink:
    """Async sink for loguru that writes to ArangoDB with buffering."""
    
    def __init__(
        self,
        db_config: Dict[str, str],
        batch_size: int = 100,
        flush_interval: float = 2.0,
        buffer_dir: Path = Path("/tmp/logger_agent_buffer"),
        max_buffer_size_mb: int = 1000
    ):
        self.db_config = db_config
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer_dir = buffer_dir
        self.max_buffer_size_mb = max_buffer_size_mb
        
        # Ensure buffer directory exists
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # Log queue and batch
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.current_batch: deque = deque(maxlen=batch_size)
        
        # Database connection
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        # Monitoring
        self.stats = {
            "total_logs": 0,
            "successful_writes": 0,
            "failed_writes": 0,
            "buffered_logs": 0,
            "last_error": None
        }
        
        # Background tasks
        self.consumer_task = None
        self.flush_task = None
        self.monitor_task = None
        
    async def connect(self) -> bool:
        """Establish connection to ArangoDB."""
        try:
            self.client = ArangoClient(hosts=self.db_config["url"])
            self.db = await self.client.db(
                self.db_config["database"],
                username=self.db_config["username"],
                password=self.db_config["password"]
            )
            self.collection = self.db.collection("log_events")
            
            # Test connection
            await self.db.version()
            self.connected = True
            logger.info("Connected to ArangoDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            self.connected = False
            self.stats["last_error"] = str(e)
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def write_batch_to_db(self, batch: List[Dict[str, Any]]) -> bool:
        """Write a batch of logs to ArangoDB with retry logic."""
        if not self.connected:
            if not await self.connect():
                raise Exception("Database connection failed")
        
        try:
            # Use truncation utility for large values
            from log_utils import log_safe_results
            safe_batch = log_safe_results(batch)
            
            result = await self.collection.insert_many(safe_batch)
            self.stats["successful_writes"] += len(batch)
            return True
            
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            self.stats["failed_writes"] += len(batch)
            self.stats["last_error"] = str(e)
            self.connected = False  # Mark as disconnected
            raise
    
    async def buffer_to_disk(self, logs: List[Dict[str, Any]]) -> None:
        """Buffer logs to disk when database is unavailable."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        buffer_file = self.buffer_dir / f"buffer_{timestamp}.jsonl"
        
        async with aiofiles.open(buffer_file, 'w') as f:
            for log in logs:
                await f.write(json.dumps(log) + '\n')
        
        self.stats["buffered_logs"] += len(logs)
        logger.warning(f"Buffered {len(logs)} logs to {buffer_file}")
        
        # Check buffer size and clean if needed
        await self.check_buffer_size()
    
    async def check_buffer_size(self) -> None:
        """Monitor buffer directory size and clean old files if needed."""
        total_size = sum(f.stat().st_size for f in self.buffer_dir.glob("*.jsonl"))
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > self.max_buffer_size_mb:
            # Remove oldest files
            files = sorted(self.buffer_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
            
            while total_size_mb > self.max_buffer_size_mb * 0.8 and files:
                oldest = files.pop(0)
                size = oldest.stat().st_size
                oldest.unlink()
                total_size_mb -= size / (1024 * 1024)
                logger.warning(f"Removed old buffer file: {oldest.name}")
    
    async def process_buffered_logs(self) -> None:
        """Process buffered logs when connection is restored."""
        if not self.connected or not self.buffer_dir.exists():
            return
        
        buffer_files = sorted(self.buffer_dir.glob("*.jsonl"))
        
        for buffer_file in buffer_files:
            try:
                logs = []
                async with aiofiles.open(buffer_file, 'r') as f:
                    async for line in f:
                        logs.append(json.loads(line.strip()))
                
                if logs:
                    # Process in batches
                    for i in range(0, len(logs), self.batch_size):
                        batch = logs[i:i + self.batch_size]
                        await self.write_batch_to_db(batch)
                
                # Remove processed file
                buffer_file.unlink()
                logger.info(f"Processed buffered file: {buffer_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to process buffer file {buffer_file}: {e}")
                break  # Stop processing if we hit an error
    
    async def log_consumer(self) -> None:
        """Consume logs from queue and batch them."""
        while True:
            try:
                # Get log from queue with timeout
                log_data = await asyncio.wait_for(
                    self.log_queue.get(),
                    timeout=self.flush_interval
                )
                
                self.current_batch.append(log_data)
                self.stats["total_logs"] += 1
                
                # Flush if batch is full
                if len(self.current_batch) >= self.batch_size:
                    await self.flush_batch()
                
            except asyncio.TimeoutError:
                # Flush on timeout
                if self.current_batch:
                    await self.flush_batch()
            except Exception as e:
                logger.error(f"Error in log consumer: {e}")
    
    async def flush_batch(self) -> None:
        """Flush current batch to database or disk buffer."""
        if not self.current_batch:
            return
        
        batch = list(self.current_batch)
        self.current_batch.clear()
        
        try:
            await self.write_batch_to_db(batch)
            
            # Try to process buffered logs after successful write
            await self.process_buffered_logs()
            
        except Exception:
            # Buffer to disk on failure
            await self.buffer_to_disk(batch)
    
    async def periodic_flush(self) -> None:
        """Periodically flush logs."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush_batch()
    
    async def monitor_performance(self) -> None:
        """Monitor sink performance and alert on issues."""
        alert_threshold = int(os.getenv("ALERT_LOG_FAILURE_THRESHOLD", "10"))
        
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            # Calculate failure rate
            total = self.stats["successful_writes"] + self.stats["failed_writes"]
            if total > 0:
                failure_rate = self.stats["failed_writes"] / total * 100
                
                if failure_rate > alert_threshold:
                    logger.critical(
                        f"High log failure rate: {failure_rate:.1f}% "
                        f"({self.stats['failed_writes']}/{total} failed)"
                    )
            
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                logger.warning(f"High memory usage: {memory_percent}%")
            
            # Log stats
            logger.info(f"Log sink stats: {self.stats}")
    
    async def start(self) -> None:
        """Start background tasks."""
        await self.connect()
        
        self.consumer_task = asyncio.create_task(self.log_consumer())
        self.flush_task = asyncio.create_task(self.periodic_flush())
        
        if os.getenv("ENABLE_MONITORING", "true").lower() == "true":
            self.monitor_task = asyncio.create_task(self.monitor_performance())
    
    async def stop(self) -> None:
        """Stop background tasks and flush remaining logs."""
        # Cancel tasks
        for task in [self.consumer_task, self.flush_task, self.monitor_task]:
            if task:
                task.cancel()
        
        # Final flush
        await self.flush_batch()
        
        # Close database connection
        if self.client:
            await self.client.close()
    
    def write(self, message: Dict[str, Any]) -> None:
        """Synchronous write method for loguru compatibility."""
        # Parse loguru message
        log_data = {
            "timestamp": message.record["time"].isoformat(),
            "level": message.record["level"].name,
            "message": message.record["message"],
            "execution_id": message.record["extra"].get("execution_id", "unknown"),
            "script_name": message.record["extra"].get("script_name", Path(message.record["file"].name).stem),
            "function_name": message.record["function"],
            "file_path": message.record["file"].path,
            "line_number": message.record["line"],
            "extra_data": message.record["extra"],
            "tags": message.record["extra"].get("tags", [])
        }
        
        # Add to queue (non-blocking)
        try:
            self.log_queue.put_nowait(log_data)
        except asyncio.QueueFull:
            # Queue is full, log to stderr as fallback
            logger.bind(skip_sink=True).error(
                f"Log queue full, dropping log: {log_data['message'][:100]}"
            )


# Global sink instance
_sink_instance: Optional[ArangoLogSink] = None


def get_arango_sink() -> ArangoLogSink:
    """Get or create the global ArangoDB sink instance."""
    global _sink_instance
    
    if _sink_instance is None:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        _sink_instance = ArangoLogSink(
            db_config=db_config,
            batch_size=int(os.getenv("LOG_BATCH_SIZE", "200")),
            flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "2")),
            buffer_dir=Path(os.getenv("LOG_BUFFER_DIR", "/tmp/logger_agent_buffer")),
            max_buffer_size_mb=int(os.getenv("LOG_MAX_BUFFER_SIZE_MB", "1000"))
        )
        
        # Start sink in background
        asyncio.create_task(_sink_instance.start())
    
    return _sink_instance


async def working_usage():
    """Test the ArangoDB sink with sample logs."""
    logger.info("=== Testing ArangoDB Sink ===")
    
    # Configure logger with our sink
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True)
    
    # Generate test logs
    execution_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    logger.bind(execution_id=execution_id, tags=["test", "sink"]).info("Test log 1")
    logger.bind(execution_id=execution_id, tags=["test"]).warning("Test warning")
    logger.bind(execution_id=execution_id).error("Test error")
    
    # Wait for logs to be written
    await asyncio.sleep(3)
    
    # Check stats
    logger.info(f"Sink stats: {sink.stats}")
    
    return True


async def debug_function():
    """Debug sink behavior under various conditions."""
    logger.info("=== Debug Mode: Testing Edge Cases ===")
    
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True)
    
    # Test 1: High volume logging
    logger.info("Test 1: High volume")
    for i in range(1000):
        logger.bind(test_id=f"volume_{i}").debug(f"High volume test {i}")
    
    await asyncio.sleep(5)
    logger.info(f"After high volume: {sink.stats}")
    
    # Test 2: Large messages
    logger.info("Test 2: Large messages")
    large_data = {"data": "x" * 10000, "array": list(range(1000))}
    logger.bind(extra_data=large_data).info("Large message test")
    
    await asyncio.sleep(2)
    
    # Test 3: Connection failure simulation
    logger.info("Test 3: Simulating connection failure")
    sink.connected = False  # Simulate disconnection
    
    for i in range(10):
        logger.bind(test="failover").error(f"Failover test {i}")
    
    await asyncio.sleep(3)
    logger.info(f"After failover: {sink.stats}")
    
    # Check buffer files
    buffer_files = list(sink.buffer_dir.glob("*.jsonl"))
    logger.info(f"Buffer files: {len(buffer_files)}")
    
    return True


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        # Cleanup
        sink = get_arango_sink()
        if sink:
            await sink.stop()
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

## Phase 3: Agent Log Manager Implementation

### Unified Logger API

```python
#!/usr/bin/env python3
"""
agent_log_manager.py - Unified API for agent logging and introspection

Provides a singleton interface for agents to log, query, and analyze
their execution history using ArangoDB backend.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

from aioarango import ArangoClient
from loguru import logger
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

# Import from existing modules
from arangodb.core.search.hybrid_search import HybridSearch
from arangodb.core.graph.relationship_extraction import RelationshipExtractor
from arangodb.core.memory.memory_agent import MemoryAgent
from log_utils import truncate_large_value


class AgentLogManager:
    """Singleton manager for agent logging operations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.db = None
            self.client = None
            self.execution_context = {}
            self.current_execution_id = None
            
            # Integration modules
            self.hybrid_search = None
            self.relationship_extractor = None
            self.memory_agent = None
            
            self._initialized = True
    
    async def initialize(self, db_config: Dict[str, str]) -> None:
        """Initialize database connection and integration modules."""
        try:
            self.client = ArangoClient(hosts=db_config["url"])
            self.db = await self.client.db(
                db_config["database"],
                username=db_config["username"],
                password=db_config["password"]
            )
            
            # Initialize integration modules
            self.hybrid_search = HybridSearch(self.db)
            self.relationship_extractor = RelationshipExtractor(self.db)
            self.memory_agent = MemoryAgent(self.db)
            
            logger.info("AgentLogManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentLogManager: {e}")
            raise
    
    def generate_execution_id(self, script_name: str) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{script_name}_{timestamp}_{unique_id}"
    
    @asynccontextmanager
    async def script_execution(self, script_name: str, metadata: Optional[Dict] = None):
        """Context manager for script execution tracking."""
        execution_id = self.generate_execution_id(script_name)
        self.current_execution_id = execution_id
        
        # Start script run
        await self.start_run(script_name, execution_id, metadata)
        
        try:
            # Bind execution context to logger
            logger.bind(
                execution_id=execution_id,
                script_name=script_name
            )
            
            yield execution_id
            
            # Mark as successful
            await self.end_run(execution_id, "success")
            
        except Exception as e:
            # Mark as failed
            await self.end_run(execution_id, "failed", str(e))
            raise
        
        finally:
            self.current_execution_id = None
    
    async def start_run(
        self,
        script_name: str,
        execution_id: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record script execution start."""
        doc = {
            "execution_id": execution_id,
            "script_name": script_name,
            "start_time": datetime.utcnow().isoformat(),
            "status": "running",
            "metadata": metadata or {},
            "pid": os.getpid(),
            "hostname": socket.gethostname()
        }
        
        try:
            await self.db.collection("script_runs").insert(doc)
            logger.info(f"Started script run: {execution_id}")
        except Exception as e:
            logger.error(f"Failed to record script start: {e}")
    
    async def end_run(
        self,
        execution_id: str,
        status: str = "success",
        error: Optional[str] = None
    ) -> None:
        """Record script execution end."""
        update_doc = {
            "end_time": datetime.utcnow().isoformat(),
            "status": status,
            "duration_seconds": None  # Will calculate from start_time
        }
        
        if error:
            update_doc["error"] = truncate_large_value(error, max_str_len=1000)
        
        try:
            # Get start time to calculate duration
            run_doc = await self.db.collection("script_runs").get({"execution_id": execution_id})
            if run_doc:
                start_time = datetime.fromisoformat(run_doc["start_time"])
                end_time = datetime.fromisoformat(update_doc["end_time"])
                update_doc["duration_seconds"] = (end_time - start_time).total_seconds()
            
            await self.db.collection("script_runs").update_match(
                {"execution_id": execution_id},
                update_doc
            )
            logger.info(f"Ended script run: {execution_id} ({status})")
            
        except Exception as e:
            logger.error(f"Failed to record script end: {e}")
    
    async def query_logs(
        self,
        aql_query: str,
        bind_vars: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute custom AQL query on logs."""
        try:
            cursor = await self.db.aql.execute(
                aql_query,
                bind_vars=bind_vars or {},
                batch_size=100
            )
            
            results = []
            async for doc in cursor:
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"AQL query failed: {e}")
            raise
    
    async def search_logs(
        self,
        query: str,
        execution_id: Optional[str] = None,
        level: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search logs with multiple filters."""
        # Build AQL query
        filters = []
        bind_vars = {"query": query, "limit": limit}
        
        if execution_id:
            filters.append("doc.execution_id == @execution_id")
            bind_vars["execution_id"] = execution_id
        
        if level:
            filters.append("doc.level == @level")
            bind_vars["level"] = level
        
        if time_range:
            if "start" in time_range:
                filters.append("doc.timestamp >= @start_time")
                bind_vars["start_time"] = time_range["start"].isoformat()
            if "end" in time_range:
                filters.append("doc.timestamp <= @end_time")
                bind_vars["end_time"] = time_range["end"].isoformat()
        
        where_clause = " AND ".join(filters) if filters else "true"
        
        aql = f"""
        FOR doc IN log_events_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        FILTER {where_clause}
        SORT BM25(doc) DESC, doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        return await self.query_logs(aql, bind_vars)
    
    async def search_bm25_logs(
        self,
        text_query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Full-text search using BM25 relevance."""
        # Use hybrid search module for advanced search
        if self.hybrid_search:
            results = await self.hybrid_search.search(
                query=text_query,
                search_type="bm25",
                collection="log_events",
                limit=limit,
                filters=filters
            )
            return results
        
        # Fallback to basic search
        return await self.search_logs(text_query, limit=limit)
    
    async def get_latest_response(
        self,
        script_name: str,
        execution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest structured response from a script."""
        bind_vars = {"script_name": script_name}
        
        if execution_id:
            bind_vars["execution_id"] = execution_id
            filter_clause = "doc.execution_id == @execution_id"
        else:
            filter_clause = "doc.script_name == @script_name"
        
        aql = f"""
        FOR doc IN log_events
        FILTER {filter_clause} AND doc.extra_data.response != null
        SORT doc.timestamp DESC
        LIMIT 1
        RETURN doc.extra_data.response
        """
        
        results = await self.query_logs(aql, bind_vars)
        return results[0] if results else None
    
    async def log_agent_learning(
        self,
        message: str,
        function_name: str,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8
    ) -> None:
        """Record an agent learning or insight."""
        doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": self.current_execution_id or "manual",
            "learning": message,
            "function_name": function_name,
            "context": context or {},
            "confidence": confidence
        }
        
        try:
            await self.db.collection("agent_learnings").insert(doc)
            logger.info(f"Recorded agent learning: {message[:100]}...")
            
            # Also log to memory agent if available
            if self.memory_agent:
                await self.memory_agent.add_memory(
                    content=message,
                    memory_type="learning",
                    metadata={
                        "function": function_name,
                        "confidence": confidence,
                        **context
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to record agent learning: {e}")
    
    async def build_execution_graph(
        self,
        execution_id: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Build a graph representation of an execution."""
        # Get all logs for execution
        logs_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        SORT doc.timestamp
        RETURN doc
        """
        
        logs = await self.query_logs(logs_aql, {"execution_id": execution_id})
        
        # Build graph structure
        graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "execution_id": execution_id,
                "total_logs": len(logs)
            }
        }
        
        # Create nodes
        for i, log in enumerate(logs):
            node = {
                "id": log.get("_id", f"log_{i}"),
                "label": f"{log['level']}: {log['message'][:50]}...",
                "timestamp": log["timestamp"],
                "level": log["level"],
                "function": log.get("function_name", "unknown")
            }
            graph["nodes"].append(node)
        
        # Extract relationships if requested
        if include_relationships and self.relationship_extractor:
            # Analyze log messages for relationships
            for i, log in enumerate(logs[:-1]):
                # Simple temporal relationship
                edge = {
                    "from": log.get("_id", f"log_{i}"),
                    "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                    "type": "FOLLOWED_BY",
                    "weight": 1.0
                }
                graph["edges"].append(edge)
                
                # Extract semantic relationships
                if "error" in log["level"].lower() and i + 1 < len(logs):
                    if "fix" in logs[i + 1]["message"].lower():
                        edge = {
                            "from": log.get("_id", f"log_{i}"),
                            "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                            "type": "FIXED_BY",
                            "weight": 0.9
                        }
                        graph["edges"].append(edge)
        
        return graph
    
    async def prune_logs(
        self,
        older_than_days: Optional[int] = None,
        execution_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Prune old logs based on criteria."""
        stats = {"examined": 0, "deleted": 0}
        
        # Build filter conditions
        filters = []
        bind_vars = {}
        
        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            filters.append("doc.timestamp < @cutoff_date")
            bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            filters.append("doc.execution_id IN @execution_ids")
            bind_vars["execution_ids"] = execution_ids
        
        if not filters:
            logger.warning("No pruning criteria specified")
            return stats
        
        where_clause = " AND ".join(filters)
        
        # Count matching documents
        count_aql = f"""
        FOR doc IN log_events
        FILTER {where_clause}
        COLLECT WITH COUNT INTO total
        RETURN total
        """
        
        count_result = await self.query_logs(count_aql, bind_vars)
        stats["examined"] = count_result[0] if count_result else 0
        
        if not dry_run and stats["examined"] > 0:
            # Delete matching documents
            delete_aql = f"""
            FOR doc IN log_events
            FILTER {where_clause}
            REMOVE doc IN log_events
            RETURN OLD
            """
            
            deleted = await self.query_logs(delete_aql, bind_vars)
            stats["deleted"] = len(deleted)
            
            logger.info(f"Pruned {stats['deleted']} logs")
        
        return stats
    
    async def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a script execution."""
        # Get run info
        run_aql = """
        FOR doc IN script_runs
        FILTER doc.execution_id == @execution_id
        RETURN doc
        """
        
        run_info = await self.query_logs(run_aql, {"execution_id": execution_id})
        
        if not run_info:
            return {"error": "Execution not found"}
        
        # Get log statistics
        stats_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        COLLECT level = doc.level WITH COUNT INTO count
        RETURN {level: level, count: count}
        """
        
        log_stats = await self.query_logs(stats_aql, {"execution_id": execution_id})
        
        # Get errors if any
        errors_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id AND doc.level IN ["ERROR", "CRITICAL"]
        SORT doc.timestamp
        LIMIT 10
        RETURN {
            timestamp: doc.timestamp,
            message: doc.message,
            function: doc.function_name
        }
        """
        
        errors = await self.query_logs(errors_aql, {"execution_id": execution_id})
        
        # Get learnings
        learnings_aql = """
        FOR doc IN agent_learnings
        FILTER doc.execution_id == @execution_id
        RETURN {
            learning: doc.learning,
            confidence: doc.confidence,
            function: doc.function_name
        }
        """
        
        learnings = await self.query_logs(learnings_aql, {"execution_id": execution_id})
        
        summary = {
            "execution_id": execution_id,
            "run_info": run_info[0],
            "log_statistics": {stat["level"]: stat["count"] for stat in log_stats},
            "errors": errors,
            "learnings": learnings,
            "total_logs": sum(stat["count"] for stat in log_stats)
        }
        
        return summary


# Global instance getter
_manager_instance: Optional[AgentLogManager] = None


async def get_log_manager() -> AgentLogManager:
    """Get or create the global AgentLogManager instance."""
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = AgentLogManager()
        
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        await _manager_instance.initialize(db_config)
    
    return _manager_instance


async def working_usage():
    """Demonstrate AgentLogManager functionality."""
    logger.info("=== Testing AgentLogManager ===")
    
    manager = await get_log_manager()
    
    # Test 1: Script execution context
    async with manager.script_execution("test_script", {"version": "1.0"}) as exec_id:
        logger.info("Starting test operations")
        
        # Log some events
        logger.debug("Debug message")
        logger.info("Processing data")
        logger.warning("Resource usage high")
        
        # Log a learning
        await manager.log_agent_learning(
            "Discovered that batch size of 100 is optimal for this dataset",
            "process_data",
            {"batch_size": 100, "performance": "optimal"}
        )
        
        # Simulate some work
        await asyncio.sleep(1)
        
        logger.success("Operations completed")
    
    # Test 2: Query logs
    logger.info("\nQuerying recent logs...")
    recent_logs = await manager.search_logs(
        "test",
        execution_id=exec_id,
        limit=5
    )
    logger.info(f"Found {len(recent_logs)} recent logs")
    
    # Test 3: Get execution summary
    logger.info("\nGetting execution summary...")
    summary = await manager.get_execution_summary(exec_id)
    logger.info(f"Summary: {json.dumps(summary, indent=2)}")
    
    return True


async def debug_function():
    """Debug advanced features of AgentLogManager."""
    logger.info("=== Debug Mode: Advanced Features ===")
    
    manager = await get_log_manager()
    
    # Test 1: Complex AQL query
    logger.info("Test 1: Complex AQL query")
    aql = """
    FOR doc IN log_events
    FILTER doc.level IN ["ERROR", "CRITICAL"]
    COLLECT level = doc.level INTO logs
    RETURN {
        level: level,
        count: LENGTH(logs),
        recent: (
            FOR log IN logs
            SORT log.doc.timestamp DESC
            LIMIT 3
            RETURN log.doc.message
        )
    }
    """
    
    results = await manager.query_logs(aql)
    logger.info(f"Error summary: {results}")
    
    # Test 2: Build execution graph
    logger.info("\nTest 2: Building execution graph")
    
    # Create a test execution with related logs
    async with manager.script_execution("graph_test") as exec_id:
        logger.info("Step 1: Initialize")
        logger.info("Step 2: Load data")
        logger.error("Step 3: Connection failed")
        logger.info("Step 4: Retrying connection")
        logger.success("Step 5: Connection restored")
        
        await asyncio.sleep(1)
    
    graph = await manager.build_execution_graph(exec_id)
    logger.info(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    
    # Test 3: Prune logs (dry run)
    logger.info("\nTest 3: Pruning old logs (dry run)")
    prune_stats = await manager.prune_logs(
        older_than_days=30,
        dry_run=True
    )
    logger.info(f"Would prune: {prune_stats}")
    
    return True


if __name__ == "__main__":
    import sys
    import os
    import socket
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logger with ArangoDB sink
    from arango_log_sink import get_arango_sink
    sink = get_arango_sink()
    logger.add(sink.write, enqueue=True)
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        # Cleanup
        await sink.stop()
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

## Phase 4: Python Script Template Integration

### Enhanced Template with Logger Agent

```python
#!/usr/bin/env python3
"""
enhanced_script_template.py - Python script template with Logger Agent integration

Demonstrates how to integrate the Logger Agent into standard Python scripts
for comprehensive logging and introspection capabilities.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Third-party imports
from loguru import logger
import redis
from dotenv import load_dotenv

# Logger Agent imports
from agent_log_manager import get_log_manager
from arango_log_sink import get_arango_sink

# Load environment
load_dotenv()

# Configure logging with ArangoDB sink
logger.remove()  # Remove default handler

# Add console output
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Add ArangoDB sink
sink = get_arango_sink()
logger.add(sink.write, enqueue=True, level="DEBUG")

# Optional: Add file logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / f"{Path(__file__).stem}_{{time}}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)

# Redis connection
try:
    redis_client = redis.Redis(decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    logger.warning("Redis not available - some features will be limited")
    redis_client = None
    REDIS_AVAILABLE = False


# ============================================
# CORE FUNCTIONS
# ============================================

async def process_data_with_logging(
    data: List[Dict[str, Any]],
    threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Process data with comprehensive logging and learning capture.
    
    Args:
        data: List of data items to process
        threshold: Processing threshold
        
    Returns:
        Processing results with statistics
    """
    manager = await get_log_manager()
    
    logger.info(f"Processing {len(data)} items with threshold {threshold}")
    
    results = {
        "processed": 0,
        "above_threshold": 0,
        "errors": 0,
        "items": []
    }
    
    for i, item in enumerate(data):
        try:
            # Log progress periodically
            if i % 100 == 0:
                logger.debug(f"Processing item {i}/{len(data)}")
            
            # Process item
            score = item.get("value", 0) * item.get("weight", 1)
            
            if score > threshold:
                results["above_threshold"] += 1
                
                # Log interesting findings
                if score > threshold * 1.5:
                    logger.info(
                        f"High score item found: {item.get('id')} (score: {score:.2f})"
                    )
            
            results["items"].append({
                "id": item.get("id"),
                "score": score,
                "passed": score > threshold
            })
            
            results["processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing item {i}: {e}")
            results["errors"] += 1
            
            # Learn from error
            await manager.log_agent_learning(
                f"Item processing failed with: {type(e).__name__}. "
                f"Consider adding validation for {list(item.keys())}",
                "process_data_with_logging",
                {"error_type": type(e).__name__, "item_keys": list(item.keys())}
            )
    
    # Log summary
    logger.success(
        f"Processing complete: {results['processed']} processed, "
        f"{results['above_threshold']} above threshold, "
        f"{results['errors']} errors"
    )
    
    # Record learnings if we discovered patterns
    if results["errors"] > len(data) * 0.1:  # More than 10% errors
        await manager.log_agent_learning(
            f"High error rate ({results['errors']}/{len(data)}) detected. "
            f"Data quality issues may be present.",
            "process_data_with_logging",
            {"error_rate": results["errors"] / len(data)},
            confidence=0.9
        )
    
    return results


async def analyze_historical_performance(
    script_name: str,
    lookback_days: int = 7
) -> Dict[str, Any]:
    """
    Analyze historical performance of a script using logged data.
    
    Args:
        script_name: Name of script to analyze
        lookback_days: Number of days to look back
        
    Returns:
        Performance analysis results
    """
    manager = await get_log_manager()
    
    # Query historical executions
    aql = """
    FOR run IN script_runs
    FILTER run.script_name == @script_name
    FILTER run.start_time >= DATE_SUBTRACT(DATE_NOW(), @days, "days")
    
    LET log_counts = (
        FOR log IN log_events
        FILTER log.execution_id == run.execution_id
        COLLECT level = log.level WITH COUNT INTO count
        RETURN {level: level, count: count}
    )
    
    RETURN {
        execution_id: run.execution_id,
        start_time: run.start_time,
        duration: run.duration_seconds,
        status: run.status,
        log_summary: log_counts
    }
    """
    
    results = await manager.query_logs(
        aql,
        {"script_name": script_name, "days": lookback_days}
    )
    
    # Analyze results
    analysis = {
        "total_runs": len(results),
        "successful_runs": sum(1 for r in results if r["status"] == "success"),
        "failed_runs": sum(1 for r in results if r["status"] == "failed"),
        "avg_duration": sum(r.get("duration", 0) for r in results) / len(results) if results else 0,
        "error_trend": []
    }
    
    # Calculate error trend
    for result in results:
        error_count = sum(
            log["count"] for log in result.get("log_summary", [])
            if log["level"] in ["ERROR", "CRITICAL"]
        )
        analysis["error_trend"].append({
            "time": result["start_time"],
            "errors": error_count
        })
    
    logger.info(f"Historical analysis complete: {analysis}")
    
    return analysis


async def working_usage():
    """Demonstrate working usage with Logger Agent integration."""
    logger.info("=== Running Working Usage Example ===")
    
    manager = await get_log_manager()
    
    # Use script execution context
    async with manager.script_execution(
        "enhanced_template_demo",
        {"mode": "working", "version": "1.0"}
    ) as execution_id:
        
        # Generate test data
        test_data = [
            {"id": f"item_{i}", "value": i * 0.1, "weight": 1.0}
            for i in range(100)
        ]
        
        # Process data
        results = await process_data_with_logging(test_data, threshold=5.0)
        
        # Save results with execution context
        output_dir = Path("/tmp/responses")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"results_{execution_id}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        # Query our own logs
        recent_errors = await manager.search_logs(
            "error",
            execution_id=execution_id,
            level="ERROR"
        )
        
        if recent_errors:
            logger.warning(f"Found {len(recent_errors)} errors in this execution")
        
        # Analyze historical performance
        analysis = await analyze_historical_performance(
            "enhanced_template_demo",
            lookback_days=7
        )
        
        logger.info(f"Success rate: {analysis['successful_runs']}/{analysis['total_runs']}")
    
    return True


async def debug_function():
    """Debug function for testing Logger Agent features."""
    logger.info("=== Running Debug Function ===")
    
    manager = await get_log_manager()
    
    # Test querying across executions
    logger.info("Searching for patterns across all executions...")
    
    pattern_aql = """
    FOR learning IN agent_learnings
    FILTER learning.confidence >= 0.8
    COLLECT pattern = learning.learning WITH COUNT INTO occurrences
    FILTER occurrences > 1
    SORT occurrences DESC
    LIMIT 10
    RETURN {
        pattern: pattern,
        occurrences: occurrences
    }
    """
    
    patterns = await manager.query_logs(pattern_aql)
    
    if patterns:
        logger.info("Recurring patterns found:")
        for pattern in patterns:
            logger.info(f"  - {pattern['pattern'][:100]}... ({pattern['occurrences']} times)")
    
    # Test error analysis
    logger.info("\nAnalyzing error patterns...")
    
    error_aql = """
    FOR log IN log_events
    FILTER log.level IN ["ERROR", "CRITICAL"]
    FILTER log.timestamp >= DATE_SUBTRACT(DATE_NOW(), 1, "days")
    COLLECT function = log.function_name INTO errors
    SORT LENGTH(errors) DESC
    LIMIT 5
    RETURN {
        function: function,
        error_count: LENGTH(errors),
        sample_messages: (
            FOR e IN errors
            LIMIT 3
            RETURN e.log.message
        )
    }
    """
    
    error_analysis = await manager.query_logs(error_aql)
    
    for func_errors in error_analysis:
        logger.warning(
            f"Function '{func_errors['function']}' had "
            f"{func_errors['error_count']} errors"
        )
    
    return True


async def stress_test():
    """Stress test Logger Agent with high volume."""
    logger.info("=== Running Stress Test ===")
    
    manager = await get_log_manager()
    
    async with manager.script_execution("stress_test") as execution_id:
        
        # Test 1: High volume logging
        logger.info("Test 1: High volume logging (10,000 logs)")
        
        start_time = datetime.utcnow()
        
        for i in range(10000):
            logger.bind(
                iteration=i,
                batch=i // 100
            ).debug(f"Stress test log {i}")
            
            if i % 1000 == 0:
                logger.info(f"Progress: {i}/10000")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.success(f"Logged 10,000 messages in {duration:.2f} seconds")
        
        # Test 2: Complex queries
        logger.info("\nTest 2: Complex aggregation query")
        
        complex_aql = """
        FOR log IN log_events
        FILTER log.execution_id == @execution_id
        COLLECT level = log.level, batch = log.extra_data.batch
        WITH COUNT INTO count
        FILTER count > 10
        SORT count DESC
        RETURN {
            level: level,
            batch: batch,
            count: count
        }
        """
        
        results = await manager.query_logs(
            complex_aql,
            {"execution_id": execution_id}
        )
        
        logger.info(f"Aggregation returned {len(results)} groups")
        
        # Test 3: Concurrent operations
        logger.info("\nTest 3: Concurrent logging")
        
        async def concurrent_logger(worker_id: int):
            for i in range(100):
                logger.bind(worker=worker_id).info(f"Worker {worker_id} log {i}")
                await asyncio.sleep(0.01)
        
        workers = [concurrent_logger(i) for i in range(10)]
        await asyncio.gather(*workers)
        
        logger.success("Stress test completed")
    
    # Get final statistics
    summary = await manager.get_execution_summary(execution_id)
    logger.info(f"Total logs generated: {summary['total_logs']}")
    
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        """Main entry point with Logger Agent lifecycle."""
        try:
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function()
            elif mode == "stress":
                logger.info("Running in STRESS TEST mode...")
                success = await stress_test()
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage()
            
            return success
            
        finally:
            # Ensure sink is properly closed
            if sink:
                await sink.stop()
    
    success = asyncio.run(main())
    exit(0 if success else 1)
```

## Phase 5: Agent-Facing Documentation

### Prompts Directory Structure

```
prompts/
├── queries/
│   ├── find_errors_in_execution.md
│   ├── analyze_performance_trends.md
│   └── extract_learnings.md
├── patterns/
│   ├── error_recovery_pattern.md
│   ├── performance_optimization.md
│   └── debugging_workflow.md
└── guides/
    ├── using_logger_agent.md
    └── best_practices.md
```

### Sample Prompt: Find Errors in Execution

```markdown
# Find Errors in Execution

## Purpose
Query the Logger Agent to find all errors that occurred during a specific execution.

## Code Template

```python
from agent_log_manager import get_log_manager

async def find_execution_errors(execution_id: str):
    """Find all errors in a specific execution."""
    manager = await get_log_manager()
    
    # Query for errors and their context
    aql = """
    FOR log IN log_events
    FILTER log.execution_id == @execution_id
    FILTER log.level IN ["ERROR", "CRITICAL"]
    
    LET context = (
        FOR ctx IN log_events
        FILTER ctx.execution_id == log.execution_id
        FILTER ctx.timestamp >= DATE_SUBTRACT(log.timestamp, 5, "seconds")
        FILTER ctx.timestamp <= DATE_ADD(log.timestamp, 5, "seconds")
        SORT ctx.timestamp
        RETURN {
            time: ctx.timestamp,
            level: ctx.level,
            message: ctx.message
        }
    )
    
    RETURN {
        error: log,
        context: context
    }
    """
    
    results = await manager.query_logs(aql, {"execution_id": execution_id})
    
    for error_data in results:
        error = error_data["error"]
        print(f"\n❌ ERROR at {error['timestamp']}")
        print(f"   Function: {error['function_name']}")
        print(f"   Message: {error['message']}")
        print(f"   File: {error['file_path']}:{error['line_number']}")
        
        print("\n   Context:")
        for ctx in error_data["context"]:
            print(f"   [{ctx['level']}] {ctx['message'][:80]}...")
```

## Usage
1. Replace `execution_id` with your actual execution ID
2. The query returns errors with 5 seconds of context before and after
3. Use the context to understand what led to the error
```

## Integration with Existing Modules

### Graph Integration

```python
# Using existing graph modules with Logger Agent
from arangodb.core.graph.relationship_extraction import RelationshipExtractor
from agent_log_manager import get_log_manager

async def extract_log_relationships(execution_id: str):
    """Extract semantic relationships between log events."""
    manager = await get_log_manager()
    extractor = RelationshipExtractor(manager.db)
    
    # Get all logs for execution
    logs = await manager.search_logs("*", execution_id=execution_id)
    
    # Extract relationships
    relationships = []
    for i, log in enumerate(logs[:-1]):
        # Use existing relationship extraction
        rels = await extractor.extract_relationships(
            log["message"],
            logs[i + 1]["message"]
        )
        
        for rel in rels:
            relationships.append({
                "from_log": log["_id"],
                "to_log": logs[i + 1]["_id"],
                "relationship": rel["type"],
                "confidence": rel["confidence"]
            })
    
    return relationships
```

### Memory Integration

```python
# Integrating with Memory Agent
from arangodb.core.memory.memory_agent import MemoryAgent
from agent_log_manager import get_log_manager

async def create_execution_memory(execution_id: str):
    """Create a memory entry for an execution."""
    manager = await get_log_manager()
    memory = MemoryAgent(manager.db)
    
    # Get execution summary
    summary = await manager.get_execution_summary(execution_id)
    
    # Create memory
    await memory.add_memory(
        content=f"Execution {execution_id} completed with "
                f"{summary['log_statistics'].get('ERROR', 0)} errors",
        memory_type="execution_summary",
        metadata={
            "execution_id": execution_id,
            "script": summary["run_info"]["script_name"],
            "duration": summary["run_info"]["duration_seconds"],
            "status": summary["run_info"]["status"]
        }
    )
```

## Monitoring Dashboard

```python
#!/usr/bin/env python3
"""
logger_monitor.py - Simple terminal monitoring for Logger Agent
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from agent_log_manager import get_log_manager

console = Console()

async def monitor_dashboard():
    """Display live monitoring dashboard."""
    manager = await get_log_manager()
    
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            # Get current stats
            stats_aql = """
            LET recent_logs = (
                FOR log IN log_events
                FILTER log.timestamp >= DATE_SUBTRACT(DATE_NOW(), 5, "minutes")
                COLLECT level = log.level WITH COUNT INTO count
                RETURN {level: level, count: count}
            )
            
            LET active_runs = (
                FOR run IN script_runs
                FILTER run.status == "running"
                RETURN run
            )
            
            RETURN {
                recent_logs: recent_logs,
                active_runs: active_runs,
                timestamp: DATE_NOW()
            }
            """
            
            stats = await manager.query_logs(stats_aql)
            
            # Create table
            table = Table(title=f"Logger Agent Monitor - {datetime.now()}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            # Add stats
            if stats:
                data = stats[0]
                
                # Log levels
                for log_stat in data.get("recent_logs", []):
                    table.add_row(
                        f"{log_stat['level']} (5 min)",
                        str(log_stat['count'])
                    )
                
                # Active runs
                table.add_row(
                    "Active Runs",
                    str(len(data.get("active_runs", [])))
                )
            
            live.update(table)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(monitor_dashboard())
```

## Summary

This comprehensive implementation provides:

1. **Complete ArangoDB Setup** with experimental features enabled
2. **Async Log Sink** with buffering and retry mechanisms
3. **Unified Agent API** for querying and managing logs
4. **Python Template Integration** showing best practices
5. **Monitoring and Alerting** capabilities
6. **Integration Examples** with existing graph, search, and memory modules

The system is designed to be:
- **Non-blocking**: Never slows down the main application
- **Reliable**: Disk buffering ensures no log loss
- **Queryable**: Rich AQL queries for complex analysis
- **Integrated**: Works seamlessly with existing modules
- **Agent-Friendly**: Simple API for AI agents to use

All code follows the Python script template standards with working_usage(), debug_function(), and proper error handling.

===REFERENCED FILES===

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/docker-compose.yml
```yaml
version: '3.8'

services:
  arangodb:
    image: arangodb:3.12.4
    container_name: logger_agent_arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=openSesame
    volumes:
      - arangodb_data:/var/lib/arangodb3
      - arangodb_apps:/var/lib/arangodb3-apps
    command: >
      arangod 
      --query.enable-experimental true
      --server.endpoint tcp://0.0.0.0:8529
      --log.level info
      --database.auto-upgrade true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  arangodb_data:
  arangodb_apps:
```

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.env
```bash
# ArangoDB Configuration
ARANGO_URL=http://localhost:8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=openSesame
ARANGO_DATABASE=script_logs

# Logger Agent Configuration
LOG_BATCH_SIZE=200
LOG_FLUSH_INTERVAL=2
LOG_BUFFER_DIR=/tmp/logger_agent_buffer
LOG_MAX_BUFFER_SIZE_MB=1000
LOG_RETENTION_DAYS=30

# Performance Monitoring
ENABLE_MONITORING=true
MONITORING_INTERVAL=60
ALERT_LOG_FAILURE_THRESHOLD=10

# Python Path
PYTHONPATH=./src
```

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/requirements.txt
```txt
# Core dependencies
loguru>=0.7.2
aioarango>=1.0.0
uvloop>=0.19.0
python-dotenv>=1.0.0
tenacity>=9.0.0

# Integration dependencies (from existing project)
numpy>=2.0.0
scipy>=1.10.0
pandas>=2.0.0
redis>=5.0.0

# Monitoring
psutil>=5.9.0
rich>=13.0.0
```

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/utils/log_utils.py
```python
"""
Module: log_utils.py
Description: Utility functions and helpers for log utils

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import logging
import re
from typing import List, Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Regex to identify common data URI patterns for images
BASE64_IMAGE_PATTERN = re.compile(r"^(data:image/[a-zA-Z+.-]+;base64,)")


def truncate_large_value(
    value: Any,
    max_str_len: int = 100,
    max_list_elements_shown: int = 10,  # Threshold above which list is summarized
) -> Any:
    """
    Truncate large strings or arrays to make them log-friendly.

    Handles base64 image strings by preserving the header and truncating the data.
    Summarizes lists/arrays longer than `max_list_elements_shown`.

    Args:
        value: The value to potentially truncate
        max_str_len: Maximum length for the data part of strings before truncation
        max_list_elements_shown: Maximum number of elements to show in arrays
                                 before summarizing the array instead.

    Returns:
        Truncated or original value
    """
    if isinstance(value, str):
        # Check if it's a base64 image data URI
        match = BASE64_IMAGE_PATTERN.match(value)
        if match:
            header = match.group(1)
            data = value[len(header) :]
            if len(data) > max_str_len:
                half_len = max_str_len // 2
                if half_len == 0 and max_str_len > 0:
                    half_len = 1
                truncated_data = (
                    f"{data[:half_len]}...{data[-half_len:]}" if half_len > 0 else "..."
                )
                return header + truncated_data
            else:
                return value
        # --- It's not a base64 image string, apply generic string truncation ---
        elif len(value) > max_str_len:
            half_len = max_str_len // 2
            if half_len == 0 and max_str_len > 0:
                half_len = 1
            return (
                f"{value[:half_len]}...{value[-half_len:]}" if half_len > 0 else "..."
            )
        else:
            return value

    elif isinstance(value, list):
        # --- Handle large lists (like embeddings) by summarizing ---
        if len(value) > max_list_elements_shown:
            if value:
                element_type = type(value[0]).__name__
                return f"[<{len(value)} {element_type} elements>]"
            else:
                return "[<0 elements>]"
        else:
            # If list elements are dicts, truncate them recursively
            return [truncate_large_value(item, max_str_len, max_list_elements_shown) if isinstance(item, dict) else item for item in value]
    elif isinstance(value, dict): # Add explicit check for dict
            # Recursively truncate values within dictionaries
            return {k: truncate_large_value(v, max_str_len, max_list_elements_shown) for k, v in value.items()}
    else:
        # Handle other types (int, float, bool, None, etc.) - return as is
        return value


def log_safe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a log-safe version of the results list by truncating large fields
    within each dictionary.

    Args:
        results (list): List of documents (dictionaries) that may contain large fields.

    Returns:
        list: Log-safe version of the input list where large fields are truncated.

    Raises:
        TypeError: If the input `results` is not a list, or if any element
                   within the list is not a dictionary.
    """
    # --- Input Validation ---
    if not isinstance(results, list):
        raise TypeError(
            f"Expected input to be a List[Dict[str, Any]], but got {type(results).__name__}."
        )

    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise TypeError(
                f"Expected all elements in the input list to be dictionaries (dict), "
                f"but found element of type {type(item).__name__} at index {index}."
            )
    # --- End Input Validation ---

    log_safe_output = []
    for doc in results:  # We now know 'doc' is a dictionary
        doc_copy = {}
        for key, value in doc.items():
            doc_copy[key] = truncate_large_value(value)
        log_safe_output.append(doc_copy)
    return log_safe_output


def log_api_request(service_name: str, request_data: Dict[str, Any], truncate: bool = True) -> None:
    """Log API request details.

    Args:
        service_name: Name of the service being called
        request_data: Request data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        # Don't modify the original data
        request_data_to_log = truncate_large_value(request_data)
    else:
        request_data_to_log = request_data

    logger.debug(f"{service_name} API Request: {request_data_to_log}")

def log_api_response(service_name: str, response_data: Any, truncate: bool = True) -> None:
    """Log API response details.

    Args:
        service_name: Name of the service being called
        response_data: Response data to log
        truncate: Whether to truncate large values
    """
    if truncate:
        # Don't modify the original data
        response_data_to_log = truncate_large_value(response_data)
    else:
        response_data_to_log = response_data

    logger.debug(f"{service_name} API Response: {response_data_to_log}")

def log_api_error(service_name: str, error: Exception, request_data: Optional[Dict[str, Any]] = None) -> None:
    """Log API error details.

    Args:
        service_name: Name of the service being called
        error: The error that occurred
        request_data: Optional request data for context
    """
    error_message = f"{service_name} API Error: {str(error)}"

    if request_data:
        truncated_data = truncate_large_value(request_data)
        error_message += f" (Request: {truncated_data})"

    logger.error(error_message)


if __name__ == "__main__":
    # --- Valid Test Data ---
    valid_test_data = [
        {
            "id": 1,
            "description": "A short description.",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "image_small": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            "tags": ["short", "list"],
        },
        {
            "id": 2,
            "description": "This description is quite long, much longer than the default one hundred characters allowed, so it should definitely be truncated according to the rules specified in the function."
            * 2,
            "embedding": [float(i) / 100 for i in range(150)],
            "image_large": "data:image/jpeg;base64," + ("B" * 500),
            "tags": ["tag" + str(i) for i in range(20)],
        },
        {
            "id": 3,
            "description": "Edge case string." + "C" * 100,
            "embedding": [],
            "image_none": None,
            "image_weird_header": "data:application/octet-stream;base64," + ("D" * 150),
            "tags": [
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
                "ten",
                "eleven",
            ],
        },
    ]

    print("--- Processing Valid Data ---")
    try:
        safe_results = log_safe_results(valid_test_data)
        print("Valid data processed successfully.")
        # print("\n--- Log-Safe Results (Valid Data) ---")
        # for item in safe_results:
        #     print(item) # Optional: print results if needed
    except TypeError as e:
        print(f" ERROR processing valid data: {e}")

    print("\n--- Testing Invalid Inputs ---")

    # Test Case 1: Input is not a list
    invalid_input_1 = {"a": 1, "b": 2}  # A dictionary
    print(f"\nTesting input: {invalid_input_1} ({type(invalid_input_1).__name__})")
    try:
        log_safe_results(invalid_input_1)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 2: Input is a list, but contains non-dict elements
    invalid_input_2 = [{"a": 1}, "string_element", {"c": 3}]  # List with a string
    print(f"\nTesting input: {invalid_input_2}")
    try:
        log_safe_results(invalid_input_2)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 3: Input is a list of simple types
    invalid_input_3 = [1, 2, 3, 4]  # List of integers
    print(f"\nTesting input: {invalid_input_3}")
    try:
        log_safe_results(invalid_input_3)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 4: Input is None
    invalid_input_4 = None
    print(f"\nTesting input: {invalid_input_4}")
    try:
        log_safe_results(invalid_input_4)
    except TypeError as e:
        print(f" Successfully caught expected error: {e}")
    except Exception as e:
        print(f" Caught unexpected error: {e}")

    # Test Case 5: Empty list (should be valid)
    valid_input_empty = []
    print(f"\nTesting input: {valid_input_empty}")
    try:
        result = log_safe_results(valid_input_empty)
        if result == []:
            print(f" Successfully processed empty list.")
        else:
            print(f" Processing empty list resulted in unexpected output: {result}")
    except Exception as e:
        print(f" Caught unexpected error processing empty list: {e}")

    # Test API logging functions
    print("\n--- Testing API Logging Functions ---")
    try:
        log_api_request("TestService", {"model": "test-model", "prompt": "This is a test prompt"})
        log_api_response("TestService", {"result": "This is a test result", "status": "success"})
        log_api_error("TestService", Exception("Test error"), {"model": "test-model"})
        print(" API logging functions executed successfully.")
    except Exception as e:
        print(f" Error testing API logging functions: {e}")
```

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/prompts/queries/find_errors_in_execution.md
```markdown
# Find Errors in Execution

## Purpose
Query the Logger Agent to find all errors that occurred during a specific execution.

## Code Template

```python
from agent_log_manager import get_log_manager

async def find_execution_errors(execution_id: str):
    """Find all errors in a specific execution."""
    manager = await get_log_manager()
    
    # Query for errors and their context
    aql = """
    FOR log IN log_events
    FILTER log.execution_id == @execution_id
    FILTER log.level IN ["ERROR", "CRITICAL"]
    
    LET context = (
        FOR ctx IN log_events
        FILTER ctx.execution_id == log.execution_id
        FILTER ctx.timestamp >= DATE_SUBTRACT(log.timestamp, 5, "seconds")
        FILTER ctx.timestamp <= DATE_ADD(log.timestamp, 5, "seconds")
        SORT ctx.timestamp
        RETURN {
            time: ctx.timestamp,
            level: ctx.level,
            message: ctx.message
        }
    )
    
    RETURN {
        error: log,
        context: context
    }
    """
    
    results = await manager.query_logs(aql, {"execution_id": execution_id})
    
    for error_data in results:
        error = error_data["error"]
        print(f"\n❌ ERROR at {error['timestamp']}")
        print(f"   Function: {error['function_name']}")
        print(f"   Message: {error['message']}")
        print(f"   File: {error['file_path']}:{error['line_number']}")
        
        print("\n   Context:")
        for ctx in error_data["context"]:
            print(f"   [{ctx['level']}] {ctx['message'][:80]}...")
```

## Usage
1. Replace `execution_id` with your actual execution ID
2. The query returns errors with 5 seconds of context before and after
3. Use the context to understand what led to the error
```

### File: /home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/prompts/guides/using_logger_agent.md
```markdown
# Using Logger Agent - Agent Guide

## Overview
The Logger Agent provides comprehensive logging and introspection capabilities for AI agents. This guide shows how to effectively use the system.

## Basic Usage

### 1. Import and Initialize
```python
from agent_log_manager import get_log_manager
from arango_log_sink import get_arango_sink
from loguru import logger

# Add ArangoDB sink to logger
sink = get_arango_sink()
logger.add(sink.write, enqueue=True)

# Get manager instance
manager = await get_log_manager()
```

### 2. Script Execution Context
```python
# Always use execution context for tracking
async with manager.script_execution("my_script", {"version": "1.0"}) as exec_id:
    logger.info("Starting script operations")
    # Your code here
    logger.success("Script completed")
```

### 3. Logging Best Practices
```python
# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning conditions")
logger.error("Error conditions")
logger.critical("Critical failures")

# Bind context data
logger.bind(user_id="123", action="process").info("Processing user request")

# Log structured data
logger.bind(response={"status": "success", "items": 42}).info("API response")
```

### 4. Recording Agent Learnings
```python
# Record insights and patterns you discover
await manager.log_agent_learning(
    "Batch size of 100 optimal for this dataset type",
    "process_data",
    {"dataset_size": 10000, "batch_size": 100},
    confidence=0.9
)
```

## Advanced Queries

### Find Recent Errors
```python
errors = await manager.search_logs(
    "error",
    level="ERROR",
    time_range={"start": datetime.utcnow() - timedelta(hours=1)},
    limit=10
)
```

### Analyze Performance Patterns
```python
aql = """
FOR run IN script_runs
FILTER run.script_name == @script_name
COLLECT status = run.status WITH COUNT INTO count
RETURN {status: status, count: count}
"""

results = await manager.query_logs(aql, {"script_name": "my_script"})
```

### Extract Learnings Across Executions
```python
aql = """
FOR learning IN agent_learnings
FILTER learning.confidence >= 0.8
SORT learning.timestamp DESC
LIMIT 20
RETURN learning
"""

learnings = await manager.query_logs(aql)
```

## Tips for Effective Logging

1. **Always use execution context** - It groups related logs
2. **Log at appropriate levels** - Don't log everything as INFO
3. **Include structured data** - Use logger.bind() for context
4. **Record learnings** - Document patterns and insights
5. **Query your history** - Learn from past executions
6. **Monitor performance** - Track execution times and errors

## Common Patterns

### Error Recovery Pattern
```python
try:
    result = await risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    
    # Query similar errors
    similar = await manager.search_logs(
        str(e),
        level="ERROR",
        limit=5
    )
    
    if similar:
        logger.info(f"Found {len(similar)} similar errors")
        # Learn from past solutions
```

### Performance Monitoring
```python
start = datetime.utcnow()
# ... operation ...
duration = (datetime.utcnow() - start).total_seconds()

logger.bind(duration_seconds=duration).info("Operation completed")

# Later, analyze performance
aql = """
FOR log IN log_events
FILTER log.extra_data.duration_seconds != null
COLLECT avg_duration = AVG(log.extra_data.duration_seconds)
RETURN avg_duration
"""
```

## Remember
- Logs are automatically batched and sent asynchronously
- Failed logs are buffered to disk and retried
- Use AQL for complex queries across executions
- The system is designed to never block your main code
```