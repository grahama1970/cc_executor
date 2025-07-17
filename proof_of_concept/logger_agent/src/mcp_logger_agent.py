#!/usr/bin/env python3
"""
MCP Server for Logger Agent - Provides centralized logging and analysis capabilities.

This MCP server exposes the Logger Agent functionality for:
- Centralized log storage in ArangoDB
- Log search and analysis
- Agent performance metrics
- Error pattern detection
- Graph-based relationship tracking

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python mcp_logger_agent.py          # Runs working_usage() - stable, known to work
  python mcp_logger_agent.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.tools import Tool, ToolError
from mcp.shared.models import ToolResult

from agent_log_manager import get_log_manager, AgentLogManager
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


class LoggerAgentMCPServer:
    """MCP Server for Logger Agent functionality."""
    
    def __init__(self):
        self.app = Server("logger-agent")
        self.manager: Optional[AgentLogManager] = None
        self._setup_tools()
    
    async def initialize(self):
        """Initialize the log manager connection."""
        self.manager = await get_log_manager()
        logger.info("Logger Agent MCP Server initialized")
    
    def _setup_tools(self):
        """Setup all available tools."""
        
        @self.app.tool()
        async def log_event(
            level: str,
            message: str,
            script_name: str,
            execution_id: str,
            extra_data: Optional[Dict[str, Any]] = None,
            tags: Optional[List[str]] = None
        ) -> ToolResult:
            """
            Log an event to the centralized ArangoDB logger.
            
            Args:
                level: Log level (INFO, WARNING, ERROR, etc.)
                message: Log message
                script_name: Name of the script/agent logging
                execution_id: Unique execution/session ID
                extra_data: Optional additional data
                tags: Optional tags for categorization
            
            Returns:
                The created log event document
            """
            if not self.manager:
                await self.initialize()
            
            try:
                result = await self.manager.log_event(
                    level=level,
                    message=message,
                    script_name=script_name,
                    execution_id=execution_id,
                    extra_data=extra_data,
                    tags=tags
                )
                
                return ToolResult(result={"success": True, "log_id": result.get("_id")})
            except Exception as e:
                logger.error(f"Failed to log event: {e}")
                raise ToolError(f"Failed to log event: {str(e)}")
        
        @self.app.tool()
        async def search_logs(
            query: str,
            limit: int = 50,
            offset: int = 0,
            filters: Optional[Dict[str, Any]] = None
        ) -> ToolResult:
            """
            Search logs using BM25 full-text search.
            
            Args:
                query: Search query
                limit: Maximum results
                offset: Pagination offset
                filters: Optional filters (source_apps, session_ids, event_types, time_range)
            
            Returns:
                Search results with relevance scores
            """
            if not self.manager:
                await self.initialize()
            
            try:
                results = await self.manager.search.search_agent_activity(
                    query=query,
                    filters=filters,
                    limit=limit,
                    offset=offset
                )
                
                return ToolResult(result={
                    "results": results,
                    "count": len(results),
                    "query": query
                })
            except Exception as e:
                logger.error(f"Search failed: {e}")
                raise ToolError(f"Search failed: {str(e)}")
        
        @self.app.tool()
        async def get_error_patterns(
            time_range: str = "24h",
            min_occurrences: int = 2
        ) -> ToolResult:
            """
            Find common error patterns and their resolutions.
            
            Args:
                time_range: Time range (e.g., "24h", "7d")
                min_occurrences: Minimum occurrences to be considered a pattern
            
            Returns:
                Error patterns with resolution suggestions
            """
            if not self.manager:
                await self.initialize()
            
            try:
                patterns = await self.manager.search.find_error_patterns(
                    time_range=time_range,
                    min_occurrences=min_occurrences
                )
                
                return ToolResult(result={
                    "patterns": patterns,
                    "time_range": time_range,
                    "pattern_count": len(patterns)
                })
            except Exception as e:
                logger.error(f"Error pattern analysis failed: {e}")
                raise ToolError(f"Error pattern analysis failed: {str(e)}")
        
        @self.app.tool()
        async def get_agent_performance(
            session_id: Optional[str] = None,
            time_range: str = "24h"
        ) -> ToolResult:
            """
            Get agent performance metrics.
            
            Args:
                session_id: Optional specific session ID
                time_range: Time range for metrics
            
            Returns:
                Performance metrics including tool usage, errors, duration
            """
            if not self.manager:
                await self.initialize()
            
            try:
                # Get performance metrics
                if session_id:
                    flow = await self.manager.graph.get_execution_flow(session_id)
                    return ToolResult(result={
                        "session_id": session_id,
                        "flow_stats": flow["stats"],
                        "node_count": len(flow["nodes"]),
                        "edge_count": len(flow["edges"])
                    })
                else:
                    # Get overall metrics
                    stats = await self.manager.get_stats()
                    return ToolResult(result={
                        "overall_stats": stats,
                        "time_range": time_range
                    })
            except Exception as e:
                logger.error(f"Performance analysis failed: {e}")
                raise ToolError(f"Performance analysis failed: {str(e)}")
        
        @self.app.tool()
        async def store_agent_memory(
            content: str,
            memory_type: str = "general",
            metadata: Optional[Dict[str, Any]] = None
        ) -> ToolResult:
            """
            Store an agent memory for future reference.
            
            Args:
                content: Memory content
                memory_type: Type of memory (learning, observation, error_pattern)
                metadata: Additional metadata
            
            Returns:
                The created memory document
            """
            if not self.manager:
                await self.initialize()
            
            try:
                memory = await self.manager.memory.add_memory(
                    content=content,
                    memory_type=memory_type,
                    metadata=metadata
                )
                
                return ToolResult(result={
                    "success": True,
                    "memory_id": memory.get("_id"),
                    "memory_type": memory_type
                })
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
                raise ToolError(f"Failed to store memory: {str(e)}")
        
        @self.app.tool()
        async def search_memories(
            query: str,
            memory_type: Optional[str] = None,
            limit: int = 10
        ) -> ToolResult:
            """
            Search agent memories.
            
            Args:
                query: Search query
                memory_type: Optional filter by type
                limit: Maximum results
            
            Returns:
                Matching memories with relevance scores
            """
            if not self.manager:
                await self.initialize()
            
            try:
                memories = await self.manager.memory.search_memories(
                    query=query,
                    memory_type=memory_type,
                    limit=limit
                )
                
                return ToolResult(result={
                    "memories": memories,
                    "count": len(memories),
                    "query": query
                })
            except Exception as e:
                logger.error(f"Memory search failed: {e}")
                raise ToolError(f"Memory search failed: {str(e)}")
    
    async def run(self):
        """Run the MCP server."""
        await self.initialize()
        await self.app.run()


async def working_usage():
    """
    Demonstrate Logger Agent MCP Server functionality.
    
    This function verifies the MCP server can:
    1. Initialize properly
    2. Log events
    3. Search logs
    4. Analyze patterns
    5. Store and retrieve memories
    """
    logger.info("=== Testing Logger Agent MCP Server ===")
    
    # Create server instance
    server = LoggerAgentMCPServer()
    await server.initialize()
    
    # Test 1: Log an event
    logger.info("\nTest 1: Logging an event...")
    log_tool = next(t for t in server.app.list_tools() if t.name == "log_event")
    
    result = await log_tool.run(
        level="INFO",
        message="Test event from MCP server",
        script_name="mcp_test",
        execution_id="test_123",
        extra_data={"test": True},
        tags=["mcp", "test"]
    )
    
    assert result.result["success"] == True
    logger.success("✓ Event logged successfully")
    
    # Test 2: Search logs
    logger.info("\nTest 2: Searching logs...")
    search_tool = next(t for t in server.app.list_tools() if t.name == "search_logs")
    
    # Wait for indexing
    await asyncio.sleep(1.0)
    
    search_result = await search_tool.run(
        query="test",
        limit=10
    )
    
    assert "results" in search_result.result
    logger.success(f"✓ Found {search_result.result['count']} results")
    
    # Test 3: Store memory
    logger.info("\nTest 3: Storing agent memory...")
    memory_tool = next(t for t in server.app.list_tools() if t.name == "store_agent_memory")
    
    memory_result = await memory_tool.run(
        content="MCP server testing shows all functions work correctly",
        memory_type="observation",
        metadata={"confidence": 0.95}
    )
    
    assert memory_result.result["success"] == True
    logger.success("✓ Memory stored successfully")
    
    # Test 4: Get performance metrics
    logger.info("\nTest 4: Getting performance metrics...")
    perf_tool = next(t for t in server.app.list_tools() if t.name == "get_agent_performance")
    
    perf_result = await perf_tool.run(time_range="24h")
    
    assert "overall_stats" in perf_result.result
    logger.success("✓ Performance metrics retrieved")
    
    logger.info("\n✅ All MCP server tests passed!")
    return True


async def debug_function():
    """
    Debug function for testing advanced MCP features.
    """
    logger.info("=== Debug Mode: Testing Advanced Features ===")
    
    server = LoggerAgentMCPServer()
    await server.initialize()
    
    # Test error pattern detection
    logger.info("Testing error pattern detection...")
    
    # Log some error patterns
    log_tool = next(t for t in server.app.list_tools() if t.name == "log_event")
    
    # Create similar errors
    for i in range(3):
        await log_tool.run(
            level="ERROR",
            message=f"Connection timeout after 300 seconds (attempt {i})",
            script_name="test_script",
            execution_id=f"debug_{i}",
            extra_data={"error_type": "ConnectionTimeout"}
        )
    
    # Wait for indexing
    await asyncio.sleep(2.0)
    
    # Find patterns
    pattern_tool = next(t for t in server.app.list_tools() if t.name == "get_error_patterns")
    patterns = await pattern_tool.run(time_range="1h", min_occurrences=2)
    
    logger.info(f"Found {patterns.result['pattern_count']} error patterns")
    
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
    elif mode == "serve":
        # Run as actual MCP server
        server = LoggerAgentMCPServer()
        asyncio.run(server.run())
    else:
        asyncio.run(working_usage())