# Local Stress Test — Self-Improving Prompt

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
- v1: Initial implementation - local websocket handler stress test

---

## 📋 TASK DEFINITION

Execute ALL stress tests from `unified_stress_test_tasks.json` directly through local `websocket_handler.py` without any server.

### Requirements:
1. Start websocket_handler.py directly as a subprocess
2. Connect to it via WebSocket client
3. Execute all tests from the JSON file
4. Verify outputs and patterns
5. Track success/failure metrics

### Success Criteria:
- All tests execute without hanging
- Expected patterns found in outputs
- No hallucinations (verified in transcript)
- Results saved to test_outputs/
- 10:1 success ratio achieved

---

## 🚀 IMPLEMENTATION

```python
#!/usr/bin/env python3
"""Local Stress Test - Run all tests directly via websocket_handler.py"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import websockets

class LocalStressTest:
    def __init__(self):
        self.ws_process = None
        self.ws_url = "ws://localhost:8003/ws/mcp"
        self.results = {"success": 0, "failure": 0, "tests": []}
        self.test_outputs_dir = Path("test_outputs/local")
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
    async def start_websocket_handler(self):
        """Start websocket_handler.py as subprocess"""
        print("Starting local websocket_handler.py...")
        
        # Start the handler
        self.ws_process = subprocess.Popen(
            [sys.executable, "-m", "src.cc_executor.core.websocket_handler"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for it to start
        await asyncio.sleep(3)
        
        # Verify it's running
        try:
            async with websockets.connect(self.ws_url) as ws:
                await ws.close()
            print("✓ WebSocket handler started successfully")
            return True
        except:
            print("✗ Failed to start WebSocket handler")
            return False
            
    def stop_websocket_handler(self):
        """Stop the websocket handler"""
        if self.ws_process:
            print("Stopping websocket handler...")
            self.ws_process.terminate()
            self.ws_process.wait(timeout=5)
            
    async def execute_test(self, test):
        """Execute a single test"""
        marker = f"LOCAL_{test['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n[{test['id']}] {test['name']}")
        print(f"Marker: {marker}")
        
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
                                "patterns_found": patterns_found
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
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("-" * 80 + "\n")
            f.write(output)
            
    async def run_all_tests(self):
        """Run all tests from JSON"""
        # Load tests
        json_path = Path("src/cc_executor/tasks/unified_stress_test_tasks.json")
        with open(json_path) as f:
            test_data = json.load(f)
            
        # Start websocket handler
        if not await self.start_websocket_handler():
            print("Failed to start websocket handler!")
            return
            
        try:
            print(f"\nRunning {sum(len(cat['tasks']) for cat in test_data['categories'].values())} tests...")
            
            # Execute all tests
            for category, cat_data in test_data['categories'].items():
                print(f"\n{'='*60}")
                print(f"Category: {category}")
                print(f"{'='*60}")
                
                for test in cat_data['tasks']:
                    await self.execute_test(test)
                    
            # Generate report
            self.generate_report()
            
        finally:
            self.stop_websocket_handler()
            
    def generate_report(self):
        """Generate test report"""
        print(f"\n{'='*60}")
        print("LOCAL STRESS TEST REPORT")
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
    print("LOCAL STRESS TEST - Direct WebSocket Handler")
    print("=" * 60)
    
    tester = LocalStressTest()
    asyncio.run(tester.run_all_tests())
```

---

## 📊 EXECUTION LOG

### Run 1: [Date]
```
MARKER_LOCAL_20250627_000000
[Results will be logged here]
```

---

## 🔧 RECOVERY TESTS

### Test 1: WebSocket Handler Startup
```python
def test_websocket_startup():
    """Ensure websocket handler starts correctly"""
    import subprocess
    import time
    
    proc = subprocess.Popen([sys.executable, "-m", "src.cc_executor.core.websocket_handler"])
    time.sleep(3)
    
    # Check if still running
    assert proc.poll() is None, "WebSocket handler crashed on startup"
    proc.terminate()
```

### Test 2: JSON Loading
```python
def test_json_valid():
    """Ensure test JSON is valid"""
    import json
    with open("src/cc_executor/tasks/unified_stress_test_tasks.json") as f:
        data = json.load(f)
    assert "categories" in data
```