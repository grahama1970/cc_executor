#!/usr/bin/env python3
"""
agent_graph_builder.py - Build and manage graph relationships for agent observability

Creates graph structures to track relationships between agent sessions,
tool executions, errors, insights, and code artifacts.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python agent_graph_builder.py          # Runs working_usage() - stable, known to work
  python agent_graph_builder.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from loguru import logger
from arango import ArangoClient
from arango.database import StandardDatabase


class AgentGraphBuilder:
    """Manages graph structures for agent activity tracking."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.graph_name = "claude_agent_observatory"
        self._current_tool_executions = {}  # Track ongoing tool executions
    
    async def initialize_graph(self):
        """Initialize the graph structure with collections and edge definitions."""
        
        def _init_sync():
            # Create vertex collections
            vertex_collections = [
                "agent_sessions",
                "tool_executions",
                "code_artifacts",
                "agent_insights", 
                "errors_and_failures"
            ]
            
            for collection in vertex_collections:
                if not self.db.has_collection(collection):
                    self.db.create_collection(collection)
                    logger.info(f"Created vertex collection: {collection}")
            
            # Create edge collections with definitions
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
            
            # Create or update graph
            if not self.db.has_graph(self.graph_name):
                self.db.create_graph(
                    self.graph_name,
                    edge_definitions=edge_definitions
                )
                logger.info(f"Created graph: {self.graph_name}")
            else:
                # Update existing graph with new edge definitions
                graph = self.db.graph(self.graph_name)
                existing_edges = {ed["edge_collection"] for ed in graph.edge_definitions()}
                
                for edge_def in edge_definitions:
                    if edge_def["edge_collection"] not in existing_edges:
                        graph.create_edge_definition(**edge_def)
                        logger.info(f"Added edge collection: {edge_def['edge_collection']}")
            
            # Create indexes for efficient queries
            self._create_indexes()
        
        await asyncio.to_thread(_init_sync)
    
    def _create_indexes(self):
        """Create indexes for efficient graph queries."""
        # Session indexes
        if self.db.has_collection("agent_sessions"):
            coll = self.db.collection("agent_sessions")
            coll.add_index({"type": "persistent", "fields": ["session_id"], "unique": True})
            coll.add_index({"type": "persistent", "fields": ["agent_name", "start_time"]})
        
        # Tool execution indexes
        if self.db.has_collection("tool_executions"):
            coll = self.db.collection("tool_executions")
            coll.add_index({"type": "persistent", "fields": ["session_id", "tool_name"]})
            coll.add_index({"type": "persistent", "fields": ["start_time"]})
        
        # Error indexes
        if self.db.has_collection("errors_and_failures"):
            coll = self.db.collection("errors_and_failures")
            coll.add_index({"type": "persistent", "fields": ["error_type", "timestamp"]})
            coll.add_index({"type": "fulltext", "fields": ["message"], "minLength": 3})
    
    async def upsert_session(self, session_id: str, agent_name: str, metadata: Dict = None):
        """Create or update an agent session node."""
        
        def _upsert_sync():
            collection = self.db.collection("agent_sessions")
            
            # Check if session exists
            existing = collection.find({"session_id": session_id})
            existing_list = list(existing)
            
            if existing_list:
                # Update existing session
                doc = existing_list[0]
                doc["last_activity"] = datetime.utcnow().isoformat()
                if metadata:
                    doc["metadata"].update(metadata)
                collection.update(doc)
                return doc
            else:
                # Create new session
                doc = {
                    "_key": f"session_{session_id}",
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "start_time": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat(),
                    "status": "active",
                    "metadata": metadata or {},
                    "stats": {
                        "tool_executions": 0,
                        "errors": 0,
                        "insights": 0,
                        "artifacts_created": 0
                    }
                }
                result = collection.insert(doc)
                doc["_id"] = f"agent_sessions/{result['_key']}"
                return doc
        
        return await asyncio.to_thread(_upsert_sync)
    
    async def create_tool_execution(
        self, 
        session_id: str,
        tool_name: str,
        command: str,
        status: str = "started"
    ):
        """Create a tool execution node."""
        
        def _create_sync():
            # Generate unique key for this execution
            exec_key = f"{session_id}_{tool_name}_{datetime.utcnow().timestamp()}"
            exec_key = hashlib.md5(exec_key.encode()).hexdigest()[:12]
            
            doc = {
                "_key": f"exec_{exec_key}",
                "session_id": session_id,
                "tool_name": tool_name,
                "command": command,
                "start_time": datetime.utcnow().isoformat(),
                "status": status,
                "duration_ms": None,
                "exit_code": None,
                "output_preview": None
            }
            
            collection = self.db.collection("tool_executions")
            result = collection.insert(doc)
            doc["_id"] = f"tool_executions/{result['_key']}"
            
            # Track for later update
            self._current_tool_executions[f"{session_id}:{tool_name}"] = doc["_id"]
            
            # Create edge from session or previous tool
            self._create_flow_edge(session_id, doc["_id"], "EXECUTES")
            
            # Update session stats
            self._update_session_stats(session_id, "tool_executions", 1)
            
            return doc
        
        return await asyncio.to_thread(_create_sync)
    
    async def update_tool_execution(
        self,
        session_id: str,
        tool_name: str,
        output: Any,
        status: str = "completed",
        exit_code: int = None
    ):
        """Update a tool execution with results."""
        
        def _update_sync():
            key = f"{session_id}:{tool_name}"
            tool_id = self._current_tool_executions.get(key)
            
            if not tool_id:
                logger.warning(f"No active tool execution found for {key}")
                return None
            
            collection = self.db.collection("tool_executions")
            doc_key = tool_id.split("/")[1]
            
            # Get existing document
            doc = collection.get(doc_key)
            if doc:
                # Calculate duration
                start_time = datetime.fromisoformat(doc["start_time"])
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Update document
                update_data = {
                    "end_time": datetime.utcnow().isoformat(),
                    "duration_ms": duration_ms,
                    "status": status,
                    "exit_code": exit_code,
                    "output_preview": str(output)[:500] if output else None
                }
                
                collection.update_match({"_key": doc_key}, update_data)
                
                # Handle errors if exit code indicates failure
                if exit_code and exit_code != 0:
                    self._create_error_from_tool(session_id, tool_id, output)
                
                # Remove from tracking
                del self._current_tool_executions[key]
            
            return doc
        
        return await asyncio.to_thread(_update_sync)
    
    async def create_error(
        self,
        session_id: str,
        error_type: str,
        message: str,
        stack_trace: str = None,
        file_context: str = None
    ):
        """Create an error node."""
        
        def _create_sync():
            doc = {
                "_key": f"error_{datetime.utcnow().timestamp()}",
                "session_id": session_id,
                "error_type": error_type,
                "message": message,
                "stack_trace": stack_trace,
                "file_context": file_context,
                "timestamp": datetime.utcnow().isoformat(),
                "resolved": False,
                "resolution": None
            }
            
            collection = self.db.collection("errors_and_failures")
            result = collection.insert(doc)
            doc["_id"] = f"errors_and_failures/{result['_key']}"
            
            # Create causality edge from last tool execution
            last_tool = self._get_last_tool_execution(session_id)
            if last_tool:
                self._create_edge(
                    "error_causality",
                    last_tool["_id"],
                    doc["_id"],
                    {"relationship": "CAUSED", "timestamp": datetime.utcnow().isoformat()}
                )
            
            # Update session stats
            self._update_session_stats(session_id, "errors", 1)
            
            return doc
        
        return await asyncio.to_thread(_create_sync)
    
    async def create_insight(
        self,
        session_id: str,
        content: str,
        confidence: float,
        context: Dict = None,
        tags: List[str] = None
    ):
        """Create an agent insight node."""
        
        def _create_sync():
            doc = {
                "_key": f"insight_{datetime.utcnow().timestamp()}",
                "session_id": session_id,
                "content": content,
                "confidence": confidence,
                "context": context or {},
                "tags": tags or [],
                "timestamp": datetime.utcnow().isoformat(),
                "applications": 0  # Track how many times this insight is applied
            }
            
            collection = self.db.collection("agent_insights")
            result = collection.insert(doc)
            doc["_id"] = f"agent_insights/{result['_key']}"
            
            # Update session stats
            self._update_session_stats(session_id, "insights", 1)
            
            return doc
        
        return await asyncio.to_thread(_create_sync)
    
    async def create_artifact(
        self,
        session_id: str,
        file_path: str,
        operation: str,
        language: str = None,
        size: int = None
    ):
        """Create a code artifact node."""
        
        def _create_sync():
            # Calculate file hash if it exists
            file_hash = None
            if Path(file_path).exists():
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            
            doc = {
                "_key": f"artifact_{Path(file_path).name}_{datetime.utcnow().timestamp()}",
                "session_id": session_id,
                "file_path": file_path,
                "operation": operation,  # created, modified, deleted
                "language": language or self._detect_language(file_path),
                "size": size,
                "hash": file_hash,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            collection = self.db.collection("code_artifacts")
            result = collection.insert(doc)
            doc["_id"] = f"code_artifacts/{result['_key']}"
            
            # Create lineage edge if this is a modification
            if operation == "modified":
                self._create_artifact_lineage(file_path, doc["_id"])
            
            # Update session stats
            if operation == "created":
                self._update_session_stats(session_id, "artifacts_created", 1)
            
            return doc
        
        return await asyncio.to_thread(_create_sync)
    
    async def complete_session(self, session_id: str, status: str = "completed"):
        """Mark a session as completed."""
        
        def _complete_sync():
            collection = self.db.collection("agent_sessions")
            
            # Find session
            sessions = list(collection.find({"session_id": session_id}))
            if sessions:
                doc = sessions[0]
                update_data = {
                    "end_time": datetime.utcnow().isoformat(),
                    "status": status,
                    "duration_seconds": None
                }
                
                # Calculate duration
                if "start_time" in doc:
                    start = datetime.fromisoformat(doc["start_time"])
                    duration = (datetime.utcnow() - start).total_seconds()
                    update_data["duration_seconds"] = duration
                
                collection.update_match({"session_id": session_id}, update_data)
                return doc
            
            return None
        
        return await asyncio.to_thread(_complete_sync)
    
    async def get_execution_flow(self, session_id: str) -> Dict:
        """Get the complete execution flow for a session."""
        
        def _get_flow_sync():
            # Get session node
            session_coll = self.db.collection("agent_sessions")
            sessions = list(session_coll.find({"session_id": session_id}))
            
            if not sessions:
                return {"nodes": [], "edges": [], "stats": {}}
            
            session = sessions[0]
            session_vertex_id = f"agent_sessions/{session['_key']}"
            
            # Traverse graph to get all related nodes
            aql = """
            LET session = DOCUMENT(@session_id)
            
            FOR v, e, p IN 1..20 OUTBOUND session 
                agent_flow, tool_dependencies, error_causality, artifact_lineage
            OPTIONS {uniqueVertices: 'path', bfs: true}
            RETURN {
                vertex: v,
                edge: e,
                path_length: LENGTH(p.edges),
                vertex_type: SPLIT(v._id, '/')[0]
            }
            """
            
            cursor = self.db.aql.execute(
                aql,
                bind_vars={"session_id": session_vertex_id}
            )
            
            nodes = [session]  # Include session node
            edges = []
            node_ids = {session_vertex_id}
            
            for result in cursor:
                # Add unique nodes
                if result["vertex"]["_id"] not in node_ids:
                    nodes.append(result["vertex"])
                    node_ids.add(result["vertex"]["_id"])
                
                # Add edges
                if result["edge"]:
                    edges.append(result["edge"])
            
            # Calculate statistics
            stats = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "tool_executions": sum(1 for n in nodes if "tool_executions" in n.get("_id", "")),
                "errors": sum(1 for n in nodes if "errors_and_failures" in n.get("_id", "")),
                "insights": sum(1 for n in nodes if "agent_insights" in n.get("_id", "")),
                "artifacts": sum(1 for n in nodes if "code_artifacts" in n.get("_id", ""))
            }
            
            return {
                "nodes": nodes,
                "edges": edges,
                "stats": stats
            }
        
        return await asyncio.to_thread(_get_flow_sync)
    
    # Helper methods
    def _create_edge(self, collection: str, from_id: str, to_id: str, attributes: Dict = None):
        """Create an edge between two vertices."""
        edge_coll = self.db.collection(collection)
        edge_doc = {
            "_from": from_id,
            "_to": to_id,
            "created_at": datetime.utcnow().isoformat()
        }
        if attributes:
            edge_doc.update(attributes)
        
        edge_coll.insert(edge_doc)
    
    def _create_flow_edge(self, session_id: str, to_id: str, relationship: str):
        """Create an agent_flow edge."""
        # Get last node in flow
        last_node = self._get_last_flow_node(session_id)
        
        if last_node:
            from_id = last_node["_id"]
        else:
            # Connect to session
            sessions = list(self.db.collection("agent_sessions").find({"session_id": session_id}))
            if sessions:
                from_id = f"agent_sessions/{sessions[0]['_key']}"
            else:
                return
        
        self._create_edge(
            "agent_flow",
            from_id,
            to_id,
            {"relationship": relationship, "sequence": datetime.utcnow().timestamp()}
        )
    
    def _get_last_flow_node(self, session_id: str) -> Optional[Dict]:
        """Get the last node in the execution flow."""
        aql = """
        FOR v IN tool_executions
        FILTER v.session_id == @session_id
        SORT v.start_time DESC
        LIMIT 1
        RETURN v
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"session_id": session_id})
        results = list(cursor)
        return results[0] if results else None
    
    def _get_last_tool_execution(self, session_id: str) -> Optional[Dict]:
        """Get the last tool execution for a session."""
        return self._get_last_flow_node(session_id)
    
    def _create_error_from_tool(self, session_id: str, tool_id: str, output: Any):
        """Create an error node from failed tool execution."""
        # Parse error from output
        error_type = "ToolExecutionError"
        message = str(output)[:500] if output else "Tool execution failed"
        
        error_doc = {
            "_key": f"error_{datetime.utcnow().timestamp()}",
            "session_id": session_id,
            "error_type": error_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "source_tool": tool_id
        }
        
        collection = self.db.collection("errors_and_failures")
        result = collection.insert(error_doc)
        error_id = f"errors_and_failures/{result['_key']}"
        
        # Create causality edge
        self._create_edge(
            "error_causality",
            tool_id,
            error_id,
            {"relationship": "CAUSED", "auto_generated": True}
        )
    
    def _create_artifact_lineage(self, file_path: str, new_artifact_id: str):
        """Create lineage edge between artifact versions."""
        # Find previous version of this file
        aql = """
        FOR a IN code_artifacts
        FILTER a.file_path == @file_path
        SORT a.timestamp DESC
        LIMIT 2
        RETURN a
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"file_path": file_path})
        artifacts = list(cursor)
        
        if len(artifacts) >= 2:
            # Create edge from old to new
            self._create_edge(
                "artifact_lineage",
                f"code_artifacts/{artifacts[1]['_key']}",
                new_artifact_id,
                {"relationship": "MODIFIED_TO"}
            )
    
    def _update_session_stats(self, session_id: str, stat_name: str, increment: int = 1):
        """Update session statistics."""
        aql = """
        FOR s IN agent_sessions
        FILTER s.session_id == @session_id
        UPDATE s WITH {
            stats: MERGE(s.stats, {@stat_name: s.stats[@stat_name] + @increment})
        } IN agent_sessions
        """
        
        self.db.aql.execute(
            aql,
            bind_vars={
                "session_id": session_id,
                "stat_name": stat_name,
                "increment": increment
            }
        )
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".jl": "julia",
            ".sh": "bash",
            ".ps1": "powershell",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".vue": "vue",
            ".jsx": "jsx",
            ".tsx": "tsx"
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "unknown")


