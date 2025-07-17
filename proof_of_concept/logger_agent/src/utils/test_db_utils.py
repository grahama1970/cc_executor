#!/usr/bin/env python3
"""
test_db_utils.py - Utilities for creating and managing test databases

Provides functions to create transient test databases for perfect test isolation.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python test_db_utils.py          # Runs working_usage() - stable, known to work
  python test_db_utils.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import os
import uuid
from typing import Tuple, Dict, Any, Optional
from arango import ArangoClient
from loguru import logger
from dotenv import load_dotenv

# Import schema creation from arango_init
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from arango_init import _create_database_schema_sync


async def setup_test_database() -> Tuple[Any, str, Dict[str, Any]]:
    """
    Creates a new, uniquely named test database and initializes its schema.
    Returns the database object, its name, and the db_config for it.
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
            sys_db.delete_database(unique_db_name)  # Ensure clean slate
        sys_db.create_database(unique_db_name)
        
        test_db_instance = client.db(unique_db_name, username=arango_username, password=arango_password)
        _create_database_schema_sync(test_db_instance)  # Use the schema creation logic
        return test_db_instance, {
            "url": arango_url,
            "database": unique_db_name,
            "username": arango_username,
            "password": arango_password
        }

    try:
        db, db_config = await asyncio.to_thread(create_and_init_db_sync)
        logger.info(f"Created and initialized test database: {unique_db_name}")
        return db, unique_db_name, db_config
    except Exception as e:
        logger.error(f"Failed to set up test database {unique_db_name}: {e}")
        raise  # Critical failure


async def teardown_test_database(db_name: str) -> None:
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
            logger.warning(f"Test database {db_name} not found during cleanup")

    try:
        await asyncio.to_thread(delete_db_sync)
    except Exception as e:
        logger.error(f"Failed to delete test database {db_name}: {e}")
        # Don't raise - cleanup failures shouldn't prevent test completion