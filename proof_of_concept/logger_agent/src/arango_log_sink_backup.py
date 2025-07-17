#!/usr/bin/env python3
"""
arango_log_sink.py - Custom loguru sink for async ArangoDB writes

Implements non-blocking log ingestion with batching, buffering,
and automatic retry mechanisms.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_log_sink_backup.py          # Runs working_usage() - stable, known to work
  python arango_log_sink_backup.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
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
import sys
import uuid # For unique test database names

from arango import ArangoClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import psutil
from dotenv import load_dotenv

from utils.log_utils import log_safe_results
from arango_init import _create_database_schema_sync # Import the schema creation helper


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
        
        # Ensure buffer directory and a subdirectory for failed buffers exist
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        (self.buffer_dir / "_failed").mkdir(exist_ok=True) # Directory for problematic files
        
        # Log queue and batch
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.current_batch: deque = deque(maxlen=batch_size)
        
        # Database connection
        self.client: Optional[ArangoClient] = None
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
            # ArangoClient is synchronous, so instantiate directly
            self.client = ArangoClient(hosts=self.db_config["url"])
            
            # DB operations are synchronous, must use asyncio.to_thread
            def sync_connect():
                db_instance = self.client.db(
                    self.db_config["database"],
                    username=self.db_config["username"],
                    password=self.db_config["password"]
                )
                # Test connection by getting version (synchronous)
                db_instance.version()
                return db_instance
            
            self.db = await asyncio.to_thread(sync_connect)
            
            def get_collection():
                return self.db.collection("log_events")
            
            self.collection = await asyncio.to_thread(get_collection)
            
            # Debug logging
            logger.debug(f"Collection object: {self.collection}")
            logger.debug(f"Collection type: {type(self.collection)}")
            
            self.connected = True
            logger.info(f"Connected to ArangoDB database: {self.db_config['database']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB (database: {self.db_config.get('database', 'N/A')}): {e}")
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
                raise Exception("Database connection failed") # Raise to trigger tenacity retry
        
        if self.collection is None:
            logger.error(f"ArangoDB collection is not initialized. self.collection={self.collection}, type={type(self.collection)}")
            logger.error(f"self.connected={self.connected}, self.db={self.db}")
            self.connected = False # Mark as disconnected to retry connection
            raise Exception("ArangoDB collection not ready")

        try:
            safe_batch = log_safe_results(batch) # Use log_safe_results here
            
            # insert_many is synchronous
            def sync_insert_many():
                return self.collection.insert_many(safe_batch)

            result = await asyncio.to_thread(sync_insert_many)
            self.stats["successful_writes"] += len(batch)
            return True
            
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            self.stats["failed_writes"] += len(batch)
            self.stats["last_error"] = str(e)
            self.connected = False  # Mark as disconnected for next attempt
            raise # Re-raise to trigger tenacity retry
    
    async def buffer_to_disk(self, logs: List[Dict[str, Any]]) -> None:
        """Buffer logs to disk when database is unavailable."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        buffer_file = self.buffer_dir / f"buffer_{timestamp}.jsonl"
        
        try:
            async with aiofiles.open(buffer_file, 'w') as f:
                for log in logs:
                    await f.write(json.dumps(log) + '\n')
            
            self.stats["buffered_logs"] += len(logs)
            logger.warning(f"Buffered {len(logs)} logs to {buffer_file}")
            
            # Check buffer size and clean if needed
            await self.check_buffer_size()
        except Exception as e:
            logger.critical(f"Failed to write logs to disk buffer {buffer_file}: {e}")
            # At this point, logs are effectively lost if disk buffering fails.
            # This should ideally trigger an external alert.
    
    async def check_buffer_size(self) -> None:
        """Monitor buffer directory size and clean old files if needed."""
        if not self.buffer_dir.exists():
            return
            
        total_size = sum(f.stat().st_size for f in self.buffer_dir.glob("*.jsonl"))
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > self.max_buffer_size_mb:
            # Remove oldest files
            files = sorted(self.buffer_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
            
            while total_size_mb > self.max_buffer_size_mb * 0.8 and files:
                oldest = files.pop(0)
                try:
                    size = oldest.stat().st_size
                    oldest.unlink()
                    total_size_mb -= size / (1024 * 1024)
                    logger.warning(f"Removed old buffer file: {oldest.name} to stay within buffer limits.")
                except OSError as e:
                    logger.error(f"Failed to delete old buffer file {oldest.name}: {e}")
    
    async def process_buffered_logs(self) -> None:
        """Process buffered logs when connection is restored."""
        if not self.connected or not self.buffer_dir.exists():
            return
        
        buffer_files = sorted(self.buffer_dir.glob("*.jsonl"))
        failed_buffer_dir = self.buffer_dir / "_failed"
        failed_buffer_dir.mkdir(exist_ok=True) # Ensure it exists
        
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
                        try:
                            await self.write_batch_to_db(batch)
                        except Exception as inner_e:
                            logger.error(f"Persistent failure to write batch from buffered file {buffer_file.name}: {inner_e}. Re-buffering this part of the file.")
                            # If write_batch_to_db fails even after its retries, re-buffer the failed batch
                            # This needs careful consideration to avoid infinite loops if DB is truly broken
                            await self.buffer_to_disk(batch) 
                            # Move the original problematic file to _failed and stop processing this file
                            buffer_file.rename(failed_buffer_dir / buffer_file.name)
                            logger.warning(f"Moved problematic buffer file to {failed_buffer_dir.name}: {buffer_file.name}")
                            break # Stop processing current file, move to next
                    else: # This 'else' runs if the for loop completed without a 'break'
                        # If all batches from this file were successfully written, remove it
                        buffer_file.unlink()
                        logger.info(f"Processed and removed buffered file: {buffer_file.name}")
                else:
                    # If file is empty, remove it
                    buffer_file.unlink()
                    logger.info(f"Removed empty buffered file: {buffer_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to process or parse buffer file {buffer_file.name}: {e}")
                # Move problematic file to a 'failed' sub-directory for manual inspection
                try:
                    buffer_file.rename(failed_buffer_dir / buffer_file.name)
                    logger.warning(f"Moved problematic buffer file to {failed_buffer_dir.name}: {buffer_file.name}")
                except Exception as move_e:
                    logger.critical(f"Could not move problematic file {buffer_file.name} to _failed directory: {move_e}")
                # Continue to next file, don't break
                continue
    
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
            
        except Exception: # Catch any exception from write_batch_to_db, which already logs failures
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
        monitoring_interval = int(os.getenv("MONITORING_INTERVAL", "60"))
        
        while True:
            await asyncio.sleep(monitoring_interval)
            
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
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Final flush
        await self.flush_batch()
        
        # Close database connection (client.close() is synchronous)
        if self.client:
            await asyncio.to_thread(self.client.close)
            logger.info("ArangoDB client closed.")
    
    def write(self, message: Dict[str, Any]) -> None:
        """Synchronous write method for loguru compatibility."""
        # Parse loguru message
        record = message.record
        
        # Extract file name without path, and function from record
        script_name = Path(record["file"].name).stem
        function_name = record["function"]
        
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "execution_id": record["extra"].get("execution_id", "unknown"),
            "script_name": record["extra"].get("script_name", script_name),
            "function_name": function_name,
            "file_path": record["file"].path,
            "line_number": record["line"],
            "extra_data": record["extra"],
            "tags": record["extra"].get("tags", [])
        }
        
        # Add to queue (non-blocking)
        try:
            self.log_queue.put_nowait(log_data)
        except asyncio.QueueFull:
            # Queue is full, log to stderr as fallback
            # IMPORTANT: Using logger.bind(skip_sink=True) for fallback to avoid infinite loop
            logger.bind(skip_sink=True).error(
                f"Log queue full, dropping log: {log_data['message'][:100]}... "
                f"(Total buffered: {self.stats['buffered_logs']})"
            )