async def working_usage():
    """Demonstrate graph builder functionality."""
    logger.info("=== Testing Agent Graph Builder ===")
    
    # Import test utilities
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from utils.test_db_utils import setup_test_database, teardown_test_database
    
    test_db = None
    test_db_name = None
    
    try:
        # Create test database
        test_db, test_db_name, test_db_config = await setup_test_database()
        logger.info(f"Created test database: {test_db_name}")
        
        # Create graph builder with test database
        builder = AgentGraphBuilder(test_db)
        await builder.initialize_graph()
        
        # Test session creation
        session_id = "test_session_123"
        await builder.upsert_session(session_id, "test_agent", {"purpose": "testing"})
        logger.info(f"Created session: {session_id}")
        
        # Test tool execution
        tool_exec = await builder.create_tool_execution(
            session_id=session_id,
            tool_name="Bash",
            command="ls -la",
            status="started"
        )
        logger.info(f"Created tool execution: {tool_exec['_id']}")
    
        # Update tool execution
        await asyncio.sleep(0.5)  # Simulate execution time
        await builder.update_tool_execution(
            session_id=session_id,
            tool_name="Bash",
            output="file1.txt\nfile2.py\nfile3.md",
            status="completed",
            exit_code=0
        )
        logger.info("Updated tool execution")
    
        # Create an insight
        insight = await builder.create_insight(
            session_id=session_id,
            content="Using ls -la provides detailed file information including permissions",
            confidence=0.9,
            context={"command": "ls -la"},
            tags=["bash", "file-listing"]
        )
        logger.info(f"Created insight: {insight['_id']}")
    
        # Create an artifact
        artifact = await builder.create_artifact(
            session_id=session_id,
            file_path="/tmp/test_file.py",
            operation="created",
            language="python",
            size=1024
        )
        logger.info(f"Created artifact: {artifact['_id']}")
    
        # Get execution flow
        flow = await builder.get_execution_flow(session_id)
        logger.info(f"Execution flow stats: {flow['stats']}")
        
        # Complete session
        await builder.complete_session(session_id)
        logger.info("Session completed")
    
        # Complete session
        await builder.complete_session(session_id)
        logger.info("Session completed")
        
        return True
        
    finally:
        # Clean up test database
        if test_db_name:
            await teardown_test_database(test_db_name)
            logger.info(f"Cleaned up test database: {test_db_name}")


