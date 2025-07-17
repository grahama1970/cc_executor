
#!/usr/bin/env python3
"""
arango_log_sink.py - Custom Loguru sink for ArangoDB

Provides a thread-safe, asynchronous sink that batches log entries
and writes them to ArangoDB for persistence and analysis.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_log_sink_new.py          # Runs working_usage() - stable, known to work
  python arango_log_sink_new.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import uuid
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import deque
import threading
from queue import Queue, Empty

from arango import ArangoClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.log_utils import truncate_large_value


class ArangoLogSink:
    """
    Custom Loguru sink that writes logs to ArangoDB.
    
    Features:
    - Asynchronous batch writes for performance
    - Thread-safe operation
    - Automatic reconnection on failures
    - Configurable batching and flushing
    """
    
    def __init__(
        self,
        db_config: Dict[str, str],
        collection_name: str = "log_events",
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize the ArangoDB sink.
        
        Args:
            db_config: Database configuration with url, database, username, password
            collection_name: Name of the collection to write logs to
            batch_size: Number of logs to batch before writing
            flush_interval: Seconds between automatic flushes
            max_retries: Maximum number of retry attempts on failure
        """
        self.db_config = db_config
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        
        # Connection objects
        self.client = None
        self.db = None
        self.collection = None
        
        # Batch management
        self.log_queue = Queue()
        self.failed_logs = deque(maxlen=1000)  # Keep last 1000 failed logs
        
        # Thread management
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "successful_writes": 0,
            "failed_writes": 0,
            "last_error": None
        }
        
        # Execution context
        self.current_execution_id = None
        self.script_name = None
    
    def connect(self) -> None:
        """Establish connection to ArangoDB."""
        try:
            self.client = ArangoClient(hosts=self.db_config["url"])
            self.db = self.client.db(
                self.db_config["database"],
                username=self.db_config["username"],
                password=self.db_config["password"]
            )
            self.collection = self.db.collection(self.collection_name)
            logger.info(f"Connected to ArangoDB database: {self.db_config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            raise
    
    def set_execution_context(self, execution_id: str, script_name: str) -> None:
        """Set the current execution context for logs."""
        self.current_execution_id = execution_id
        self.script_name = script_name
    
    def write(self, message) -> None:
        """
        Write method called by Loguru.
        
        This method is called in the thread that generates the log,
        so we just queue it for batch processing.
        """
        try:
            # Parse the log record
            record = message.record
            
            # Prepare log document
            log_doc = {
                # Execution context
                "execution_id": self.current_execution_id or record.get("extra", {}).get("execution_id", "unknown"),
                "script_name": self.script_name or record.get("extra", {}).get("script_name", "unknown"),
                
                # Standard fields
                "timestamp": datetime.fromisoformat(record["time"].isoformat()),
                "level": record["level"].name,
                "logger_name": record["name"],
                "function_name": record["function"],
                "line_number": record["line"],
                "message": record["message"],
                
                # System context
                "process_id": record["process"].id,
                "process_name": record["process"].name,
                "thread_id": record["thread"].id,
                "thread_name": record["thread"].name,
                "hostname": socket.gethostname(),
                
                # Extra data (truncated if needed)
                "extra_data": truncate_large_value(
                    {k: v for k, v in record.get("extra", {}).items() 
                     if k not in ["execution_id", "script_name"]}
                )
            }
            
            # Add exception info if present
            if record.get("exception"):
                exc_info = record["exception"]
                log_doc["exception"] = {
                    "type": exc_info.type.__name__ if exc_info.type else None,
                    "value": str(exc_info.value) if exc_info.value else None,
                    "traceback": exc_info.traceback if exc_info.traceback else None
                }
            
            # Queue the log
            self.log_queue.put(log_doc)
            self.stats["total_logs"] += 1
            
        except Exception as e:
            # Don't raise exceptions in the logging path
            print(f"Error queuing log: {e}")
    
    def _worker_loop(self) -> None:
        """Background worker that processes the log queue."""
        batch = []
        last_flush = datetime.utcnow()
        
        while not self.stop_event.is_set():
            try:
                # Check if we should flush based on time
                now = datetime.utcnow()
                should_flush = (now - last_flush).total_seconds() >= self.flush_interval
                
                # Try to get a log from the queue
                timeout = 0.1 if not should_flush else 0.01
                try:
                    log_doc = self.log_queue.get(timeout=timeout)
                    batch.append(log_doc)
                except Empty:
                    pass
                
                # Flush if batch is full or timeout reached
                if len(batch) >= self.batch_size or (should_flush and batch):
                    self._flush_batch(batch)
                    batch = []
                    last_flush = now
                    
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                # Save failed batch
                self.failed_logs.extend(batch)
                batch = []
        
        # Final flush on shutdown
        if batch:
            self._flush_batch(batch)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _flush_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Flush a batch of logs to ArangoDB with retry logic."""
        if not batch:
            return
        
        try:
            # Ensure we have a valid collection
            if self.collection is None:
                self.connect()
            
            # Batch insert
            result = self.collection.insert_many(batch, overwrite=False)
            
            # Update statistics
            self.stats["successful_writes"] += len(batch)
            
            # Check for any errors in the result
            if hasattr(result, 'errors') and result.errors:
                failed_count = sum(1 for error in result.errors if error)
                self.stats["failed_writes"] += failed_count
                logger.warning(f"Failed to write {failed_count} logs")
                
        except Exception as e:
            # Update statistics
            self.stats["failed_writes"] += len(batch)
            self.stats["last_error"] = str(e)
            
            # Save failed logs
            self.failed_logs.extend(batch)
            
            logger.error(f"Failed to flush batch of {len(batch)} logs: {e}")
            raise
    
    async def start(self) -> None:
        """Start the sink's background worker."""
        # Connect to database
        self.connect()
        
        # Start worker thread
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="ArangoLogSink-Worker",
            daemon=True
        )
        self.worker_thread.start()
        logger.info("ArangoLogSink worker started")
    
    async def stop(self) -> None:
        """Stop the sink and flush remaining logs."""
        logger.info("Stopping ArangoLogSink...")
        
        # Signal worker to stop
        self.stop_event.set()
        
        # Wait for worker to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        # Final flush of any remaining logs
        remaining = []
        while not self.log_queue.empty():
            try:
                remaining.append(self.log_queue.get_nowait())
            except Empty:
                break
        
        if remaining:
            logger.info(f"Flushing {len(remaining)} remaining logs...")
            self._flush_batch(remaining)
        
        # Close database connection
        if self.client:
            self.client.close()
        
        logger.info(f"ArangoLogSink stopped. Stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current sink statistics."""
        return {
            **self.stats,
            "buffered_logs": self.log_queue.qsize(),
            "failed_logs_retained": len(self.failed_logs)
        }
    
    def get_failed_logs(self) -> List[Dict[str, Any]]:
        """Retrieve logs that failed to write."""
        return list(self.failed_logs)
    
    def retry_failed_logs(self) -> int:
        """Retry writing failed logs."""
        if not self.failed_logs:
            return 0
        
        # Get all failed logs and clear the deque
        retry_batch = []
        while self.failed_logs:
            try:
                retry_batch.append(self.failed_logs.popleft())
            except IndexError:
                break
        
        if retry_batch:
            logger.info(f"Retrying {len(retry_batch)} failed logs...")
            try:
                self._flush_batch(retry_batch)
                return len(retry_batch)
            except Exception as e:
                # Put them back if retry fails
                self.failed_logs.extend(retry_batch)
                logger.error(f"Retry failed: {e}")
                return 0
        
        return 0


# Convenience function for creating and configuring the sink
async def get_arango_sink(
    db_config: Optional[Dict[str, str]] = None,
    **kwargs
) -> ArangoLogSink:
    """
    Create and start an ArangoDB sink with default configuration.
    
    Args:
        db_config: Optional database configuration override
        **kwargs: Additional arguments passed to ArangoLogSink
    
    Returns:
        Configured and started ArangoLogSink instance
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if db_config is None:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
    
    # Create sink with defaults
    sink = ArangoLogSink(
        db_config=db_config,
        batch_size=kwargs.get("batch_size", 100),
        flush_interval=kwargs.get("flush_interval", 5.0),
        **{k: v for k, v in kwargs.items() if k not in ["batch_size", "flush_interval"]}
    )
    
    # Start the sink
    await sink.start()
    
    return sink


# Test database isolation functions
async def setup_test_database() -> tuple:
    """Create and initialize a test database."""
    import os
    from dotenv import load_dotenv
    from arango import ArangoClient
    from arango_init import _create_database_schema_sync
    
    load_dotenv()
    
    # Generate unique test database name
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"
    
    # Connect to system database
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    sys_db = client.db(
        "_system",
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Create test database
    sys_db.create_database(unique_db_name)
    
    # Connect to test database
    test_db = client.db(
        unique_db_name,
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Initialize schema
    _create_database_schema_sync(test_db)
    
    # Return test database connection
    logger.info(f"Created and initialized test database: {unique_db_name}")
    return test_db, unique_db_name


def _test_sink_usage():
    """Test the ArangoDB sink with isolation."""
    
    async def run_test():
        # Setup test database
        test_db, test_db_name = await setup_test_database()
        logger.info(f"=== Testing ArangoDB Sink against isolated DB: {test_db_name} ===")
        
        # Create sink for test database
        sink = ArangoLogSink(
            db_config={
                "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
                "database": test_db_name,
                "username": os.getenv("ARANGO_USERNAME", "root"),
                "password": os.getenv("ARANGO_PASSWORD", "openSesame")
            },
            batch_size=10,
            flush_interval=2.0
        )
        
        # Start the sink
        await sink.start()
        
        # Add sink to logger
        handler_id = logger.add(sink.write, enqueue=True)
        
        # Set execution context
        execution_id = f"test_run_sink_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        sink.set_execution_context(execution_id, "sink_test")
        
        try:
            # Generate some logs
            logger.info("Test log 1")
            logger.warning("Test warning")
            logger.error("Test error")
            
            # Log with extra data
            logger.bind(user_id=123, action="test").info("User action")
            
            # Log with exception
            try:
                raise ValueError("Test exception")
            except Exception:
                logger.exception("Caught exception")
            
            # Wait for flush
            await asyncio.sleep(5)
            
            # Check stats
            stats = sink.get_stats()
            logger.info(f"Sink stats: {stats}")
            
            # Verify logs were written
            def count_logs_sync():
                return test_db.collection("log_events").count()
                
            count = await asyncio.to_thread(count_logs_sync)
            logger.info(f"Logs found in isolated DB for {execution_id}: {count}")
            
        finally:
            # Remove handler
            logger.remove(handler_id)
            
            # Stop sink
            await sink.stop()
            
            # Cleanup test database
            def delete_db_sync():
                client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
                sys_db = client.db(
                    "_system",
                    username=os.getenv("ARANGO_USERNAME", "root"),
                    password=os.getenv("ARANGO_PASSWORD", "openSesame")
                )
                sys_db.delete_database(test_db_name)
                
            await asyncio.to_thread(delete_db_sync)
            logger.info(f"Deleted test database: {test_db_name}")
    
    # Run the async test
    asyncio.run(run_test())


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    _test_sink_usage()

