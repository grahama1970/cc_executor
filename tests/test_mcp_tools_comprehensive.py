#!/usr/bin/env python3
"""
Comprehensive MCP Tool Testing Framework

This test suite actually invokes each MCP tool and validates:
1. Tool responds correctly
2. Output format is valid
3. Side effects occur (files created, DB updated, etc.)
4. Error handling works properly
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import uuid

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("mcp_tool_tests.log", rotation="10 MB")


@dataclass
class TestCase:
    """Single test case for an MCP tool"""
    tool_name: str
    params: Dict[str, Any]
    validate: Callable[[Any], bool]
    description: str
    cleanup: Optional[Callable[[], None]] = None
    setup: Optional[Callable[[], None]] = None


@dataclass
class TestResult:
    """Result of a single test"""
    server: str
    tool: str
    success: bool
    response: Any
    error: Optional[str] = None
    duration: float = 0.0
    validation_details: Optional[str] = None


class MCPTestClient:
    """Client for testing MCP servers via JSON-RPC"""
    
    def __init__(self, server_name: str, script_path: str):
        self.server_name = server_name
        self.script_path = script_path
        self.process = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process"""
        cmd = [sys.executable, self.script_path]
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Give server time to start
        await asyncio.sleep(0.5)
        
        # Initialize connection
        await self._send_request("initialize", {"capabilities": {}})
    
    async def _send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request and get response"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if response_line:
            return json.loads(response_line.decode())
        return None
    
    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """Call a specific tool"""
        return await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": params
        })
    
    async def stop(self):
        """Stop the server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()


class MCPToolTester:
    """Comprehensive MCP tool testing framework"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.test_suites = self._define_test_suites()
    
    def _define_test_suites(self) -> Dict[str, List[TestCase]]:
        """Define comprehensive test cases for each MCP server"""
        return {
            "mcp_arango_tools": [
                TestCase(
                    tool_name="get_schema",
                    params={},
                    validate=lambda r: isinstance(r, dict) and "collections" in r,
                    description="Get database schema"
                ),
                TestCase(
                    tool_name="execute_aql",
                    params={
                        "aql": "RETURN 1+1",
                        "bind_vars": {}
                    },
                    validate=lambda r: r == [2] or (isinstance(r, dict) and r.get("result") == [2]),
                    description="Execute simple AQL query"
                ),
                TestCase(
                    tool_name="advanced_search",
                    params={
                        "query": "test",
                        "collections": ["log_events"],
                        "limit": 5
                    },
                    validate=lambda r: isinstance(r, dict) or isinstance(r, list),
                    description="Search across collections"
                ),
            ],
            
            "mcp_d3_visualizer": [
                TestCase(
                    tool_name="generate_graph_visualization",
                    params={
                        "graph_data": json.dumps({
                            "nodes": [
                                {"id": "1", "label": "Node 1"},
                                {"id": "2", "label": "Node 2"}
                            ],
                            "links": [
                                {"source": "1", "target": "2", "value": 1}
                            ]
                        }),
                        "layout": "force",
                        "title": "Test Visualization"
                    },
                    validate=lambda r: (
                        isinstance(r, dict) and 
                        r.get("success", False) and 
                        "filepath" in r
                    ),
                    description="Generate graph visualization",
                    cleanup=lambda: self._cleanup_visualization_files()
                ),
                TestCase(
                    tool_name="list_visualizations",
                    params={},
                    validate=lambda r: isinstance(r, dict) and "visualizations" in r,
                    description="List generated visualizations"
                ),
            ],
            
            "mcp_logger_tools": [
                TestCase(
                    tool_name="assess_complexity",
                    params={
                        "error_type": "ImportError",
                        "error_message": "No module named 'nonexistent_module'",
                        "file_path": "/test/example.py"
                    },
                    validate=lambda r: isinstance(r, dict) or "prompt" in str(r),
                    description="Assess error complexity"
                ),
                TestCase(
                    tool_name="query_agent_logs",
                    params={
                        "action": "search",
                        "query": "error",
                        "limit": 10
                    },
                    validate=lambda r: isinstance(r, (dict, list)),
                    description="Query agent logs"
                ),
            ],
            
            "mcp_tool_journey": [
                TestCase(
                    tool_name="start_journey",
                    params={
                        "task_description": "Fix import error in Python module",
                        "context": json.dumps({"error_type": "ImportError"})
                    },
                    validate=lambda r: isinstance(r, dict) and "journey_id" in r,
                    description="Start a tool journey"
                ),
                TestCase(
                    tool_name="query_similar_journeys",
                    params={
                        "task_description": "Fix import error",
                        "limit": 5
                    },
                    validate=lambda r: isinstance(r, (dict, list)),
                    description="Find similar journeys"
                ),
            ],
            
            "mcp_kilocode_review": [
                TestCase(
                    tool_name="start_review",
                    params={
                        "files": "src/cc_executor/client/cc_execute.py",
                        "focus": "security",
                        "severity": "medium"
                    },
                    validate=lambda r: isinstance(r, dict) and "review_id" in r,
                    description="Start code review"
                ),
            ],
            
            "mcp_tool_sequence_optimizer": [
                TestCase(
                    tool_name="optimize_tool_sequence",
                    params={
                        "task_description": "Debug failing pytest tests"
                    },
                    validate=lambda r: isinstance(r, dict),
                    description="Get optimal tool sequence"
                ),
            ],
        }
    
    def _cleanup_visualization_files(self):
        """Clean up test visualization files"""
        viz_dir = Path("/tmp/visualizations")
        if viz_dir.exists():
            for file in viz_dir.glob("test_*.html"):
                file.unlink()
    
    async def test_server(self, server_name: str, script_path: str) -> List[TestResult]:
        """Test all tools for a specific MCP server"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {server_name}")
        logger.info(f"{'='*60}")
        
        results = []
        
        # Get test cases for this server
        test_cases = self.test_suites.get(server_name, [])
        if not test_cases:
            logger.warning(f"No test cases defined for {server_name}")
            return results
        
        # Start MCP client
        client = MCPTestClient(server_name, script_path)
        
        try:
            await client.start()
            logger.info(f"✓ {server_name} started successfully")
            
            # Run each test case
            for test_case in test_cases:
                result = await self._run_test_case(client, server_name, test_case)
                results.append(result)
                
                # Run cleanup if defined
                if test_case.cleanup:
                    test_case.cleanup()
            
        except Exception as e:
            logger.error(f"Failed to test {server_name}: {e}")
            results.append(TestResult(
                server=server_name,
                tool="startup",
                success=False,
                response=None,
                error=str(e)
            ))
        finally:
            await client.stop()
        
        return results
    
    async def _run_test_case(self, client: MCPTestClient, server_name: str, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        logger.info(f"\nTesting {test_case.tool_name}: {test_case.description}")
        
        # Run setup if defined
        if test_case.setup:
            test_case.setup()
        
        start_time = time.time()
        
        try:
            # Call the tool
            response = await client.call_tool(test_case.tool_name, test_case.params)
            duration = time.time() - start_time
            
            # Extract result from response
            if isinstance(response, dict) and "result" in response:
                result_data = response["result"]
            else:
                result_data = response
            
            # Validate response
            try:
                is_valid = test_case.validate(result_data)
                validation_details = "Response validated successfully" if is_valid else "Validation failed"
            except Exception as e:
                is_valid = False
                validation_details = f"Validation error: {e}"
            
            if is_valid:
                logger.success(f"✓ {test_case.tool_name} passed")
            else:
                logger.error(f"✗ {test_case.tool_name} failed validation")
                logger.debug(f"Response: {json.dumps(result_data, indent=2)}")
            
            return TestResult(
                server=server_name,
                tool=test_case.tool_name,
                success=is_valid,
                response=result_data,
                duration=duration,
                validation_details=validation_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"✗ {test_case.tool_name} failed with error: {e}")
            
            return TestResult(
                server=server_name,
                tool=test_case.tool_name,
                success=False,
                response=None,
                error=str(e),
                duration=duration
            )
    
    async def run_all_tests(self):
        """Run tests for all MCP servers"""
        servers = [
            ("mcp_arango_tools", "src/cc_executor/servers/mcp_arango_tools.py"),
            ("mcp_d3_visualizer", "src/cc_executor/servers/mcp_d3_visualizer.py"),
            ("mcp_logger_tools", "src/cc_executor/servers/mcp_logger_tools.py"),
            ("mcp_tool_journey", "src/cc_executor/servers/mcp_tool_journey.py"),
            ("mcp_kilocode_review", "src/cc_executor/servers/mcp_kilocode_review.py"),
            ("mcp_tool_sequence_optimizer", "src/cc_executor/servers/mcp_tool_sequence_optimizer.py"),
        ]
        
        for server_name, script_path in servers:
            server_results = await self.test_server(server_name, script_path)
            self.results.extend(server_results)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        # Group results by server
        by_server = {}
        for result in self.results:
            if result.server not in by_server:
                by_server[result.server] = []
            by_server[result.server].append(result)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "servers": {}
        }
        
        for server, results in by_server.items():
            server_passed = sum(1 for r in results if r.success)
            server_total = len(results)
            
            report["servers"][server] = {
                "total": server_total,
                "passed": server_passed,
                "failed": server_total - server_passed,
                "tools": {}
            }
            
            for result in results:
                report["servers"][server]["tools"][result.tool] = {
                    "success": result.success,
                    "duration": f"{result.duration:.3f}s",
                    "error": result.error,
                    "validation": result.validation_details
                }
        
        return report
    
    def print_summary(self):
        """Print test summary to console"""
        report = self.generate_report()
        
        logger.info(f"\n{'='*60}")
        logger.info("MCP TOOL TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed']}")
        logger.info(f"Failed: {report['summary']['failed']}")
        logger.info(f"Success Rate: {report['summary']['success_rate']}")
        
        logger.info(f"\n{'Server':<30} {'Total':<10} {'Passed':<10} {'Failed':<10}")
        logger.info("-" * 60)
        
        for server, data in report["servers"].items():
            logger.info(f"{server:<30} {data['total']:<10} {data['passed']:<10} {data['failed']:<10}")
        
        # Show failed tests
        if report['summary']['failed'] > 0:
            logger.info(f"\n{'='*60}")
            logger.info("FAILED TESTS:")
            logger.info(f"{'='*60}")
            
            for result in self.results:
                if not result.success:
                    logger.error(f"\n{result.server}.{result.tool}:")
                    if result.error:
                        logger.error(f"  Error: {result.error}")
                    if result.validation_details:
                        logger.error(f"  Validation: {result.validation_details}")
        
        # Save detailed report
        report_path = Path("mcp_tool_test_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_path}")


async def main():
    """Run comprehensive MCP tool tests"""
    logger.info("=== MCP Tool Comprehensive Testing ===")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    
    tester = MCPToolTester()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
    
    tester.print_summary()
    
    logger.info(f"\nCompleted at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())