async def debug_function():
    """Debug graph traversal and complex queries."""
    logger.info("=== Debug Mode: Graph Traversal ===")
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from agent_log_manager import get_log_manager
    manager = await get_log_manager()
    
    builder = AgentGraphBuilder(manager.db)
    
    # Create a complex execution scenario
    session_id = f"debug_session_{datetime.utcnow().timestamp()}"
    await builder.upsert_session(session_id, "debug_agent")
    
    # Tool 1: Read file
    await builder.create_tool_execution(session_id, "Read", "read file.py")
    await asyncio.sleep(0.1)
    
    # Tool 2: Edit file (depends on read)
    await builder.create_tool_execution(session_id, "Edit", "edit file.py")
    
    # Create error
    error = await builder.create_error(
        session_id=session_id,
        error_type="SyntaxError",
        message="Invalid syntax on line 42",
        file_context="file.py:42"
    )
    
    # Tool 3: Fix error
    await builder.create_tool_execution(session_id, "Edit", "fix syntax error")
    
    # Create insight from fix
    await builder.create_insight(
        session_id=session_id,
        content="Missing colon after if statement is a common Python syntax error",
        confidence=0.95,
        tags=["python", "syntax-error"]
    )
    
    # Get and analyze flow
    flow = await builder.get_execution_flow(session_id)
    logger.info(f"Complex flow created:")
    logger.info(f"  Nodes: {flow['stats']['total_nodes']}")
    logger.info(f"  Edges: {flow['stats']['total_edges']}")
    logger.info(f"  Errors: {flow['stats']['errors']}")
    logger.info(f"  Insights: {flow['stats']['insights']}")
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())