# Global sink instance (for main application usage, NOT for isolated tests)
_main_sink_instance: Optional[ArangoLogSink] = None

def get_main_arango_sink() -> ArangoLogSink:
    """
    Get or create the global ArangoDB sink instance for the MAIN configured database.
    This should be used by the application, not for isolated tests.
    """
    global _main_sink_instance
    
    if _main_sink_instance is None:
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"), # Use the main configured database
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        _main_sink_instance = ArangoLogSink(
            db_config=db_config,
            batch_size=int(os.getenv("LOG_BATCH_SIZE", "200")),
            flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "2")),
            buffer_dir=Path(os.getenv("LOG_BUFFER_DIR", "/tmp/logger_agent_buffer")),
            max_buffer_size_mb=int(os.getenv("LOG_MAX_BUFFER_SIZE_MB", "1000"))
        )
        
        asyncio.create_task(_main_sink_instance.start())
    
    return _main_sink_instance


# ============================================
# TEST DATABASE SETUP/TEARDOWN
# ============================================

async def setup_test_database():
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database config dictionary and its name.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)
    
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"

    def create_and_init_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(unique_db_name):
            sys_db.delete_database(unique_db_name) # Ensure clean slate if name clashes for some reason
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance) # Use the schema creation logic
        return {
            "url": arango_url,
            "database": unique_db_name,
            "username": arango_username,
            "password": arango_password
        }

    try:
        db_config = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db_config, unique_db_name
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise # Critical failure

