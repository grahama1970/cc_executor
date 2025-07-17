#!/usr/bin/env python3
"""
agent_log_manager.py - Unified API for agent logging and introspection

Provides a singleton interface for agents to log, query, and analyze
their execution history using ArangoDB backend.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python agent_log_manager_old.py          # Runs working_usage() - stable, known to work
  python agent_log_manager_old.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import uuid
import os 
import socket 
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

from arango import ArangoClient
from loguru import logger
# numpy is imported but not used directly in the provided snippet's logic, keeping it for compatibility if other parts of the project use it.
import numpy as np 
from tenacity import retry, stop_after_attempt, wait_exponential

# Import from existing modules
from arangodb.core.search.hybrid_search import HybridSearch
from arangodb.core.graph.relationship_extraction import RelationshipExtractor
from arangodb.core.memory.memory_agent import MemoryAgent
from utils.log_utils import truncate_large_value 


class AgentLogManager:
    """Singleton manager for agent logging operations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.db = None
            self.client = None
            self.execution_context = {}
            self.current_execution_id = None
            
            # Integration modules
            self.hybrid_search = None
            self.relationship_extractor = None
            self.memory_agent = None
            
            self._initialized = True
    
    async def initialize(self, db_config: Dict[str, str]) -> None:
        """Initialize database connection and integration modules."""
        try:
            def _connect_sync():
                client = ArangoClient(hosts=db_config["url"])
                db = client.db(
                    db_config["database"],
                    username=db_config["username"],
                    password=db_config["password"]
                )
                return client, db
            
            self.client, self.db = await asyncio.to_thread(_connect_sync)
            
            # Initialize integration modules
            self.hybrid_search = HybridSearch(self.db)
            self.relationship_extractor = RelationshipExtractor(self.db)
            self.memory_agent = MemoryAgent(self.db)
            
            logger.info("AgentLogManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentLogManager: {e}")
            raise
    
    def generate_execution_id(self, script_name: str) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{script_name}_{timestamp}_{unique_id}"
    
    @asynccontextmanager
    async def script_execution(self, script_name: str, metadata: Optional[Dict] = None):
        """
        Context manager for script execution tracking.
        Yields a Loguru logger instance with `execution_id` and `script_name` bound.
        """
        execution_id = self.generate_execution_id(script_name)
        self.current_execution_id = execution_id
        
        # Start script run
        await self.start_run(script_name, execution_id, metadata)
        
        try:
            # Bind execution context to logger (using an existing loguru feature)
            logger_with_context = logger.bind(
                execution_id=execution_id,
                script_name=script_name
            )
            
            yield logger_with_context
            
            # Mark as successful
            await self.end_run(execution_id, "success")
            
        except Exception as e:
            # Mark as failed
            logger.error(f"Script {script_name} failed with error: {e}", 
                         execution_id=execution_id, script_name=script_name)
            await self.end_run(execution_id, "failed", str(e))
            raise
        
        finally:
            self.current_execution_id = None
    
    async def start_run(
        self,
        script_name: str,
        execution_id: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record script execution start."""
        doc = {
            "execution_id": execution_id,
            "script_name": script_name,
            "start_time": datetime.utcnow().isoformat(),
            "status": "running",
            "metadata": metadata or {},
            "pid": os.getpid(),
            "hostname": socket.gethostname()
        }
        
        try:
            await asyncio.to_thread(
                self.db.collection("script_runs").insert,
                doc
            )
            logger.info(f"Started script run: {execution_id}")
        except Exception as e:
            logger.error(f"Failed to record script start: {e}")
    
    async def end_run(
        self,
        execution_id: str,
        status: str = "success",
        error: Optional[str] = None
    ) -> None:
        """Record script execution end."""
        update_doc = {
            "end_time": datetime.utcnow().isoformat(),
            "status": status,
            "duration_seconds": None  # Will calculate from start_time
        }
        
        if error:
            update_doc["error"] = truncate_large_value(error, max_str_len=1000)
        
        try:
            # Get start time to calculate duration (synchronous operation)
            # Use AQL to get the document instead
            get_aql = """
            FOR doc IN script_runs
            FILTER doc.execution_id == @execution_id
            LIMIT 1
            RETURN doc
            """
            result = await self.query_logs(get_aql, {"execution_id": execution_id})
            run_doc = result[0] if result else None
            
            if run_doc:
                start_time = datetime.fromisoformat(run_doc["start_time"])
                end_time = datetime.fromisoformat(update_doc["end_time"])
                update_doc["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Update the document using AQL
            update_aql = """
            FOR doc IN script_runs
            FILTER doc.execution_id == @execution_id
            UPDATE doc WITH @update IN script_runs
            RETURN NEW
            """
            await self.query_logs(update_aql, {
                "execution_id": execution_id,
                "update": update_doc
            })
            logger.info(f"Ended script run: {execution_id} ({status})")
            
        except Exception as e:
            logger.error(f"Failed to record script end: {e}")
    
    async def query_logs(
        self,
        aql_query: str,
        bind_vars: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute custom AQL query on logs."""
        try:
            def _execute_query():
                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars=bind_vars or {},
                    batch_size=100
                )
                # Consume cursor in sync context
                return list(cursor)
            
            results = await asyncio.to_thread(_execute_query)
            return results
            
        except Exception as e:
            logger.error(f"AQL query failed: {e}")
            raise
    
    async def search_logs(
        self,
        query: str,
        execution_id: Optional[str] = None,
        level: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search logs with multiple filters."""
        # Build AQL query
        filters = []
        bind_vars = {"query": query, "limit": limit}
        
        if execution_id:
            filters.append("doc.execution_id == @execution_id")
            bind_vars["execution_id"] = execution_id
        
        if level:
            filters.append("doc.level == @level")
            bind_vars["level"] = level
        
        if time_range:
            if "start" in time_range:
                filters.append("doc.timestamp >= @start_time")
                bind_vars["start_time"] = time_range["start"].isoformat()
            if "end" in time_range:
                filters.append("doc.timestamp <= @end_time")
                bind_vars["end_time"] = time_range["end"].isoformat()
        
        where_clause = " AND ".join(filters) if filters else "true"
        
        # Use simple AQL search, if hybrid_search is to be used, it would be called here.
        # For this search_logs, it's a basic AQL with ArangoSearch view.
        aql = f"""
        FOR doc IN log_events_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        FILTER {where_clause}
        SORT BM25(doc) DESC, doc.timestamp DESC
        LIMIT @limit
        RETURN doc
        """
        
        return await self.query_logs(aql, bind_vars)
    
    async def search_bm25_logs(
        self,
        text_query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Full-text search using BM25 relevance."""
        # Use hybrid search module for advanced search
        if self.hybrid_search:
            results = await self.hybrid_search.search(
                query=text_query,
                search_type="bm25",
                collection="log_events",
                limit=limit,
                filters=filters
            )
            return results
        
        # Fallback to basic search if hybrid_search is not initialized/available
        return await self.search_logs(text_query, limit=limit)
    
    async def get_latest_response(
        self,
        script_name: str,
        execution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest structured response from a script."""
        bind_vars = {"script_name": script_name}
        
        if execution_id:
            bind_vars["execution_id"] = execution_id
            filter_clause = "doc.execution_id == @execution_id"
        else:
            filter_clause = "doc.script_name == @script_name"
        
        aql = f"""
        FOR doc IN log_events
        FILTER {filter_clause} AND doc.extra_data.response != null
        SORT doc.timestamp DESC
        LIMIT 1
        RETURN doc.extra_data.response
        """
        
        results = await self.query_logs(aql, bind_vars)
        return results[0] if results else None
    
    async def log_agent_learning(
        self,
        message: str,
        function_name: str,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8
    ) -> None:
        """Record an agent learning or insight."""
        doc = {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": self.current_execution_id or "manual",
            "learning": message,
            "function_name": function_name,
            "context": context or {},
            "confidence": confidence
        }
        
        try:
            await self.db.collection("agent_learnings").insert(doc)
            logger.info(f"Recorded agent learning: {message[:100]}...")
            
            # Also log to memory agent if available
            if self.memory_agent:
                await self.memory_agent.add_memory(
                    content=message,
                    memory_type="learning",
                    metadata={
                        "function": function_name,
                        "confidence": confidence,
                        **(context or {}) 
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to record agent learning: {e}")
    
    async def build_execution_graph(
        self,
        execution_id: str,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Build a graph representation of an execution."""
        # Get all logs for execution
        logs_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        SORT doc.timestamp
        RETURN doc
        """
        
        logs = await self.query_logs(logs_aql, {"execution_id": execution_id})
        
        # Build graph structure
        graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "execution_id": execution_id,
                "total_logs": len(logs)
            }
        }
        
        # Create nodes
        for i, log in enumerate(logs):
            node = {
                "id": log.get("_id", f"log_{i}"), 
                "label": f"{log['level']}: {log['message'][:50]}...",
                "timestamp": log["timestamp"],
                "level": log["level"],
                "function": log.get("function_name", "unknown")
            }
            graph["nodes"].append(node)
        
        # Extract relationships if requested
        if include_relationships and self.relationship_extractor:
            # Analyze log messages for relationships
            for i, log in enumerate(logs[:-1]):
                # Simple temporal relationship
                edge = {
                    "from": log.get("_id", f"log_{i}"),
                    "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                    "type": "FOLLOWED_BY",
                    "weight": 1.0
                }
                graph["edges"].append(edge)
                
                # Extract semantic relationships using relationship extractor
                rels_from_extractor = await self.relationship_extractor.extract_relationships(
                    log["message"],
                    logs[i + 1]["message"]
                )
                for rel in rels_from_extractor:
                    graph["edges"].append({
                        "from": log.get("_id", f"log_{i}"),
                        "to": logs[i + 1].get("_id", f"log_{i + 1}"),
                        "type": rel["type"],
                        "confidence": rel["confidence"]
                    })
        
        return graph
    
    async def prune_logs(
        self,
        older_than_days: Optional[int] = None,
        execution_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Prune old logs based on criteria."""
        stats = {"examined": 0, "deleted": 0}
        
        # Build filter conditions
        filters = []
        bind_vars = {}
        
        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            filters.append("doc.timestamp < @cutoff_date")
            bind_vars["cutoff_date"] = cutoff_date.isoformat()
        
        if execution_ids:
            filters.append("doc.execution_id IN @execution_ids")
            bind_vars["execution_ids"] = execution_ids
        
        if not filters:
            logger.warning("No pruning criteria specified")
            return stats
        
        where_clause = " AND ".join(filters)
        
        # Count matching documents
        count_aql = f"""
        FOR doc IN log_events
        FILTER {where_clause}
        COLLECT WITH COUNT INTO total
        RETURN total
        """
        
        count_result = await self.query_logs(count_aql, bind_vars)
        stats["examined"] = count_result[0] if count_result else 0
        
        if not dry_run and stats["examined"] > 0:
            # Delete matching documents
            delete_aql = f"""
            FOR doc IN log_events
            FILTER {where_clause}
            REMOVE doc IN log_events
            RETURN OLD
            """
            
            deleted = await self.query_logs(delete_aql, bind_vars)
            stats["deleted"] = len(deleted)
            
            logger.info(f"Pruned {stats['deleted']} logs")
        
        return stats
    
    async def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a script execution."""
        # Get run info
        run_aql = """
        FOR doc IN script_runs
        FILTER doc.execution_id == @execution_id
        RETURN doc
        """
        
        run_info = await self.query_logs(run_aql, {"execution_id": execution_id})
        
        if not run_info:
            return {"error": "Execution not found"}
        
        # Get log statistics
        stats_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id
        COLLECT level = doc.level WITH COUNT INTO count
        RETURN {level: level, count: count}
        """
        
        log_stats = await self.query_logs(stats_aql, {"execution_id": execution_id})
        
        # Get errors if any
        errors_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @execution_id AND doc.level IN ["ERROR", "CRITICAL"]
        SORT doc.timestamp
        LIMIT 10
        RETURN {
            timestamp: doc.timestamp,
            message: doc.message,
            function: doc.function_name
        }
        """
        
        errors = await self.query_logs(errors_aql, {"execution_id": execution_id})
        
        # Get learnings
        learnings_aql = """
        FOR doc IN agent_learnings
        FILTER doc.execution_id == @execution_id
        RETURN {
            learning: doc.learning,
            confidence: doc.confidence,
            function: doc.function_name
        }
        """
        
        learnings = await self.query_logs(learnings_aql, {"execution_id": execution_id})
        
        summary = {
            "execution_id": execution_id,
            "run_info": run_info[0],
            "log_statistics": {stat["level"]: stat["count"] for stat in log_stats},
            "errors": errors,
            "learnings": learnings,
            "total_logs": sum(stat["count"] for stat in log_stats) if log_stats else 0
        }
        
        return summary


# Global instance getter
_manager_instance: Optional[AgentLogManager] = None


async def get_log_manager() -> AgentLogManager:
    """Get or create the global AgentLogManager instance."""
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = AgentLogManager()
        
        db_config = {
            "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
            "database": os.getenv("ARANGO_DATABASE", "script_logs"),
            "username": os.getenv("ARANGO_USERNAME", "root"),
            "password": os.getenv("ARANGO_PASSWORD", "openSesame")
        }
        
        await _manager_instance.initialize(db_config)
    
    return _manager_instance


async def working_usage():
    """Demonstrate AgentLogManager functionality."""
    logger.info("=== Testing AgentLogManager ===")
    
    manager = await get_log_manager()
    
    # Test 1: Script execution context
    # Note: The yield from script_execution is now the bound logger
    async with manager.script_execution("test_script", {"version": "1.0"}) as logger_ctx: 
        logger_ctx.info("Starting test operations")
        
        # Log some events
        logger_ctx.debug("Debug message")
        logger_ctx.info("Processing data")
        logger_ctx.warning("Resource usage high")
        
        # Log a learning
        await manager.log_agent_learning(
            "Discovered that batch size of 100 is optimal for this dataset",
            "process_data",
            {"batch_size": 100, "performance": "optimal"}
        )
        
        # Simulate some work
        await asyncio.sleep(1)
        
        logger_ctx.success("Operations completed")
    
    # Retrieve the execution_id from the manager after context exits
    # For a real scenario, you'd capture it when entering the context.
    # For this test, we'll get it from recent runs.
    recent_runs = await manager.query_logs(
        "FOR r IN script_runs SORT r.start_time DESC LIMIT 1 RETURN r"
    )
    exec_id = recent_runs[0]["execution_id"] if recent_runs else "unknown"


    # Test 2: Query logs
    logger.info(f"\nQuerying recent logs for execution: {exec_id}...")
    recent_logs = await manager.search_logs(
        "test",
        execution_id=exec_id,
        limit=5
    )
    logger.info(f"Found {len(recent_logs)} recent logs")
    
    # Test 3: Get execution summary
    logger.info(f"\nGetting execution summary for {exec_id}...")
    summary = await manager.get_execution_summary(exec_id)
    logger.info(f"Summary: {json.dumps(summary, indent=2)}")
    
    return True


async def debug_function():
    """Debug advanced features of AgentLogManager."""
    logger.info("=== Debug Mode: Advanced Features ===")
    
    manager = await get_log_manager()
    
    # Test 1: Complex AQL query
    logger.info("Test 1: Complex AQL query")
    aql = """
    FOR doc IN log_events
    FILTER doc.level IN ["ERROR", "CRITICAL"]
    COLLECT level = doc.level INTO logs
    RETURN {
        level: level,
        count: LENGTH(logs),
        recent: (
            FOR log IN logs
            SORT log.doc.timestamp DESC
            LIMIT 3
            RETURN log.doc.message
        )
    }
    """
    
    results = await manager.query_logs(aql)
    logger.info(f"Error summary: {results}")
    
    # Test 2: Build execution graph
    logger.info("\nTest 2: Building execution graph")
    
    # Create a test execution with related logs
    async with manager.script_execution("graph_test") as logger_ctx:
        logger_ctx.info("Step 1: Initialize")
        logger_ctx.info("Step 2: Load data")
        logger_ctx.error("Step 3: Connection failed")
        logger_ctx.info("Step 4: Retrying connection")
        logger_ctx.success("Step 5: Connection restored")
        
        await asyncio.sleep(1)

    recent_runs = await manager.query_logs(
        "FOR r IN script_runs SORT r.start_time DESC LIMIT 1 RETURN r"
    )
    exec_id_graph = recent_runs[0]["execution_id"] if recent_runs else "unknown"

    graph = await manager.build_execution_graph(exec_id_graph)
    logger.info(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    
    # Test 3: Prune logs (dry run)
    logger.info("\nTest 3: Pruning old logs (dry run)")
    prune_stats = await manager.prune_logs(
        older_than_days=30,
        dry_run=True
    )
    logger.info(f"Would prune: {prune_stats}")
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    import os
    import socket 
    from dotenv import load_dotenv
    from utils.test_db_utils import setup_test_database, teardown_test_database
    
    load_dotenv()
    
    # Configure logger with ArangoDB sink
    from arango_log_sink import ArangoLogSink
    
    # For standalone scripts, logger.remove() is used to ensure a clean slate,
    # preventing duplicate output if run multiple times in a session.
    # In a larger, long-running application, logging setup should be centralized
    # and might not involve calling logger.remove() indiscriminately.
    logger.remove() 
    logger.add(sys.stderr, level="INFO") # Add a console handler for general output
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    async def main():
        # Initialize test database and sink
        test_db = None
        test_db_name = None
        test_db_config = None
        sink = None
        sink_handler_id = None
        success = False
        
        try:
            # Create test database
            test_db, test_db_name, test_db_config = await setup_test_database()
            logger.info(f"Created test database: {test_db_name}")
            
            # Create sink for test database
            sink = ArangoLogSink(
                db_config={
                    "url": test_db_config["url"],
                    "database": test_db_name,
                    "username": test_db_config["username"], 
                    "password": test_db_config["password"]
                },
                batch_size=50,
                flush_interval=1.0
            )
            await sink.start()
            sink_handler_id = logger.add(sink.write, enqueue=True, level="DEBUG")
            
            # Pass test_db to the usage functions
            if mode == "debug":
                logger.info("Running in DEBUG mode...")
                success = await debug_function()
            else:
                logger.info("Running in WORKING mode...")
                success = await working_usage()
                
        except Exception as e:
            logger.error(f"Main execution failed: {e}")
            logger.exception("Full traceback:")
            success = False
        finally:
            # Ensure sink is properly closed
            if sink_handler_id is not None:
                logger.remove(sink_handler_id)
            if sink:
                logger.info("Stopping ArangoLogSink...")
                await sink.stop()
                logger.info("ArangoLogSink stopped.")
            # Cleanup test database
            if test_db_name:
                await teardown_test_database(test_db_name)
        
        return success
    
    success = asyncio.run(main())
    exit(0 if success else 1)