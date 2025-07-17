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
Custom tool for analyzing agent performance from logs.

This tool provides insights into:
- Execution patterns
- Common failures
- Performance metrics
- Tool usage statistics

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python analyze_agent_performance.py          # Runs working_usage() - stable, known to work
  python analyze_agent_performance.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arango import ArangoClient
from typing import Dict, List, Any, Optional


class PerformanceAnalyzer:
    """Analyze agent performance from logs."""
    
    def __init__(self):
        # Check if we're in test mode
        if hasattr(self.__class__, '_test_db'):
            self.db = self.__class__._test_db
            self.client = None
        else:
            self.client = ArangoClient(hosts='http://localhost:8529')
            self.db = self.client.db('script_logs', username='root', password='openSesame')
    
    def analyze_tool_performance(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze performance metrics by tool."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Get tool execution times
        aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND doc.extra_data.hook_event_type == "PostToolUse"
            AND doc.extra_data.payload.duration_ms != null
        COLLECT tool = doc.extra_data.payload.tool_name INTO executions
        RETURN {
            tool: tool,
            count: LENGTH(executions),
            avg_duration_ms: AVG(executions[*].doc.extra_data.payload.duration_ms),
            max_duration_ms: MAX(executions[*].doc.extra_data.payload.duration_ms),
            min_duration_ms: MIN(executions[*].doc.extra_data.payload.duration_ms)
        }
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"cutoff": cutoff.isoformat()})
        tool_stats = list(cursor)
        
        # Get failure rates
        failure_aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND doc.extra_data.hook_event_type == "PostToolUse"
            AND (doc.extra_data.payload.success == false 
                 OR doc.extra_data.payload.return_code > 0)
        COLLECT tool = doc.extra_data.payload.tool_name WITH COUNT INTO failures
        RETURN {tool: tool, failures: failures}
        """
        
        failure_cursor = self.db.aql.execute(failure_aql, bind_vars={"cutoff": cutoff.isoformat()})
        failures = {item["tool"]: item["failures"] for item in failure_cursor}
        
        # Combine stats
        for stat in tool_stats:
            tool = stat["tool"]
            stat["failure_count"] = failures.get(tool, 0)
            stat["success_rate"] = (stat["count"] - stat["failure_count"]) / stat["count"] if stat["count"] > 0 else 0
        
        return {
            "time_range_hours": hours,
            "tool_performance": tool_stats,
            "total_executions": sum(s["count"] for s in tool_stats),
            "overall_success_rate": sum(s["success_rate"] * s["count"] for s in tool_stats) / sum(s["count"] for s in tool_stats) if tool_stats else 0
        }
    
    def find_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Find common execution patterns."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Get tool sequences
        aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND doc.extra_data.hook_event_type IN ["PreToolUse", "PostToolUse"]
        SORT doc.timestamp
        RETURN {
            session: doc.execution_id,
            timestamp: doc.timestamp,
            tool: doc.extra_data.payload.tool_name,
            event: doc.extra_data.hook_event_type
        }
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"cutoff": cutoff.isoformat()})
        events = list(cursor)
        
        # Group by session
        sessions = defaultdict(list)
        for event in events:
            if event["event"] == "PreToolUse":
                sessions[event["session"]].append(event["tool"])
        
        # Find common sequences
        sequence_counts = defaultdict(int)
        for session_tools in sessions.values():
            # Look at pairs of tools
            for i in range(len(session_tools) - 1):
                pair = f"{session_tools[i]} -> {session_tools[i+1]}"
                sequence_counts[pair] += 1
            
            # Look at triplets
            for i in range(len(session_tools) - 2):
                triplet = f"{session_tools[i]} -> {session_tools[i+1]} -> {session_tools[i+2]}"
                sequence_counts[triplet] += 1
        
        # Get most common
        common_sequences = sorted(sequence_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "time_range_hours": hours,
            "total_sessions": len(sessions),
            "common_sequences": [{"pattern": seq, "count": count} for seq, count in common_sequences],
            "avg_tools_per_session": statistics.mean([len(tools) for tools in sessions.values()]) if sessions else 0
        }
    
    def get_error_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error patterns."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Get errors by type
        aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND (doc.level IN ["ERROR", "CRITICAL"]
                 OR doc.extra_data.payload.return_code > 0
                 OR doc.extra_data.payload.success == false)
        LET error_type = (
            doc.level == "ERROR" ? "log_error" :
            doc.level == "CRITICAL" ? "critical_error" :
            doc.extra_data.payload.return_code > 0 ? "command_failed" :
            doc.extra_data.payload.success == false ? "operation_failed" :
            "unknown"
        )
        COLLECT type = error_type, tool = doc.extra_data.payload.tool_name INTO errors
        RETURN {
            error_type: type,
            tool: tool,
            count: LENGTH(errors),
            recent_examples: (
                FOR e IN errors
                SORT e.doc.timestamp DESC
                LIMIT 3
                RETURN {
                    timestamp: e.doc.timestamp,
                    message: e.doc.message,
                    details: e.doc.extra_data.payload
                }
            )
        }
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"cutoff": cutoff.isoformat()})
        error_analysis = list(cursor)
        
        # Get recovery patterns (errors followed by success)
        recovery_aql = """
        FOR doc IN log_events
        FILTER doc.timestamp >= @cutoff
            AND doc.extra_data.hook_event_type == "PostToolUse"
        LET next_event = (
            FOR next IN log_events
            FILTER next.execution_id == doc.execution_id
                AND next.timestamp > doc.timestamp
                AND next.extra_data.hook_event_type == "PostToolUse"
                AND next.extra_data.payload.tool_name == doc.extra_data.payload.tool_name
            SORT next.timestamp
            LIMIT 1
            RETURN next
        )[0]
        FILTER doc.extra_data.payload.success == false
            AND next_event != null
            AND next_event.extra_data.payload.success == true
        COLLECT tool = doc.extra_data.payload.tool_name WITH COUNT INTO recoveries
        RETURN {tool: tool, recovery_count: recoveries}
        """
        
        recovery_cursor = self.db.aql.execute(recovery_aql, bind_vars={"cutoff": cutoff.isoformat()})
        recoveries = list(recovery_cursor)
        
        return {
            "time_range_hours": hours,
            "error_breakdown": error_analysis,
            "total_errors": sum(e["count"] for e in error_analysis),
            "recovery_patterns": recoveries
        }


def main():
    """Main entry point for the tool."""
    # Parse command from stdin
    input_data = json.loads(sys.stdin.read())
    
    # Extract parameters
    analysis_type = input_data.get("analysis_type", "performance")
    hours = input_data.get("hours", 24)
    
    # Create analyzer
    analyzer = PerformanceAnalyzer()
    
    try:
        if analysis_type == "performance":
            result = analyzer.analyze_tool_performance(hours)
        elif analysis_type == "patterns":
            result = analyzer.find_patterns(hours)
        elif analysis_type == "errors":
            result = analyzer.get_error_analysis(hours)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        output = {
            "status": "success",
            "analysis_type": analysis_type,
            "result": result
        }
        
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        error_output = {
            "status": "error",
            "error": str(e),
            "analysis_type": analysis_type
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


async def working_usage():
    """Demonstrate analyzer functionality with test database."""
    print("Testing Performance Analyzer...")
    
    # Import test utilities
    from src.utils.test_utils import with_test_db
    
    @with_test_db
    async def test_analyzer(test_db, test_db_name, manager):
        # Create analyzer with test database
        analyzer = PerformanceAnalyzer()
        analyzer.db = test_db
        
        # Insert some test data
        log_events = test_db.collection("log_events")
        
        # Create test logs with tool usage
        test_logs = []
        base_time = datetime.utcnow() - timedelta(hours=2)
        tools = ["Bash", "Read", "Write", "Edit"]
        
        for i in range(20):
            test_logs.append({
                "timestamp": (base_time + timedelta(minutes=i*3)).isoformat(),
                "level": "INFO",
                "message": f"Tool execution {i}",
                "execution_id": f"test_exec_{i // 5}",
                "extra_data": {
                    "hook_event_type": "PostToolUse",
                    "payload": {
                        "tool_name": tools[i % len(tools)],
                        "duration_ms": 100 + (i * 10),
                        "success": i % 5 != 0,  # Some failures
                        "return_code": 0 if i % 5 != 0 else 1
                    }
                }
            })
        
        log_events.insert_many(test_logs)
        
        # Test 1: Tool performance
        print("\n1. Analyzing tool performance:")
        perf = await analyzer.analyze_tool_performance(24)
        print(f"Total executions: {perf['total_executions']}")
        print(f"Overall success rate: {perf['overall_success_rate']:.2%}")
        
        # Test 2: Execution patterns
        print("\n2. Finding execution patterns:")
        patterns = await analyzer.find_patterns(24)
        print(f"Sessions analyzed: {patterns['total_sessions']}")
        print(f"Avg tools per session: {patterns['avg_tools_per_session']:.1f}")
        
        # Test 3: Error analysis
        print("\n3. Analyzing errors:")
        errors = await analyzer.get_error_analysis(24)
        print(f"Total errors: {errors['total_errors']}")
        
        return True
    
    # Run the test
    return await test_analyzer()


async def debug_function():
    """Test with command interface using test database."""
    print("=== Debug Mode: Testing Command Interface ===")
    
    from src.utils.test_utils import TestEnvironment
    
    # Create test environment
    env = TestEnvironment()
    await env.setup()
    
    try:
        # Create analyzer with test database
        analyzer = PerformanceAnalyzer()
        analyzer.db = env.db
        
        # Insert test data
        log_events = env.db.collection("log_events")
        
        # Create error logs for testing
        test_errors = []
        base_time = datetime.utcnow() - timedelta(hours=1)
        
        for i in range(10):
            test_errors.append({
                "timestamp": (base_time + timedelta(minutes=i*5)).isoformat(),
                "level": "ERROR" if i % 2 == 0 else "CRITICAL",
                "message": f"Test error {i}",
                "execution_id": f"error_exec_{i // 3}",
                "extra_data": {
                    "hook_event_type": "PostToolUse",
                    "payload": {
                        "tool_name": "Bash",
                        "success": False,
                        "return_code": 1
                    }
                }
            })
        
        log_events.insert_many(test_errors)
        
        # Test command interface
        test_input = {
            "analysis_type": "errors",
            "hours": 24
        }
        
        print(f"Testing with input: {json.dumps(test_input, indent=2)}")
        
        # Mock stdin for command interface
        import io
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(test_input))
        
        # Temporarily replace the analyzer in main()
        old_db = None
        if hasattr(PerformanceAnalyzer, '_test_db'):
            old_db = PerformanceAnalyzer._test_db
        PerformanceAnalyzer._test_db = env.db
        
        try:
            # Note: main() creates its own analyzer, so we need to patch the class
            main()
        finally:
            sys.stdin = old_stdin
            if old_db:
                PerformanceAnalyzer._test_db = old_db
            else:
                delattr(PerformanceAnalyzer, '_test_db')
        
        return True
        
    finally:
        await env.teardown()


if __name__ == "__main__":
    import asyncio
    
    if len(sys.argv) > 1 and sys.argv[1] in ["debug", "working"]:
        mode = sys.argv[1]
        if mode == "debug":
            success = asyncio.run(debug_function())
        else:
            success = asyncio.run(working_usage())
        sys.exit(0 if success else 1)
    else:
        main()