async def teardown_test_database(db_name: str):
    """
    Deletes the specified test database.
    """
    load_dotenv()
    arango_url = os.getenv("ARANGO_URL", "http://localhost:8529")
    arango_username = os.getenv("ARANGO_USERNAME", "root")
    arango_password = os.getenv("ARANGO_PASSWORD", "openSesame")

    client = ArangoClient(hosts=arango_url)

    def delete_db_sync():
        sys_db = client.db("_system", username=arango_username, password=arango_password)
        if sys_db.has_database(db_name):
            sys_db.delete_database(db_name)
            logger.info(f"Deleted test database: {db_name}")
        else:
            logger.warning(f"Test database {db_name} not found for deletion.")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to tear down test database {db_name}: {e}")
        # Don't re-raise, allow main to complete, but log the error


# ============================================
# MAIN EXECUTION FOR TESTING SINK
# ============================================

async def _test_sink_usage(test_db_config: Dict[str, str]):
    """Internal helper to run sink tests with a given DB config."""
    logger.info(f"=== Testing ArangoDB Sink against isolated DB: {test_db_config['database']} ===")
    
    # Create a new sink instance specifically for this test database
    sink = ArangoLogSink(
        db_config=test_db_config,
        batch_size=int(os.getenv("LOG_BATCH_SIZE", "20")), # Smaller batch for faster testing
        flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "1")), # Faster flush
        buffer_dir=Path(f"/tmp/logger_agent_buffer_test_{test_db_config['database']}"),
        max_buffer_size_mb=100 # Smaller buffer limit for tests
    )
    # Start this specific sink instance
    await sink.start()

    # Configure logger with our sink (temporarily remove existing handlers if any from root logger)
    logger.remove() 
    logger.add(sys.stderr, level="INFO") # Keep console output for test results
    logger.add(sink.write, enqueue=True, level="DEBUG") # Add the test sink

    # Generate test logs
    execution_id = f"test_run_sink_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    logger.bind(execution_id=execution_id, tags=["test", "sink"]).info("Test log 1")
    logger.bind(execution_id=execution_id, tags=["test"]).warning("Test warning")
    logger.bind(execution_id=execution_id).error("Test error")
    
    # Wait for logs to be written
    await asyncio.sleep(sink.flush_interval * 2 + 1) # Ensure logs are flushed and processed

    # Verify logs in DB by connecting directly to the test DB
    client_test = ArangoClient(hosts=test_db_config['url'])
    db_test = client_test.db(
        test_db_config['database'],
        username=test_db_config['username'],
        password=test_db_config['password']
    )
    
    def count_logs_sync():
        try:
            aql = "FOR doc IN log_events FILTER doc.execution_id == @exec_id RETURN doc"
            cursor = db_test.aql.execute(aql, bind_vars={"exec_id": execution_id})
            return len(list(cursor))
        except Exception as e:
            logger.error(f"Failed to query logs for verification: {e}")
            return 0
    
    logged_count = await asyncio.to_thread(count_logs_sync)

    # Check stats
    logger.info(f"Sink stats: {sink.stats}")
    logger.info(f"Logs found in isolated DB for {execution_id}: {logged_count}")
    
    # Basic assertions
    assert sink.stats["total_logs"] >= 3, "Expected at least 3 logs to be processed."
    assert sink.stats["successful_writes"] >= 3, "Expected at least 3 successful writes."
    assert logged_count >= 3, "Expected at least 3 logs to be found in the isolated database."

    # Cleanup this specific sink instance
    await sink.stop()
    return True


