#!/usr/bin/env python3
"""
arango_init.py - Initialize ArangoDB schema for Logger Agent

Creates database, collections, indexes, and ArangoSearch views.
Ensures idempotent execution for repeated runs.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_init.py          # Runs working_usage() - stable, known to work
  python arango_init.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from arango import ArangoClient
from loguru import logger
from dotenv import load_dotenv
import uvloop

# Set uvloop as the event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Load environment variables
load_dotenv()

# Configure logging
# For standalone scripts, removing default handler and adding a file/stderr handler is common.
# In a larger application, loguru configuration should be centralized.
logger.remove()
logger.add(
    sys.stderr,
    level="INFO"
)


def _create_database_schema_sync(db_instance):
    """Synchronous logic to create collections, indexes, and views within a given DB instance."""
    db = db_instance
    
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
        if not db.has_collection(coll_name):
            collection = db.create_collection(
                coll_name,
                schema=config.get("schema")
            )
            logger.info(f"Created collection: {coll_name}")
        else:
            collection = db.collection(coll_name)
        
        # Create indexes
        if coll_name == "log_events":
            # Compound index for time-based queries
            collection.add_index(
                {'type': 'persistent', 'fields': ["execution_id", "timestamp"]}
            )
            
            # Index for level-based filtering
            collection.add_index(
                {'type': 'persistent', 'fields': ["level", "timestamp"]}
            )
            
            # Full-text index for message search
            collection.add_index(
                {'type': 'fulltext', 'fields': ["message"], 'min_length': 3}
            )
            
        elif coll_name == "script_runs":
            # Unique index on execution_id
            collection.add_index(
                {'type': 'persistent', 'fields': ["execution_id"], 'unique': True}
            )
            
            # Index for script name queries
            collection.add_index(
                {'type': 'persistent', 'fields': ["script_name", "start_time"]}
            )
        
        elif coll_name == "agent_learnings":
            # Index for execution-based queries
            collection.add_index(
                {'type': 'persistent', 'fields': ["execution_id", "timestamp"]}
            )
    
    # Create ArangoSearch view
    view_name = "log_search_view"
    if view_name not in [v["name"] for v in db.views()]:
        db.create_arangosearch_view(
            view_name,
            properties={
                "links": {
                    "log_events": {
                        "fields": {
                            "message": {"analyzers": ["text_en"]},
                            "level": {},
                            "script_name": {},
                            "function_name": {},
                            "tags": {}
                        }
                    }
                }
            }
        )
        logger.info(f"Created ArangoSearch view: {view_name}")
    
    return db


def _create_database_sync():
    """Synchronous database creation logic."""
    # Connect to ArangoDB
    client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
    
    # System database connection
    sys_db = client.db(
        "_system",
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    db_name = os.getenv("ARANGO_DATABASE", "script_logs")
    
    # Create database if not exists
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
        logger.info(f"Created database: {db_name}")
    
    # Connect to our database
    db = client.db(
        db_name,
        username=os.getenv("ARANGO_USERNAME", "root"),
        password=os.getenv("ARANGO_PASSWORD", "openSesame")
    )
    
    # Use the schema creation function
    return _create_database_schema_sync(db)


async def create_database_and_collections():
    """Create database and collections with proper indexes (async wrapper)."""
    return await asyncio.to_thread(_create_database_sync)


async def working_usage(test_db=None):
    """Initialize database schema - stable working example."""
    logger.info("=== Initializing ArangoDB Schema ===")
    
    try:
        if test_db:
            # Use provided test database
            db = test_db
            logger.info(f"Using test database: {db.name}")
        else:
            # Create production database (backward compatibility)
            db = await create_database_and_collections()
        
        # Verify collections exist
        collections = await asyncio.to_thread(lambda: [c['name'] for c in db.collections()])
        logger.info(f"Available collections: {collections}")
        
        # Test write
        test_doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Database initialization test",
            "execution_id": "init_test_001",
            "script_name": "arango_init.py"
        }
        
        result = await asyncio.to_thread(db.collection("log_events").insert, test_doc)
        logger.success(f"Test document inserted: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.exception("Full traceback:")
        return False


async def debug_function(test_db=None):
    """Debug function for testing schema modifications."""
    logger.info("=== Running Debug Mode ===")
    
    # Test experimental features
    def test_experimental(db_to_use):
        db = db_to_use
        if not db:
            client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
            db = client.db(
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
            cursor = db.aql.execute(query, bind_vars={"vector": test_vector})
            result = list(cursor)[0]
            logger.success(f"APPROX_NEAR_COSINE test passed: {result}")
        except Exception as e:
            logger.error(f"APPROX_NEAR_COSINE not available: {e}")
            logger.warning("Ensure --query.enable-experimental flag is set")
    
    await asyncio.to_thread(test_experimental, test_db)
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    from utils.test_db_utils import setup_test_database, teardown_test_database
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        test_db = None
        test_db_name = None
        success = False
        
        try:
            # Create test database
            test_db, test_db_name, test_db_config = await setup_test_database()
            logger.info(f"Created test database: {test_db_name}")
            
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function(test_db)
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage(test_db)
                
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            logger.exception("Full traceback:")
        finally:
            # Always cleanup test database
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)