#!/usr/bin/env python3
"""
Cache database schema in logger agent for quick retrieval.

This tool inspects the ArangoDB schema and stores it in the logger agent
database with proper categorization for easy retrieval. This enables
efficient natural language to AQL conversion without repeated inspections.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python cache_db_schema.py          # Runs working_usage() - stable, known to work
  python cache_db_schema.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from loguru import logger

# Add logger agent to path
LOGGER_AGENT_PATH = Path(__file__).parent.parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
sys.path.insert(0, str(LOGGER_AGENT_PATH))

try:
    from agent_log_manager import get_log_manager
    from inspect_arangodb_schema import inspect_logger_agent_schema, generate_agent_prompt_from_schema
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    IMPORTS_AVAILABLE = False


async def cache_schema_in_logger(
    force_refresh: bool = False,
    cache_duration_hours: int = 24
) -> Dict[str, Any]:
    """
    Cache the database schema in logger agent for quick retrieval.
    
    Args:
        force_refresh: Force a fresh schema inspection even if cache exists
        cache_duration_hours: How long to consider the cache valid
        
    Returns:
        Dictionary with schema info and cache metadata
    """
    
    if not IMPORTS_AVAILABLE:
        return {"error": "Required imports not available"}
    
    manager = await get_log_manager()
    
    # Check if we have a recent cached schema
    if not force_refresh:
        cached_schema = await get_cached_schema(manager, cache_duration_hours)
        if cached_schema:
            logger.info("Using cached schema from logger agent")
            return cached_schema
    
    logger.info("Inspecting database schema...")
    
    # Inspect the current schema
    schema_report = await inspect_logger_agent_schema()
    
    # Generate the agent prompt
    agent_prompt = generate_agent_prompt_from_schema(schema_report)
    
    # Prepare the document for storage
    schema_doc = {
        "category": "db_schema",
        "schema_version": "1.0",
        "inspected_at": datetime.utcnow().isoformat(),
        "database": schema_report.get("database", "logger_agent"),
        "summary": schema_report.get("summary", {}),
        "collections": schema_report.get("collections", {}),
        "graphs": schema_report.get("graphs", {}),
        "views": schema_report.get("views", {}),
        "sample_queries": schema_report.get("sample_queries", []),
        "agent_prompt": agent_prompt,
        "cache_metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=cache_duration_hours)).isoformat(),
            "duration_hours": cache_duration_hours
        }
    }
    
    # Store in logger agent
    stored_doc = await manager.log_event(
        level="INFO",
        message="Database schema cached for agent retrieval",
        script_name="cache_db_schema",
        execution_id=f"schema_cache_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        extra_data=schema_doc,
        tags=["db_schema", "cache", "infrastructure", "agent_resource"]
    )
    
    logger.success(f"Schema cached with ID: {stored_doc['_id']}")
    
    # Also store a simplified lookup document
    lookup_doc = await manager.log_event(
        level="INFO",
        message="Schema lookup reference",
        script_name="cache_db_schema",
        execution_id=stored_doc["execution_id"],
        extra_data={
            "category": "db_schema_lookup",
            "schema_doc_id": stored_doc["_id"],
            "collections_count": len(schema_report.get("collections", {})),
            "views_count": len(schema_report.get("views", {})),
            "graphs_count": len(schema_report.get("graphs", {})),
            "cached_at": datetime.utcnow().isoformat()
        },
        tags=["db_schema_lookup", "latest"]
    )
    
    return {
        "schema_doc_id": stored_doc["_id"],
        "lookup_doc_id": lookup_doc["_id"],
        "cache_metadata": schema_doc["cache_metadata"],
        "summary": schema_report.get("summary", {}),
        "success": True
    }


async def get_cached_schema(
    manager, 
    cache_duration_hours: int
) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached schema from logger agent if still valid.
    """
    
    # Query for the most recent schema cache
    aql = """
    FOR doc IN log_events
    FILTER doc.extra_data.category == "db_schema"
    FILTER doc.timestamp > DATE_ISO8601(DATE_ADD(NOW(), -@hours, 'hour'))
    SORT doc.timestamp DESC
    LIMIT 1
    RETURN doc
    """
    
    try:
        cursor = await manager.db.aql.execute(
            aql,
            bind_vars={"hours": cache_duration_hours}
        )
        
        results = list(cursor)
        if results:
            doc = results[0]
            logger.info(f"Found cached schema from {doc['timestamp']}")
            
            # Return the cached data
            return {
                "schema_doc_id": doc["_id"],
                "cache_metadata": doc["extra_data"].get("cache_metadata", {}),
                "summary": doc["extra_data"].get("summary", {}),
                "collections": doc["extra_data"].get("collections", {}),
                "views": doc["extra_data"].get("views", {}),
                "graphs": doc["extra_data"].get("graphs", {}),
                "sample_queries": doc["extra_data"].get("sample_queries", []),
                "agent_prompt": doc["extra_data"].get("agent_prompt", ""),
                "from_cache": True,
                "cached_at": doc["timestamp"]
            }
    except Exception as e:
        logger.error(f"Failed to retrieve cached schema: {e}")
    
    return None