async def _test_sink_debug_usage(test_db_config: Dict[str, str]):
    """Internal helper to run sink debug tests with a given DB config."""
    logger.info(f"=== Debug Mode: Testing Sink Edge Cases against isolated DB: {test_db_config['database']} ===")
    
    sink = ArangoLogSink(
        db_config=test_db_config,
        batch_size=int(os.getenv("LOG_BATCH_SIZE", "5")), # Very small batch for debug
        flush_interval=float(os.getenv("LOG_FLUSH_INTERVAL", "0.5")), # Very fast flush
        buffer_dir=Path(f"/tmp/logger_agent_buffer_debug_{test_db_config['database']}"),
        max_buffer_size_mb=10 # Smaller buffer limit for tests
    )
    await sink.start()

    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(sink.write, enqueue=True, level="DEBUG")

    # Test 1: High volume logging
    logger.info("Test 1: High volume")
    initial_total_logs = sink.stats["total_logs"]
    for i in range(100): # Reduced count for faster debug
        logger.bind(test_id=f"volume_{i}").debug(f"High volume test {i}")
    
    await asyncio.sleep(sink.flush_interval * 3 + 1)
    logger.info(f"After high volume: {sink.stats}")
    assert sink.stats["total_logs"] >= initial_total_logs + 100, "Expected all high volume logs to be queued."
    
    # Test 2: Large messages
    logger.info("Test 2: Large messages")
    initial_total_logs = sink.stats["total_logs"]
    large_data = {"data": "x" * 1000, "array": list(range(100))} # Reduced size for faster debug
    logger.bind(extra_data=large_data).info("Large message test")
    
    await asyncio.sleep(sink.flush_interval + 1)
    logger.info(f"After large message: {sink.stats}")
    assert sink.stats["total_logs"] >= initial_total_logs + 1, "Expected large message to be queued."

    # Test 3: Connection failure simulation (logs will buffer to disk)
    logger.info("Test 3: Simulating connection failure (logs will buffer to disk)")
    
    sink.connected = False
    sink.db = None # Invalidate current DB object
    
    initial_buffered_logs = sink.stats["buffered_logs"]
    for i in range(5): # Reduced count for faster debug
        logger.bind(test="failover").error(f"Failover test {i}")
    
    await asyncio.sleep(sink.flush_interval * 2 + 1)
    logger.info(f"After failover (buffered logs might not show up immediately in DB): {sink.stats}")
    assert sink.stats["buffered_logs"] >= initial_buffered_logs + 5, "Expected logs to be buffered to disk."
    
    logger.info("Re-enabling connection to process buffered logs...")
    await sink.connect()
    await asyncio.sleep(sink.flush_interval * 3 + 1)
    
    logger.info(f"After reconnect and processing: {sink.stats}")

    buffer_files = list(sink.buffer_dir.glob("*.jsonl"))
    failed_buffer_files = list((sink.buffer_dir / "_failed").glob("*.jsonl"))
    logger.info(f"Remaining buffer files: {len(buffer_files)}")
    logger.info(f"Failed buffer files (quarantined): {len(failed_buffer_files)}")
    
    assert len(buffer_files) == 0, "Expected all non-problematic buffer files to be processed and removed."
    
    await sink.stop()
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    load_dotenv()
    
    # Ensure a basic console logger is always present for script output
    logger.remove() 
    logger.add(sys.stderr, level="INFO")

    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db_config = None
        test_db_name = None
        success = False
        try:
            test_db_config, test_db_name = await setup_test_database()
            
            if mode == "debug":
                success = await _test_sink_debug_usage(test_db_config)
            else:
                success = await _test_sink_usage(test_db_config)
            
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            # Cleanup is handled inside the test functions
            pass
            
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    asyncio.run(main())
    exit(0 if success else 1)