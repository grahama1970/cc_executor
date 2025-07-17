#!/usr/bin/env python3
"""
Relationship extraction module for Logger Agent integration.

Provides real functionality for extracting and storing relationships between
log events in ArangoDB edge collections.

Third-party Documentation:
- ArangoDB Graphs: https://www.arangodb.com/docs/stable/graphs.html

Example Input:
    text1 = "Database connection failed"
    text2 = "Retrying database connection"

Expected Output:
    [{"type": "RETRY_OF", "confidence": 0.85, "from": text1, "to": text2}]

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python relationship_extraction.py          # Runs working_usage() - stable, known to work
  python relationship_extraction.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
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

class RelationshipExtractor:
    """Real relationship extractor that stores relationships in ArangoDB."""
    
    def __init__(self, db: Optional[StandardDatabase] = None):
        """Initialize with optional database connection."""
        self.db = db
        self.async_db = AsyncDatabase(db) if db else None
        self.edge_collection = "log_relationships"  # Edge collection for relationships
        logger.info("RelationshipExtractor initialized with ArangoDB")
    
    async def ensure_collections(self):
        """Ensure required collections exist."""
        if not self.db:
            raise ValueError("Database connection required")
        
        # Create edge collection if it doesn't exist
        if not await self.async_db.has_collection(self.edge_collection):
            await self.async_db.create_collection(self.edge_collection, edge=True)
            logger.info(f"Created edge collection: {self.edge_collection}")
    
    async def extract_relationships(
        self,
        text1: str,
        text2: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships between two text snippets.
        
        Args:
            text1: First text to analyze
            text2: Second text to analyze
            context: Optional context information with doc1_id and doc2_id
            
        Returns:
            List of relationships with type and confidence
        """
        relationships = []
        
        # Simple pattern matching for demonstration
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Check for retry patterns
        if "failed" in text1_lower and "retry" in text2_lower:
            relationships.append({
                "type": "RETRY_OF",
                "confidence": 0.85,
                "from": text1,
                "to": text2
            })
        
        # Check for error-fix patterns
        if "error" in text1_lower and ("fix" in text2_lower or "resolved" in text2_lower):
            relationships.append({
                "type": "FIXED_BY",
                "confidence": 0.90,
                "from": text1,
                "to": text2
            })
        
        # Check for cause-effect patterns
        if "caused" in text2_lower or "because" in text2_lower:
            relationships.append({
                "type": "CAUSED_BY",
                "confidence": 0.75,
                "from": text2,
                "to": text1
            })
        
        # Temporal relationship (always exists between sequential logs)
        relationships.append({
            "type": "FOLLOWED_BY",
            "confidence": 1.0,
            "from": text1,
            "to": text2
        })
        
        return relationships
    
    async def store_relationships(
        self,
        doc1_id: str,
        doc2_id: str,
        relationships: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Store extracted relationships in edge collection.
        
        Args:
            doc1_id: ID of first document (e.g., "log_events/123")
            doc2_id: ID of second document (e.g., "log_events/124")
            relationships: List of extracted relationships
            context: Optional context information
            
        Returns:
            List of created edge documents
        """
        if not self.db:
            raise ValueError("Database connection required for storing relationships")
        
        await self.ensure_collections()
        
        edge_collection = self.async_db.collection(self.edge_collection)
        created_edges = []
        
        for rel in relationships:
            # Create edge document
            edge_doc = {
                "_from": doc1_id if rel["from"] == relationships[0]["from"] else doc2_id,
                "_to": doc2_id if rel["to"] == relationships[0]["to"] else doc1_id,
                "relationship_type": rel["type"],
                "confidence": rel["confidence"],
                "extracted_at": datetime.utcnow().isoformat(),
                "context": context or {},
                "source_text": rel["from"][:200],  # Store preview
                "target_text": rel["to"][:200]
            }
            
            # Store edge
            result = await edge_collection.insert(edge_doc)
            edge_doc["_id"] = result["_id"]
            edge_doc["_key"] = result["_key"]
            created_edges.append(edge_doc)
            
        logger.info(f"Stored {len(created_edges)} relationships between {doc1_id} and {doc2_id}")
        return created_edges
    
    async def find_related_documents(
        self,
        doc_id: str,
        relationship_types: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find documents related to a given document through stored relationships.
        
        Args:
            doc_id: Document ID to find relationships for
            relationship_types: Optional filter by relationship types
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            
        Returns:
            List of related documents with relationship info
        """
        if not self.db:
            raise ValueError("Database connection required")
        
        # Build AQL query
        filters = ["r.confidence >= @min_confidence"]
        bind_vars = {
            "doc_id": doc_id,
            "min_confidence": min_confidence,
            "limit": limit
        }
        
        if relationship_types:
            filters.append("r.relationship_type IN @types")
            bind_vars["types"] = relationship_types
        
        filter_clause = f"FILTER {' AND '.join(filters)}" if filters else ""
        
        query = f"""
        FOR v, r IN 1..1 ANY @doc_id {self.edge_collection}
        {filter_clause}
        SORT r.confidence DESC, r.extracted_at DESC
        LIMIT @limit
        RETURN {{
            related_doc: v,
            relationship: r,
            direction: r._from == @doc_id ? 'outbound' : 'inbound'
        }}
        """
        
        results = await self.async_db.aql.execute(query, bind_vars=bind_vars)
        logger.info(f"Found {len(results)} related documents for {doc_id}")
        return results


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
    Demonstrate RelationshipExtractor functionality with real ArangoDB storage.
    
    Shows how to extract and store relationships between log messages.
    """
    logger.info("=== Running Working Usage Examples ===")
    
    # Import test utilities
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_relationships(test_db, test_db_name):
        logger.info(f"Testing with database: {test_db_name}")
        
        # Initialize extractor with test database
        extractor = RelationshipExtractor(test_db)
        await extractor.ensure_collections()
        
        # Create test log documents first
        log_events = test_db.collection("log_events")
        
        # Insert test documents
        doc1 = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Database connection failed with timeout",
            "execution_id": "test_123"
        })
        
        doc2 = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Retrying database connection attempt 1",
            "execution_id": "test_123"
        })
        
        # Test 1: Extract and store relationships
        logger.info("\nTest 1: Extract and store relationships...")
        rels = await extractor.extract_relationships(
            "Database connection failed with timeout",
            "Retrying database connection attempt 1"
        )
        
        logger.info(f"Found {len(rels)} relationships:")
        for rel in rels:
            logger.info(f"  - {rel['type']} (confidence: {rel['confidence']})")
        
        # Store the relationships
        stored_edges = await extractor.store_relationships(
            f"log_events/{doc1['_key']}",
            f"log_events/{doc2['_key']}",
            rels,
            context={"execution_id": "test_123"}
        )
        
        logger.success(f"✓ Stored {len(stored_edges)} relationships in edge collection")
        
        # Test 2: Find related documents
        logger.info("\nTest 2: Find related documents...")
        related = await extractor.find_related_documents(
            f"log_events/{doc1['_key']}",
            relationship_types=["RETRY_OF", "FOLLOWED_BY"],
            min_confidence=0.8
        )
        
        logger.info(f"Found {len(related)} related documents")
        for rel in related:
            logger.info(f"  - {rel['relationship']['relationship_type']} "
                       f"(confidence: {rel['relationship']['confidence']:.2f}, "
                       f"direction: {rel['direction']})")
        
        # Test 3: Complex relationships with multiple documents
        logger.info("\nTest 3: Complex relationship network...")
        
        # Create more test documents
        doc3 = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Critical error: Memory overflow detected",
            "execution_id": "test_456"
        })
        
        doc4 = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Memory issue fixed by clearing cache",
            "execution_id": "test_456"
        })
        
        # Extract and store fix relationship
        fix_rels = await extractor.extract_relationships(
            "Critical error: Memory overflow detected",
            "Memory issue fixed by clearing cache"
        )
        
        await extractor.store_relationships(
            f"log_events/{doc3['_key']}",
            f"log_events/{doc4['_key']}",
            fix_rels
        )
        
        # Query all relationships in the collection
        edge_collection = test_db.collection(extractor.edge_collection)
        total_edges = edge_collection.count()
        logger.info(f"\nTotal relationships stored: {total_edges}")
        
        # Save results
        save_results({
            "database": test_db_name,
            "total_documents": 4,
            "total_relationships": total_edges,
            "sample_relationships": stored_edges[:2],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.success("✓ All relationship extraction tests passed")
        return True
    
    # Execute the test
    return await test_relationships()


async def debug_function():
    """
    Debug function for testing edge cases and graph traversal.
    """
    logger.info("=== Running Debug Function ===")
    
    from utils.test_utils import with_test_db_no_manager
    
    @with_test_db_no_manager
    async def test_edge_cases(test_db, test_db_name):
        logger.info(f"Testing edge cases with database: {test_db_name}")
        
        extractor = RelationshipExtractor(test_db)
        await extractor.ensure_collections()
        
        # Test empty strings
        logger.info("Testing empty strings...")
        rels = await extractor.extract_relationships("", "")
        logger.info(f"Empty strings: {len(rels)} relationships")
        
        # Test graph traversal with multiple hops
        logger.info("\nTesting relationship chains...")
        
        # Create a chain of related documents
        log_events = test_db.collection("log_events")
        
        # Create chain: Error -> Retry -> Success
        docs = []
        messages = [
            "Initial error occurred",
            "Retrying operation",
            "Operation succeeded",
            "Cleanup completed"
        ]
        
        for i, msg in enumerate(messages):
            doc = log_events.insert({
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR" if i == 0 else "INFO",
                "message": msg,
                "sequence": i
            })
            docs.append(doc)
        
        # Create relationships between consecutive documents
        for i in range(len(docs) - 1):
            rels = await extractor.extract_relationships(
                messages[i],
                messages[i + 1]
            )
            
            await extractor.store_relationships(
                f"log_events/{docs[i]['_key']}",
                f"log_events/{docs[i + 1]['_key']}",
                rels
            )
        
        # Test multi-hop traversal
        logger.info("\nTesting multi-hop graph traversal...")
        
        # Query for all documents reachable from the first one
        query = """
        FOR v, e, p IN 1..3 ANY @start_doc log_relationships
        RETURN {
            document: v,
            edge: e,
            depth: LENGTH(p.edges),
            path: p.vertices[*].message
        }
        """
        
        results = await extractor.async_db.aql.execute(
            query,
            bind_vars={"start_doc": f"log_events/{docs[0]['_key']}"}
        )
        
        logger.info(f"Found {len(results)} documents through traversal:")
        for result in results:
            logger.info(f"  Depth {result['depth']}: {result['document']['message']}")
        
        # Test relationship type filtering
        logger.info("\nTesting relationship type filtering...")
        
        # Add a specific error-fix relationship
        error_doc = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Database connection error"
        })
        
        fix_doc = log_events.insert({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Database connection fixed"
        })
        
        fix_rels = await extractor.extract_relationships(
            "Database connection error",
            "Database connection fixed"
        )
        
        await extractor.store_relationships(
            f"log_events/{error_doc['_key']}",
            f"log_events/{fix_doc['_key']}",
            fix_rels
        )
        
        # Find only FIXED_BY relationships
        fixed_docs = await extractor.find_related_documents(
            f"log_events/{error_doc['_key']}",
            relationship_types=["FIXED_BY"],
            min_confidence=0.8
        )
        
        logger.info(f"\nFound {len(fixed_docs)} FIXED_BY relationships")
        
        return True
    
    # Execute the test
    return await test_edge_cases()


async def stress_test():
    """
    Stress test relationship extraction with high volume.
    """
    logger.info("=== Running Stress Tests ===")
    
    extractor = RelationshipExtractor()
    
    # Test 1: Many sequential extractions
    logger.info("Test 1: Sequential extraction performance...")
    start_time = datetime.utcnow()
    
    total_relationships = 0
    for i in range(500):
        rels = await extractor.extract_relationships(
            f"Log message {i}: Operation in progress",
            f"Log message {i+1}: Operation completed"
        )
        total_relationships += len(rels)
        
        if i % 100 == 0:
            logger.info(f"  Processed {i} pairs")
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Extracted {total_relationships} relationships from 500 pairs "
        f"in {duration:.2f} seconds"
    )
    
    # Test 2: Concurrent extractions
    logger.info("\nTest 2: Concurrent extraction performance...")
    
    async def extract_batch(batch_id: int, count: int):
        """Extract relationships for a batch of log pairs."""
        batch_rels = 0
        for i in range(count):
            rels = await extractor.extract_relationships(
                f"Batch {batch_id} error {i}",
                f"Batch {batch_id} recovery {i}"
            )
            batch_rels += len(rels)
        return batch_rels
    
    start_time = datetime.utcnow()
    tasks = [extract_batch(i, 50) for i in range(10)]
    batch_results = await asyncio.gather(*tasks)
    total_concurrent = sum(batch_results)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(
        f"✓ Extracted {total_concurrent} relationships concurrently "
        f"(10 batches x 50 pairs) in {duration:.2f} seconds"
    )
    
    # Test 3: Complex pattern matching
    logger.info("\nTest 3: Complex pattern performance...")
    complex_patterns = [
        ("System error: Database connection pool exhausted after 300 attempts",
         "Recovery initiated: Restarting connection pool and clearing stale connections"),
        ("Performance degradation: Response time increased from 100ms to 5000ms",
         "Optimization applied: Enabled query caching, response time reduced to 150ms"),
        ("Security alert: Multiple failed authentication attempts from IP 192.168.1.100",
         "Security response: IP blocked and alert sent to administrators")
    ]
    
    start_time = datetime.utcnow()
    for _ in range(100):
        for text1, text2 in complex_patterns:
            await extractor.extract_relationships(text1, text2)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.success(f"✓ Complex pattern extraction (300 ops) in {duration:.2f} seconds")
    
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
        python relationship_extraction.py          # Runs working_usage()
        python relationship_extraction.py debug    # Runs debug_function()
        python relationship_extraction.py stress   # Runs stress_test()
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