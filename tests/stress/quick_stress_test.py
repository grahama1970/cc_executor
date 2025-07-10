#!/usr/bin/env python3
"""
Quick stress test for CC Executor - all versions
Tests Python API, MCP local, and Docker deployment
"""

import asyncio
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig

class QuickStressTest:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {
                "python_api": [],
                "mcp_local": [],
                "docker": []
            },
            "summary": {}
        }
        
    async def test_python_api(self):
        """Test Python API directly"""
        print("\n🐍 Testing Python API...")
        
        test_cases = [
            {
                "name": "Simple calculation",
                "prompt": "What is 2+2? Just respond with the number.",
                "timeout": 30
            },
            {
                "name": "List generation",
                "prompt": "List the first 5 prime numbers, comma separated.",
                "timeout": 30
            },
            {
                "name": "Error case",
                "prompt": "What is the square root of -1 in real numbers?",
                "timeout": 30
            }
        ]
        
        for test in test_cases:
            print(f"  Testing: {test['name']}")
            start_time = time.time()
            
            try:
                # Create config with timeout
                config = CCExecutorConfig(timeout=test['timeout'])
                
                result = await cc_execute(
                    task=test['prompt'],
                    config=config,
                    stream=False
                )
                
                duration = time.time() - start_time
                
                self.results["tests"]["python_api"].append({
                    "name": test['name'],
                    "success": True,
                    "duration": duration,
                    "result": result.get('content', '') if isinstance(result, dict) else str(result)
                })
                print(f"    ✅ Success ({duration:.2f}s)")
                
            except Exception as e:
                duration = time.time() - start_time
                self.results["tests"]["python_api"].append({
                    "name": test['name'],
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
                print(f"    ❌ Failed: {str(e)} ({duration:.2f}s)")
    
    def test_mcp_local(self):
        """Test MCP local server"""
        print("\n🏠 Testing MCP Local...")
        
        # Skip health check - just try to use the server
            
        # Test MCP WebSocket endpoint directly
        test_cases = [
            {
                "name": "MCP WebSocket test",
                "task": "What is 3+3? Just the number.",
                "timeout": 30
            }
        ]
        
        for test in test_cases:
            print(f"  Testing: {test['name']}")
            start_time = time.time()
            
            try:
                # Create a simple WebSocket client test
                import websockets
                import asyncio
                
                async def test_websocket():
                    uri = "ws://127.0.0.1:8003/ws/mcp"
                    try:
                        async with websockets.connect(uri) as websocket:
                            # Send a test message
                            await websocket.send(json.dumps({
                                "task": test['task'],
                                "session_id": "test_session"
                            }))
                            
                            # Wait for response
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            return response
                    except Exception as e:
                        return str(e)
                
                result_text = asyncio.run(test_websocket())
                
                duration = time.time() - start_time
                
                if "error" not in result_text.lower():
                    self.results["tests"]["mcp_local"].append({
                        "name": test['name'],
                        "success": True,
                        "duration": duration,
                        "result": result_text
                    })
                    print(f"    ✅ Success ({duration:.2f}s)")
                else:
                    self.results["tests"]["mcp_local"].append({
                        "name": test['name'],
                        "success": False,
                        "duration": duration,
                        "error": result_text
                    })
                    print(f"    ❌ Failed: {result_text} ({duration:.2f}s)")
                    
            except Exception as e:
                duration = time.time() - start_time
                self.results["tests"]["mcp_local"].append({
                    "name": test['name'],
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
                print(f"    ❌ Failed: {str(e)} ({duration:.2f}s)")
    
    def test_docker(self):
        """Test Docker deployment"""
        print("\n🐳 Testing Docker...")
        
        # Check if container is running
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'cc_execute' not in result.stdout:
                print("  ❌ Docker container 'cc_execute' not running")
                self.results["tests"]["docker"].append({
                    "name": "Container check",
                    "success": False,
                    "error": "Container not running"
                })
                return
        except Exception as e:
            print(f"  ❌ Cannot check Docker status: {e}")
            return
            
        # Test Docker WebSocket endpoint
        test_cases = [
            {
                "name": "Docker WebSocket",
                "task": "What is 4+4? Just the number.",
                "timeout": 30
            }
        ]
        
        for test in test_cases:
            print(f"  Testing: {test['name']}")
            start_time = time.time()
            
            try:
                # Test Docker WebSocket
                import websockets
                import asyncio
                
                async def test_docker_ws():
                    uri = "ws://localhost:8004/ws/mcp"
                    try:
                        async with websockets.connect(uri) as websocket:
                            # Send a test message
                            await websocket.send(json.dumps({
                                "task": test['task'],
                                "session_id": "docker_test"
                            }))
                            
                            # Wait for response
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            return response
                    except Exception as e:
                        return str(e)
                
                result_text = asyncio.run(test_docker_ws())
                
                duration = time.time() - start_time
                
                if "error" not in result_text.lower():
                    self.results["tests"]["docker"].append({
                        "name": test['name'],
                        "success": True,
                        "duration": duration,
                        "result": result_text
                    })
                    print(f"    ✅ Success ({duration:.2f}s)")
                else:
                    self.results["tests"]["docker"].append({
                        "name": test['name'],
                        "success": False,
                        "duration": duration,
                        "error": result_text
                    })
                    print(f"    ❌ Failed: {result_text} ({duration:.2f}s)")
                    
            except Exception as e:
                duration = time.time() - start_time
                self.results["tests"]["docker"].append({
                    "name": test['name'],
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
                print(f"    ❌ Failed: {str(e)} ({duration:.2f}s)")
    
    def generate_summary(self):
        """Generate test summary"""
        for test_type in ["python_api", "mcp_local", "docker"]:
            tests = self.results["tests"][test_type]
            if tests:
                total = len(tests)
                successful = sum(1 for t in tests if t.get("success", False))
                avg_duration = sum(t.get("duration", 0) for t in tests) / total if total > 0 else 0
                
                self.results["summary"][test_type] = {
                    "total_tests": total,
                    "successful": successful,
                    "failed": total - successful,
                    "success_rate": f"{(successful/total)*100:.1f}%" if total > 0 else "0%",
                    "avg_duration": f"{avg_duration:.2f}s"
                }
    
    def save_results(self):
        """Save results to file"""
        output_dir = Path("tests/stress_test_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save raw JSON
        raw_file = output_dir / f"stress_test_raw_{self.timestamp}.json"
        with open(raw_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save prettified report
        report_file = output_dir / f"stress_test_report_{self.timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(f"# CC Executor Stress Test Report\n")
            f.write(f"Generated: {self.results['timestamp']}\n\n")
            
            f.write("## Summary\n\n")
            for test_type, summary in self.results["summary"].items():
                f.write(f"### {test_type.replace('_', ' ').title()}\n")
                f.write(f"- Total Tests: {summary['total_tests']}\n")
                f.write(f"- Successful: {summary['successful']}\n")
                f.write(f"- Failed: {summary['failed']}\n")
                f.write(f"- Success Rate: {summary['success_rate']}\n")
                f.write(f"- Average Duration: {summary['avg_duration']}\n\n")
            
            f.write("## Detailed Results\n\n")
            for test_type, tests in self.results["tests"].items():
                if tests:
                    f.write(f"### {test_type.replace('_', ' ').title()}\n\n")
                    for test in tests:
                        status = "✅" if test.get("success") else "❌"
                        f.write(f"**{test['name']}** {status}\n")
                        f.write(f"- Duration: {test.get('duration', 0):.2f}s\n")
                        if test.get("success"):
                            f.write(f"- Result: `{test.get('result', 'N/A')[:100]}{'...' if len(str(test.get('result', ''))) > 100 else ''}`\n")
                        else:
                            f.write(f"- Error: {test.get('error', 'Unknown error')}\n")
                        f.write("\n")
        
        print(f"\n📊 Results saved to:")
        print(f"  - Raw JSON: {raw_file}")
        print(f"  - Report: {report_file}")
        
        return raw_file, report_file

async def main():
    """Run stress test"""
    print("🚀 Starting CC Executor Quick Stress Test")
    print("=" * 50)
    
    tester = QuickStressTest()
    
    # Run tests
    await tester.test_python_api()
    tester.test_mcp_local()
    tester.test_docker()
    
    # Generate summary and save
    tester.generate_summary()
    raw_file, report_file = tester.save_results()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    for test_type, summary in tester.results["summary"].items():
        print(f"\n{test_type.replace('_', ' ').title()}:")
        print(f"  Success Rate: {summary['success_rate']}")
        print(f"  Avg Duration: {summary['avg_duration']}")

if __name__ == "__main__":
    asyncio.run(main())