#!/usr/bin/env python3
"""
Direct testing of MCP tool functionality.

This script tests the actual MCP tool functions by calling them directly.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_arango_tools():
    """Test ArangoDB tools functionality."""
    logger.info("\n=== Testing ArangoDB Tools ===")
    
    try:
        # Import the tools
        from cc_executor.servers.mcp_arango_tools import (
            get_schema, execute_aql, query, advanced_search
        )
        
        # Test 1: Get schema
        logger.info("\n1. Testing get_schema:")
        schema_result = await get_schema()
        schema_data = json.loads(schema_result)
        logger.info(f"   Collections: {len(schema_data.get('collections', []))}")
        logger.info(f"   Graphs: {len(schema_data.get('graphs', []))}")
        
        # Test 2: Execute simple AQL
        logger.info("\n2. Testing execute_aql:")
        aql_result = await execute_aql(
            'FOR doc IN log_events LIMIT 3 RETURN {"id": doc._id, "type": doc.event_type}'
        )
        aql_data = json.loads(aql_result)
        logger.info(f"   Found {len(aql_data)} documents")
        
        # Test 3: Advanced search
        logger.info("\n3. Testing advanced_search:")
        search_result = await advanced_search(
            collections="log_events",
            text_query="error",
            limit=5
        )
        search_data = json.loads(search_result)
        logger.info(f"   Found {search_data.get('total', 0)} matches")
        
        logger.success("✅ ArangoDB tools working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ArangoDB tools failed: {e}")
        return False


async def test_d3_visualizer():
    """Test D3 visualizer functionality."""
    logger.info("\n=== Testing D3 Visualizer ===")
    
    try:
        from cc_executor.servers.mcp_d3_visualizer import (
            generate_graph_visualization, list_visualizations
        )
        
        # Test 1: Generate visualization
        logger.info("\n1. Testing generate_graph_visualization:")
        
        graph_data = {
            "nodes": [
                {"id": "1", "label": "Node A", "type": "start"},
                {"id": "2", "label": "Node B", "type": "process"},
                {"id": "3", "label": "Node C", "type": "end"}
            ],
            "links": [
                {"source": "1", "target": "2", "value": 1},
                {"source": "2", "target": "3", "value": 2}
            ]
        }
        
        viz_result = await generate_graph_visualization(
            graph_data=json.dumps(graph_data),
            layout="force",
            title="Test Graph"
        )
        viz_data = json.loads(viz_result)
        logger.info(f"   Created: {viz_data.get('filepath', 'Unknown')}")
        
        # Test 2: List visualizations
        logger.info("\n2. Testing list_visualizations:")
        list_result = await list_visualizations()
        list_data = json.loads(list_result)
        logger.info(f"   Found {len(list_data.get('visualizations', []))} visualizations")
        
        logger.success("✅ D3 Visualizer working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ D3 Visualizer failed: {e}")
        return False


async def test_logger_tools():
    """Test logger tools functionality."""
    logger.info("\n=== Testing Logger Tools ===")
    
    try:
        from cc_executor.servers.mcp_debugging_assistant import (
            assess_complexity, query_agent_logs, analyze_agent_performance
        )
        
        # Test 1: Assess complexity
        logger.info("\n1. Testing assess_complexity:")
        complexity_result = await assess_complexity(
            error_type="ModuleNotFoundError",
            error_message="No module named 'test_module'",
            file_path="/test/file.py"
        )
        complexity_data = json.loads(complexity_result)
        logger.info(f"   Assessment: {complexity_data}")
        
        # Test 2: Query logs
        logger.info("\n2. Testing query_agent_logs:")
        logs_result = await query_agent_logs(
            action="search",
            event_type="tool_use",
            limit=5
        )
        logs_data = json.loads(logs_result)
        logger.info(f"   Found {len(logs_data.get('logs', []))} log entries")
        
        # Test 3: Analyze performance
        logger.info("\n3. Testing analyze_agent_performance:")
        perf_result = await analyze_agent_performance(
            analysis_type="tool_usage"
        )
        perf_data = json.loads(perf_result)
        logger.info(f"   Analysis complete: {perf_data.get('summary', 'No summary')}")
        
        logger.success("✅ Logger tools working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Logger tools failed: {e}")
        return False


async def test_tool_journey():
    """Test tool journey functionality."""
    logger.info("\n=== Testing Tool Journey ===")
    
    try:
        # Import test functions since decorated ones can't be called directly
        from cc_executor.servers.mcp_tool_journey import (
            _test_start_journey, _test_record_tool_step, _test_complete_journey
        )
        
        # Test 1: Start journey
        logger.info("\n1. Testing start_journey:")
        start_result = await _test_start_journey(
            task_description="Test task for MCP tools",
            context=json.dumps({"test": True})
        )
        start_data = json.loads(start_result)
        journey_id = start_data.get("journey_id")
        logger.info(f"   Journey ID: {journey_id}")
        logger.info(f"   Recommended: {start_data.get('recommended_sequence', [])}")
        
        # Test 2: Record steps
        logger.info("\n2. Testing record_tool_step:")
        for i, tool in enumerate(start_data.get('recommended_sequence', [])[:2]):
            step_result = await _test_record_tool_step(
                journey_id=journey_id,
                tool_name=tool,
                success=True,
                duration_ms=100
            )
            step_data = json.loads(step_result)
            logger.info(f"   Step {i+1}: {tool} recorded")
        
        # Test 3: Complete journey
        logger.info("\n3. Testing complete_journey:")
        complete_result = await _test_complete_journey(
            journey_id=journey_id,
            outcome="success",
            solution_description="Test completed"
        )
        complete_data = json.loads(complete_result)
        logger.info(f"   Journey completed: {complete_data.get('outcome')}")
        
        logger.success("✅ Tool journey working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Tool journey failed: {e}")
        return False


async def test_tool_sequence_optimizer():
    """Test tool sequence optimizer functionality."""
    logger.info("\n=== Testing Tool Sequence Optimizer ===")
    
    try:
        from cc_executor.servers.mcp_tool_sequence_optimizer import (
            _test_optimize_sequence, _test_record_step, _test_complete_journey
        )
        
        # Test 1: Optimize sequence
        logger.info("\n1. Testing optimize_tool_sequence:")
        optimize_result = await _test_optimize_sequence(
            task_description="Fix ModuleNotFoundError in Python script"
        )
        optimize_data = json.loads(optimize_result)
        journey_id = optimize_data.get("journey_id", "test_journey")
        logger.info(f"   Optimal sequence: {optimize_data.get('optimal_sequence', [])}")
        
        # Test 2: Record step
        logger.info("\n2. Testing record_sequence_step:")
        step_result = await _test_record_step(
            journey_id=journey_id,
            tool_name="assess_complexity",
            success=True,
            duration_ms=150
        )
        step_data = json.loads(step_result)
        logger.info(f"   Step recorded: {step_data.get('status')}")
        
        # Test 3: Complete journey
        logger.info("\n3. Testing complete_sequence_journey:")
        complete_result = await _test_complete_journey(
            journey_id=journey_id,
            outcome="success",
            solution_description="Error fixed by installing module"
        )
        complete_data = json.loads(complete_result)
        logger.info(f"   Journey completed: {complete_data.get('status')}")
        
        logger.success("✅ Tool sequence optimizer working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Tool sequence optimizer failed: {e}")
        return False


async def test_kilocode_review():
    """Test kilocode review functionality."""
    logger.info("\n=== Testing Kilocode Review ===")
    
    try:
        from cc_executor.servers.mcp_kilocode_review import tools
        
        # Test 1: Check if kilocode command exists
        logger.info("\n1. Checking kilocode command:")
        import subprocess
        result = subprocess.run(["which", "kilocode"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"   Kilocode found at: {result.stdout.strip()}")
        else:
            logger.warning("   Kilocode command not found - review will fail")
        
        # Test 2: Test review tools instance
        logger.info("\n2. Testing review tools:")
        logger.info(f"   Tools instance created: {tools is not None}")
        logger.info(f"   Has run_review method: {hasattr(tools, 'run_review')}")
        logger.info(f"   Has parse_review_results method: {hasattr(tools, 'parse_review_results')}")
        
        logger.success("✅ Kilocode review tools initialized!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Kilocode review failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("=== MCP Tools Direct Testing ===")
    logger.info(f"Date: {datetime.now().isoformat()}")
    
    results = {}
    
    # Run all tests
    test_functions = [
        ("ArangoDB Tools", test_arango_tools),
        ("D3 Visualizer", test_d3_visualizer),
        ("Logger Tools", test_logger_tools),
        ("Tool Journey", test_tool_journey),
        ("Tool Sequence Optimizer", test_tool_sequence_optimizer),
        ("Kilocode Review", test_kilocode_review)
    ]
    
    for name, test_func in test_functions:
        try:
            success = await test_func()
            results[name] = {"status": "success" if success else "failure"}
        except Exception as e:
            logger.error(f"Failed to test {name}: {e}")
            results[name] = {"status": "error", "error": str(e)}
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    total_tests = len(results)
    successful = sum(1 for r in results.values() if r["status"] == "success")
    
    logger.info(f"Total tests: {total_tests}")
    logger.info(f"Successful: {successful}/{total_tests}")
    logger.info(f"Success rate: {(successful/total_tests)*100:.1f}%")
    
    for name, result in results.items():
        status = result["status"]
        emoji = "✅" if status == "success" else "❌"
        logger.info(f"{emoji} {name}: {status}")
    
    # Save results
    with open("test_results_mcp_tools_direct.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to: test_results_mcp_tools_direct.json")


if __name__ == "__main__":
    asyncio.run(main())