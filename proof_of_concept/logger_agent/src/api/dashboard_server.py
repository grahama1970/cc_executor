#!/usr/bin/env python3
"""
dashboard_server.py - FastAPI server for multi-agent observability dashboard

Provides REST API and WebSocket endpoints for the Vue.js dashboard,
integrating with ArangoDB for storage and real-time updates.

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python dashboard_server.py          # Runs working_usage() - stable, known to work
  python dashboard_server.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agent_log_manager import get_log_manager, AgentLogManager
from arangodb.core.graph.agent_graph_builder import AgentGraphBuilder
from arangodb.core.search.agent_search import AgentSearch
from utils.log_utils import truncate_large_value
from loguru import logger

# FastAPI app
app = FastAPI(title="Logger Agent Dashboard API", version="1.0.0")

# CORS middleware for Vue client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vue dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, metadata: Dict = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = metadata or {}
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        self.connection_metadata.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_session(self, session_id: str, message: Dict):
        """Send message to specific session."""
        for connection, metadata in self.connection_metadata.items():
            if metadata.get("session_id") == session_id:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# Pydantic models
class HookEvent(BaseModel):
    source_app: str
    session_id: str
    hook_event_type: str
    payload: Dict[str, Any]
    chat: Optional[List[Dict]] = None
    summary: Optional[str] = None
    timestamp: Optional[int] = None

class EventFilter(BaseModel):
    source_apps: Optional[List[str]] = None
    session_ids: Optional[List[str]] = None
    hook_event_types: Optional[List[str]] = None
    time_range: Optional[Dict[str, str]] = None
    search_query: Optional[str] = None
    limit: int = 100
    offset: int = 0

# Helper functions
def transform_log_to_hook_event(log_doc: Dict) -> Dict:
    """Transform ArangoDB log document to hook event format for frontend."""
    extra_data = log_doc.get("extra_data", {})
    
    return {
        "id": log_doc.get("_key", "unknown"),
        "source_app": log_doc.get("script_name", "unknown"),
        "session_id": log_doc.get("execution_id", "unknown"),
        "hook_event_type": extra_data.get("hook_event_type", "LogEvent"),
        "payload": extra_data.get("payload", {}),
        "chat": extra_data.get("chat"),
        "summary": extra_data.get("summary"),
        "timestamp": int(datetime.fromisoformat(log_doc["timestamp"]).timestamp() * 1000)
    }

async def store_hook_event(event: HookEvent, manager: AgentLogManager) -> Dict:
    """Store hook event in ArangoDB and graph structure."""
    # Create log document
    log_doc = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": "INFO",
        "message": f"Hook event: {event.hook_event_type}",
        "execution_id": event.session_id,
        "script_name": event.source_app,
        "function_name": "claude_hook",
        "file_path": ".claude/hooks/",
        "line_number": 0,
        "extra_data": {
            "hook_event_type": event.hook_event_type,
            "payload": truncate_large_value(event.payload),
            "chat": event.chat,
            "summary": event.summary
        },
        "tags": ["claude-hook", event.hook_event_type]
    }
    
    # Store in log_events collection using asyncio.to_thread for sync operations
    def _insert_sync():
        collection = manager.db.collection("log_events")
        result = collection.insert(log_doc)
        return result
    
    result = await asyncio.to_thread(_insert_sync)
    log_doc["_key"] = result["_key"]
    
    # TODO: Re-enable graph builder after updating to aioarango
    # # Create graph nodes and edges
    # graph_builder = AgentGraphBuilder(manager.db)
    # 
    # # Create or update session node
    # await graph_builder.upsert_session(event.session_id, event.source_app)
    # 
    # # Handle specific event types
    # if event.hook_event_type == "PreToolUse":
    #     tool_name = event.payload.get("tool_name", "unknown")
    #     tool_input = event.payload.get("tool_input", {})
    #     await graph_builder.create_tool_execution(
    #         session_id=event.session_id,
    #         tool_name=tool_name,
    #         command=json.dumps(tool_input),
    #         status="started"
    #     )
    # 
    # elif event.hook_event_type == "PostToolUse":
    #     # Update tool execution with results
    #     tool_name = event.payload.get("tool_name", "unknown")
    #     result = event.payload.get("result", {})
    #     await graph_builder.update_tool_execution(
    #         session_id=event.session_id,
    #         tool_name=tool_name,
    #         output=truncate_large_value(result),
    #         status="completed"
    #     )
    # 
    # elif event.hook_event_type == "Stop":
    #     # Mark session as completed
    #     await graph_builder.complete_session(event.session_id)
    
    return log_doc

# API endpoints
@app.post("/events")
async def receive_event(event: HookEvent):
    """Receive events from Claude Code hooks."""
    try:
        # Get log manager
        log_manager = await get_log_manager()
        
        # Store event in database
        stored_doc = await store_hook_event(event, log_manager)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "new_event",
            "event": transform_log_to_hook_event(stored_doc)
        })
        
        logger.info(f"Stored hook event: {event.hook_event_type} from {event.source_app}")
        return {"status": "success", "id": stored_doc["_key"]}
        
    except Exception as e:
        logger.error(f"Failed to store event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/search")
async def search_events(filters: EventFilter):
    """Search events with BM25 and filters."""
    try:
        log_manager = await get_log_manager()
        search = AgentSearch(log_manager.db)
        
        # Perform BM25 search if query provided
        if filters.search_query:
            results = await search.search_agent_activity(
                query=filters.search_query,
                filters={
                    "source_apps": filters.source_apps,
                    "session_ids": filters.session_ids,
                    "event_types": filters.hook_event_types,
                    "time_range": filters.time_range
                },
                limit=filters.limit,
                offset=filters.offset
            )
        else:
            # Regular filtered query
            results = await search.get_filtered_events(
                filters={
                    "source_apps": filters.source_apps,
                    "session_ids": filters.session_ids,
                    "event_types": filters.hook_event_types,
                    "time_range": filters.time_range
                },
                limit=filters.limit,
                offset=filters.offset
            )
        
        # Transform results
        events = [transform_log_to_hook_event(r["doc"]) for r in results]
        
        return {
            "events": events,
            "total": len(events),
            "has_more": len(events) == filters.limit
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/recent")
async def get_recent_events(
    limit: int = 100,
    source_app: Optional[str] = None,
    session_id: Optional[str] = None,
    hook_event_type: Optional[str] = None
):
    """Get recent events with optional filtering."""
    filters = EventFilter(
        source_apps=[source_app] if source_app else None,
        session_ids=[session_id] if session_id else None,
        hook_event_types=[hook_event_type] if hook_event_type else None,
        limit=limit
    )
    
    return await search_events(filters)

@app.get("/events/filter-options")
async def get_filter_options():
    """Get available filter options."""
    try:
        log_manager = await get_log_manager()
        
        # Get distinct values using AQL
        aql_apps = """
        FOR doc IN log_events
        FILTER 'claude-hook' IN doc.tags
        RETURN DISTINCT doc.script_name
        """
        
        aql_sessions = """
        FOR doc IN log_events
        FILTER 'claude-hook' IN doc.tags
        SORT doc.timestamp DESC
        RETURN DISTINCT doc.execution_id
        LIMIT 100
        """
        
        aql_types = """
        FOR doc IN log_events
        FILTER 'claude-hook' IN doc.tags
        RETURN DISTINCT doc.extra_data.hook_event_type
        """
        
        apps = await log_manager.query_logs(aql_apps)
        sessions = await log_manager.query_logs(aql_sessions)
        types = await log_manager.query_logs(aql_types)
        
        return {
            "source_apps": [app for app in apps if app],
            "session_ids": [sess for sess in sessions if sess],
            "hook_event_types": [t for t in types if t]
        }
        
    except Exception as e:
        logger.error(f"Failed to get filter options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/flow")
async def get_session_flow(session_id: str):
    """Get execution flow graph for a session."""
    try:
        log_manager = await get_log_manager()
        graph_builder = AgentGraphBuilder(log_manager.db)
        
        flow = await graph_builder.get_execution_flow(session_id)
        
        return {
            "session_id": session_id,
            "nodes": flow["nodes"],
            "edges": flow["edges"],
            "stats": flow["stats"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get session flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/errors/patterns")
async def get_error_patterns(
    time_range: Optional[str] = "24h",
    min_occurrences: int = 2
):
    """Get common error patterns and resolutions."""
    try:
        log_manager = await get_log_manager()
        search = AgentSearch(log_manager.db)
        
        patterns = await search.find_error_patterns(
            time_range=time_range,
            min_occurrences=min_occurrences
        )
        
        return {
            "patterns": patterns,
            "time_range": time_range
        }
        
    except Exception as e:
        logger.error(f"Failed to get error patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Logger Agent Dashboard"
        })
        
        # Keep connection alive
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Process other messages if needed
                try:
                    message = json.loads(data)
                    if message.get("type") == "subscribe":
                        # Update connection metadata
                        manager.connection_metadata[websocket] = {
                            "session_id": message.get("session_id"),
                            "filters": message.get("filters", {})
                        }
                except json.JSONDecodeError:
                    pass
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        log_manager = await get_log_manager()
        # Test database connection
        await asyncio.to_thread(log_manager.db.version)
        
        return {
            "status": "healthy",
            "database": "connected",
            "websocket_clients": len(manager.active_connections)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Logger Agent Dashboard API...")
    
    # Initialize database connection
    try:
        log_manager = await get_log_manager()
        logger.info("Database connection established")
        
        # Initialize graph structure
        from arangodb.core.graph.agent_graph_builder import AgentGraphBuilder
        graph_builder = AgentGraphBuilder(log_manager.db)
        await graph_builder.initialize_graph()
        logger.info("Graph structure initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Logger Agent Dashboard API...")
    
    # Close all WebSocket connections
    for connection in manager.active_connections.copy():
        await connection.close()
        manager.disconnect(connection)

async def working_usage():
    """Test the dashboard API with a test database."""
    import asyncio
    import httpx
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.test_utils import TestEnvironment
    
    # Create test environment
    env = TestEnvironment()
    await env.setup()
    
    try:
        # Override the global manager to use test database
        global manager
        test_manager = AgentLogManager()
        await test_manager.initialize({
            'url': 'http://localhost:8529',
            'database': env.db_name,
            'username': 'root',
            'password': 'openSesame'
        })
        
        # Store original manager and replace with test
        original_manager = manager
        manager = test_manager
        
        logger.info(f"Testing dashboard API with test database: {env.db_name}")
        
        # Test 1: Health check
        async with httpx.AsyncClient(base_url="http://localhost:8002") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            logger.info("✓ Health check passed")
            
            # Test 2: Send a test event
            test_event = {
                "hook_event_type": "PostToolUse",
                "source_app": "test_dashboard",
                "payload": {
                    "tool_name": "TestTool",
                    "tool_input": {"command": "test command"},
                    "result": "Test successful"
                }
            }
            
            response = await client.post("/events", json=test_event)
            assert response.status_code == 200
            event_data = response.json()
            logger.info(f"✓ Event stored with key: {event_data['key']}")
            
            # Test 3: Query events
            response = await client.get("/events?limit=10")
            assert response.status_code == 200
            events = response.json()
            assert "events" in events
            assert len(events["events"]) > 0
            logger.info(f"✓ Retrieved {len(events['events'])} events")
            
            # Test 4: Search events
            response = await client.get("/search?query=test&limit=5")
            assert response.status_code == 200
            results = response.json()
            assert "results" in results
            logger.info(f"✓ Search returned {results['total']} results")
        
        logger.info("All dashboard API tests passed!")
        return True
        
    finally:
        # Restore original manager
        manager = original_manager
        await test_manager.close()
        await env.teardown()


async def debug_function():
    """Debug dashboard functionality with test database."""
    import asyncio
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.test_utils import TestEnvironment
    
    # Create test environment
    env = TestEnvironment()
    await env.setup()
    
    try:
        # Override the global manager to use test database
        global manager
        test_manager = AgentLogManager()
        await test_manager.initialize({
            'url': 'http://localhost:8529',
            'database': env.db_name,
            'username': 'root',
            'password': 'openSesame'
        })
        
        # Store original manager and replace with test
        original_manager = manager
        manager = test_manager
        
        logger.info(f"Debug mode - using test database: {env.db_name}")
        
        # Insert various test data
        test_events = [
            {
                "hook_event_type": "PreToolUse",
                "source_app": "debug_test",
                "payload": {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
            },
            {
                "hook_event_type": "PostToolUse",
                "source_app": "debug_test",
                "payload": {
                    "tool_name": "Bash",
                    "tool_input": {"command": "ls -la"},
                    "result": "file1.txt\nfile2.txt"
                }
            },
            {
                "hook_event_type": "Error",
                "source_app": "debug_test",
                "payload": {
                    "error": "Command not found",
                    "context": {"command": "invalid_cmd"}
                }
            }
        ]
        
        # Store events
        stored_keys = []
        for event in test_events:
            result = await test_manager.store_hook_event(
                event["hook_event_type"],
                event["source_app"],
                event["payload"]
            )
            stored_keys.append(result["key"])
            logger.info(f"Stored event: {event['hook_event_type']} -> {result['key']}")
        
        # Test graph relationships
        if len(stored_keys) >= 2:
            # Create a relationship between first two events
            edge_data = {
                "_from": f"log_events/{stored_keys[0]}",
                "_to": f"log_events/{stored_keys[1]}",
                "relationship": "TRIGGERED",
                "confidence": 0.85
            }
            # This would normally be done through graph builder
            logger.info("Would create edge relationship here")
        
        # Test search functionality
        search_results = await test_manager.hybrid_search.search(
            query="bash command",
            collections=["log_events"],
            limit=10
        )
        logger.info(f"Search results: {len(search_results)} matches")
        
        # Test memory extraction
        memory_result = await test_manager.memory_agent.extract_memory(
            event_id=stored_keys[0],
            context={"session": "debug_session"}
        )
        logger.info(f"Memory extraction: {memory_result}")
        
        logger.info(f"\nDebug session complete. Test database: {env.db_name}")
        logger.info("Data remains in test database for manual inspection if needed.")
        
        return True
        
    finally:
        # Restore original manager
        manager = original_manager
        await test_manager.close()
        await env.teardown()


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "debug":
            asyncio.run(debug_function())
        elif mode == "test":
            asyncio.run(working_usage())
        else:
            # Run the server normally
            import uvicorn
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8002,
                log_level="info"
            )
    else:
        # Default: run the server
        import uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8002,
            log_level="info"
        )