async def retrieve_schema_for_agent() -> Dict[str, Any]:
    """
    Retrieve schema in a format optimized for agent use.
    
    This is what the natural language to AQL tool would call.
    """
    
    manager = await get_log_manager()
    
    # Try to get cached schema (valid for 24 hours by default)
    cached = await get_cached_schema(manager, cache_duration_hours=24)
    
    if cached:
        return cached
    
    # If no cache, create one
    logger.info("No cached schema found, creating new cache...")
    result = await cache_schema_in_logger(force_refresh=True)
    
    # Retrieve the newly cached schema
    if result.get("success"):
        return await get_cached_schema(manager, cache_duration_hours=24)
    
    return {"error": "Failed to cache or retrieve schema"}


async def working_usage():
    """
    Demonstrate caching and retrieving database schema.
    
    AGENT: This is the stable, working example.
    """
    logger.info("=== Testing Schema Caching ===")
    
    if not IMPORTS_AVAILABLE:
        logger.error("Required imports not available")
        return False
    
    # Test 1: Cache the schema
    logger.info("\nTest 1: Caching database schema...")
    result = await cache_schema_in_logger(force_refresh=True)
    
    assert result.get("success"), "Schema caching should succeed"
    assert result.get("schema_doc_id"), "Should return schema document ID"
    logger.success(f"✓ Schema cached with ID: {result['schema_doc_id']}")
    
    # Test 2: Retrieve cached schema
    logger.info("\nTest 2: Retrieving cached schema...")
    cached = await retrieve_schema_for_agent()
    
    assert cached.get("from_cache"), "Should retrieve from cache"
    assert cached.get("collections"), "Should have collections info"
    logger.success(f"✓ Retrieved cached schema from {cached['cached_at']}")
    
    # Test 3: Verify schema content
    logger.info("\nTest 3: Verifying schema content...")
    assert "summary" in cached, "Should have summary"
    assert "agent_prompt" in cached, "Should have agent prompt"
    
    if cached.get("summary"):
        summary = cached["summary"]
        logger.info(f"  Total collections: {summary.get('total_collections', 0)}")
        logger.info(f"  Document collections: {summary.get('document_collections', 0)}")
        logger.info(f"  Edge collections: {summary.get('edge_collections', 0)}")
    
    logger.success("✓ Schema content verified")
    
    # Test 4: Quick access pattern
    logger.info("\nTest 4: Testing quick access pattern...")
    
    # This is how the natural language to AQL tool would use it
    schema_info = await retrieve_schema_for_agent()
    
    # Extract just what's needed for AQL generation
    collections = list(schema_info.get("collections", {}).keys())
    views = list(schema_info.get("views", {}).keys())
    
    logger.info(f"  Available collections: {collections[:5]}...")
    logger.info(f"  Available views: {views}")
    
    logger.success("✓ Quick access pattern works")
    
    logger.success("\n✅ All schema caching tests passed!")
    return True


