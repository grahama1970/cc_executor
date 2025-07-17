#!/usr/bin/env python3
"""
Hybrid search module for Logger Agent integration.

Provides real BM25 search functionality by delegating to AgentSearch
for comprehensive search capabilities across ArangoDB collections.

Third-party Documentation:
- ArangoDB Search: https://www.arangodb.com/docs/stable/arangosearch.html

Example Input:
    query = "error connection timeout"
    search_type = "bm25"
    collection = "log_events"

Expected Output:
    [
        {"_id": "log_events/123", "message": "Connection timeout error", "score": 0.95},
        {"_id": "log_events/456", "message": "Database connection failed", "score": 0.87}
    ]

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python hybrid_search.py          # Runs working_usage() - stable, known to work
  python hybrid_search.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger
from arango.database import StandardDatabase

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from arangodb.core.search.agent_search import AgentSearch

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

class HybridSearch:
    """Real hybrid search implementation using AgentSearch."""
    
    def __init__(self, db: Optional[StandardDatabase] = None):
        """Initialize with optional database connection."""
        self.db = db
        self.agent_search = AgentSearch(db) if db else None
        logger.info("HybridSearch initialized with ArangoDB")
    
    async def initialize(self):
        """Initialize search views and indexes."""
        if not self.agent_search:
            raise ValueError("Database connection required")
        
        await self.agent_search.initialize_search_view()
        logger.info("Search views initialized")
    
    async def search(
        self,
        query: str,
        search_type: str = "bm25",
        collection: str = "log_events",
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform real search using ArangoDB's BM25 capabilities.
        
        Args:
            query: Search query string
            search_type: Type of search (bm25, semantic, hybrid)
            collection: Collection to search in (used for filtering)
            limit: Maximum results to return
            filters: Optional filters to apply
            
        Returns:
            List of search results with scores from ArangoDB
        """
        if not self.db:
            raise ValueError("Database connection required for search")
        
        logger.info(f"Real search: query='{query}', type={search_type}, collection={collection}")
        
        # Prepare filters for AgentSearch
        search_filters = filters or {}
        
        # If specific collection requested, add to filters
        if collection and collection != "log_events":
            # Map collection names to event types or other filters
            collection_mapping = {
                "agent_learnings": {"event_types": ["learning", "insight"]},
                "script_runs": {"event_types": ["script_start", "script_end"]},
                "tool_executions": {"event_types": ["tool_execution"]}
            }
            if collection in collection_mapping:
                search_filters.update(collection_mapping[collection])
        
        # Convert level filter to extra_data filter for AgentSearch compatibility
        level_filter = None
        if "level" in search_filters:
            # AgentSearch expects filters to work on the actual document structure
            # For now, we'll handle level filtering post-search
            level_filter = search_filters.pop("level")
        
        # Different search strategies based on type
        if search_type == "bm25":
            # Use standard BM25 search
            results = await self.agent_search.search_agent_activity(
                query=query,
                filters=search_filters,
                limit=limit,
                sort_by_relevance=True
            )
        
        elif search_type == "semantic":
            # For semantic search, we could use different analyzers or strategies
            # For now, fall back to BM25 with adjusted parameters
            results = await self.agent_search.search_agent_activity(
                query=query,
                filters=search_filters,
                limit=limit * 2,  # Get more results for semantic filtering
                sort_by_relevance=True
            )
            # Could apply additional semantic filtering here
            results = results[:limit]
        
        elif search_type == "hybrid":
            # Hybrid approach: combine BM25 with other signals
            # First get BM25 results
            bm25_results = await self.agent_search.search_agent_activity(
                query=query,
                filters=search_filters,
                limit=limit,
                sort_by_relevance=True
            )
            
            # If we have results, enrich them with additional context
            if bm25_results:
                # Could fetch related documents, check for patterns, etc.
                # For now, just return BM25 results
                results = bm25_results
            else:
                results = []
        
        else:
            # Default to BM25
            results = await self.agent_search.search_agent_activity(
                query=query,
                filters=search_filters,
                limit=limit,
                sort_by_relevance=True
            )
        
        # Transform results to expected format
        formatted_results = []
        for result in results:
            doc = result.get('doc', {})
            
            # Apply level filter if specified
            if level_filter and doc.get('level') != level_filter:
                continue
            
            formatted_result = {
                "_id": doc.get('_id', ''),
                "_key": doc.get('_key', ''),
                "message": doc.get('message', ''),
                "level": doc.get('level', 'INFO'),
                "timestamp": doc.get('timestamp', ''),
                "score": result.get('score', 0.0),
                "type": result.get('type', 'unknown')
            }
            
            # Add any extra fields from the document
            if 'extra_data' in doc:
                formatted_result['extra_data'] = doc['extra_data']
            
            formatted_results.append(formatted_result)
        
        logger.info(f"Returning {len(formatted_results)} search results")
        return formatted_results
    
    async def search_errors(
        self,
        error_pattern: str = None,
        time_range: Dict[str, str] = None,
        include_resolutions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search specifically for errors and their resolutions.
        
        Args:
            error_pattern: Optional pattern to match in error messages
            time_range: Optional time range filter
            include_resolutions: Whether to include resolution information
            
        Returns:
            List of errors with optional resolution data
        """
        if not self.agent_search:
            raise ValueError("Database connection required")
        
        if include_resolutions:
            # Use the specialized error search with resolutions
            return await self.agent_search.search_errors_with_resolutions(
                error_pattern=error_pattern,
                time_range=time_range,
                include_unresolved=True
            )
        else:
            # Just search for error documents
            filters = {"level": "ERROR"}
            if time_range:
                filters["time_range"] = time_range
            
            return await self.search(
                query=error_pattern or "error",
                filters=filters,
                limit=100
            )


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
    Demonstrate HybridSearch functionality with real ArangoDB search.
    
    This shows how the Logger Agent will use the search module.
    """
    logger.info("=== Running Working Usage Examples ===")
    
    # Import test utilities
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_hybrid_search(test_db, test_db_name):
        logger.info(f"Testing with database: {test_db_name}")
        
        # Initialize search
        search = HybridSearch(test_db)
        await search.initialize()
        
        # Insert test data
        log_events = test_db.collection("log_events")
        
        test_docs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Connection timeout error occurred while accessing database",
                "execution_id": "test_123",
                "extra_data": {
                    "error_code": "CONN_TIMEOUT",
                    "retry_count": 3
                }
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Database connection failed with authentication error",
                "execution_id": "test_124",
                "extra_data": {
                    "error_code": "AUTH_FAILED",
                    "database": "prod_db"
                }
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "WARNING",
                "message": "Memory usage warning: 85% utilized, consider scaling",
                "execution_id": "test_125",
                "extra_data": {
                    "memory_percent": 85,
                    "threshold": 80
                }
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "Successfully connected to database after retry",
                "execution_id": "test_123",
                "extra_data": {
                    "retry_attempt": 4,
                    "connection_time": 1.23
                }
            }
        ]
        
        log_events.insert_many(test_docs)
        logger.info(f"Inserted {len(test_docs)} test documents")
        
        # Wait for indexing
        await asyncio.sleep(2.0)
        
        # Test 1: Search for errors
        logger.info("\nTest 1: Searching for errors...")
        error_results = await search.search(
            query="error connection",
            search_type="bm25",
            limit=10
        )
        
        logger.info(f"Found {len(error_results)} error results")
        for result in error_results[:3]:
            logger.info(f"  - {result['message'][:50]}... (score: {result['score']:.3f})")
        
        assert len(error_results) > 0, "Should find error results"
        
        # Test 2: Search with filters
        logger.info("\nTest 2: Searching with filters...")
        filtered_results = await search.search(
            query="database",
            filters={"level": "ERROR"},
            limit=5
        )
        
        logger.info(f"Found {len(filtered_results)} filtered results")
        for result in filtered_results:
            assert result.get("level") == "ERROR", f"Expected ERROR, got {result.get('level')}"
            logger.info(f"  - Level: {result['level']}, Message: {result['message'][:40]}...")
        
        # Test 3: Different search types
        logger.info("\nTest 3: Testing different search types...")
        for search_type in ["bm25", "semantic", "hybrid"]:
            results = await search.search(
                query="memory warning",
                search_type=search_type,
                limit=3
            )
            logger.info(f"  {search_type}: {len(results)} results")
            if results:
                logger.info(f"    Top result: {results[0]['message'][:50]}...")
        
        # Test 4: Error search with resolutions
        logger.info("\nTest 4: Searching for errors with resolutions...")
        
        # Insert some error and resolution pairs
        errors_collection = test_db.collection("errors_and_failures")
        error_doc = errors_collection.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Critical database connection error",
            "error_type": "DatabaseError",
            "session_id": "test_session_1",
            "resolved": True,
            "resolution": "Increased connection pool size"
        })
        
        error_results = await search.search_errors(
            error_pattern="database",
            include_resolutions=True
        )
        
        logger.info(f"Found {len(error_results)} errors with resolution data")
        
        # Save test results
        save_results({
            "database": test_db_name,
            "total_documents": len(test_docs),
            "search_results": {
                "error_search": len(error_results),
                "filtered_search": len(filtered_results),
                "sample_result": error_results[0] if error_results else None
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.success("✓ All search tests passed")
        return True
    
    # Execute the test
    return await test_hybrid_search()


async def debug_function():
    """
    Debug function for testing search edge cases and performance.
    
    Use this to test specific search scenarios or debug issues.
    """
    logger.info("=== Running Debug Function ===")
    
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_search_edge_cases(test_db, test_db_name):
        logger.info(f"Testing edge cases with database: {test_db_name}")
        
        search = HybridSearch(test_db)
        await search.initialize()
        
        # Insert diverse test data
        log_events = test_db.collection("log_events")
        
        # Insert documents with various characteristics
        edge_case_docs = [
            # Empty message
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "",
                "execution_id": "empty_test"
            },
            # Very long message
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Error: " + "A" * 1000,
                "execution_id": "long_test"
            },
            # Special characters
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "WARNING",
                "message": "Special chars: @#$%^&*()_+{}[]|\\:;\"'<>,.?/",
                "execution_id": "special_test"
            },
            # Unicode content
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "Unicode test: 你好世界 🌍 Testing international chars",
                "execution_id": "unicode_test"
            },
            # Numeric patterns
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Error code 12345: Failed at line 67890",
                "execution_id": "numeric_test"
            }
        ]
        
        log_events.insert_many(edge_case_docs)
        await asyncio.sleep(2.0)  # Wait for indexing
        
        # Test empty query
        logger.info("\nTesting empty query...")
        empty_results = await search.search(query="", limit=5)
        logger.info(f"Empty query returned {len(empty_results)} results")
        
        # Test very long query
        logger.info("\nTesting very long query...")
        long_query = " ".join(["error"] * 50)
        long_results = await search.search(query=long_query, limit=5)
        logger.info(f"Long query returned {len(long_results)} results")
        
        # Test special characters
        logger.info("\nTesting special characters...")
        special_results = await search.search(query="@#$%", limit=5)
        logger.info(f"Special char query returned {len(special_results)} results")
        
        # Test Unicode search
        logger.info("\nTesting Unicode search...")
        unicode_results = await search.search(query="你好", limit=5)
        logger.info(f"Unicode query returned {len(unicode_results)} results")
        
        # Test numeric search
        logger.info("\nTesting numeric patterns...")
        numeric_results = await search.search(query="12345", limit=5)
        logger.info(f"Numeric query returned {len(numeric_results)} results")
        
        # Test collection-specific searches
        logger.info("\nTesting collection filtering...")
        
        # Insert data in different collections
        tool_executions = test_db.collection("tool_executions")
        tool_executions.insert({
            "tool_name": "Bash",
            "command": "test command",
            "output_preview": "Test output",
            "session_id": "test_session",
            "start_time": datetime.utcnow().isoformat()
        })
        
        await asyncio.sleep(1.0)
        
        # Search across different logical collections
        for collection in ["log_events", "tool_executions", "agent_learnings"]:
            results = await search.search(
                query="test",
                collection=collection,
                limit=2
            )
            logger.info(f"  {collection}: {len(results)} results")
        
        # Test search performance
        logger.info("\nTesting search performance...")
        import time
        
        # Insert more documents for performance testing
        perf_docs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": f"Performance test message {i} with some keywords",
                "execution_id": f"perf_test_{i}"
            }
            for i in range(100)
        ]
        log_events.insert_many(perf_docs)
        await asyncio.sleep(2.0)
        
        # Time different search operations
        search_times = {}
        
        # Simple search
        start = time.time()
        results = await search.search("performance", limit=20)
        search_times["simple"] = time.time() - start
        
        # Filtered search
        start = time.time()
        results = await search.search(
            "test",
            filters={"level": "INFO"},
            limit=20
        )
        search_times["filtered"] = time.time() - start
        
        # Complex query
        start = time.time()
        results = await search.search(
            "performance test message keywords",
            search_type="hybrid",
            limit=20
        )
        search_times["complex"] = time.time() - start
        
        logger.info("\nSearch performance:")
        for search_type, duration in search_times.items():
            logger.info(f"  {search_type}: {duration:.3f}s")
        
        return True
    
    # Execute the test
    return await test_search_edge_cases()


