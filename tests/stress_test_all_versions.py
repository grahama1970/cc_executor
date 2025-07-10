#!/usr/bin/env python3
"""
Comprehensive stress test for CC Executor - all versions
Tests Python API, MCP local, and Docker deployment
"""

import asyncio
import json
import time
import uuid
import subprocess
import os
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cc_executor.client.cc_execute import cc_execute
from src.cc_executor.client.client import WebSocketClient

class CCExecutorStressTest:
    def __init__(self):
        self.execution_uuid = str(uuid.uuid4())
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "execution_uuid": self.execution_uuid,
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
                "expected": "4"
            },
            {
                "name": "Code generation",
                "prompt": "Write a Python function that returns the first 10 fibonacci numbers. Just the function, no explanation.",
                "expected": "def"
            },
            {
                "name": "JSON mode",
                "prompt": "List 3 colors",
                "json_mode": True,
                "expected": "result"
            },
            {
                "name": "Long task",
                "prompt": "Count from 1 to 20, one number per line",
                "expected": "20"
            },
            {
                "name": "Error handling",
                "prompt": "What is the square root of -1 in real numbers?",
                "expected": "imaginary"
            }
        ]
        
        for test in test_cases:
            start = time.time()
            try:
                if test.get("json_mode"):
                    result = await cc_execute(test["prompt"], json_mode=True)
                    success = test["expected"] in str(result)
                    output = json.dumps(result)[:200]
                else:
                    result = await cc_execute(test["prompt"])
                    success = test["expected"].lower() in result.lower()
                    output = result[:200]
                
                duration = time.time() - start
                
                self.results["tests"]["python_api"].append({
                    "test": test["name"],
                    "success": success,
                    "duration": duration,
                    "output": output,
                    "error": None
                })
                
                status = "✅" if success else "❌"
                print(f"{status} {test['name']}: {duration:.2f}s")
                
            except Exception as e:
                duration = time.time() - start
                self.results["tests"]["python_api"].append({
                    "test": test["name"],
                    "success": False,
                    "duration": duration,
                    "output": None,
                    "error": str(e)
                })
                print(f"❌ {test['name']}: {e}")
    
    async def test_mcp_local(self):
        """Test MCP WebSocket locally"""
        print("\n🔌 Testing MCP Local WebSocket...")
        
        # Check if local server is running
        try:
            client = WebSocketClient(host="localhost", port=8003)
            
            test_cases = [
                {
                    "name": "Echo test",
                    "command": "echo 'MCP Local Test'",
                    "expected": "MCP Local Test"
                },
                {
                    "name": "Claude simple",
                    "command": "claude -p \"What is 3+3? Just the number.\"",
                    "expected": "6"
                },
                {
                    "name": "Python execution",
                    "command": "python -c \"print('Hello from MCP')\"",
                    "expected": "Hello from MCP"
                }
            ]
            
            for test in test_cases:
                start = time.time()
                try:
                    result = await client.execute_command(test["command"], timeout=30)
                    output = result.get("output_data", "")
                    success = test["expected"] in output
                    duration = time.time() - start
                    
                    self.results["tests"]["mcp_local"].append({
                        "test": test["name"],
                        "success": success,
                        "duration": duration,
                        "output": output[:200],
                        "exit_code": result.get("exit_code", -1),
                        "error": None
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"{status} {test['name']}: {duration:.2f}s")
                    
                except Exception as e:
                    duration = time.time() - start
                    self.results["tests"]["mcp_local"].append({
                        "test": test["name"],
                        "success": False,
                        "duration": duration,
                        "output": None,
                        "error": str(e)
                    })
                    print(f"❌ {test['name']}: {e}")
                    
        except Exception as e:
            print(f"⚠️  MCP Local not available: {e}")
            self.results["tests"]["mcp_local"].append({
                "test": "Connection",
                "success": False,
                "error": f"Server not running: {e}"
            })
    
    async def test_docker(self):
        """Test Docker deployment"""
        print("\n🐳 Testing Docker Deployment...")
        
        # Check if Docker is running
        docker_check = subprocess.run(
            ["docker", "ps", "--filter", "name=cc_execute"],
            capture_output=True,
            text=True
        )
        
        if "cc_execute" not in docker_check.stdout:
            print("⚠️  Docker container not running")
            self.results["tests"]["docker"].append({
                "test": "Container check",
                "success": False,
                "error": "Docker container 'cc_execute' not found"
            })
            return
        
        # Test Docker WebSocket
        try:
            client = WebSocketClient(host="localhost", port=8004)
            
            test_cases = [
                {
                    "name": "Docker echo",
                    "command": "echo 'Docker Test'",
                    "expected": "Docker Test"
                },
                {
                    "name": "Docker Claude",
                    "command": "claude -p \"What is 4+4? Just the number.\"",
                    "expected": "8"
                },
                {
                    "name": "Docker Python",
                    "command": "python -c \"import sys; print(f'Python {sys.version.split()[0]}')\"",
                    "expected": "Python"
                }
            ]
            
            for test in test_cases:
                start = time.time()
                try:
                    result = await client.execute_command(test["command"], timeout=30)
                    output = result.get("output_data", "")
                    success = test["expected"] in output
                    duration = time.time() - start
                    
                    self.results["tests"]["docker"].append({
                        "test": test["name"],
                        "success": success,
                        "duration": duration,
                        "output": output[:200],
                        "exit_code": result.get("exit_code", -1),
                        "error": None
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"{status} {test['name']}: {duration:.2f}s")
                    
                except Exception as e:
                    duration = time.time() - start
                    self.results["tests"]["docker"].append({
                        "test": test["name"],
                        "success": False,
                        "duration": duration,
                        "output": None,
                        "error": str(e)
                    })
                    print(f"❌ {test['name']}: {e}")
                    
        except Exception as e:
            print(f"⚠️  Docker WebSocket not available: {e}")
            self.results["tests"]["docker"].append({
                "test": "Connection",
                "success": False,
                "error": f"WebSocket not available: {e}"
            })
        
        # Test Docker REST API
        print("\n🌐 Testing Docker REST API...")
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            try:
                # Health check
                async with session.get("http://localhost:8001/health") as resp:
                    if resp.status == 200:
                        print("✅ Docker API health check passed")
                        self.results["tests"]["docker"].append({
                            "test": "API health check",
                            "success": True,
                            "duration": 0.1
                        })
                    else:
                        print(f"❌ Docker API health check failed: {resp.status}")
                        
                # Test execution endpoint
                payload = {
                    "tasks": ["What is 5+5?"],
                    "timeout_per_task": 30
                }
                
                start = time.time()
                async with session.post(
                    "http://localhost:8001/execute",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        duration = time.time() - start
                        success = result.get("completed_tasks", 0) > 0
                        
                        self.results["tests"]["docker"].append({
                            "test": "API execution",
                            "success": success,
                            "duration": duration,
                            "output": str(result)[:200]
                        })
                        
                        status = "✅" if success else "❌"
                        print(f"{status} Docker API execution: {duration:.2f}s")
                        
            except Exception as e:
                print(f"❌ Docker API error: {e}")
                self.results["tests"]["docker"].append({
                    "test": "API execution",
                    "success": False,
                    "error": str(e)
                })
    
    async def run_stress_test(self):
        """Run all stress tests"""
        print(f"🔐 Stress Test UUID: {self.execution_uuid}")
        print("=" * 60)
        
        # Run all tests
        await self.test_python_api()
        await self.test_mcp_local()
        await self.test_docker()
        
        # Calculate summary
        for version, tests in self.results["tests"].items():
            if tests:
                total = len(tests)
                passed = sum(1 for t in tests if t.get("success", False))
                avg_duration = sum(t.get("duration", 0) for t in tests if t.get("duration")) / max(1, len([t for t in tests if t.get("duration")]))
                
                self.results["summary"][version] = {
                    "total_tests": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": f"{(passed/total)*100:.1f}%",
                    "avg_duration": f"{avg_duration:.2f}s"
                }
        
        # Save results
        results_dir = Path(__file__).parent / "stress_test_results"
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / f"stress_test_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Print summary
        print("\n📊 Summary:")
        print("=" * 60)
        for version, summary in self.results["summary"].items():
            print(f"\n{version.upper()}:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Passed: {summary['passed']}")
            print(f"  Failed: {summary['failed']}")
            print(f"  Success rate: {summary['success_rate']}")
            print(f"  Avg duration: {summary['avg_duration']}")
        
        print(f"\n🔐 Verification UUID: {self.execution_uuid}")
        
        return self.results

async def main():
    """Run the stress test"""
    tester = CCExecutorStressTest()
    await tester.run_stress_test()

if __name__ == "__main__":
    asyncio.run(main())