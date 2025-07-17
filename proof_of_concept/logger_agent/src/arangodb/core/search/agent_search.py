#!/usr/bin/env python3
"""
agent_search.py - BM25 search and query capabilities for agent observability

Provides powerful search functionality across all agent activity using
ArangoDB's full-text search with BM25 scoring.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python agent_search.py          # Runs working_usage() - stable, known to work
  python agent_search.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import re
from pathlib import Path

from loguru import logger
from arango.database import StandardDatabase


class AgentSearch:
    """Advanced search capabilities for agent activity."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.view_name = "agent_activity_search"
    
    async def initialize_search_view(self):
        """Create or update the ArangoSearch view for agent activity."""
        
        def _init_view_sync():
            view_config = {
                "links": {
                    "log_events": {
                        "analyzers": ["text_en", "identity"],
                        "fields": {
                            "message": {"analyzers": ["text_en"]},
                            "extra_data.payload.tool_input.command": {"analyzers": ["text_en", "identity"]},
                            "extra_data.payload.result": {"analyzers": ["text_en"]},
                            "extra_data.summary": {"analyzers": ["text_en"]},
                            "script_name": {"analyzers": ["identity"]},
                            "execution_id": {"analyzers": ["identity"]},
                            "tags": {"analyzers": ["identity"]}
                        },
                        "includeAllFields": False,
                        "storeValues": "id",
                        "trackListPositions": False
                    },
                    "tool_executions": {
                        "analyzers": ["text_en", "identity"],
                        "fields": {
                            "command": {"analyzers": ["text_en", "identity"]},
                            "output_preview": {"analyzers": ["text_en"]},
                            "tool_name": {"analyzers": ["identity"]},
                            "session_id": {"analyzers": ["identity"]}
                        },
                        "includeAllFields": False,
                        "storeValues": "id"
                    },
                    "agent_insights": {
                        "analyzers": ["text_en"],
                        "fields": {
                            "content": {"analyzers": ["text_en"]},
                            "context.problem": {"analyzers": ["text_en"]},
                            "context.solution": {"analyzers": ["text_en"]},
                            "tags": {"analyzers": ["identity"]},
                            "session_id": {"analyzers": ["identity"]}
                        },
                        "includeAllFields": False,
                        "storeValues": "id"
                    },
                    "errors_and_failures": {
                        "analyzers": ["text_en", "identity"],
                        "fields": {
                            "message": {"analyzers": ["text_en"]},
                            "error_type": {"analyzers": ["identity"]},
                            "resolution": {"analyzers": ["text_en"]},
                            "stack_trace": {"analyzers": ["text_en"]},
                            "session_id": {"analyzers": ["identity"]}
                        },
                        "includeAllFields": False,
                        "storeValues": "id"
                    },
                    "code_artifacts": {
                        "analyzers": ["identity"],
                        "fields": {
                            "file_path": {"analyzers": ["identity"]},
                            "language": {"analyzers": ["identity"]},
                            "operation": {"analyzers": ["identity"]},
                            "session_id": {"analyzers": ["identity"]}
                        },
                        "includeAllFields": False,
                        "storeValues": "id"
                    }
                }
            }
            
            # Check if view exists
            existing_views = [v['name'] for v in self.db.views()]
            
            if self.view_name not in existing_views:
                # Create new view
                self.db.create_arangosearch_view(self.view_name, properties=view_config)
                logger.info(f"Created search view: {self.view_name}")
            else:
                # Update existing view
                # Note: ArangoDB doesn't support direct view updates, so we might need to recreate
                logger.info(f"Search view already exists: {self.view_name}")
        
        await asyncio.to_thread(_init_view_sync)
        
        # Wait for the view to be ready for indexing
        logger.info(f"Waiting for view {self.view_name} to be ready...")
        await asyncio.sleep(2.0)
    
    async def search_agent_activity(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by_relevance: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search across all agent activity using BM25 scoring.
        
        Args:
            query: Search query string
            filters: Optional filters (source_apps, session_ids, event_types, time_range)
            limit: Maximum results to return
            offset: Pagination offset
            sort_by_relevance: Sort by BM25 score (True) or timestamp (False)
        
        Returns:
            List of search results with documents and scores
        """
        
        def _search_sync():
            # Build filter clause
            filter_conditions = self._build_filter_conditions(filters)
            
            # Build search clause based on query complexity
            search_clause = self._build_search_clause(query)
            
            # Construct AQL query
            aql = f"""
            FOR doc IN {self.view_name}
            SEARCH {search_clause}
            {filter_conditions}
            LET score = BM25(doc)
            LET doc_type = REGEX_TEST(doc._id, '^log_events/') ? 'log' :
                          REGEX_TEST(doc._id, '^tool_executions/') ? 'tool' :
                          REGEX_TEST(doc._id, '^agent_insights/') ? 'insight' :
                          REGEX_TEST(doc._id, '^errors_and_failures/') ? 'error' :
                          REGEX_TEST(doc._id, '^code_artifacts/') ? 'artifact' : 'unknown'
            {"SORT score DESC" if sort_by_relevance else "SORT doc.timestamp DESC"}
            LIMIT @offset, @limit
            RETURN {{
                doc: doc,
                score: score,
                type: doc_type,
                highlights: {{
                    message: doc.message ? SUBSTRING(doc.message, 0, 200) : null,
                    command: doc.command ? SUBSTRING(doc.command, 0, 200) : null,
                    content: doc.content ? SUBSTRING(doc.content, 0, 200) : null
                }}
            }}
            """
            
            bind_vars = {
                "query": query,
                "limit": limit,
                "offset": offset
            }
            
            # Add filter bind variables
            if filters:
                bind_vars.update(self._get_filter_bind_vars(filters))
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        
        return await asyncio.to_thread(_search_sync)
    
    async def search_errors_with_resolutions(
        self,
        error_pattern: str = None,
        error_type: str = None,
        time_range: Dict[str, str] = None,
        include_unresolved: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for errors and their resolutions using graph traversal.
        """
        
        def _search_errors_sync():
            # Build error filters
            error_filters = []
            bind_vars = {}
            
            if error_pattern:
                error_filters.append(
                    "ANALYZER(doc.message IN TOKENS(@pattern, 'text_en'), 'text_en')"
                )
                bind_vars["pattern"] = error_pattern
            
            if error_type:
                error_filters.append("doc.error_type == @error_type")
                bind_vars["error_type"] = error_type
            
            if time_range:
                if "start" in time_range:
                    error_filters.append("doc.timestamp >= @start_time")
                    bind_vars["start_time"] = time_range["start"]
                if "end" in time_range:
                    error_filters.append("doc.timestamp <= @end_time")
                    bind_vars["end_time"] = time_range["end"]
            
            if not include_unresolved:
                error_filters.append("doc.resolved == true")
            
            filter_clause = f"FILTER {' AND '.join(error_filters)}" if error_filters else ""
            
            # Query with graph traversal for resolutions
            aql = f"""
            FOR doc IN errors_and_failures
            {filter_clause}
            LET resolutions = (
                FOR v, e, p IN 1..3 OUTBOUND doc error_causality
                FILTER e.relationship IN ['FIXED_BY', 'RESOLVED_BY', 'TRIGGERED']
                RETURN {{
                    vertex: v,
                    edge: e,
                    path_length: LENGTH(p.edges),
                    vertex_type: SPLIT(v._id, '/')[0]
                }}
            )
            LET insights = (
                FOR insight IN resolutions
                FILTER insight.vertex_type == 'agent_insights'
                RETURN insight.vertex
            )
            SORT doc.timestamp DESC
            RETURN {{
                error: doc,
                resolutions: resolutions,
                insights: insights,
                resolution_count: LENGTH(resolutions),
                has_fix: LENGTH(resolutions) > 0,
                time_to_fix: doc.resolved ? 
                    DATE_DIFF(doc.timestamp, doc.resolution_time, 's') : null
            }}
            """
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        
        return await asyncio.to_thread(_search_errors_sync)
    
    async def find_similar_executions(
        self,
        tool_name: str,
        command_pattern: str,
        session_id: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar tool executions based on command patterns.
        """
        
        def _find_similar_sync():
            # Build query for similar executions
            aql = """
            FOR doc IN tool_executions
            FILTER doc.tool_name == @tool_name
            FILTER CONTAINS(LOWER(doc.command), LOWER(@pattern))
            FILTER doc.session_id != @current_session
            LET similarity_score = (
                LENGTH(@pattern) / LENGTH(doc.command) + 
                (doc.exit_code == 0 ? 0.2 : 0)
            )
            SORT similarity_score DESC, doc.start_time DESC
            LIMIT @limit
            RETURN {
                execution: doc,
                similarity: similarity_score,
                success: doc.exit_code == 0,
                duration_ms: doc.duration_ms,
                session_id: doc.session_id
            }
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={
                    "tool_name": tool_name,
                    "pattern": command_pattern,
                    "current_session": session_id or "none",
                    "limit": limit
                }
            )
            return list(cursor)
        
        return await asyncio.to_thread(_find_similar_sync)
    
    async def get_insights_for_context(
        self,
        context: Dict[str, Any],
        tags: List[str] = None,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find relevant insights based on context and tags.
        """
        
        def _get_insights_sync():
            # Build context search
            context_conditions = []
            bind_vars = {"min_confidence": min_confidence}
            
            if "error_type" in context:
                context_conditions.append(
                    "CONTAINS(LOWER(doc.content), LOWER(@error_type))"
                )
                bind_vars["error_type"] = context["error_type"]
            
            if "tool_name" in context:
                context_conditions.append(
                    "CONTAINS(LOWER(doc.content), LOWER(@tool_name))"
                )
                bind_vars["tool_name"] = context["tool_name"]
            
            if tags:
                context_conditions.append("doc.tags ANY IN @tags")
                bind_vars["tags"] = tags
            
            filter_clause = f"FILTER {' OR '.join(context_conditions)}" if context_conditions else ""
            
            aql = f"""
            FOR doc IN agent_insights
            {filter_clause}
            FILTER doc.confidence >= @min_confidence
            LET applications = (
                FOR v, e IN 1..1 OUTBOUND doc insight_applications
                RETURN v._id
            )
            SORT doc.confidence DESC, doc.timestamp DESC
            LIMIT 20
            RETURN {{
                insight: doc,
                relevance_score: doc.confidence,
                applied_count: LENGTH(applications),
                applications: SLICE(applications, 0, 3)
            }}
            """
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        
        return await asyncio.to_thread(_get_insights_sync)
    
    async def get_filtered_events(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get events with filters but without text search.
        """
        
        def _get_filtered_sync():
            # Build filter conditions
            conditions = []
            bind_vars = {"limit": limit, "offset": offset}
            
            # Always filter for claude-hook events
            conditions.append("'claude-hook' IN doc.tags")
            
            if filters.get("source_apps"):
                conditions.append("doc.script_name IN @source_apps")
                bind_vars["source_apps"] = filters["source_apps"]
            
            if filters.get("session_ids"):
                conditions.append("doc.execution_id IN @session_ids")
                bind_vars["session_ids"] = filters["session_ids"]
            
            if filters.get("event_types"):
                conditions.append("doc.extra_data.hook_event_type IN @event_types")
                bind_vars["event_types"] = filters["event_types"]
            
            if filters.get("time_range"):
                time_range = filters["time_range"]
                if isinstance(time_range, dict):
                    if "start" in time_range:
                        conditions.append("doc.timestamp >= @start_time")
                        bind_vars["start_time"] = time_range["start"]
                    if "end" in time_range:
                        conditions.append("doc.timestamp <= @end_time")
                        bind_vars["end_time"] = time_range["end"]
                elif isinstance(time_range, str):
                    # Handle relative time like "1h", "24h", "7d"
                    delta = self._parse_time_range(time_range)
                    if delta:
                        start_time = (datetime.utcnow() - delta).isoformat()
                        conditions.append("doc.timestamp >= @start_time")
                        bind_vars["start_time"] = start_time
            
            where_clause = f"FILTER {' AND '.join(conditions)}" if conditions else ""
            
            aql = f"""
            FOR doc IN log_events
            {where_clause}
            SORT doc.timestamp DESC
            LIMIT @offset, @limit
            RETURN {{
                doc: doc,
                score: 1.0,
                type: 'log'
            }}
            """
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        
        return await asyncio.to_thread(_get_filtered_sync)
    
    async def find_error_patterns(
        self,
        time_range: str = "24h",
        min_occurrences: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find common error patterns and their resolutions.
        """
        
        def _find_patterns_sync():
            # Calculate time boundary
            delta = self._parse_time_range(time_range)
            start_time = (datetime.utcnow() - delta).isoformat() if delta else None
            
            aql = """
            FOR error IN errors_and_failures
            FILTER error.timestamp >= @start_time
            COLLECT error_type = error.error_type, 
                    error_pattern = REGEX_REPLACE(error.message, "[0-9]+", "N")
            WITH COUNT INTO occurrences
            FILTER occurrences >= @min_occurrences
            
            LET sample_errors = (
                FOR e IN errors_and_failures
                FILTER e.error_type == error_type
                FILTER REGEX_REPLACE(e.message, "[0-9]+", "N") == error_pattern
                SORT e.timestamp DESC
                LIMIT 3
                RETURN e
            )
            
            LET resolutions = (
                FOR error IN sample_errors
                FOR v, e IN 1..2 OUTBOUND error error_causality
                FILTER e.relationship IN ['FIXED_BY', 'RESOLVED_BY']
                RETURN DISTINCT {
                    type: SPLIT(v._id, '/')[0],
                    description: v.content OR v.command OR v.message,
                    success: e.resolution_status == 'success'
                }
            )
            
            LET success_rate = (
                LENGTH(FOR r IN resolutions FILTER r.success == true RETURN r) / 
                LENGTH(resolutions) * 100
            )
            
            SORT occurrences DESC
            RETURN {
                error_type: error_type,
                pattern: error_pattern,
                count: occurrences,
                sample_messages: sample_errors[*].message,
                resolutions: resolutions,
                success_rate: success_rate || 0,
                avg_fix_time: AVG(sample_errors[*].time_to_fix)
            }
            """
            
            bind_vars = {
                "start_time": start_time,
                "min_occurrences": min_occurrences
            }
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        
        return await asyncio.to_thread(_find_patterns_sync)
    
    # Helper methods
    def _build_search_clause(self, query: str) -> str:
        """Build ArangoSearch clause based on query complexity."""
        # Check if query contains special operators
        if any(op in query for op in ['AND', 'OR', 'NOT', '"']):
            # Advanced query - needs to be handled differently
            # For now, just extract the words and search for all of them
            # Remove operators and quotes
            clean_query = query.replace(' AND ', ' ').replace(' OR ', ' ').replace(' NOT ', ' ').replace('"', '')
            return f"""(
                ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.command IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.content IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.output_preview IN TOKENS(@query, 'text_en'), 'text_en')
            )"""
        else:
            # Simple query - search in multiple fields using TOKENS
            # This matches the reference implementation from bm25_search.py
            return f"""(
                ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.command IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.content IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.output_preview IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.error IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.stack_trace IN TOKENS(@query, 'text_en'), 'text_en') OR
                ANALYZER(doc.resolution IN TOKENS(@query, 'text_en'), 'text_en') OR
                PHRASE(doc.file_path, @query, 'identity')
            )"""
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> str:
        """Build filter conditions for AQL query."""
        if not filters:
            return ""
        
        conditions = []
        
        if filters.get("source_apps"):
            conditions.append("doc.script_name IN @source_apps")
        
        if filters.get("session_ids"):
            conditions.append("(doc.execution_id IN @session_ids OR doc.session_id IN @session_ids)")
        
        if filters.get("event_types"):
            conditions.append("doc.extra_data.hook_event_type IN @event_types")
        
        if filters.get("time_range"):
            # Handle both dict and string time ranges
            time_range = filters["time_range"]
            if isinstance(time_range, dict):
                if "start" in time_range:
                    conditions.append("doc.timestamp >= @start_time")
                if "end" in time_range:
                    conditions.append("doc.timestamp <= @end_time")
        
        return f"FILTER {' AND '.join(conditions)}" if conditions else ""
    
    def _get_filter_bind_vars(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract bind variables from filters."""
        bind_vars = {}
        
        if filters.get("source_apps"):
            bind_vars["source_apps"] = filters["source_apps"]
        
        if filters.get("session_ids"):
            bind_vars["session_ids"] = filters["session_ids"]
        
        if filters.get("event_types"):
            bind_vars["event_types"] = filters["event_types"]
        
        if filters.get("time_range"):
            time_range = filters["time_range"]
            if isinstance(time_range, dict):
                if "start" in time_range:
                    bind_vars["start_time"] = time_range["start"]
                if "end" in time_range:
                    bind_vars["end_time"] = time_range["end"]
        
        return bind_vars
    
    def _parse_time_range(self, time_range_str: str) -> Optional[timedelta]:
        """Parse time range string like '1h', '24h', '7d' to timedelta."""
        match = re.match(r'^(\d+)([hdwm])$', time_range_str)
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        elif unit == 'm':
            return timedelta(days=value * 30)  # Approximate
        
        return None


async def _insert_test_data(test_db):
    """Insert test data for search testing."""
    from datetime import datetime, timedelta
    import time
    
    # Insert test log events
    log_events = test_db.collection('log_events')
    
    test_events = [
        {
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "level": "ERROR" if i % 3 == 0 else "INFO",
            "message": f"Test error message {i}" if i % 3 == 0 else f"Normal operation {i}",
            "execution_id": f"test_exec_{i // 2}",
            "script_name": "test_script",
            "tags": ["claude-hook", "test"],
            "extra_data": {
                "hook_event_type": "PostToolUse" if i % 2 == 0 else "PreToolUse",
                "payload": {
                    "tool_name": "Bash" if i % 3 == 0 else "Python",
                    "error": "Command failed" if i % 3 == 0 else None,
                    "tool_input": {
                        "command": f"test command {i}"
                    },
                    "result": f"Result for test {i}" if i % 2 == 0 else None
                },
                "summary": f"Summary for event {i}"
            }
        }
        for i in range(10)
    ]
    
    log_events.insert_many(test_events)
    
    # Insert test insights
    insights = test_db.collection('agent_insights')
    test_insights = [
        {
            "content": "Always use pytest for Python testing",
            "confidence": 0.9,
            "tags": ["python", "testing"],
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "test_session_1",
            "context": {
                "problem": "Testing Python code",
                "solution": "Use pytest framework"
            }
        },
        {
            "content": "Use -v flag for verbose output",
            "confidence": 0.8,
            "tags": ["bash", "debugging"],
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "test_session_2",
            "context": {
                "problem": "Debugging bash scripts",
                "solution": "Add verbose flags"
            }
        }
    ]
    insights.insert_many(test_insights)
    
    # Insert test errors
    errors = test_db.collection('errors_and_failures')
    test_errors = [
        {
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "message": f"Test error message {i}",
            "error_type": "TestError" if i % 2 == 0 else "RuntimeError",
            "stack_trace": f"Stack trace for error {i}",
            "session_id": f"test_session_{i}",
            "resolved": i % 3 == 0,
            "resolution": f"Fixed by solution {i}" if i % 3 == 0 else None,
            "resolution_time": datetime.utcnow().isoformat() if i % 3 == 0 else None
        }
        for i in range(5)
    ]
    errors.insert_many(test_errors)
    
    # Wait a bit for the view to catch up with the inserts
    await asyncio.sleep(0.5)


async def working_usage():
    """Demonstrate search functionality with test database."""
    logger.info("=== Testing Agent Search ===")
    
    # Import test utilities
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from utils.test_utils import with_test_db
    
    @with_test_db
    async def test_search(test_db, test_db_name, manager):
        logger.info(f"Testing with database: {test_db_name}")
        
        search = AgentSearch(test_db)
        await search.initialize_search_view()
        
        # Insert test data
        await _insert_test_data(test_db)
        
        # Wait for view to index the data
        logger.info("Waiting for search view to index data...")
        await asyncio.sleep(2.0)
        
        # Test 1: Basic text search
        logger.info("\nTest 1: Basic text search for 'error'")
        results = await search.search_agent_activity("error", limit=5)
        logger.info(f"Found {len(results)} results")
        for result in results[:3]:
            logger.info(f"  Score: {result['score']:.2f}, Type: {result['type']}")
        
        # Test 2: Search with filters
        logger.info("\nTest 2: Search with filters")
        results = await search.search_agent_activity(
            "test",
            filters={
                "event_types": ["PreToolUse", "PostToolUse"],
                "time_range": "24h"
            },
            limit=5
        )
        logger.info(f"Found {len(results)} filtered results")
        
        # Test 3: Find error patterns
        logger.info("\nTest 3: Finding error patterns")
        patterns = await search.find_error_patterns(time_range="7d", min_occurrences=1)
        logger.info(f"Found {len(patterns)} error patterns")
        for pattern in patterns[:2]:
            logger.info(f"  Pattern: {pattern.get('error_type', 'Unknown')} ({pattern.get('count', 0)} occurrences)")
        
        # Test 4: Get insights
        logger.info("\nTest 4: Getting relevant insights")
        insights = await search.get_insights_for_context(
            {"tool_name": "python"},
            min_confidence=0.5
        )
        logger.info(f"Found {len(insights)} relevant insights")
        
        return True
    
    # Execute the test
    return await test_search()


async def debug_function():
    """Debug advanced search queries with test database."""
    logger.info("=== Debug Mode: Advanced Search ===")
    
    # Import test utilities
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from utils.test_utils import with_test_db
    
    @with_test_db
    async def test_advanced_search(test_db, test_db_name, manager):
        logger.info(f"Testing advanced search with database: {test_db_name}")
        
        search = AgentSearch(test_db)
        await search.initialize_search_view()
        
        # Insert test data
        await _insert_test_data(test_db)
        
        # Test complex boolean search
        logger.info("Test 1: Boolean search")
        results = await search.search_agent_activity(
            'error AND "test" NOT warning',
            limit=10
        )
        logger.info(f"Boolean search found {len(results)} results")
        
        # Test similarity search
        logger.info("\nTest 2: Find similar executions")
        similar = await search.find_similar_executions(
            tool_name="Bash",
            command_pattern="test",
            limit=5
        )
        logger.info(f"Found {len(similar)} similar executions")
        
        # Test performance
        logger.info("\nTest 3: Search performance")
        import time
        start = time.time()
        
        # Run multiple searches
        for query in ["error", "test", "python", "bash"]:
            results = await search.search_agent_activity(query, limit=10)
            logger.info(f"  Query '{query}': {len(results)} results")
        
        elapsed = time.time() - start
        logger.info(f"Total search time: {elapsed:.2f}s")
        
        return True
    
    # Execute the test
    return await test_advanced_search()

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