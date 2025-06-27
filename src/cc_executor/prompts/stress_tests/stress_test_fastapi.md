# FastAPI Local Stress Test — Self-Improving Prompt

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-27
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation - FastAPI local server stress test

---

## 📋 TASK DEFINITION

Execute ALL stress tests from `unified_stress_test_tasks.json` through FastAPI server running locally.

### Requirements:
1. Start FastAPI server with uvicorn
2. Connect to WebSocket endpoint at ws://localhost:8003/ws/mcp
3. Execute all tests from the JSON file
4. Verify outputs and patterns
5. Track success/failure metrics

### Success Criteria:
- FastAPI server starts and remains healthy
- All tests execute without hanging
- Expected patterns found in outputs
- No hallucinations (verified in transcript)
- Results saved to test_outputs/
- 10:1 success ratio achieved

---

## 🚀 IMPLEMENTATION

```python
#!/usr/bin/env python3
"""FastAPI Local Stress Test - Run all tests through local FastAPI server"""

import asyncio
import json
import subprocess
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
import websockets

class FastAPIStressTest:
    def __init__(self):
        self.server_process = None
        self.base_url = "http://localhost:8003"
        self.ws_url = "ws://localhost:8003/ws/mcp"
        self.results = {"success": 0, "failure": 0, "tests": []}
        self.test_outputs_dir = Path("test_outputs/fastapi")
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
    async def start_fastapi_server(self):
        """Start FastAPI server with uvicorn"""
        print("Starting FastAPI server...")
        
        # Start the server
        self.server_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "src.cc_executor.core.main:app",
                "--host", "0.0.0.0",
                "--port", "8003",
                "--log-level", "info"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        for i in range(30):  # 30 second timeout
            await asyncio.sleep(1)
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=1)
                if resp.status_code == 200:
                    health = resp.json()
                    print(f"✓ FastAPI server started: {health['service']} v{health['version']}")
                    return True
            except:
                continue
                
        print("✗ Failed to start FastAPI server")
        return False
        
    def stop_fastapi_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("Stopping FastAPI server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                
    async def check_server_health(self):
        """Check if server is healthy"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2)
            return resp.status_code == 200
        except:
            return False
            
    async def execute_test(self, test):
        """Execute a single test"""
        marker = f"FASTAPI_{test['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n[{test['id']}] {test['name']}")
        print(f"Marker: {marker}")
        
        # Check server health before test
        if not await self.check_server_health():
            print("  ✗ Server unhealthy, restarting...")
            self.stop_fastapi_server()
            if not await self.start_fastapi_server():
                self.results["failure"] += 1
                return False
        
        try:
            request = test['natural_language_request']
            metatags = test.get('metatags', '')
            
            execute_request = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "executable": "claude",
                    "args": [
                        "--print",
                        f"[marker:{marker}] {metatags} {request}",
                        "--output-format", "stream-json",
                        "--verbose"
                    ]
                },
                "id": 1
            }
            
            # Execute via WebSocket
            output_lines = []
            patterns_found = []
            start_time = time.time()
            
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.send(json.dumps(execute_request))
                
                timeout = test['verification']['timeout']
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        if "params" in data and "output" in data["params"]:
                            output = data["params"]["output"]
                            output_lines.append(output)
                            
                            # Check patterns
                            for pattern in test['verification']['expected_patterns']:
                                if pattern.lower() in output.lower() and pattern not in patterns_found:
                                    patterns_found.append(pattern)
                                    
                        elif "result" in data:
                            duration = time.time() - start_time
                            exit_code = data["result"].get("exit_code", -1)
                            
                            success = exit_code == 0 and len(patterns_found) > 0
                            
                            # Save output
                            self.save_output(test, "\n".join(output_lines), success, duration)
                            
                            if success:
                                self.results["success"] += 1
                                print(f"  ✓ PASSED in {duration:.1f}s")
                                print(f"    Patterns: {patterns_found}")
                            else:
                                self.results["failure"] += 1
                                print(f"  ✗ FAILED in {duration:.1f}s")
                                print(f"    Exit code: {exit_code}")
                                
                            self.results["tests"].append({
                                "id": test['id'],
                                "success": success,
                                "duration": duration,
                                "patterns_found": patterns_found,
                                "server_healthy": True
                            })
                            
                            return success
                            
                    except asyncio.TimeoutError:
                        continue
                        
            # Timeout reached
            self.results["failure"] += 1
            print(f"  ✗ TIMEOUT after {timeout}s")
            return False
            
        except Exception as e:
            self.results["failure"] += 1
            print(f"  ✗ ERROR: {e}")
            return False
            
    def save_output(self, test, output, success, duration):
        """Save test output"""
        filename = f"{test['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.test_outputs_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(f"Test: {test['id']} - {test['name']}\n")
            f.write(f"Success: {success}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Server: FastAPI Local\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("-" * 80 + "\n")
            f.write(output)
            
    async def run_all_tests(self):
        """Run all tests from JSON"""
        # Load tests
        json_path = Path("src/cc_executor/tasks/unified_stress_test_tasks.json")
        with open(json_path) as f:
            test_data = json.load(f)
            
        # Start FastAPI server
        if not await self.start_fastapi_server():
            print("Failed to start FastAPI server!")
            return
            
        try:
            # Get server stats
            resp = requests.get(f"{self.base_url}/health")
            health = resp.json()
            print(f"\nServer Stats:")
            print(f"  Active Sessions: {health['active_sessions']}")
            print(f"  Max Sessions: {health['max_sessions']}")
            
            print(f"\nRunning {sum(len(cat['tasks']) for cat in test_data['categories'].values())} tests...")
            
            # Execute all tests
            for category, cat_data in test_data['categories'].items():
                print(f"\n{'='*60}")
                print(f"Category: {category}")
                print(f"{'='*60}")
                
                for test in cat_data['tasks']:
                    await self.execute_test(test)
                    
            # Check final server health
            if await self.check_server_health():
                resp = requests.get(f"{self.base_url}/health")
                final_health = resp.json()
                print(f"\nFinal Server Stats:")
                print(f"  Active Sessions: {final_health['active_sessions']}")
                print(f"  Uptime: {final_health['uptime_seconds']}s")
                    
            # Generate report
            self.generate_report()
            
        finally:
            self.stop_fastapi_server()
            
    def generate_report(self):
        """Generate test report"""
        print(f"\n{'='*60}")
        print("FASTAPI LOCAL STRESS TEST REPORT")
        print(f"{'='*60}")
        
        total = self.results["success"] + self.results["failure"]
        success_rate = self.results["success"] / max(1, total) * 100
        
        print(f"Total Tests: {total}")
        print(f"Successful: {self.results['success']}")
        print(f"Failed: {self.results['failure']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        ratio = self.results["success"] / max(1, self.results["failure"])
        print(f"Success Ratio: {ratio:.1f}:1 (need 10:1 to graduate)")
        
        # Save detailed report
        report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed report: {report_path}")

if __name__ == "__main__":
    print("FASTAPI LOCAL STRESS TEST")
    print("=" * 60)
    
    tester = FastAPIStressTest()
    asyncio.run(tester.run_all_tests())
```

---

## 📊 EXECUTION LOG

### Run 1: [Date]
```
MARKER_FASTAPI_20250627_000000
[Results will be logged here]
```

---

## 🔧 RECOVERY TESTS

### Test 1: FastAPI Server Health
```python
def test_fastapi_health():
    """Ensure FastAPI server responds to health checks"""
    import requests
    resp = requests.get("http://localhost:8003/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
```

### Test 2: WebSocket Endpoint
```python
async def test_websocket_endpoint():
    """Ensure WebSocket endpoint accepts connections"""
    import websockets
    async with websockets.connect("ws://localhost:8003/ws/mcp") as ws:
        # Connection successful
        await ws.close()
```

### Test 3: Server Restart
```python
def test_server_restart():
    """Ensure server can be stopped and restarted"""
    import subprocess
    import time
    
    # Start server
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.cc_executor.core.main:app"])
    time.sleep(3)
    
    # Stop server
    proc.terminate()
    proc.wait()
    
    # Restart
    proc2 = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.cc_executor.core.main:app"])
    time.sleep(3)
    
    assert proc2.poll() is None
    proc2.terminate()
```