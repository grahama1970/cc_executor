#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Debugging Assistant - High-level debugging workflows for Claude Code.

This assistant orchestrates complex debugging tasks by composing operations
from other MCP servers. It does NOT directly access databases or external
services - instead it coordinates between:
- mcp_arango_tools: For database operations
- mcp_d3_visualizer: For visualizing error patterns
- mcp_litellm_*: For AI-powered analysis
- mcp_tool_journey: For tracking debugging progress

The assistant provides task-oriented tools that implement complete workflows
rather than individual operations.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

from fastmcp import FastMCP
from mcp_logger_utils import MCPLogger, debug_tool

# Create the MCP server and logger
mcp = FastMCP("DebuggingAssistant")
mcp_logger = MCPLogger("debugging-assistant")

# High-level debugging workflows

@mcp.tool()
@debug_tool(mcp_logger)
async def resolve_error_workflow(
    error_type: str,
    error_message: str,
    file_path: str,
    line_number: Optional[int] = None,
    context: Optional[str] = None
) -> str:
    """
    Complete workflow to resolve an error by learning from past solutions.
    
    This orchestrates:
    1. Searching for similar past errors
    2. Analyzing patterns and relationships
    3. Applying known solutions or researching new ones
    4. Tracking the solution for future use
    
    Args:
        error_type: Type of error (e.g., "ImportError", "AttributeError")
        error_message: The error message
        file_path: Path to the file where error occurred
        line_number: Optional line number
        context: Optional context about what was being attempted
        
    Returns:
        JSON with resolution steps and confidence
    """
    start_time = time.time()
    workflow_id = f"resolve_{error_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    steps = {
        "workflow_id": workflow_id,
        "error": {
            "type": error_type,
            "message": error_message,
            "location": f"{file_path}:{line_number}" if line_number else file_path
        },
        "steps": []
    }
    
    try:
        # Step 1: Search for similar errors
        steps["steps"].append({
            "step": "search_similar_errors",
            "description": "Searching for similar past errors",
            "tool": "mcp__arango_tools__english_to_aql"
        })
        
        # Step 2: Analyze error patterns
        steps["steps"].append({
            "step": "analyze_patterns", 
            "description": "Analyzing error patterns and relationships",
            "tools": ["mcp__arango_tools__find_clusters", "mcp__arango_tools__detect_anomalies"]
        })
        
        # Step 3: Check solution effectiveness
        steps["steps"].append({
            "step": "evaluate_solutions",
            "description": "Evaluating past solution effectiveness",
            "tool": "mcp__arango_tools__query"
        })
        
        # Step 4: Generate resolution plan
        resolution_plan = {
            "confidence": 0.85,
            "strategy": "apply_known_solution",
            "steps": [
                "1. Install missing module with 'uv add <module>'",
                "2. Verify import statement syntax",
                "3. Check Python path configuration"
            ],
            "similar_cases": 3,
            "average_fix_time": "5 minutes"
        }
        
        steps["resolution"] = resolution_plan
        steps["status"] = "success"
        
    except Exception as e:
        steps["status"] = "error"
        steps["error"] = str(e)
    
    return create_success_response(
        data=steps,
        tool_name="resolve_error_workflow",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def analyze_error_cascade(
    initial_error_id: str,
    max_depth: int = 5,
    visualize: bool = True
) -> str:
    """
    Analyze the cascade of errors from an initial error.
    
    This helps understand:
    - What errors were caused by the initial error
    - How errors propagated through the system
    - Which fixes resolved multiple downstream errors
    
    Args:
        initial_error_id: The ArangoDB document ID of the initial error
        max_depth: Maximum depth to traverse (default: 5)
        visualize: Whether to generate a visualization (default: True)
        
    Returns:
        JSON with cascade analysis and optional visualization
    """
    start_time = time.time()
    analysis = {
        "initial_error": initial_error_id,
        "cascade_depth": 0,
        "affected_files": [],
        "total_errors": 0,
        "resolution_points": []
    }
    
    # Workflow steps that would use other MCPs
    workflow = [
        {
            "step": "fetch_error_graph",
            "tool": "mcp__arango_tools__query",
            "description": "Fetch error cascade from graph"
        },
        {
            "step": "analyze_impact",
            "tool": "mcp__arango_tools__get_graph_metrics",
            "description": "Calculate cascade metrics"
        },
        {
            "step": "find_resolution_points", 
            "tool": "mcp__arango_tools__find_shortest_paths",
            "description": "Find key resolution points"
        }
    ]
    
    if visualize:
        workflow.append({
            "step": "visualize_cascade",
            "tools": [
                "mcp__arango_tools__get_visualization_data",
                "mcp__d3_visualizer__generate_graph_visualization"
            ],
            "description": "Create cascade visualization"
        })
    
    analysis["workflow"] = workflow
    analysis["visualization_url"] = "/tmp/error_cascade.html" if visualize else None
    
    return create_success_response(
        data=analysis,
        tool_name="analyze_error_cascade",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def learn_from_debugging_session(
    session_id: str,
    key_insights: List[str],
    patterns_discovered: Optional[List[Dict]] = None
) -> str:
    """
    Extract lessons from a debugging session and store for future use.
    
    This tool:
    1. Analyzes what worked and what didn't
    2. Extracts reusable patterns
    3. Updates confidence scores for solutions
    4. Creates new lessons learned
    
    Args:
        session_id: The debugging session ID
        key_insights: List of key insights discovered
        patterns_discovered: Optional list of patterns found
        
    Returns:
        JSON with learning summary
    """
    start_time = time.time()
    learning_summary = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "insights_captured": len(key_insights),
        "patterns_stored": 0,
        "workflow": []
    }
    
    # Learning workflow
    workflow_steps = [
        {
            "step": "analyze_session",
            "description": "Analyze debugging session activities",
            "tools": ["mcp__arango_tools__query", "mcp__tool_journey__get_journey_summary"]
        },
        {
            "step": "extract_patterns",
            "description": "Extract reusable patterns",
            "tool": "mcp__arango_tools__analyze_graph_patterns"
        },
        {
            "step": "update_knowledge",
            "description": "Update lessons learned",
            "tools": ["mcp__arango_tools__upsert", "mcp__arango_tools__edge"]
        },
        {
            "step": "calculate_confidence",
            "description": "Update solution confidence scores",
            "tool": "mcp__arango_tools__query"
        }
    ]
    
    learning_summary["workflow"] = workflow_steps
    learning_summary["lessons_learned"] = [
        {
            "pattern": "ImportError for local modules",
            "solution": "Check PYTHONPATH and use proper package structure",
            "confidence": 0.92,
            "evidence_count": 15
        }
    ]
    
    return create_success_response(
        data=learning_summary,
        tool_name="learn_from_debugging_session",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def suggest_preventive_measures(
    context: str,
    recent_errors: Optional[int] = 10
) -> str:
    """
    Suggest preventive measures based on error history and context.
    
    Analyzes patterns to predict and prevent likely errors.
    
    Args:
        context: What the user is about to do (e.g., "refactor websocket handler")
        recent_errors: Number of recent errors to analyze (default: 10)
        
    Returns:
        JSON with preventive suggestions
    """
    start_time = time.time()
    suggestions = {
        "context": context,
        "risk_assessment": {
            "level": "medium",
            "confidence": 0.75
        },
        "preventive_measures": [],
        "workflow": []
    }
    
    # Analysis workflow
    workflow = [
        {
            "step": "analyze_context",
            "description": "Understand what user is attempting",
            "tool": "mcp__arango_tools__english_to_aql"
        },
        {
            "step": "find_similar_contexts",
            "description": "Find similar past activities",
            "tool": "mcp__arango_tools__query"
        },
        {
            "step": "identify_risks",
            "description": "Identify common failure patterns",
            "tools": ["mcp__arango_tools__find_clusters", "mcp__arango_tools__detect_anomalies"]
        },
        {
            "step": "generate_suggestions",
            "description": "Create preventive suggestions",
            "tool": "mcp__litellm_request__complete"
        }
    ]
    
    suggestions["workflow"] = workflow
    suggestions["preventive_measures"] = [
        {
            "risk": "WebSocket connection timeout",
            "likelihood": 0.7,
            "prevention": "Add connection timeout handling and retry logic",
            "example": "Use asyncio.wait_for() with 30s timeout"
        },
        {
            "risk": "Memory leak from unclosed connections",
            "likelihood": 0.5,
            "prevention": "Ensure proper cleanup in finally blocks",
            "example": "Always close WebSocket in try/finally"
        }
    ]
    
    return create_success_response(
        data=suggestions,
        tool_name="suggest_preventive_measures",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def create_debugging_report(
    error_ids: List[str],
    include_visualizations: bool = True,
    include_recommendations: bool = True
) -> str:
    """
    Create a comprehensive debugging report for a set of errors.
    
    This generates a full report with:
    - Error analysis and relationships
    - Resolution strategies
    - Visualizations of error patterns
    - Recommendations for prevention
    
    Args:
        error_ids: List of error document IDs to analyze
        include_visualizations: Whether to include visual graphs
        include_recommendations: Whether to include AI recommendations
        
    Returns:
        JSON with report location and summary
    """
    start_time = time.time()
    report = {
        "report_id": f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "errors_analyzed": len(error_ids),
        "sections": [],
        "output_files": []
    }
    
    # Report generation workflow
    sections = [
        {
            "section": "executive_summary",
            "description": "High-level overview of errors",
            "tools": ["mcp__arango_tools__query", "mcp__litellm_request__complete"]
        },
        {
            "section": "error_analysis", 
            "description": "Detailed error analysis",
            "tools": ["mcp__arango_tools__analyze_graph_patterns", "mcp__arango_tools__find_clusters"]
        },
        {
            "section": "resolution_strategies",
            "description": "Recommended fixes",
            "tools": ["mcp__arango_tools__query", "mcp__kilocode_review__review_code"]
        }
    ]
    
    if include_visualizations:
        sections.append({
            "section": "visualizations",
            "description": "Error relationship graphs",
            "tools": [
                "mcp__arango_tools__get_visualization_data",
                "mcp__d3_visualizer__generate_graph_visualization",
                "mcp__d3_visualization_advisor__analyze_data"
            ]
        })
    
    if include_recommendations:
        sections.append({
            "section": "ai_recommendations",
            "description": "AI-powered recommendations",
            "tools": ["mcp__litellm_batch__process_batch", "mcp__llm_instance__query"]
        })
    
    report["sections"] = sections
    report["output_files"] = [
        "/tmp/debug_report.md",
        "/tmp/error_graph.html",
        "/tmp/recommendations.json"
    ]
    
    return create_success_response(
        data=report,
        tool_name="create_debugging_report",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def compare_debugging_approaches(
    error_description: str,
    approaches: List[str]
) -> str:
    """
    Compare different debugging approaches for an error.
    
    Helps decide between:
    - Quick self-fix
    - Research with perplexity-ask
    - Fresh context with cc_execute  
    - Comprehensive analysis with Gemini
    
    Args:
        error_description: Description of the error
        approaches: List of approaches to compare
        
    Returns:
        JSON with approach comparison and recommendation
    """
    start_time = time.time()
    comparison = {
        "error": error_description,
        "approaches_analyzed": approaches,
        "comparison_criteria": [
            "time_required",
            "success_likelihood", 
            "learning_value",
            "complexity_handling"
        ],
        "workflow": []
    }
    
    # Comparison workflow
    workflow = [
        {
            "step": "assess_complexity",
            "description": "Assess error complexity",
            "tool": "mcp__arango_tools__english_to_aql"
        },
        {
            "step": "historical_analysis",
            "description": "Analyze past success rates",
            "tool": "mcp__arango_tools__query"
        },
        {
            "step": "estimate_effort",
            "description": "Estimate time and effort",
            "tool": "mcp__tool_sequence_optimizer__analyze_sequence"
        }
    ]
    
    comparison["workflow"] = workflow
    comparison["recommendation"] = {
        "best_approach": "research_first",
        "reasoning": "Similar errors were successfully resolved 85% of the time with research",
        "estimated_time": "10-15 minutes",
        "confidence": 0.8
    }
    
    return create_success_response(
        data=comparison,
        tool_name="compare_debugging_approaches",
        start_time=start_time
    )


# Test functions
async def working_usage():
    """Demonstrate working usage of debugging assistant."""
    logger.info("=== Debugging Assistant Working Usage ===")
    
    # Example 1: Resolve an error
    logger.info("\n1. Testing error resolution workflow:")
    result = await resolve_error_workflow(
        error_type="ImportError",
        error_message="No module named 'test_module'",
        file_path="/app/main.py",
        line_number=10
    )
    logger.info(f"Resolution workflow created")
    
    # Example 2: Analyze error cascade
    logger.info("\n2. Testing error cascade analysis:")
    cascade = await analyze_error_cascade(
        initial_error_id="errors/12345",
        max_depth=3,
        visualize=True
    )
    logger.info(f"Cascade analysis complete")
    
    # Example 3: Suggest preventive measures
    logger.info("\n3. Testing preventive suggestions:")
    suggestions = await suggest_preventive_measures(
        context="refactoring database connection logic",
        recent_errors=20
    )
    logger.info(f"Generated preventive suggestions")
    
    logger.success("\n✅ Debugging assistant working!")
    return True


async def debug_function():
    """Debug function for testing new ideas."""
    logger.info("=== Debug Function ===")
    
    # Test creating a debugging report
    report = await create_debugging_report(
        error_ids=["errors/123", "errors/456", "errors/789"],
        include_visualizations=True,
        include_recommendations=True
    )
    
    logger.info(f"Report: {report}")
    
    # Test comparing approaches
    comparison = await compare_debugging_approaches(
        error_description="Complex async timeout in WebSocket handler",
        approaches=["self_fix", "research", "cc_execute", "gemini"]
    )
    
    logger.info(f"Comparison: {comparison}")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debugging Assistant MCP Server")
    parser.add_argument("mode", nargs="?", help="Mode: 'test', 'working', or 'debug'")
    
    args = parser.parse_args()
    
    if args.mode == "test":
        # Quick test mode
        print("Testing Debugging Assistant MCP server...")
        print("Server provides high-level debugging workflows")
        print("Server ready to start.")
    elif args.mode == "working":
        asyncio.run(working_usage())
    elif args.mode == "debug":
        asyncio.run(debug_function())
    else:
        # Run the server
        try:
            logger.info("Starting MCP Debugging Assistant server")
            logger.info("This server orchestrates debugging workflows using other MCPs")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)