async def stress_test():
    """
    Stress test the search functionality.
    
    Tests high-volume and concurrent search operations.
    """
    logger.info("=== Running Stress Tests ===")
    
    search = HybridSearch()
    
    # Test 1: Many sequential searches
    logger.info("Test 1: Sequential search performance...")
    start_time = datetime.utcnow()
    
    for i in range(100):
        await search.search(f"query_{i}", limit=10)
        if i % 20 == 0:
            logger.info(f"  Completed {i} searches")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ 100 sequential searches in {duration:.2f} seconds")
    
    # Test 2: Concurrent searches
    logger.info("\nTest 2: Concurrent search performance...")
    
    async def concurrent_search(worker_id: int, count: int):
        """Run multiple searches concurrently."""
        for i in range(count):
            await search.search(f"worker_{worker_id}_query_{i}", limit=5)
    
    start_time = datetime.utcnow()
    workers = [concurrent_search(i, 10) for i in range(10)]
    await asyncio.gather(*workers)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ 100 concurrent searches (10x10) in {duration:.2f} seconds")
    
    # Test 3: Large result sets
    logger.info("\nTest 3: Large result set handling...")
    large_results = await search.search("error", limit=1000)
    logger.success(f"✓ Handled large result request (got {len(large_results)} results)")
    
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
        python hybrid_search.py          # Runs working_usage() - stable tests
        python hybrid_search.py debug    # Runs debug_function() - experimental
        python hybrid_search.py stress   # Runs stress_test() - performance tests
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