#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-arango",
#     "python-dotenv",
#     "loguru",
# ]
# ///
"""
Custom tool for querying agent logs from ArangoDB.

This tool provides a clean interface for Claude Code to search and analyze
logs without needing to write complex Python code or AQL queries.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python query_agent_logs.py          # Runs working_usage() - stable, known to work
  python query_agent_logs.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arango import ArangoClient
import asyncio
from typing import Dict, List, Any, Optional


class LogQueryTool:
    """Tool for querying agent logs."""
    
    def __init__(self):
        # Check if we're in test mode
        if hasattr(self.__class__, '_test_db'):
            self.db = self.__class__._test_db
            self.client = None
        else:
            self.client = ArangoClient(hosts='http://localhost:8529')
            self.db = self.client.db('script_logs', username='root', password='openSesame')
    
    def search_logs(self, query: str, filters: Dict[str, Any]) -> List[Dict]:
        """Search logs with various filters."""
        bind_vars = {"query": query}
        conditions = []
        
        # Build filter conditions
        if filters.get("session_id"):
            conditions.append("doc.execution_id == @session_id")
            bind_vars["session_id"] = filters["session_id"]
        
        if filters.get("tool_name"):
            conditions.append("doc.extra_data.payload.tool_name == @tool_name")
            bind_vars["tool_name"] = filters["tool_name"]
        
        if filters.get("time_range_hours"):
            cutoff = datetime.utcnow() - timedelta(hours=filters["time_range_hours"])
            conditions.append("doc.timestamp >= @cutoff")
            bind_vars["cutoff"] = cutoff.isoformat()
        
        if filters.get("event_type"):
            conditions.append("doc.extra_data.hook_event_type == @event_type")
            bind_vars["event_type"] = filters["event_type"]
        
        # Build AQL query
        where_clause = " AND ".join(conditions) if conditions else "true"
        
        aql = f"""
        FOR doc IN log_events
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
            OR ANALYZER(doc.extra_data.payload IN TOKENS(@query, 'text_en'), 'text_en')
        FILTER {where_clause}
        SORT doc.timestamp DESC
        LIMIT {filters.get('limit', 50)}
        RETURN {{
            id: doc._key,
            timestamp: doc.timestamp,
            level: doc.level,
            message: doc.message,
            tool_name: doc.extra_data.payload.tool_name,
            event_type: doc.extra_data.hook_event_type,
            session_id: doc.execution_id,
            summary: doc.extra_data.summary
        }}
        """
        
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        return list(cursor)
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a session."""
        # Get all events for session
        aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @session_id
        COLLECT 
            tool = doc.extra_data.payload.tool_name,
            event = doc.extra_data.hook_event_type
        WITH COUNT INTO count
        RETURN {tool: tool, event: event, count: count}
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"session_id": session_id})
        tool_stats = list(cursor)
        
        # Get session timeline
        timeline_aql = """
        FOR doc IN log_events
        FILTER doc.execution_id == @session_id
        SORT doc.timestamp
        RETURN {
            timestamp: doc.timestamp,
            event: doc.extra_data.hook_event_type,
            tool: doc.extra_data.payload.tool_name,
            message: doc.message
        }
        """
        
        timeline_cursor = self.db.aql.execute(timeline_aql, bind_vars={"session_id": session_id})
        timeline = list(timeline_cursor)
        
        # Calculate duration if we have events
        duration = None
        if timeline:
            start = datetime.fromisoformat(timeline[0]["timestamp"])
            end = datetime.fromisoformat(timeline[-1]["timestamp"])
            duration = (end - start).total_seconds()
        
        return {
            "session_id": session_id,
            "tool_usage": tool_stats,
            "event_count": len(timeline),
            "duration_seconds": duration,
            "timeline_sample": timeline[:5]  # First 5 events
        }
    
    def get_recent_errors(self, hours: int = 24) -> List[Dict]:
        """Get recent errors and failures."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND (doc.level IN ["ERROR", "CRITICAL"] 
                 OR doc.extra_data.payload.return_code > 0
                 OR doc.extra_data.payload.success == false)
        SORT doc.timestamp DESC
        LIMIT 100
        RETURN {
            timestamp: doc.timestamp,
            level: doc.level,
            message: doc.message,
            tool: doc.extra_data.payload.tool_name,
            session: doc.execution_id,
            details: doc.extra_data.payload
        }
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"cutoff": cutoff.isoformat()})
        return list(cursor)


def main():
    """Main entry point for the tool."""
    parser = argparse.ArgumentParser(description="Query agent logs from ArangoDB")
    
    # Parse command from stdin (from tools.json)
    input_data = json.loads(sys.stdin.read())
    
    # Extract parameters
    action = input_data.get("action", "search")
    
    # Create tool instance
    tool = LogQueryTool()
    
    try:
        if action == "search":
            # Search logs with filters
            results = tool.search_logs(
                query=input_data.get("query", ""),
                filters={
                    "session_id": input_data.get("session_id"),
                    "tool_name": input_data.get("tool_name"),
                    "time_range_hours": input_data.get("time_range_hours", 24),
                    "event_type": input_data.get("event_type"),
                    "limit": input_data.get("limit", 50)
                }
            )
            
            output = {
                "status": "success",
                "action": "search",
                "query": input_data.get("query"),
                "result_count": len(results),
                "results": results
            }
            
        elif action == "session_summary":
            # Get session summary
            session_id = input_data.get("session_id")
            if not session_id:
                raise ValueError("session_id required for session_summary action")
            
            summary = tool.get_session_summary(session_id)
            
            output = {
                "status": "success",
                "action": "session_summary",
                "summary": summary
            }
            
        elif action == "recent_errors":
            # Get recent errors
            hours = input_data.get("hours", 24)
            errors = tool.get_recent_errors(hours)
            
            output = {
                "status": "success",
                "action": "recent_errors",
                "hours": hours,
                "error_count": len(errors),
                "errors": errors
            }
            
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Output results
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        error_output = {
            "status": "error",
            "error": str(e),
            "action": action
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


async def working_usage():
    """Test the tool functionality with test database."""
    print("Testing LogQueryTool...")
    
    # Import test utilities
    from src.utils.test_utils import with_test_db
    
    @with_test_db
    async def test_query_tool(test_db, test_db_name, manager):
        # Create tool with test database
        tool = LogQueryTool()
        tool.db = test_db
        
        # Insert test data
        log_events = test_db.collection("log_events")
        
        # Create test logs
        test_logs = []
        base_time = datetime.utcnow() - timedelta(hours=2)
        
        for i in range(10):
            test_logs.append({
                "timestamp": (base_time + timedelta(minutes=i*5)).isoformat(),
                "level": "INFO" if i % 3 != 0 else "ERROR",
                "message": f"Tool execution {i} with Bash",
                "execution_id": f"test_session_{i // 3}",
                "extra_data": {
                    "hook_event_type": "PostToolUse",
                    "payload": {
                        "tool_name": "Bash" if i % 2 == 0 else "Read",
                        "return_code": 0 if i % 3 != 0 else 1,
                        "success": i % 3 != 0
                    },
                    "summary": f"Test summary {i}"
                }
            })
        
        log_events.insert_many(test_logs)
        
        # Test 1: Search for bash commands
        print("\n1. Searching for Bash commands:")
        results = tool.search_logs("Bash", {"tool_name": "Bash", "limit": 5})
        print(f"Found {len(results)} Bash command logs")
        
        # Test 2: Get recent errors
        print("\n2. Getting recent errors:")
        errors = tool.get_recent_errors(24)
        print(f"Found {len(errors)} errors in last 24 hours")
        
        # Test 3: Session summary
        session_id = "test_session_0"
        print(f"\n3. Getting summary for session {session_id}:")
        summary = tool.get_session_summary(session_id)
        print(json.dumps(summary, indent=2))
        
        return True
    
    # Run the test
    return await test_query_tool()


async def debug_function():
    """Test tool with command-line interface using test database."""
    print("=== Debug Mode: Testing Command Interface ===")
    
    from src.utils.test_utils import TestEnvironment
    
    # Create test environment
    env = TestEnvironment()
    await env.setup()
    
    try:
        # Create tool with test database
        tool = LogQueryTool()
        tool.db = env.db
        
        # Insert test data
        log_events = env.db.collection("log_events")
        
        # Create test data with PreToolUse events
        test_logs = []
        base_time = datetime.utcnow() - timedelta(minutes=30)
        
        for i in range(15):
            test_logs.append({
                "timestamp": (base_time + timedelta(minutes=i*2)).isoformat(),
                "level": "INFO",
                "message": f"Tool use event {i}",
                "execution_id": f"debug_session_{i // 5}",
                "extra_data": {
                    "hook_event_type": "PreToolUse" if i % 2 == 0 else "PostToolUse",
                    "payload": {
                        "tool_name": ["Bash", "Read", "Write"][i % 3]
                    }
                }
            })
        
        log_events.insert_many(test_logs)
        
        # Test command interface
        test_input = {
            "action": "search",
            "query": "PreToolUse",
            "event_type": "PreToolUse",
            "limit": 10
        }
        
        print(f"Testing with input: {json.dumps(test_input, indent=2)}")
        
        # Mock stdin for command interface
        import io
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(test_input))
        
        # Patch the class to use test database
        old_db = None
        if hasattr(LogQueryTool, '_test_db'):
            old_db = LogQueryTool._test_db
        LogQueryTool._test_db = env.db
        
        try:
            main()
        finally:
            sys.stdin = old_stdin
            if old_db:
                LogQueryTool._test_db = old_db
            else:
                delattr(LogQueryTool, '_test_db')
        
        return True
        
    finally:
        await env.teardown()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["debug", "working"]:
        mode = sys.argv[1]
        if mode == "debug":
            success = asyncio.run(debug_function())
        else:
            success = asyncio.run(working_usage())
        sys.exit(0 if success else 1)
    else:
        main()