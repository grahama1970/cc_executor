#!/usr/bin/env python3
"""
Comprehensive test database setup for logger_agent.

This module provides complete test database initialization including:
- All required collections
- Graph structures  
- BM25 search views
- Indexes
- Proper cleanup

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python comprehensive_test_db.py          # Runs working_usage() - stable, known to work
  python comprehensive_test_db.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
from typing import Tuple, Dict, Any, Optional
from arango import ArangoClient
from arango.database import StandardDatabase
import uuid
from loguru import logger


async def create_comprehensive_test_db() -> Tuple[StandardDatabase, str, Dict[str, str]]:
    """
    Create a complete test database with all required structures.
    
    Returns:
        - test_db: The test database instance
        - test_db_name: Name of the test database
        - test_db_config: Connection configuration
    """
    
    def _create_sync():
        # Generate unique test database name
        test_db_name = f"test_logger_{uuid.uuid4().hex[:8]}"
        
        # Connect to system database
        client = ArangoClient(hosts='http://localhost:8529')
        sys_db = client.db('_system', username='root', password='openSesame')
        
        # Create test database
        sys_db.create_database(test_db_name)
        logger.info(f"Created test database: {test_db_name}")
        
        # Connect to test database
        test_db = client.db(test_db_name, username='root', password='openSesame')
        
        # Create collections
        collections = {
            # Core collections
            'log_events': {'type': 'collection'},
            'script_runs': {'type': 'collection'},
            'agent_learnings': {'type': 'collection'},
            
            # Graph vertex collections
            'agent_sessions': {'type': 'collection'},
            'tool_executions': {'type': 'collection'},
            'code_artifacts': {'type': 'collection'},
            'agent_insights': {'type': 'collection'},
            'errors_and_failures': {'type': 'collection'},
            
            # Graph edge collections
            'agent_flow': {'type': 'edge'},
            'tool_dependencies': {'type': 'edge'},
            'error_causality': {'type': 'edge'},
            'artifact_lineage': {'type': 'edge'},
            'insight_applications': {'type': 'edge'},
            
            # Dashboard collections
            'raw_responses': {'type': 'collection'},
            'agent_messages': {'type': 'collection'}
        }
        
        for name, config in collections.items():
            if config['type'] == 'edge':
                test_db.create_collection(name, edge=True)
            else:
                test_db.create_collection(name)
            logger.debug(f"Created collection: {name}")
        
        # Create graph
        edge_definitions = [
            {
                "edge_collection": "agent_flow",
                "from_vertex_collections": ["tool_executions", "agent_sessions"],
                "to_vertex_collections": ["tool_executions", "errors_and_failures", "code_artifacts"]
            },
            {
                "edge_collection": "tool_dependencies",
                "from_vertex_collections": ["tool_executions"],
                "to_vertex_collections": ["tool_executions", "code_artifacts"]
            },
            {
                "edge_collection": "error_causality",
                "from_vertex_collections": ["errors_and_failures", "tool_executions"],
                "to_vertex_collections": ["tool_executions", "agent_insights", "code_artifacts"]
            },
            {
                "edge_collection": "artifact_lineage",
                "from_vertex_collections": ["code_artifacts"],
                "to_vertex_collections": ["code_artifacts"]
            },
            {
                "edge_collection": "insight_applications",
                "from_vertex_collections": ["agent_insights"],
                "to_vertex_collections": ["tool_executions", "code_artifacts"]
            }
        ]
        
        test_db.create_graph(
            "claude_agent_observatory",
            edge_definitions=edge_definitions
        )
        logger.debug("Created graph: claude_agent_observatory")
        
        # Create BM25 search view for log_events
        test_db.create_arangosearch_view(
            name='log_events_view',
            properties={
                'links': {
                    'log_events': {
                        'analyzers': ['text_en'],
                        'fields': {
                            'message': {'analyzers': ['text_en']},
                            'extra_data': {
                                'fields': {
                                    'payload': {'analyzers': ['text_en']},
                                    'summary': {'analyzers': ['text_en']}
                                }
                            }
                        },
                        'includeAllFields': False,
                        'storeValues': 'id',
                        'trackListPositions': False
                    }
                }
            }
        )
        logger.debug("Created BM25 search view: log_events_view")
        
        # Create indexes
        # log_events indexes
        log_events = test_db.collection('log_events')
        log_events.add_index({'type': 'persistent', 'fields': ['timestamp']})
        log_events.add_index({'type': 'persistent', 'fields': ['execution_id', 'timestamp']})
        log_events.add_index({'type': 'persistent', 'fields': ['level']})
        
        # script_runs indexes
        script_runs = test_db.collection('script_runs')
        script_runs.add_index({'type': 'persistent', 'fields': ['execution_id'], 'unique': True})
        script_runs.add_index({'type': 'persistent', 'fields': ['script_name', 'start_time']})
        
        # Graph collection indexes
        agent_sessions = test_db.collection('agent_sessions')
        agent_sessions.add_index({'type': 'persistent', 'fields': ['session_id'], 'unique': True})
        
        tool_executions = test_db.collection('tool_executions')
        tool_executions.add_index({'type': 'persistent', 'fields': ['session_id', 'tool_name']})
        tool_executions.add_index({'type': 'persistent', 'fields': ['start_time']})
        
        errors_and_failures = test_db.collection('errors_and_failures')
        errors_and_failures.add_index({'type': 'persistent', 'fields': ['error_type', 'timestamp']})
        
        logger.debug("Created all indexes")
        
        # Configuration
        config = {
            'url': 'http://localhost:8529',
            'database': test_db_name,
            'username': 'root',
            'password': 'openSesame'
        }
        
        return test_db, test_db_name, config
    
    # Run synchronously in thread
    return await asyncio.to_thread(_create_sync)


async def cleanup_test_db(test_db_name: str) -> None:
    """
    Clean up test database.
    
    Args:
        test_db_name: Name of test database to remove
    """
    def _cleanup_sync():
        try:
            client = ArangoClient(hosts='http://localhost:8529')
            sys_db = client.db('_system', username='root', password='openSesame')
            
            if test_db_name in sys_db.databases():
                sys_db.delete_database(test_db_name)
                logger.info(f"Deleted test database: {test_db_name}")
            else:
                logger.warning(f"Test database not found: {test_db_name}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup test database: {e}")
    
    await asyncio.to_thread(_cleanup_sync)


async def truncate_test_collections(test_db: StandardDatabase) -> None:
    """
    Truncate all collections in test database instead of deleting.
    
    Args:
        test_db: Test database instance
    """
    def _truncate_sync():
        collections = [
            'log_events', 'script_runs', 'agent_learnings',
            'agent_sessions', 'tool_executions', 'code_artifacts',
            'agent_insights', 'errors_and_failures',
            'agent_flow', 'tool_dependencies', 'error_causality',
            'artifact_lineage', 'insight_applications',
            'raw_responses', 'agent_messages'
        ]
        
        for coll_name in collections:
            if test_db.has_collection(coll_name):
                collection = test_db.collection(coll_name)
                collection.truncate()
                logger.debug(f"Truncated collection: {coll_name}")
    
    await asyncio.to_thread(_truncate_sync)


# Context manager for test database
class TestDatabase:
    """Context manager for test database lifecycle."""
    
    def __init__(self, cleanup: bool = True):
        self.cleanup = cleanup
        self.db = None
        self.db_name = None
        self.config = None
    
    async def __aenter__(self) -> Tuple[StandardDatabase, str]:
        self.db, self.db_name, self.config = await create_comprehensive_test_db()
        return self.db, self.db_name
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup and self.db_name:
            await cleanup_test_db(self.db_name)


async def working_usage():
    """Demonstrate comprehensive test database setup."""
    logger.info("=== Testing Comprehensive Test Database ===")
    
    # Use context manager
    async with TestDatabase() as (test_db, test_db_name):
        logger.info(f"Working with test database: {test_db_name}")
        
        # Verify collections exist
        collections = test_db.collections()
        logger.info(f"Created {len(collections)} collections")
        
        # Test BM25 search
        log_events = test_db.collection('log_events')
        
        # Insert test documents
        test_docs = [
            {
                "timestamp": "2025-01-14T20:00:00",
                "level": "INFO",
                "message": "Testing BM25 search functionality",
                "execution_id": "test_123",
                "extra_data": {
                    "payload": {"tool": "Bash"},
                    "summary": "Running bash command"
                }
            },
            {
                "timestamp": "2025-01-14T20:01:00",
                "level": "ERROR",
                "message": "Error in bash execution",
                "execution_id": "test_123",
                "extra_data": {
                    "payload": {"error": "Command failed"},
                    "summary": "Bash command failed with exit code 1"
                }
            }
        ]
        
        log_events.insert_many(test_docs)
        logger.info("Inserted test documents")
        
        # Test BM25 search
        aql = """
        FOR doc IN log_events_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        SORT BM25(doc) DESC
        RETURN doc
        """
        
        cursor = test_db.aql.execute(aql, bind_vars={"query": "bash"})
        results = list(cursor)
        logger.info(f"BM25 search found {len(results)} results")
        
        # Test graph
        graph = test_db.graph('claude_agent_observatory')
        logger.info(f"Graph has {len(graph.edge_definitions())} edge definitions")
        
        # Truncate collections
        await truncate_test_collections(test_db)
        logger.info("Truncated all collections")
        
        # Verify truncation
        count = log_events.count()
        logger.info(f"After truncation, log_events has {count} documents")
    
    logger.info("Test database cleaned up automatically")
    return True


async def debug_function():
    """Test manual cleanup and persistence."""
    logger.info("=== Testing Manual Cleanup ===")
    
    # Create without auto-cleanup
    test_db, test_db_name, config = await create_comprehensive_test_db()
    
    try:
        logger.info(f"Created persistent test database: {test_db_name}")
        
        # Do some work
        sessions = test_db.collection('agent_sessions')
        sessions.insert({
            "session_id": "debug_123",
            "agent_name": "debug_agent",
            "status": "active"
        })
        
        logger.info("Inserted test data")
        logger.info(f"Database will persist at: {config['url']}/{test_db_name}")
        logger.info("Remember to clean up manually!")
        
        # Optionally truncate instead of delete
        if input("Truncate collections? (y/n): ").lower() == 'y':
            await truncate_test_collections(test_db)
            logger.info("Collections truncated")
        
        if input("Delete database? (y/n): ").lower() == 'y':
            await cleanup_test_db(test_db_name)
        else:
            logger.info(f"Database {test_db_name} preserved for inspection")
            
    except Exception as e:
        logger.error(f"Error in debug mode: {e}")
        await cleanup_test_db(test_db_name)
    
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