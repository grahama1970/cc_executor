#!/usr/bin/env python3
"""
Comprehensive test suite for all MCP servers in cc_executor.

This script tests each MCP server to ensure:
1. Server starts without timeout
2. All tools are callable
3. Basic functionality works
4. Lazy loading is properly implemented where needed

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python test_all_mcp_servers.py          # Runs all tests
  python test_all_mcp_servers.py debug    # Runs debug mode for specific server
"""

import asyncio
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Test results storage
test_results: Dict[str, Dict[str, Any]] = {}


async def test_server_startup(server_name: str, script_path: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Test if server starts within timeout."""
    logger.info(f"\nTesting {server_name} startup...")
    
    start_time = time.time()
    cmd = [sys.executable, script_path, "test"]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "duration": duration,
                "stdout": stdout.decode()[:200],
                "stderr": stderr.decode()[:200] if stderr else None
            }
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
            return {
                "status": "timeout",
                "duration": timeout,
                "error": f"Server took longer than {timeout}s to start"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "duration": time.time() - start_time,
            "error": str(e)
        }


async def test_mcp_arango_tools():
    """Test ArangoDB tools functionality."""
    server_name = "mcp_arango_tools"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_arango_tools.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Test specific functionality if startup succeeded
    if startup_result["status"] == "success":
        # Run the working_usage function
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path, "working",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode()
            if "✅ All examples completed successfully!" in output:
                results["tests"]["working_usage"] = {"status": "success", "message": "All examples passed"}
            else:
                results["tests"]["working_usage"] = {"status": "failure", "output": output[-500:]}
                
        except Exception as e:
            results["tests"]["working_usage"] = {"status": "error", "error": str(e)}
    
    return results


async def test_mcp_cc_execute():
    """Test CC executor functionality."""
    server_name = "mcp_cc_execute"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_cc_execute.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Note: This server requires WebSocket connections, so basic test only
    if startup_result["status"] == "success":
        results["tests"]["status"] = {
            "status": "info",
            "message": "Server starts successfully. Full testing requires WebSocket client."
        }
    
    return results


async def test_mcp_d3_visualizer():
    """Test D3 visualizer functionality."""
    server_name = "mcp_d3_visualizer"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_d3_visualizer.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Test working usage
    if startup_result["status"] == "success":
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path, "working",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode()
            if "✅ D3 Visualizer working!" in output:
                results["tests"]["working_usage"] = {"status": "success", "message": "Visualization tests passed"}
            else:
                results["tests"]["working_usage"] = {"status": "failure", "output": output[-500:]}
                
        except Exception as e:
            results["tests"]["working_usage"] = {"status": "error", "error": str(e)}
    
    return results


async def test_mcp_kilocode_review():
    """Test kilocode review functionality."""
    server_name = "mcp_kilocode_review"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_kilocode_review.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Check if test mode works
    if startup_result["status"] == "success" and "Server ready to start" in startup_result.get("stdout", ""):
        results["tests"]["test_mode"] = {"status": "success", "message": "Test mode works correctly"}
    else:
        results["tests"]["test_mode"] = {"status": "failure", "message": "Test mode not working"}
    
    return results


async def test_mcp_logger_tools():
    """Test logger tools functionality."""
    server_name = "mcp_logger_tools"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_logger_tools.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Test working usage
    if startup_result["status"] == "success":
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path, "working",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode()
            if "✅ Logger tools working!" in output:
                results["tests"]["working_usage"] = {"status": "success", "message": "Logger tests passed"}
            else:
                results["tests"]["working_usage"] = {"status": "failure", "output": output[-500:]}
                
        except Exception as e:
            results["tests"]["working_usage"] = {"status": "error", "error": str(e)}
    
    return results


async def test_mcp_tool_journey():
    """Test tool journey functionality."""
    server_name = "mcp_tool_journey"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup (should be fast with lazy loading)
    script_path = "src/cc_executor/servers/mcp_tool_journey.py"
    startup_result = await test_server_startup(server_name, script_path, timeout=5.0)
    results["startup"] = startup_result
    
    # Test working usage
    if startup_result["status"] == "success":
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path, "working",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode()
            if "✅ Tool journey system working with lazy loading!" in output:
                results["tests"]["working_usage"] = {"status": "success", "message": "Lazy loading verified"}
                
                # Check lazy loading timing
                if "Loading sentence transformer model (first use)" in output:
                    results["tests"]["lazy_loading"] = {
                        "status": "success",
                        "message": "Model loads only on first use"
                    }
            else:
                results["tests"]["working_usage"] = {"status": "failure", "output": output[-500:]}
                
        except Exception as e:
            results["tests"]["working_usage"] = {"status": "error", "error": str(e)}
    
    return results


async def test_mcp_tool_sequence_optimizer():
    """Test tool sequence optimizer functionality."""
    server_name = "mcp_tool_sequence_optimizer"
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {server_name}")
    logger.info(f"{'='*60}")
    
    results = {"server": server_name, "tests": {}}
    
    # Test startup
    script_path = "src/cc_executor/servers/mcp_tool_sequence_optimizer.py"
    startup_result = await test_server_startup(server_name, script_path)
    results["startup"] = startup_result
    
    # Test working usage
    if startup_result["status"] == "success":
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path, "working",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode()
            if "✅ Tool sequence optimizer working!" in output:
                results["tests"]["working_usage"] = {"status": "success", "message": "Optimizer tests passed"}
            else:
                results["tests"]["working_usage"] = {"status": "failure", "output": output[-500:]}
                
        except Exception as e:
            results["tests"]["working_usage"] = {"status": "error", "error": str(e)}
    
    return results


async def working_usage():
    """Run all MCP server tests."""
    logger.info("=== MCP Servers Comprehensive Test ===")
    logger.info(f"Date: {datetime.now().isoformat()}")
    
    all_results = []
    
    # Test each server
    test_functions = [
        test_mcp_arango_tools,
        test_mcp_cc_execute,
        test_mcp_d3_visualizer,
        test_mcp_kilocode_review,
        test_mcp_logger_tools,
        test_mcp_tool_journey,
        test_mcp_tool_sequence_optimizer
    ]
    
    for test_func in test_functions:
        try:
            result = await test_func()
            all_results.append(result)
        except Exception as e:
            logger.error(f"Failed to test {test_func.__name__}: {e}")
            all_results.append({
                "server": test_func.__name__.replace("test_", ""),
                "startup": {"status": "error", "error": str(e)},
                "tests": {}
            })
    
    # Generate summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    total_servers = len(all_results)
    successful_startups = sum(1 for r in all_results if r["startup"]["status"] == "success")
    
    logger.info(f"Total servers tested: {total_servers}")
    logger.info(f"Successful startups: {successful_startups}/{total_servers}")
    
    # Detailed results
    for result in all_results:
        server = result["server"]
        startup = result["startup"]["status"]
        startup_time = result["startup"].get("duration", 0)
        
        logger.info(f"\n{server}:")
        logger.info(f"  Startup: {startup} ({startup_time:.2f}s)")
        
        for test_name, test_result in result.get("tests", {}).items():
            status = test_result["status"]
            message = test_result.get("message", test_result.get("error", ""))
            logger.info(f"  {test_name}: {status} - {message}")
    
    # Save results
    output_file = Path("test_results_mcp_servers.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    # Identify servers needing lazy loading
    logger.info("\n=== LAZY LOADING RECOMMENDATIONS ===")
    for result in all_results:
        if result["startup"]["status"] == "timeout":
            logger.warning(f"{result['server']}: Needs lazy loading (timeout on startup)")
        elif result["startup"].get("duration", 0) > 5.0:
            logger.warning(f"{result['server']}: Consider lazy loading (slow startup: {result['startup']['duration']:.2f}s)")
    
    return True


async def debug_function():
    """Debug specific server issues."""
    logger.info("=== Debug Mode ===")
    
    # Test a specific server with more detail
    server_to_debug = "mcp_logger_tools"
    script_path = f"src/cc_executor/servers/{server_to_debug}.py"
    
    logger.info(f"Debugging {server_to_debug}...")
    
    # Test with extended timeout
    result = await test_server_startup(server_to_debug, script_path, timeout=30.0)
    logger.info(f"Startup result: {json.dumps(result, indent=2)}")
    
    # Try to identify what's causing slow startup
    if result["status"] == "timeout":
        logger.error("Server is timing out. Check for:")
        logger.error("1. Heavy imports at module level")
        logger.error("2. Database connections during import")
        logger.error("3. Model loading during import")
        logger.error("4. Missing lazy loading pattern")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())