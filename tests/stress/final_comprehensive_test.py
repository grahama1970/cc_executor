#!/usr/bin/env python3
"""
Final comprehensive test for CC Executor - all deployment modes
Tests Python API, MCP local server, and Docker deployment
"""

import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig
from cc_executor.client.client import WebSocketClient

class ComprehensiveStressTest:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "deployment_modes": {
                "python_api": {
                    "tests": [],
                    "summary": {}
                },
                "mcp_local_websocket": {
                    "tests": [],
                    "summary": {}
                },
                "docker_websocket": {
                    "tests": [],
                    "summary": {}
                }
            },
            "overall_summary": {}
        }
        
    async def test_python_api(self):
        """Test Python API directly using cc_execute"""
        print("\n🐍 Testing Python API (cc_execute)...")
        
        test_cases = [
            {
                "name": "Simple arithmetic",
                "task": "What is 5+7? Just respond with the number.",
                "timeout": 30
            },
            {
                "name": "Prime numbers",
                "task": "List the first 7 prime numbers, separated by commas.",
                "timeout": 30
            },
            {
                "name": "Complex question",
                "task": "What is the capital of France? Just the city name.",
                "timeout": 30
            }
        ]
        
        for test in test_cases:
            print(f"  📝 {test['name']}...")
            start_time = time.time()
            
            try:
                config = CCExecutorConfig(timeout=test['timeout'])
                result = await cc_execute(
                    task=test['task'],
                    config=config,
                    stream=False
                )
                
                duration = time.time() - start_time
                
                self.results["deployment_modes"]["python_api"]["tests"].append({
                    "name": test['name'],
                    "success": True,
                    "duration": duration,
                    "result": result.strip() if isinstance(result, str) else str(result)
                })
                print(f"    ✅ Success: {result.strip()[:50]}{'...' if len(str(result)) > 50 else ''} ({duration:.2f}s)")
                
            except Exception as e:
                duration = time.time() - start_time
                self.results["deployment_modes"]["python_api"]["tests"].append({
                    "name": test['name'],
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
                print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
    
    async def test_mcp_local_websocket(self):
        """Test MCP local server via WebSocket"""
        print("\n🏠 Testing MCP Local WebSocket...")
        
        # Test if server is accessible
        try:
            client = WebSocketClient("ws://127.0.0.1:8003/ws/mcp")
            await client.connect()
            print("  ✅ Connected to MCP local server")
            
            test_cases = [
                {
                    "name": "Simple WebSocket test",
                    "task": "What is 10-3? Just the number.",
                    "timeout": 30
                },
                {
                    "name": "List task via WebSocket",
                    "task": "Name 3 colors of the rainbow, comma separated.",
                    "timeout": 30
                }
            ]
            
            for test in test_cases:
                print(f"  📝 {test['name']}...")
                start_time = time.time()
                
                try:
                    # Send task
                    await client.send_message({
                        "task": test['task'],
                        "session_id": f"mcp_test_{int(time.time())}",
                        "timeout": test['timeout']
                    })
                    
                    # Collect response
                    response = ""
                    async for message in client.receive_stream():
                        if isinstance(message, dict):
                            if message.get("type") == "error":
                                raise Exception(message.get("message", "Unknown error"))
                            elif message.get("type") == "stream":
                                response += message.get("content", "")
                            elif message.get("type") == "complete":
                                break
                        else:
                            response += str(message)
                    
                    duration = time.time() - start_time
                    
                    self.results["deployment_modes"]["mcp_local_websocket"]["tests"].append({
                        "name": test['name'],
                        "success": True,
                        "duration": duration,
                        "result": response.strip()
                    })
                    print(f"    ✅ Success: {response.strip()[:50]}{'...' if len(response) > 50 else ''} ({duration:.2f}s)")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.results["deployment_modes"]["mcp_local_websocket"]["tests"].append({
                        "name": test['name'],
                        "success": False,
                        "duration": duration,
                        "error": str(e)
                    })
                    print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
            
            await client.close()
            
        except Exception as e:
            print(f"  ❌ Cannot connect to MCP local server: {e}")
            self.results["deployment_modes"]["mcp_local_websocket"]["tests"].append({
                "name": "Connection test",
                "success": False,
                "duration": 0,
                "error": str(e)
            })
    
    async def test_docker_websocket(self):
        """Test Docker deployment via WebSocket"""
        print("\n🐳 Testing Docker WebSocket...")
        
        # Check if container is running
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'cc_execute' not in result.stdout:
                print("  ⚠️  Docker container 'cc_execute' not running")
                self.results["deployment_modes"]["docker_websocket"]["tests"].append({
                    "name": "Container check",
                    "success": False,
                    "duration": 0,
                    "error": "Container not running"
                })
                return
        except Exception as e:
            print(f"  ❌ Cannot check Docker status: {e}")
            return
        
        # Test WebSocket connection
        try:
            client = WebSocketClient("ws://localhost:8004/ws/mcp")
            await client.connect()
            print("  ✅ Connected to Docker WebSocket")
            
            test_cases = [
                {
                    "name": "Docker arithmetic test",
                    "task": "What is 15/3? Just the number.",
                    "timeout": 30
                },
                {
                    "name": "Docker text generation",
                    "task": "Write the word 'success' in uppercase.",
                    "timeout": 30
                }
            ]
            
            for test in test_cases:
                print(f"  📝 {test['name']}...")
                start_time = time.time()
                
                try:
                    # Send task
                    await client.send_message({
                        "task": test['task'],
                        "session_id": f"docker_test_{int(time.time())}",
                        "timeout": test['timeout']
                    })
                    
                    # Collect response
                    response = ""
                    async for message in client.receive_stream():
                        if isinstance(message, dict):
                            if message.get("type") == "error":
                                raise Exception(message.get("message", "Unknown error"))
                            elif message.get("type") == "stream":
                                response += message.get("content", "")
                            elif message.get("type") == "complete":
                                break
                        else:
                            response += str(message)
                    
                    duration = time.time() - start_time
                    
                    self.results["deployment_modes"]["docker_websocket"]["tests"].append({
                        "name": test['name'],
                        "success": True,
                        "duration": duration,
                        "result": response.strip()
                    })
                    print(f"    ✅ Success: {response.strip()[:50]}{'...' if len(response) > 50 else ''} ({duration:.2f}s)")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.results["deployment_modes"]["docker_websocket"]["tests"].append({
                        "name": test['name'],
                        "success": False,
                        "duration": duration,
                        "error": str(e)
                    })
                    print(f"    ❌ Failed: {str(e)[:100]} ({duration:.2f}s)")
            
            await client.close()
            
        except Exception as e:
            print(f"  ❌ Cannot connect to Docker WebSocket: {e}")
            self.results["deployment_modes"]["docker_websocket"]["tests"].append({
                "name": "Connection test",
                "success": False,
                "duration": 0,
                "error": str(e)
            })
    
    def generate_summaries(self):
        """Generate summaries for each deployment mode and overall"""
        for mode_name, mode_data in self.results["deployment_modes"].items():
            tests = mode_data["tests"]
            if tests:
                total = len(tests)
                successful = sum(1 for t in tests if t.get("success", False))
                failed = total - successful
                avg_duration = sum(t.get("duration", 0) for t in tests) / total if total > 0 else 0
                
                mode_data["summary"] = {
                    "total_tests": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": f"{(successful/total)*100:.1f}%",
                    "avg_duration": f"{avg_duration:.2f}s"
                }
        
        # Overall summary
        all_tests = []
        for mode_data in self.results["deployment_modes"].values():
            all_tests.extend(mode_data["tests"])
        
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
                "deployment_modes_tested": len([m for m in self.results["deployment_modes"].values() if m["tests"]])
            }
    
    def save_results(self):
        """Save comprehensive results and generate assessment report"""
        output_dir = Path("tests/stress_test_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save raw JSON results
        raw_file = output_dir / f"comprehensive_test_raw_{self.timestamp}.json"
        with open(raw_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate comprehensive assessment report
        report_file = output_dir / f"CC_EXECUTOR_ASSESSMENT_{self.timestamp}.md"
        with open(report_file, 'w') as f:
            f.write("# CC Executor Comprehensive Assessment Report\n")
            f.write(f"Generated: {self.results['timestamp']}\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            overall = self.results.get("overall_summary", {})
            f.write(f"- **Total Tests Run:** {overall.get('total_tests', 0)}\n")
            f.write(f"- **Success Rate:** {overall.get('success_rate', 'N/A')}\n")
            f.write(f"- **Average Response Time:** {overall.get('avg_duration', 'N/A')}\n")
            f.write(f"- **Deployment Modes Tested:** {overall.get('deployment_modes_tested', 0)}/3\n\n")
            
            # Deployment Mode Details
            f.write("## Deployment Mode Results\n\n")
            
            for mode_name, mode_data in self.results["deployment_modes"].items():
                summary = mode_data.get("summary", {})
                f.write(f"### {mode_name.replace('_', ' ').title()}\n\n")
                
                if summary:
                    f.write(f"**Status:** {'✅ OPERATIONAL' if summary.get('failed', 1) == 0 else '⚠️ ISSUES DETECTED' if summary.get('successful', 0) > 0 else '❌ FAILING'}\n\n")
                    f.write(f"- Tests Run: {summary.get('total_tests', 0)}\n")
                    f.write(f"- Successful: {summary.get('successful', 0)}\n")
                    f.write(f"- Failed: {summary.get('failed', 0)}\n")
                    f.write(f"- Success Rate: {summary.get('success_rate', 'N/A')}\n")
                    f.write(f"- Avg Response Time: {summary.get('avg_duration', 'N/A')}\n\n")
                    
                    # Test details
                    if mode_data["tests"]:
                        f.write("**Test Results:**\n\n")
                        for test in mode_data["tests"]:
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
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            # Check each mode and provide recommendations
            for mode_name, mode_data in self.results["deployment_modes"].items():
                summary = mode_data.get("summary", {})
                if not summary or summary.get("failed", 1) > 0:
                    f.write(f"### {mode_name.replace('_', ' ').title()}\n")
                    if not summary:
                        f.write("- Mode was not tested - ensure server/container is running\n")
                    else:
                        failed_tests = [t for t in mode_data["tests"] if not t.get("success")]
                        for test in failed_tests:
                            f.write(f"- Fix: {test['name']} - {test.get('error', 'Unknown error')[:100]}\n")
                    f.write("\n")
            
            # Raw JSON Reference
            f.write("## Raw Test Data\n\n")
            f.write(f"Complete test results with all details are available in:\n")
            f.write(f"`{raw_file}`\n\n")
            
            # Pretty-printed sample of raw JSON
            f.write("### Sample Raw JSON Response\n\n")
            f.write("```json\n")
            sample_test = None
            for mode_data in self.results["deployment_modes"].values():
                for test in mode_data["tests"]:
                    if test.get("success"):
                        sample_test = test
                        break
                if sample_test:
                    break
            
            if sample_test:
                f.write(json.dumps(sample_test, indent=2)[:500])
                if len(json.dumps(sample_test, indent=2)) > 500:
                    f.write("\n... (truncated)")
            else:
                f.write("No successful tests to show")
            f.write("\n```\n")
        
        print(f"\n📊 Assessment Complete!")
        print(f"  - Raw JSON: {raw_file}")
        print(f"  - Assessment Report: {report_file}")
        
        return raw_file, report_file

async def main():
    """Run comprehensive stress test"""
    print("🚀 CC Executor Comprehensive Assessment")
    print("=" * 50)
    
    tester = ComprehensiveStressTest()
    
    # Run all tests
    await tester.test_python_api()
    await tester.test_mcp_local_websocket()
    await tester.test_docker_websocket()
    
    # Generate summaries and save results
    tester.generate_summaries()
    raw_file, report_file = tester.save_results()
    
    # Print final summary
    print("\n" + "=" * 50)
    print("📊 Overall Assessment Summary:")
    overall = tester.results.get("overall_summary", {})
    print(f"  Total Tests: {overall.get('total_tests', 0)}")
    print(f"  Success Rate: {overall.get('success_rate', 'N/A')}")
    print(f"  Avg Response Time: {overall.get('avg_duration', 'N/A')}")
    
    # Status by deployment mode
    print("\n📈 Deployment Mode Status:")
    for mode_name, mode_data in tester.results["deployment_modes"].items():
        summary = mode_data.get("summary", {})
        if summary:
            status = "✅" if summary.get("failed", 1) == 0 else "⚠️" if summary.get("successful", 0) > 0 else "❌"
            print(f"  {mode_name}: {status} {summary.get('success_rate', 'N/A')}")
        else:
            print(f"  {mode_name}: ❌ Not tested")

if __name__ == "__main__":
    asyncio.run(main())