async def debug_function():
    """
    Debug function for testing schema caching features.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    """
    logger.info("=== Debug Mode: Advanced Schema Caching ===")
    
    if not IMPORTS_AVAILABLE:
        logger.error("Required imports not available")
        return False
    
    manager = await get_log_manager()
    
    # Test 1: Query all cached schemas
    logger.info("Test 1: Finding all cached schemas...")
    
    aql = """
    FOR doc IN log_events
    FILTER doc.extra_data.category == "db_schema"
    SORT doc.timestamp DESC
    LIMIT 10
    RETURN {
        id: doc._id,
        cached_at: doc.timestamp,
        expires_at: doc.extra_data.cache_metadata.expires_at,
        collections_count: LENGTH(KEYS(doc.extra_data.collections)),
        size_bytes: LENGTH(TO_STRING(doc))
    }
    """
    
    cursor = await manager.db.aql.execute(aql)
    schemas = list(cursor)
    
    logger.info(f"Found {len(schemas)} cached schemas:")
    for schema in schemas:
        logger.info(f"  - {schema['id']}: {schema['collections_count']} collections, {schema['size_bytes']} bytes")
    
    # Test 2: Cache with custom metadata
    logger.info("\nTest 2: Caching with custom metadata...")
    
    # Get fresh schema
    schema_report = await inspect_logger_agent_schema()
    
    # Add custom analysis
    custom_doc = await manager.log_event(
        level="INFO",
        message="Schema analysis for natural language queries",
        script_name="cache_db_schema",
        execution_id=f"schema_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        extra_data={
            "category": "db_schema_analysis",
            "analysis_type": "nl_to_aql_optimization",
            "field_frequencies": analyze_field_frequencies(schema_report),
            "common_patterns": identify_common_patterns(schema_report),
            "query_hints": generate_query_hints(schema_report)
        },
        tags=["db_schema", "analysis", "nl_to_aql"]
    )
    
    logger.success(f"✓ Custom analysis stored: {custom_doc['_id']}")
    
    # Test 3: Schema evolution tracking
    logger.info("\nTest 3: Schema evolution tracking...")
    
    # Compare with previous schema
    evolution_aql = """
    // Get last two schemas
    FOR doc IN log_events
    FILTER doc.extra_data.category == "db_schema"
    SORT doc.timestamp DESC
    LIMIT 2
    RETURN doc.extra_data.summary
    """
    
    cursor = await manager.db.aql.execute(evolution_aql)
    summaries = list(cursor)
    
    if len(summaries) >= 2:
        current, previous = summaries[0], summaries[1]
        
        # Compare collection counts
        collections_diff = current.get("total_collections", 0) - previous.get("total_collections", 0)
        docs_diff = current.get("total_documents", 0) - previous.get("total_documents", 0)
        
        logger.info(f"  Collections change: {collections_diff:+d}")
        logger.info(f"  Documents change: {docs_diff:+d}")
    
    return True


def analyze_field_frequencies(schema_report: Dict[str, Any]) -> Dict[str, int]:
    """Analyze which fields appear most frequently across collections."""
    field_freq = {}
    
    for col_name, col_info in schema_report.get("collections", {}).items():
        for field in col_info.get("schema", {}).keys():
            base_field = field.split(".")[0]  # Get root field
            field_freq[base_field] = field_freq.get(base_field, 0) + 1
    
    return dict(sorted(field_freq.items(), key=lambda x: x[1], reverse=True)[:20])


def identify_common_patterns(schema_report: Dict[str, Any]) -> list:
    """Identify common patterns in the schema."""
    patterns = []
    
    # Check for timestamp fields
    collections = schema_report.get("collections", {})
    timestamp_collections = [
        name for name, info in collections.items()
        if "timestamp" in info.get("schema", {})
    ]
    
    if timestamp_collections:
        patterns.append({
            "pattern": "timestamp_filtering",
            "collections": timestamp_collections,
            "hint": "Use DATE_DIFF() for time-based queries"
        })
    
    # Check for error-related collections
    error_collections = [
        name for name in collections.keys()
        if "error" in name.lower() or "log" in name.lower()
    ]
    
    if error_collections:
        patterns.append({
            "pattern": "error_tracking",
            "collections": error_collections,
            "hint": "Filter by level, error_type for error analysis"
        })
    
    return patterns


def generate_query_hints(schema_report: Dict[str, Any]) -> Dict[str, str]:
    """Generate query hints based on schema structure."""
    hints = {}
    
    # Check for search views
    views = schema_report.get("views", {})
    for view_name, view_info in views.items():
        if "search" in view_name.lower():
            hints["text_search"] = f"Use {view_name} with BM25() for text search"
    
    # Check for graph structures
    if schema_report.get("graphs"):
        hints["graph_traversal"] = "Use FOR v, e, p IN traversal patterns"
    
    # Check for edge collections
    edge_collections = [
        name for name, info in schema_report.get("collections", {}).items()
        if info.get("type") == "edge"
    ]
    
    if edge_collections:
        hints["relationships"] = f"Traverse edges: {', '.join(edge_collections[:3])}"
    
    return hints


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    # Check if called with JSON arguments (from MCP server)
    if len(sys.argv) > 1 and sys.argv[1].startswith('{'):
        # Parse JSON arguments
        args = json.loads(sys.argv[1])
        
        async def run_cache():
            result = await cache_schema_in_logger(
                force_refresh=args.get("force_refresh", False),
                cache_duration_hours=args.get("cache_duration_hours", 24)
            )
            print(json.dumps(result, indent=2))
        
        asyncio.run(run_cache())
    else:
        # Original behavior
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        if mode == "debug":
            asyncio.run(debug_function())
        else:
            asyncio.run(working_usage())