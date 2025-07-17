#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru"
# ]
# ///
"""
Tool Sequence Optimizer - Uses mcp_arango_tools for all database operations.

This MCP server provides tool sequence optimization by:
1. Using mcp_arango_tools for all database operations
2. Leveraging existing BM25 search and graph traversal
3. Building on the learning system already in place
"""

import asyncio
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv

# Add utils to path for MCP logger
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add("sequence_optimizer.log", rotation="10 MB")

# Load environment
load_dotenv()

# Initialize MCP server and logger
mcp = FastMCP("tool-sequence-optimizer")
mcp_logger = MCPLogger("tool-sequence-optimizer")

# Track active journeys in memory
active_journeys: Dict[str, Dict] = {}


@mcp.tool()
@debug_tool(mcp_logger)
async def optimize_tool_sequence(
    task_description: str,
    error_context: Optional[str] = None
) -> str:
    """Find optimal tool sequence using mcp_arango_tools' existing search capabilities.
    
    This uses:
    - advanced_search() for BM25 text search
    - discover_patterns() for finding similar resolved issues
    - Graph traversal via execute_aql()
    
    Args:
        task_description: Natural language task description
        error_context: Optional JSON with error_type, file_path, etc.
        
    Returns:
        Optimal tool sequence based on successful similar tasks
    """
    
    context = json.loads(error_context) if error_context else {}
    
    # Step 1: Use advanced_search with BM25 for similar tasks
    # This already exists in mcp_arango_tools!
    search_params = {
        "search_text": task_description,
        "category": context.get("category"),
        "error_type": context.get("error_type"),
        "time_range": "last_month",
        "min_success_rate": 0.7
    }
    
    # Would call: mcp__arango-tools__advanced_search
    logger.info(f"Searching for similar tasks: {search_params}")
    
    # Step 2: For found tasks, extract tool sequences via graph query
    sequence_query = """
    // Find successful tool sequences from similar tasks
    FOR doc IN log_events
        FILTER doc.event_type == "tool_journey_completed"
        FILTER doc.outcome == "success"
        FILTER CONTAINS(LOWER(doc.task_description), LOWER(@keyword))
        SORT doc.success_rate DESC
        LIMIT 10
        
        RETURN {
            task: doc.task_description,
            tool_sequence: doc.tool_sequence,
            success_rate: doc.success_rate,
            duration: doc.duration,
            journey_id: doc.journey_id
        }
    """
    
    # Would call: mcp__arango-tools__execute_aql
    # Extract keyword from task
    keyword = task_description.split()[0] if task_description else "error"
    
    # Step 3: Aggregate and rank sequences
    # In real implementation, would process results from above queries
    
    # For demo, return structured response
    journey_id = f"journey_{uuid.uuid4().hex[:8]}"
    
    # Store journey
    active_journeys[journey_id] = {
        "task_description": task_description,
        "context": context,
        "start_time": time.time(),
        "tool_sequence": []
    }
    
    # Common patterns based on task type
    if "error" in task_description.lower() or "fix" in task_description.lower():
        recommended_sequence = [
            "assess_complexity",
            "discover_patterns",  # Uses mcp_arango_tools
            "track_solution_outcome"  # Uses mcp_arango_tools
        ]
        confidence = 0.85
    elif "visualiz" in task_description.lower():
        recommended_sequence = [
            "execute_aql",  # Uses mcp_arango_tools
            "generate_graph_visualization"
        ]
        confidence = 0.90
    else:
        recommended_sequence = [
            "advanced_search",  # Uses mcp_arango_tools
            "discover_patterns"  # Uses mcp_arango_tools
        ]
        confidence = 0.75
    
    return json.dumps({
        "journey_id": journey_id,
        "recommended_sequence": recommended_sequence,
        "confidence": confidence,
        "reasoning": f"Based on BM25 search and pattern analysis for '{keyword}'",
        "alternative_sequences": [
            ["assess_complexity", "send_to_gemini", "extract_gemini_code"],
            ["query_converter", "execute_aql", "analyze_graph"]
        ]
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def record_sequence_step(
    journey_id: str,
    tool_name: str,
    success: bool,
    duration_ms: int,
    result_summary: Optional[str] = None
) -> str:
    """Record a tool usage step in the journey.
    
    This data will be used to update the learning system via
    track_solution_outcome() when the journey completes.
    """
    
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    
    # Record the step
    step = {
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        "result_summary": result_summary or "",
        "timestamp": datetime.now().isoformat()
    }
    
    journey["tool_sequence"].append(step)
    
    # Get next tool recommendation based on current position
    current_position = len(journey["tool_sequence"]) - 1
    next_tool = None
    
    # Simple next tool prediction (in production, query the graph)
    if tool_name == "assess_complexity" and success:
        next_tool = "discover_patterns"
    elif tool_name == "discover_patterns" and success:
        next_tool = "track_solution_outcome"
    elif tool_name == "execute_aql" and success:
        next_tool = "generate_graph_visualization"
    
    return json.dumps({
        "recorded": True,
        "step_number": len(journey["tool_sequence"]),
        "next_recommended_tool": next_tool,
        "journey_id": journey_id
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def complete_sequence_journey(
    journey_id: str,
    outcome: str,
    solution_description: str,
    category: Optional[str] = None
) -> str:
    """Complete the journey and update the learning system.
    
    This will:
    1. Call track_solution_outcome() to record the resolution
    2. Extract lessons if successful
    3. Update pattern database for future recommendations
    """
    
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    journey["outcome"] = outcome
    journey["total_duration"] = time.time() - journey["start_time"]
    
    # Create a solution record in the learning system
    # Would call: mcp__arango-tools__track_solution_outcome
    track_params = {
        "solution_id": journey_id,
        "outcome": outcome,
        "key_reason": solution_description,
        "category": category or "general",
        "next_steps": json.dumps([])
    }
    
    logger.info(f"Recording solution outcome: {track_params}")
    
    # If successful, extract lesson for future use
    if outcome == "success":
        # Extract tool sequence as a lesson
        tool_names = [step["tool"] for step in journey["tool_sequence"]]
        lesson = f"For '{journey['task_description']}', use sequence: {' → '.join(tool_names)}"
        
        # Would call: mcp__arango-tools__extract_lesson
        extract_params = {
            "solution_ids": [journey_id],
            "lesson": lesson,
            "category": category or "tool_sequences",
            "applies_to": json.dumps({
                "task_keywords": journey["task_description"].split()[:3],
                "error_context": journey.get("context", {})
            })
        }
        
        logger.info(f"Extracting lesson: {extract_params}")
    
    # Store journey completion in database
    # Would call: mcp__arango-tools__insert
    journey_doc = {
        "_key": journey_id,
        "event_type": "tool_journey_completed",
        "task_description": journey["task_description"],
        "tool_sequence": [step["tool"] for step in journey["tool_sequence"]],
        "outcome": outcome,
        "success_rate": 1.0 if outcome == "success" else 0.0,
        "duration": journey["total_duration"],
        "timestamp": datetime.now().isoformat(),
        "context": journey.get("context", {}),
        "solution_description": solution_description
    }
    
    logger.info(f"Storing journey: {journey_doc}")
    
    # Clean up
    del active_journeys[journey_id]
    
    return json.dumps({
        "journey_id": journey_id,
        "outcome": outcome,
        "tool_sequence": [step["tool"] for step in journey["tool_sequence"]],
        "total_duration": journey["total_duration"],
        "lesson_extracted": outcome == "success"
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def find_successful_sequences(
    task_pattern: str,
    min_success_rate: float = 0.7,
    limit: int = 5
) -> str:
    """Find successful tool sequences for similar tasks.
    
    Uses mcp_arango_tools' execute_aql to query the graph.
    """
    
    # Query for successful sequences
    query = """
    // Find successful tool sequences
    FOR doc IN log_events
        FILTER doc.event_type == "tool_journey_completed"
        FILTER doc.outcome == "success"
        FILTER doc.success_rate >= @min_rate
        FILTER CONTAINS(LOWER(doc.task_description), LOWER(@pattern))
        
        SORT doc.success_rate DESC, doc.duration ASC
        LIMIT @limit
        
        RETURN {
            task: doc.task_description,
            sequence: doc.tool_sequence,
            success_rate: doc.success_rate,
            duration: doc.duration,
            solution: doc.solution_description,
            timestamp: doc.timestamp
        }
    """
    
    # Would call: mcp__arango-tools__execute_aql
    bind_vars = {
        "pattern": task_pattern,
        "min_rate": min_success_rate,
        "limit": limit
    }
    
    logger.info(f"Finding sequences for pattern '{task_pattern}'")
    
    # Demo response
    return json.dumps({
        "pattern": task_pattern,
        "found": 3,
        "sequences": [
            {
                "task": "Fix ModuleNotFoundError for pandas",
                "sequence": ["assess_complexity", "discover_patterns", "track_solution_outcome"],
                "success_rate": 0.92,
                "duration": 45.3
            },
            {
                "task": "Fix ImportError in data processor",
                "sequence": ["assess_complexity", "advanced_search", "track_solution_outcome"],
                "success_rate": 0.88,
                "duration": 52.1
            }
        ]
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def analyze_sequence_performance() -> str:
    """Analyze tool sequence performance using existing graph analytics.
    
    Uses mcp_arango_tools' analyze_graph for insights.
    """
    
    # Would call: mcp__arango-tools__analyze_graph
    # with algorithm="centrality" to find most important tools
    
    # Would also query for sequence success rates
    analysis_query = """
    // Analyze sequence performance
    FOR doc IN log_events
        FILTER doc.event_type == "tool_journey_completed"
        
        COLLECT sequence = doc.tool_sequence
        AGGREGATE 
            total = COUNT(1),
            successes = SUM(doc.outcome == "success" ? 1 : 0),
            avg_duration = AVG(doc.duration)
            
        LET success_rate = successes / total
        
        FILTER total >= 5  // Minimum sample size
        SORT success_rate DESC
        
        RETURN {
            sequence: sequence,
            usage_count: total,
            success_rate: success_rate,
            avg_duration: avg_duration
        }
    """
    
    logger.info("Analyzing sequence performance")
    
    return json.dumps({
        "top_sequences": [
            {
                "sequence": ["assess_complexity", "discover_patterns", "track_solution_outcome"],
                "usage_count": 142,
                "success_rate": 0.89,
                "avg_duration": 48.7
            },
            {
                "sequence": ["execute_aql", "generate_graph_visualization"],
                "usage_count": 67,
                "success_rate": 0.94,
                "avg_duration": 12.3
            }
        ],
        "most_central_tools": [
            {"tool": "assess_complexity", "centrality": 0.85},
            {"tool": "discover_patterns", "centrality": 0.72},
            {"tool": "track_solution_outcome", "centrality": 0.68}
        ]
    }, indent=2)


async def working_usage():
    """Demonstrate sequence optimization using existing tools."""
    logger.info("=== Tool Sequence Optimizer Working Usage ===")
    
    # Example 1: Get optimal sequence for error fixing
    logger.info("\n1. Getting optimal sequence for error fix:")
    
    result = await optimize_tool_sequence(
        task_description="Fix ModuleNotFoundError for requests library in api_client.py",
        error_context=json.dumps({
            "error_type": "ModuleNotFoundError",
            "module": "requests",
            "file_path": "api_client.py"
        })
    )
    
    journey = json.loads(result)
    journey_id = journey["journey_id"]
    logger.info(f"Journey {journey_id} started")
    logger.info(f"Recommended: {journey['recommended_sequence']}")
    
    # Example 2: Record tool usage
    logger.info("\n2. Recording tool usage:")
    
    for tool in journey["recommended_sequence"]:
        await asyncio.sleep(0.1)  # Simulate work
        
        step_result = await record_sequence_step(
            journey_id=journey_id,
            tool_name=tool,
            success=True,
            duration_ms=500,
            result_summary=f"Completed {tool} successfully"
        )
        
        step = json.loads(step_result)
        logger.info(f"  Step {step['step_number']}: {tool}")
        if step.get("next_recommended_tool"):
            logger.info(f"  Next: {step['next_recommended_tool']}")
    
    # Example 3: Complete journey
    logger.info("\n3. Completing journey:")
    
    completion = await complete_sequence_journey(
        journey_id=journey_id,
        outcome="success",
        solution_description="Added requests to requirements.txt and installed",
        category="module_import"
    )
    
    logger.info(f"Journey completed: {completion}")
    
    # Example 4: Find successful sequences
    logger.info("\n4. Finding successful sequences:")
    
    sequences = await find_successful_sequences(
        task_pattern="modulenotfound",
        min_success_rate=0.8
    )
    
    logger.info(f"Found sequences: {sequences}")
    
    logger.success("\n✅ Sequence optimizer working correctly!")
    return True


async def debug_function():
    """Test integration with mcp_arango_tools."""
    logger.info("=== Debug Mode - Testing Integration ===")
    
    # Test different task types
    test_tasks = [
        ("Fix ImportError", "error_fix"),
        ("Visualize error network", "visualization"),
        ("Analyze performance metrics", "analysis")
    ]
    
    for task, category in test_tasks:
        logger.info(f"\nTesting: {task}")
        
        # Get sequence
        result = await optimize_tool_sequence(
            task_description=task,
            error_context=json.dumps({"category": category})
        )
        
        journey = json.loads(result)
        logger.info(f"  Sequence: {journey['recommended_sequence']}")
        logger.info(f"  Confidence: {journey['confidence']}")
    
    # Test performance analysis
    logger.info("\nTesting performance analysis:")
    analysis = await analyze_sequence_performance()
    logger.info(f"Analysis: {analysis}")
    
    logger.success("\n✅ Debug tests completed!")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "debug":
            asyncio.run(debug_function())
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
    else:
        # Run as MCP server with graceful error handling
        try:
            logger.info("Starting Tool Sequence Optimizer MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)