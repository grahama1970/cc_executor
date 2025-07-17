#!/usr/bin/env python3
"""
Shared test utilities for logger_agent.

Provides consistent test database setup and teardown for all test functions.
This ensures no production data is polluted during testing.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python test_utils.py          # Runs working_usage() - stable, known to work
  python test_utils.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import functools
from typing import Callable, Any
from loguru import logger
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.comprehensive_test_db import (
    create_comprehensive_test_db,
    cleanup_test_db,
    truncate_test_collections,
    TestDatabase
)
from agent_log_manager import AgentLogManager


def with_test_db(func: Callable) -> Callable:
    """
    Decorator that provides a test database to async functions.
    
    The decorated function will receive:
    - test_db: StandardDatabase instance
    - test_db_name: Name of the test database
    - manager: AgentLogManager instance configured with test DB
    
    Example:
        @with_test_db
        async def my_test_function(test_db, test_db_name, manager):
            # Use test_db and manager here
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        test_db = None
        test_db_name = None
        manager = None
        
        try:
            # Create test database
            test_db, test_db_name, test_db_config = await create_comprehensive_test_db()
            logger.info(f"Test database created: {test_db_name}")
            
            # Create AgentLogManager with test database
            manager = AgentLogManager()
            await manager.initialize({
                "url": test_db_config["url"],
                "database": test_db_name,
                "username": test_db_config["username"],
                "password": test_db_config["password"]
            })
            
            # Set the manager's db to test_db for direct access
            manager.db = test_db
            
            # Call the wrapped function
            result = await func(test_db, test_db_name, manager, *args, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Test function failed: {e}")
            raise
            
        finally:
            # Always cleanup
            if test_db_name:
                await cleanup_test_db(test_db_name)
                logger.info(f"Test database cleaned up: {test_db_name}")
    
    return wrapper


def with_test_db_no_manager(func: Callable) -> Callable:
    """
    Decorator that provides only test database (no AgentLogManager).
    
    The decorated function will receive:
    - test_db: StandardDatabase instance
    - test_db_name: Name of the test database
    
    Example:
        @with_test_db_no_manager
        async def my_test_function(test_db, test_db_name):
            # Use test_db here
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        test_db = None
        test_db_name = None
        
        try:
            # Create test database
            test_db, test_db_name, test_db_config = await create_comprehensive_test_db()
            logger.info(f"Test database created: {test_db_name}")
            
            # Call the wrapped function
            result = await func(test_db, test_db_name, *args, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Test function failed: {e}")
            raise
            
        finally:
            # Always cleanup
            if test_db_name:
                await cleanup_test_db(test_db_name)
                logger.info(f"Test database cleaned up: {test_db_name}")
    
    return wrapper


class TestEnvironment:
    """
    Shared test environment for scripts that need persistent state across tests.
    
    Usage:
        env = TestEnvironment()
        await env.setup()
        try:
            # Use env.db, env.manager, etc.
        finally:
            await env.teardown()
    """
    
    def __init__(self):
        self.db = None
        self.db_name = None
        self.db_config = None
        self.manager = None
        self._setup_complete = False
    
    async def setup(self):
        """Initialize test environment."""
        if self._setup_complete:
            return
            
        # Create test database
        self.db, self.db_name, self.db_config = await create_comprehensive_test_db()
        logger.info(f"Test environment database: {self.db_name}")
        
        # Create AgentLogManager
        self.manager = AgentLogManager()
        await self.manager.initialize(self.db_config)
        self.manager.db = self.db
        
        self._setup_complete = True
    
    async def teardown(self):
        """Clean up test environment."""
        if self.db_name:
            await cleanup_test_db(self.db_name)
            logger.info(f"Test environment cleaned up: {self.db_name}")
        
        self.db = None
        self.db_name = None
        self.db_config = None
        self.manager = None
        self._setup_complete = False
    
    async def truncate_all(self):
        """Truncate all collections without destroying database."""
        if self.db:
            await truncate_test_collections(self.db)
            logger.info("Truncated all test collections")
    
    def __repr__(self):
        return f"<TestEnvironment db={self.db_name} setup={self._setup_complete}>"


# Convenience functions for common test patterns

async def run_with_test_db(test_function: Callable, *args, **kwargs):
    """
    Run a function with a test database and cleanup afterwards.
    
    The function should accept (test_db, test_db_name, manager) as first parameters.
    """
    async with TestDatabase() as (test_db, test_db_name):
        manager = AgentLogManager()
        await manager.initialize({
            "url": "http://localhost:8529",
            "database": test_db_name,
            "username": "root",
            "password": "openSesame"
        })
        manager.db = test_db
        
        return await test_function(test_db, test_db_name, manager, *args, **kwargs)


# Test data generators

def generate_test_logs(count: int = 10) -> list:
    """Generate test log entries."""
    import random
    from datetime import datetime, timedelta
    
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    tools = ["Bash", "Read", "Write", "Edit", "Search"]
    
    logs = []
    base_time = datetime.utcnow() - timedelta(hours=1)
    
    for i in range(count):
        logs.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "level": random.choice(levels),
            "message": f"Test log message {i}",
            "execution_id": f"test_exec_{i // 3}",  # Group some logs
            "script_name": "test_script",
            "function_name": f"test_function_{i % 3}",
            "extra_data": {
                "tool": random.choice(tools),
                "index": i
            }
        })
    
    return logs


def generate_test_sessions(count: int = 5) -> list:
    """Generate test agent sessions."""
    sessions = []
    
    for i in range(count):
        sessions.append({
            "session_id": f"test_session_{i}",
            "agent_name": f"test_agent_{i % 2}",
            "start_time": datetime.utcnow().isoformat(),
            "status": "active" if i == count - 1 else "completed",
            "metadata": {
                "test": True,
                "index": i
            }
        })
    
    return sessions


# Example usage patterns

async def working_usage():
    """Demonstrate test utilities."""
    logger.info("=== Testing Shared Test Utilities ===")
    
    # Method 1: Using decorator
    @with_test_db
    async def test_with_decorator(test_db, test_db_name, manager):
        logger.info(f"Decorator provided DB: {test_db_name}")
        
        # Use manager
        async with manager.script_execution("test_script") as log:
            log.info("Test message")
        
        # Query logs
        results = await manager.search_logs("test", limit=10)
        logger.info(f"Found {len(results)} logs")
        
        return True
    
    # Method 2: Using context manager
    logger.info("\nMethod 2: Context Manager")
    async with TestDatabase() as (test_db, test_db_name):
        logger.info(f"Context manager provided DB: {test_db_name}")
        
        # Insert test data
        log_events = test_db.collection("log_events")
        test_logs = generate_test_logs(5)
        log_events.insert_many(test_logs)
        logger.info(f"Inserted {len(test_logs)} test logs")
    
    # Method 3: Using TestEnvironment
    logger.info("\nMethod 3: TestEnvironment")
    env = TestEnvironment()
    await env.setup()
    
    try:
        logger.info(f"Environment DB: {env.db_name}")
        
        # Use environment
        sessions = env.db.collection("agent_sessions")
        test_sessions = generate_test_sessions(3)
        sessions.insert_many(test_sessions)
        
        # Truncate and verify
        await env.truncate_all()
        count = sessions.count()
        logger.info(f"After truncate: {count} sessions")
        
    finally:
        await env.teardown()
    
    # Run decorated function
    logger.info("\nRunning decorated test function")
    result = await test_with_decorator()
    logger.info(f"Decorator test result: {result}")
    
    return True


async def debug_function():
    """Test error handling and cleanup."""
    logger.info("=== Testing Error Handling ===")
    
    # Test cleanup on error
    @with_test_db
    async def failing_test(test_db, test_db_name, manager):
        logger.info(f"About to fail with DB: {test_db_name}")
        raise ValueError("Intentional test error")
    
    try:
        await failing_test()
    except ValueError as e:
        logger.info(f"Caught expected error: {e}")
        logger.info("Database should still be cleaned up")
    
    # Verify no test databases remain
    from arango import ArangoClient
    client = ArangoClient(hosts='http://localhost:8529')
    sys_db = client.db('_system', username='root', password='openSesame')
    
    test_dbs = [db for db in sys_db.databases() if db.startswith('test_logger_')]
    logger.info(f"Remaining test databases: {len(test_dbs)}")
    
    if test_dbs:
        logger.warning(f"Found orphaned test databases: {test_dbs}")
        if input("Clean up orphaned databases? (y/n): ").lower() == 'y':
            for db_name in test_dbs:
                sys_db.delete_database(db_name)
                logger.info(f"Cleaned up: {db_name}")
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())