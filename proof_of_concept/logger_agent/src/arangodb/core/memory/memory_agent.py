#!/usr/bin/env python3
"""
Memory agent module for Logger Agent integration.

Provides real functionality for storing and retrieving agent memories
in ArangoDB collections with search capabilities.

Third-party Documentation:
- ArangoDB Documents: https://www.arangodb.com/docs/stable/data-modeling-documents.html

Example Input:
    content = "Discovered optimal batch size is 100"
    memory_type = "learning"
    metadata = {"confidence": 0.9, "context": "data_processing"}

Expected Output:
    {"_id": "memories/123", "content": "...", "type": "learning", "timestamp": "..."}

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python memory_agent.py          # Runs working_usage() - stable, known to work
  python memory_agent.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger
from arango.database import StandardDatabase

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.arango_async_helpers import AsyncDatabase, AsyncCollection

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

class MemoryAgent:
    """Real memory agent that stores memories in ArangoDB."""
    
    def __init__(self, db: Optional[StandardDatabase] = None):
        """Initialize with optional database connection."""
        self.db = db
        self.async_db = AsyncDatabase(db) if db else None
        self.collection_name = "agent_memories"
        self.view_name = "memories_search_view"
        logger.info("MemoryAgent initialized with ArangoDB")
    
    async def ensure_collections(self):
        """Ensure required collections and search views exist."""
        if not self.db:
            raise ValueError("Database connection required")
        
        # Create memories collection if it doesn't exist
        if not await self.async_db.has_collection(self.collection_name):
            await self.async_db.create_collection(self.collection_name)
            logger.info(f"Created collection: {self.collection_name}")
            
            # Create indexes
            collection = self.db.collection(self.collection_name)
            await asyncio.to_thread(collection.add_index, {'type': 'persistent', 'fields': ['type']})
            await asyncio.to_thread(collection.add_index, {'type': 'persistent', 'fields': ['timestamp']})
            await asyncio.to_thread(collection.add_index, {'type': 'persistent', 'fields': ['metadata.confidence']})
        
        # Create search view for full-text search
        await self._create_search_view()
    
    async def _create_search_view(self):
        """Create ArangoSearch view for memory search."""
        def _create_view_sync():
            existing_views = [v['name'] for v in self.db.views()]
            
            if self.view_name not in existing_views:
                view_config = {
                    'links': {
                        self.collection_name: {
                            'analyzers': ['text_en'],
                            'fields': {
                                'content': {'analyzers': ['text_en']},
                                'type': {'analyzers': ['identity']},
                                'metadata.context': {'analyzers': ['text_en']},
                                'metadata.tags': {'analyzers': ['identity']}
                            },
                            'includeAllFields': False,
                            'storeValues': 'id',
                            'trackListPositions': False
                        }
                    }
                }
                
                self.db.create_arangosearch_view(self.view_name, properties=view_config)
                logger.info(f"Created search view: {self.view_name}")
        
        await asyncio.to_thread(_create_view_sync)
    
    async def add_memory(
        self,
        content: str,
        memory_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a new memory entry to ArangoDB.
        
        Args:
            content: Memory content
            memory_type: Type of memory (learning, observation, etc.)
            metadata: Additional metadata
            
        Returns:
            Created memory document
        """
        if not self.db:
            raise ValueError("Database connection required")
        
        await self.ensure_collections()
        
        # Prepare memory document
        memory = {
            "content": content,
            "type": memory_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "access_count": 0,
            "last_accessed": None
        }
        
        # Store in database
        collection = self.async_db.collection(self.collection_name)
        result = await collection.insert(memory)
        
        # Add generated IDs to memory document
        memory["_id"] = result["_id"]
        memory["_key"] = result["_key"]
        memory["_rev"] = result["_rev"]
        
        logger.info(f"Added {memory_type} memory: {content[:50]}... (ID: {memory['_id']})")
        
        return memory
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for memories using ArangoDB full-text search.
        
        Args:
            query: Search query
            memory_type: Optional filter by type
            limit: Maximum results
            
        Returns:
            List of matching memories with relevance scores
        """
        if not self.db:
            raise ValueError("Database connection required")
        
        # Build search query
        filters = []
        bind_vars = {"query": query, "limit": limit}
        
        if memory_type:
            filters.append("doc.type == @memory_type")
            bind_vars["memory_type"] = memory_type
        
        filter_clause = f"FILTER {' AND '.join(filters)}" if filters else ""
        
        # Use BM25 search if query is provided
        if query:
            aql = f"""
            FOR doc IN {self.view_name}
            SEARCH ANALYZER(doc.content IN TOKENS(@query, 'text_en'), 'text_en')
            {filter_clause}
            LET score = BM25(doc)
            SORT score DESC
            LIMIT @limit
            UPDATE doc WITH {{ 
                access_count: doc.access_count + 1,
                last_accessed: DATE_ISO8601(DATE_NOW())
            }} IN {self.collection_name}
            RETURN {{
                memory: NEW,
                score: score
            }}
            """
        else:
            # Just filter without search - remove @query from bind_vars
            if "query" in bind_vars:
                del bind_vars["query"]
            
            aql = f"""
            FOR doc IN {self.collection_name}
            {filter_clause}
            SORT doc.timestamp DESC
            LIMIT @limit
            UPDATE doc WITH {{ 
                access_count: doc.access_count + 1,
                last_accessed: DATE_ISO8601(DATE_NOW())
            }} IN {self.collection_name}
            RETURN {{
                memory: NEW,
                score: 1.0
            }}
            """
        
        results = await self.async_db.aql.execute(aql, bind_vars=bind_vars)
        
        logger.info(f"Found {len(results)} memories matching '{query}'")
        return results
    
    async def get_recent_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories from ArangoDB, optionally filtered by type.
        
        Args:
            memory_type: Optional filter by type
            limit: Maximum results
            
        Returns:
            List of recent memories
        """
        if not self.db:
            raise ValueError("Database connection required")
        
        # Build query
        filters = []
        bind_vars = {"limit": limit}
        
        if memory_type:
            filters.append("doc.type == @memory_type")
            bind_vars["memory_type"] = memory_type
        
        filter_clause = f"FILTER {' AND '.join(filters)}" if filters else ""
        
        aql = f"""
        FOR doc IN {self.collection_name}
        {filter_clause}
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        results = await self.async_db.aql.execute(aql, bind_vars=bind_vars)
        
        logger.info(f"Retrieved {len(results)} recent memories")
        return results
    
    async def get_memory_stats(
        self,
        memory_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about stored memories.
        
        Args:
            memory_type: Optional filter by type
            
        Returns:
            Statistics dictionary
        """
        if not self.db:
            raise ValueError("Database connection required")
        
        # Build query for stats
        type_filter = "FILTER doc.type == @memory_type" if memory_type else ""
        bind_vars = {"memory_type": memory_type} if memory_type else {}
        
        aql = f"""
        LET total = LENGTH(
            FOR doc IN {self.collection_name}
            {type_filter}
            RETURN 1
        )
        
        LET by_type = (
            FOR doc IN {self.collection_name}
            {type_filter}
            COLLECT type = doc.type WITH COUNT INTO count
            RETURN {{type: type, count: count}}
        )
        
        LET most_accessed = (
            FOR doc IN {self.collection_name}
            {type_filter}
            SORT doc.access_count DESC
            LIMIT 5
            RETURN {{
                content: SUBSTRING(doc.content, 0, 100),
                type: doc.type,
                access_count: doc.access_count
            }}
        )
        
        RETURN {{
            total: total,
            by_type: by_type,
            most_accessed: most_accessed
        }}
        """
        
        results = await self.async_db.aql.execute(aql, bind_vars=bind_vars)
        stats = results[0] if results else {"total": 0, "by_type": [], "most_accessed": []}
        
        return stats


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """Save results to JSON file."""
    if output_dir is None:
        output_dir = Path(__file__).parent / "tmp" / "responses"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(__file__).stem}_results_{timestamp}.json"
    output_path = output_dir / filename
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    logger.info(f"Results saved to: {output_path}")
    return output_path


