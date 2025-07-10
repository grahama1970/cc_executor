#!/usr/bin/env python3
"""
Comprehensive stress test for CC Executor
Tests local cc_execute, Docker cc_execute, MCP local, and MCP Docker
"""

import asyncio
import json
import time
import websockets
import subprocess
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig

class ComprehensiveTest:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_categories": {
                "python_api_local": {"tests": [], "summary": {}},
                "mcp_local_websocket": {"tests": [], "summary": {}},
                "docker_api": {"tests": [], "summary": {}},
                "mcp_docker_websocket": {"tests": [], "summary": {}}
            },
            "overall_summary": {}
        }
        
    async def test_python_api_local(self):
        """Test Python API locally"""
        print("\n🐍 Testing Python API (Local cc_execute)...")
        
        test_cases = [
            {"name": "Simple math", "task": "What is 17 + 25? Just the number."},
            {"name": "List colors", "task": "Name 3 primary colors, comma separated."},
            {"name": "Boolean logic", "task": "Is 10 greater than 5? Answer yes or no."}
        ]
        
        for test in test_cases:
            print(f"  📝 {test['name']}...")
            start = time.time()
            
            try:
                config = CCExecutorConfig(timeout=30)
                result = await cc_execute(task=test['task'], config=config, stream=False)
                duration = time.time() - start
                
                self.results["test_categories"]["python_api_local"]["tests"].append({
                    "name": test['name'],
                    "success": True,
                    "duration": duration,
                    "result": str(result).strip()
                })
                print(f"    ✅ Success: {str(result).strip()[:50]} ({duration:.2f}s)")
                
            except Exception as e:
                duration = time.time() - start
                self.results["test_categories"]["python_api_local"]["tests"].append({
                    "name": test['name'],
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
                print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
    
    async def test_mcp_local_websocket(self):
        """Test MCP local WebSocket server"""
        print("\n🏠 Testing MCP Local WebSocket (port 8003)...")
        
        test_cases = [
            {"name": "Math via MCP", "task": "What is 50 divided by 10? Just the number."},
            {"name": "Text via MCP", "task": "What's the opposite of 'day'? One word."}
        ]
        
        try:
            uri = "ws://localhost:8003/ws"
            async with websockets.connect(uri) as websocket:
                print(f"  ✅ Connected to MCP local server")
                
                for test in test_cases:
                    print(f"  📝 {test['name']}...")
                    start = time.time()
                    
                    try:
                        # Send JSON-RPC request
                        request = {
                            "jsonrpc": "2.0",
                            "method": "execute",
                            "params": {"command": test['task']},
                            "id": test['name']
                        }
                        await websocket.send(json.dumps(request))
                        
                        # Collect responses
                        full_output = ""
                        while True:
                            try:
                                msg = await asyncio.wait_for(websocket.recv(), timeout=30)
                                data = json.loads(msg)
                                
                                # Handle different message types
                                if data.get("method") == "process.output":
                                    params = data.get("params", {})
                                    if params.get("type") == "stdout":
                                        full_output += params.get("data", "")
                                
                                # Check for completion
                                elif "result" in data or "error" in data:
                                    duration = time.time() - start
                                    
                                    if "error" in data:
                                        raise Exception(data["error"].get("message", "Unknown error"))
                                    
                                    self.results["test_categories"]["mcp_local_websocket"]["tests"].append({
                                        "name": test['name'],
                                        "success": True,
                                        "duration": duration,
                                        "result": full_output.strip() or "Process started"
                                    })
                                    print(f"    ✅ Success: {full_output.strip()[:50] or 'Process started'} ({duration:.2f}s)")
                                    break
                                    
                            except asyncio.TimeoutError:
                                raise Exception("Timeout waiting for response")
                                
                    except Exception as e:
                        duration = time.time() - start
                        self.results["test_categories"]["mcp_local_websocket"]["tests"].append({
                            "name": test['name'],
                            "success": False,
                            "duration": duration,
                            "error": str(e)
                        })
                        print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
                        
        except Exception as e:
            print(f"  ❌ Cannot connect to MCP local server: {e}")
            self.results["test_categories"]["mcp_local_websocket"]["tests"].append({
                "name": "Connection test",
                "success": False,
                "duration": 0,
                "error": str(e)
            })
    
    async def test_docker_websocket(self):
        """Test Docker MCP WebSocket"""
        print("\n🐳 Testing Docker MCP WebSocket (port 8004)...")
        
        test_cases = [
            {"name": "Math via Docker", "task": "What is 12 times 12? Just the number."},
            {"name": "Word via Docker", "task": "What color is the sky on a clear day? One word."}
        ]
        
        try:
            uri = "ws://localhost:8004/ws"
            async with websockets.connect(uri) as websocket:
                print(f"  ✅ Connected to Docker WebSocket")
                
                for test in test_cases:
                    print(f"  📝 {test['name']}...")
                    start = time.time()
                    
                    try:
                        # Send JSON-RPC request
                        request = {
                            "jsonrpc": "2.0",
                            "method": "execute",
                            "params": {"command": test['task']},
                            "id": test['name']
                        }
                        await websocket.send(json.dumps(request))
                        
                        # Collect responses
                        full_output = ""
                        while True:
                            try:
                                msg = await asyncio.wait_for(websocket.recv(), timeout=30)
                                data = json.loads(msg)
                                
                                # Handle different message types
                                if data.get("method") == "process.output":
                                    params = data.get("params", {})
                                    if params.get("type") == "stdout":
                                        full_output += params.get("data", "")
                                
                                # Check for completion
                                elif "result" in data or "error" in data:
                                    duration = time.time() - start
                                    
                                    if "error" in data:
                                        raise Exception(data["error"].get("message", "Unknown error"))
                                    
                                    self.results["test_categories"]["mcp_docker_websocket"]["tests"].append({
                                        "name": test['name'],
                                        "success": True,
                                        "duration": duration,
                                        "result": full_output.strip() or "Process started"
                                    })
                                    print(f"    ✅ Success: {full_output.strip()[:50] or 'Process started'} ({duration:.2f}s)")
                                    break
                                    
                            except asyncio.TimeoutError:
                                raise Exception("Timeout waiting for response")
                                
                    except Exception as e:
                        duration = time.time() - start
                        self.results["test_categories"]["mcp_docker_websocket"]["tests"].append({
                            "name": test['name'],
                            "success": False,
                            "duration": duration,
                            "error": str(e)
                        })
                        print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
                        
        except Exception as e:
            print(f"  ❌ Cannot connect to Docker WebSocket: {e}")
            self.results["test_categories"]["mcp_docker_websocket"]["tests"].append({
                "name": "Connection test",
                "success": False,
                "duration": 0,
                "error": str(e)
            })
    
    def generate_summaries(self):
        """Generate summaries for each category"""
        all_tests = []
        
        for category, data in self.results["test_categories"].items():
            tests = data["tests"]
            if tests:
                total = len(tests)
                successful = sum(1 for t in tests if t.get("success", False))
                failed = total - successful
                avg_duration = sum(t.get("duration", 0) for t in tests) / total if total > 0 else 0
                
                data["summary"] = {
                    "total_tests": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": f"{(successful/total)*100:.1f}%",
                    "avg_duration": f"{avg_duration:.2f}s"
                }
                all_tests.extend(tests)
        
        # Overall summary
        if all_tests:
            total = len(all_tests)
            successful = sum(1 for t in all_tests if t.get("success", False))
            failed = total - successful
            avg_duration = sum(t.get("duration", 0) for t in all_tests) / total if total > 0 else 0
            
            self.results["overall_summary"] = {
                "total_tests": total,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/total)*100:.1f}%",
                "avg_duration": f"{avg_duration:.2f}s",
                "categories_tested": len([c for c in self.results["test_categories"].values() if c["tests"]])
            }
    
    def save_comprehensive_report(self):
        """Save comprehensive assessment report"""
        output_dir = Path("tests/stress_test_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save raw JSON
        raw_file = output_dir / f"comprehensive_raw_{self.timestamp}.json"
        with open(raw_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate comprehensive Markdown report
        report_file = output_dir / f"CC_EXECUTOR_COMPREHENSIVE_ASSESSMENT_{self.timestamp}.md"
        with open(report_file, 'w') as f:
            f.write("# CC Executor Comprehensive Assessment Report\n")
            f.write(f"Generated: {self.results['timestamp']}\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            overall = self.results.get("overall_summary", {})
            f.write(f"- **Total Tests Run:** {overall.get('total_tests', 0)}\n")
            f.write(f"- **Overall Success Rate:** {overall.get('success_rate', 'N/A')}\n")
            f.write(f"- **Average Response Time:** {overall.get('avg_duration', 'N/A')}\n")
            f.write(f"- **Deployment Categories Tested:** {overall.get('categories_tested', 0)}/4\n\n")
            
            # Category Results
            f.write("## Deployment Category Results\n\n")
            
            category_names = {
                "python_api_local": "Python API (Local)",
                "mcp_local_websocket": "MCP Local WebSocket",
                "docker_api": "Docker API",
                "mcp_docker_websocket": "MCP Docker WebSocket"
            }
            
            for category_key, category_name in category_names.items():
                data = self.results["test_categories"][category_key]
                summary = data.get("summary", {})
                
                f.write(f"### {category_name}\n\n")
                
                if summary:
                    status = "✅ OPERATIONAL" if summary.get("failed", 1) == 0 else "⚠️ ISSUES DETECTED" if summary.get("successful", 0) > 0 else "❌ FAILING"
                    f.write(f"**Status:** {status}\n\n")
                    f.write(f"- Tests Run: {summary.get('total_tests', 0)}\n")
                    f.write(f"- Successful: {summary.get('successful', 0)}\n")
                    f.write(f"- Failed: {summary.get('failed', 0)}\n")
                    f.write(f"- Success Rate: {summary.get('success_rate', 'N/A')}\n")
                    f.write(f"- Avg Response Time: {summary.get('avg_duration', 'N/A')}\n\n")
                    
                    # Test details
                    if data["tests"]:
                        f.write("**Test Results:**\n\n")
                        for test in data["tests"]:
                            status = "✅" if test.get("success") else "❌"
                            f.write(f"- {test['name']} {status}\n")
                            f.write(f"  - Duration: {test.get('duration', 0):.2f}s\n")
                            if test.get("success"):
                                result = test.get('result', 'N/A')
                                f.write(f"  - Result: `{result[:100]}{'...' if len(str(result)) > 100 else ''}`\n")
                            else:
                                f.write(f"  - Error: {test.get('error', 'Unknown error')[:200]}\n")
                        f.write("\n")
                else:
                    f.write("**Status:** ❌ NOT TESTED\n\n")
            
            # Raw Data Reference
            f.write("## Raw Test Data\n\n")
            f.write(f"Complete test results are available in: `{raw_file}`\n\n")
            
            # Sample successful response
            f.write("### Sample Successful Response (Raw JSON)\n\n")
            f.write("```json\n")
            
            # Find a successful test
            sample = None
            for cat_data in self.results["test_categories"].values():
                for test in cat_data["tests"]:
                    if test.get("success"):
                        sample = test
                        break
                if sample:
                    break
            
            if sample:
                f.write(json.dumps(sample, indent=2))
            else:
                f.write("No successful tests to display")
            f.write("\n```\n")
        
        print(f"\n📊 Comprehensive Assessment Complete!")
        print(f"  - Raw JSON: {raw_file}")
        print(f"  - Assessment Report: {report_file}")
        
        return raw_file, report_file

async def main():
    """Run comprehensive test suite"""
    print("🚀 CC Executor Comprehensive Stress Test")
    print("=" * 60)
    
    tester = ComprehensiveTest()
    
    # Run all tests
    await tester.test_python_api_local()
    await tester.test_mcp_local_websocket()
    await tester.test_docker_websocket()
    
    # Generate reports
    tester.generate_summaries()
    raw_file, report_file = tester.save_comprehensive_report()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Overall Summary:")
    overall = tester.results.get("overall_summary", {})
    print(f"  Total Tests: {overall.get('total_tests', 0)}")
    print(f"  Success Rate: {overall.get('success_rate', 'N/A')}")
    print(f"  Average Response Time: {overall.get('avg_duration', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())