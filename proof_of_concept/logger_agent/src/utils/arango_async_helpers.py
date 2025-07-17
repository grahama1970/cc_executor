#!/usr/bin/env python3
"""
Async helper functions for python-arango to reduce boilerplate.

These helpers wrap common ArangoDB operations with asyncio.to_thread,
providing a cleaner API while we wait for python-arango-async to mature.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_async_helpers.py          # Runs working_usage() - stable, known to work
  python arango_async_helpers.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
from typing import Dict, List, Any, Optional
from arango.database import StandardDatabase
from arango.collection import StandardCollection


class AsyncCollection:
    """Async wrapper for ArangoDB collection operations."""
    
    def __init__(self, collection: StandardCollection):
        self._collection = collection
    
    async def insert(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a document asynchronously."""
        return await asyncio.to_thread(self._collection.insert, document)
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple documents asynchronously."""
        return await asyncio.to_thread(self._collection.insert_many, documents)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a document by key asynchronously."""
        return await asyncio.to_thread(self._collection.get, key)
    
    async def update(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Update a document asynchronously."""
        return await asyncio.to_thread(self._collection.update, document)
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """Delete a document asynchronously."""
        return await asyncio.to_thread(self._collection.delete, key)
    
    async def find(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Find documents matching filters asynchronously."""
        def _find():
            cursor = self._collection.find(filters, limit=limit)
            return list(cursor)
        return await asyncio.to_thread(_find)


class AsyncAQL:
    """Async wrapper for AQL query execution."""
    
    def __init__(self, db: StandardDatabase):
        self._db = db
    
    async def execute(
        self, 
        query: str, 
        bind_vars: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute an AQL query asynchronously."""
        def _execute():
            cursor = self._db.aql.execute(query, bind_vars=bind_vars, **kwargs)
            return list(cursor)
        return await asyncio.to_thread(_execute)


class AsyncDatabase:
    """Async wrapper for ArangoDB database operations."""
    
    def __init__(self, db: StandardDatabase):
        self._db = db
        self.aql = AsyncAQL(db)
    
    def collection(self, name: str) -> AsyncCollection:
        """Get an async collection wrapper."""
        return AsyncCollection(self._db.collection(name))
    
    async def has_collection(self, name: str) -> bool:
        """Check if collection exists asynchronously."""
        return await asyncio.to_thread(self._db.has_collection, name)
    
    async def create_collection(self, name: str, **kwargs) -> StandardCollection:
        """Create a collection asynchronously."""
        return await asyncio.to_thread(self._db.create_collection, name, **kwargs)


# Usage example
async def working_usage():
    """Demonstrate async helpers usage with test database."""
    from test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_async_helpers(test_db, test_db_name):
        print(f"Testing with database: {test_db_name}")
        
        # Wrap test DB in async helper
        db = AsyncDatabase(test_db)
        
        # Now use clean async syntax
        collection = db.collection('log_events')
        
        # Insert document
        doc = {
            "timestamp": "2025-01-14T20:00:00",
            "level": "INFO",
            "message": "Test async helper"
        }
        result = await collection.insert(doc)
        print(f"Inserted: {result['_key']}")
        
        # Query with AQL
        results = await db.aql.execute(
            "FOR doc IN log_events LIMIT 5 RETURN doc"
        )
        print(f"Found {len(results)} documents")
        
        return True
    
    # Execute the test
    return await test_async_helpers()


async def debug_function():
    """Test migration path comparison."""
    from test_utils import TestEnvironment
    
    print("Comparing boilerplate reduction with test database...")
    
    # Create test environment
    env = TestEnvironment()
    await env.setup()
    
    try:
        # Current approach
        print("\n1. Current asyncio.to_thread approach:")
        print("""
        result = await asyncio.to_thread(
            collection.insert,
            document
        )
        """)
        
        # With helpers
        print("\n2. With async helpers:")
        print("""
        async_collection = AsyncCollection(collection)
        result = await async_collection.insert(document)
        """)
        
        # Future python-arango-async
        print("\n3. Future python-arango-async (when stable):")
        print("""
        # Direct async/await syntax
        result = await collection.insert(document)
        """)
        
        print("\nRecommendation: Use helpers now, migrate to python-arango-async at v1.0+")
        print(f"\nTest database {env.db_name} used for comparison")
        
    finally:
        await env.teardown()
    
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
        success = asyncio.run(debug_function())
    else:
        success = asyncio.run(working_usage())
    
    sys.exit(0 if success else 1)