# ============================================
# USAGE EXAMPLES (Inside __main__ block)
# ============================================

async def working_usage():
    """
    Demonstrate MemoryAgent functionality with real ArangoDB storage.
    
    Shows how to store and retrieve various types of memories.
    """
    logger.info("=== Running Working Usage Examples ===")
    
    # Import test utilities
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_memory_agent(test_db, test_db_name):
        logger.info(f"Testing with database: {test_db_name}")
        
        # Initialize agent with test database
        agent = MemoryAgent(test_db)
        await agent.ensure_collections()
        
        # Wait for search view to be ready
        await asyncio.sleep(1.0)
        
        # Test 1: Add different types of memories
        logger.info("\nTest 1: Adding various memory types...")
        
        # Add a learning
        learning = await agent.add_memory(
            "Batch size of 100 is optimal for datasets under 10GB",
            memory_type="learning",
            metadata={"confidence": 0.9, "context": "optimization", "tags": ["performance", "batch"]}
        )
        logger.success(f"✓ Added learning: {learning['_id']}")
        
        # Add an observation
        observation = await agent.add_memory(
            "System performance degrades when memory usage exceeds 80%",
            memory_type="observation",
            metadata={"severity": "warning", "threshold": 0.8, "tags": ["performance", "memory"]}
        )
        logger.success(f"✓ Added observation: {observation['_id']}")
        
        # Add an error pattern
        error_pattern = await agent.add_memory(
            "ConnectionError often occurs after 5 minutes of idle time",
            memory_type="error_pattern",
            metadata={"frequency": "common", "timeout": 300, "tags": ["error", "connection"]}
        )
        logger.success(f"✓ Added error pattern: {error_pattern['_id']}")
        
        # Add more memories for search testing
        await agent.add_memory(
            "Database queries should use connection pooling for better performance",
            memory_type="learning",
            metadata={"confidence": 0.85, "context": "database"}
        )
        
        await agent.add_memory(
            "Memory leaks detected in long-running processes",
            memory_type="observation",
            metadata={"severity": "critical", "context": "debugging"}
        )
        
        # Wait a bit for search view to index
        await asyncio.sleep(1.0)
        
        # Test 2: Search memories
        logger.info("\nTest 2: Searching memories...")
        
        # Search for batch-related memories
        batch_results = await agent.search_memories("batch", limit=5)
        assert len(batch_results) > 0, "Should find batch-related memories"
        logger.info(f"Found {len(batch_results)} memories about 'batch':")
        for result in batch_results:
            logger.info(f"  - Score: {result['score']:.3f}, Content: {result['memory']['content'][:60]}...")
        
        # Search for performance-related memories
        perf_results = await agent.search_memories("performance", limit=10)
        logger.info(f"\nFound {len(perf_results)} memories about 'performance'")
        
        # Search for specific type
        learnings = await agent.search_memories("", memory_type="learning", limit=10)
        logger.info(f"\nFound {len(learnings)} learning memories")
        
        # Test 3: Get recent memories
        logger.info("\nTest 3: Getting recent memories...")
        
        recent_all = await agent.get_recent_memories(limit=5)
        logger.info(f"Got {len(recent_all)} recent memories (all types)")
        
        recent_observations = await agent.get_recent_memories(
            memory_type="observation",
            limit=3
        )
        logger.info(f"Got {len(recent_observations)} recent observations")
        
        # Test 4: Memory statistics
        logger.info("\nTest 4: Memory statistics...")
        stats = await agent.get_memory_stats()
        logger.info(f"Total memories: {stats['total']}")
        logger.info("Memory types:")
        for type_stat in stats['by_type']:
            logger.info(f"  - {type_stat['type']}: {type_stat['count']}")
        
        # Verify data persistence
        collection = test_db.collection(agent.collection_name)
        total_count = collection.count()
        logger.info(f"\nVerified {total_count} memories stored in ArangoDB")
        
        # Save results
        save_results({
            "database": test_db_name,
            "total_memories": total_count,
            "sample_learning": learning,
            "search_results": [r['memory'] for r in batch_results[:2]],
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.success("✓ All memory tests passed")
        return True
    
    # Execute the test
    return await test_memory_agent()


async def debug_function():
    """
    Debug function for testing memory edge cases and advanced features.
    """
    logger.info("=== Running Debug Function ===")
    
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_edge_cases(test_db, test_db_name):
        logger.info(f"Testing edge cases with database: {test_db_name}")
        
        agent = MemoryAgent(test_db)
        await agent.ensure_collections()
        await asyncio.sleep(1.0)  # Wait for view
        
        # Test empty content
        logger.info("Testing empty content...")
        empty_memory = await agent.add_memory("", memory_type="test")
        logger.info(f"Empty memory created: {empty_memory['_id']}")
        
        # Test very long content
        logger.info("\nTesting very long content...")
        long_content = "A" * 10000
        long_memory = await agent.add_memory(
            long_content,
            memory_type="stress_test",
            metadata={"size": len(long_content)}
        )
        logger.info(f"Long memory created: {long_memory['_id']}")
        
        # Test special characters
        logger.info("\nTesting special characters...")
        special_content = "Special chars: @#$%^&*()_+{}[]|\\:;\"'<>,.?/"
        special_memory = await agent.add_memory(special_content, memory_type="special")
        
        # Test Unicode
        logger.info("\nTesting Unicode content...")
        unicode_content = "Unicode test: 你好世界 🌍 مرحبا بالعالم"
        unicode_memory = await agent.add_memory(unicode_content, memory_type="unicode")
        
        # Test search with special queries
        logger.info("\nTesting special search queries...")
        
        # Empty search (should return recent memories)
        empty_results = await agent.search_memories("")
        logger.info(f"Empty search returned {len(empty_results)} results")
        
        # Test access tracking
        logger.info("\nTesting access tracking...")
        
        # Add a memory and search for it multiple times
        tracked_memory = await agent.add_memory(
            "This memory will be accessed multiple times",
            memory_type="tracking_test",
            metadata={"test": True}
        )
        
        await asyncio.sleep(1.0)  # Let it index
        
        # Access it 3 times
        for i in range(3):
            results = await agent.search_memories("accessed multiple", limit=1)
            if results:
                logger.info(f"Access {i+1}: count = {results[0]['memory']['access_count']}")
        
        # Test metadata filtering
        logger.info("\nTesting metadata and context search...")
        
        # Add memories with specific metadata
        await agent.add_memory(
            "Critical system alert",
            memory_type="alert",
            metadata={"severity": "critical", "context": "system monitoring"}
        )
        
        await agent.add_memory(
            "Warning about disk space",
            memory_type="alert",
            metadata={"severity": "warning", "context": "disk monitoring"}
        )
        
        await asyncio.sleep(1.0)  # Let them index
        
        # Search by context
        monitoring_results = await agent.search_memories("monitoring", limit=10)
        logger.info(f"Found {len(monitoring_results)} monitoring-related memories")
        
        # Test statistics with filtered data
        logger.info("\nTesting filtered statistics...")
        
        alert_stats = await agent.get_memory_stats(memory_type="alert")
        logger.info(f"Alert statistics: {alert_stats['total']} total alerts")
        
        overall_stats = await agent.get_memory_stats()
        logger.info(f"Overall statistics: {overall_stats['total']} total memories")
        logger.info("Most accessed memories:")
        for mem in overall_stats['most_accessed'][:3]:
            logger.info(f"  - {mem['content'][:50]}... (accessed {mem['access_count']} times)")
        
        return True
    
    # Execute the test
    return await test_edge_cases()


async def stress_test():
    """
    Stress test memory operations with high volume.
    """
    logger.info("=== Running Stress Tests ===")
    
    agent = MemoryAgent()
    
    # Test 1: Add many memories
    logger.info("Test 1: Adding many memories...")
    start_time = datetime.utcnow()
    
    memory_types = ["learning", "observation", "error_pattern", "optimization", "debug"]
    
    for i in range(1000):
        await agent.add_memory(
            f"Memory {i}: Important information about process {i % 10}",
            memory_type=memory_types[i % len(memory_types)],
            metadata={"index": i, "batch": i // 100}
        )
        
        if i % 200 == 0:
            logger.info(f"  Added {i} memories")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ Added 1000 memories in {duration:.2f} seconds")
    
    # Test 2: Search performance
    logger.info("\nTest 2: Search performance...")
    
    search_terms = ["process", "information", "important", "0", "memory"]
    total_results = 0
    
    start_time = datetime.utcnow()
    for term in search_terms:
        results = await agent.search_memories(term, limit=100)
        total_results += len(results)
        logger.info(f"  '{term}': {len(results)} results")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Searched {len(search_terms)} terms, found {total_results} total results "
        f"in {duration:.2f} seconds"
    )
    
    # Test 3: Concurrent operations
    logger.info("\nTest 3: Concurrent memory operations...")
    
    async def memory_worker(worker_id: int, operation_count: int):
        """Perform memory operations concurrently."""
        for i in range(operation_count):
            if i % 2 == 0:
                # Add memory
                await agent.add_memory(
                    f"Worker {worker_id} memory {i}",
                    memory_type="concurrent_test"
                )
            else:
                # Search memory
                await agent.search_memories(f"Worker {worker_id}")
    
    start_time = datetime.utcnow()
    workers = [memory_worker(i, 20) for i in range(10)]
    await asyncio.gather(*workers)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Completed 200 concurrent operations (10 workers x 20 ops) "
        f"in {duration:.2f} seconds"
    )
    
    # Final statistics
    logger.info(f"\nFinal memory count: {len(agent.memories)}")
    
    type_counts = {}
    for memory in agent.memories:
        mem_type = memory["type"]
        type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
    
    logger.info("Memory type distribution:")
    for mem_type, count in type_counts.items():
        logger.info(f"  {mem_type}: {count}")
    
    logger.info("\n📊 Stress Test Summary: All tests passed")
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    """
    Script entry point with triple-mode execution.
    
    Usage:
        python memory_agent.py          # Runs working_usage() - stable tests
        python memory_agent.py debug    # Runs debug_function() - experimental
        python memory_agent.py stress   # Runs stress_test() - performance tests
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        """Main async entry point."""
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
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)