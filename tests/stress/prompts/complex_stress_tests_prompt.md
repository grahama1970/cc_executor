# Complex Stress Tests — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial implementation for complex stress tests.     | TBD    |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Execute complex stress tests that push cc_executor's limits with long-form content generation, detailed technical analysis, and comprehensive guides (90-300s). These tests validate system stability under heavy load.

### 2. Core Principles & Constraints
- Each test must complete within 300 seconds
- Focus on long-form content, technical documentation, and detailed analysis
- Test memory efficiency with large outputs
- Monitor resource usage during execution
- Validate proper stream handling for extended responses

### 3. API Contract & Dependencies
- **Input**: JSON configuration file at `/home/graham/workspace/experiments/cc_executor/tests/stress/configs/complex_stress_tests.json`
- **Output**: Markdown report at `/home/graham/workspace/experiments/cc_executor/tests/stress/reports/complex_stress_tests_report.md`
- **Dependencies**:
  - cc_executor server running on localhost:8000
  - Claude CLI available in PATH
  - Python 3.10+ with asyncio support
  - psutil for resource monitoring

---
## 🤖 IMPLEMENTER'S WORKSPACE

### **Implementation Code Block**
```python
#!/usr/bin/env python3
"""
Complex Stress Test Runner for cc_executor

Executes complex, long-running tests that generate extensive output.
"""
import asyncio
import json
import time
import sys
import os
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add library paths to Python path
sys.path.insert(0, "/home/graham/workspace/experiments/cc_executor/tests/stress/lib")
sys.path.insert(0, "/home/graham/workspace/experiments/cc_executor/src")

try:
    # Try to import the minimal client first
    from cc_executor.client.websocket_client_standalone import WebSocketClient
except ImportError:
    # Fall back to the full client if available
    from cc_executor.client.websocket_client_standalone import WebSocketClient

# Configuration
CONFIG_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/configs/complex_stress_tests.json")
REPORT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/reports/complex_stress_tests_report.md")
EXECUTION_MARKER = f"COMPLEX_STRESS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class ComplexStressTestRunner:
    """Runs complex stress tests against cc_executor with resource monitoring."""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.config = None
        self.process = psutil.Process()
        self.client = WebSocketClient(host="localhost", port=8004)
        
    async def load_config(self) -> Dict[str, Any]:
        """Load test configuration from JSON."""
        with open(CONFIG_PATH, 'r') as f:
            self.config = json.load(f)
        return self.config
        
    def get_system_resources(self) -> Dict[str, float]:
        """Get current system resource usage."""
        return {
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "memory_percent": self.process.memory_percent(),
            "num_threads": self.process.num_threads(),
        }
        
    async def execute_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test with resource monitoring."""
        test_start = time.time()
        resources_start = self.get_system_resources()
        
        result = {
            "id": test["id"],
            "name": test["name"],
            "description": test["description"],
            "command": test["command"],
            "started_at": datetime.now().isoformat(),
            "success": False,
            "error": None,
            "output": "",
            "duration": 0,
            "patterns_found": [],
            "output_length": 0,
            "chunks_received": 0,
            "resources": {
                "start": resources_start,
                "peak": resources_start.copy(),
                "end": None
            }
        }
        
        # Resource monitoring task
        peak_resources = resources_start.copy()
        monitor_task = asyncio.create_task(self._monitor_resources(peak_resources))
        
        try:
            # Track progress
            last_progress_time = time.time()
            
            # Execute command via WebSocket client
            ws_result = await self.client.execute_command(
                command=test["command"],
                timeout=self.config.get("timeout", 300),
                restart_handler=True  # Restart for each test to ensure clean state
            )
            
            # Process WebSocket result
            if ws_result["success"]:
                result["success"] = True
                result["exit_code"] = ws_result.get("exit_code", 0)
                result["output"] = "\n".join(ws_result.get("output_data", []))
                result["duration"] = ws_result["duration"]
                result["output_length"] = len(result["output"])
                result["chunks_received"] = ws_result.get("outputs", 0)
                
                # Check for expected patterns
                for pattern in test.get("expected_patterns", []):
                    if pattern.lower() in result["output"].lower():
                        result["patterns_found"].append(pattern)
                
                # Mark as successful if enough patterns found (80% for complex tests)
                required_patterns = len(test.get("expected_patterns", []))
                if required_patterns > 0:
                    pattern_ratio = len(result["patterns_found"]) / required_patterns
                    if pattern_ratio < 0.8:
                        result["success"] = False
                        result["error"] = f"Pattern coverage too low: {pattern_ratio*100:.0f}% (need 80%)"
            else:
                result["error"] = ws_result.get("error", "Unknown error")
                result["duration"] = ws_result.get("duration", 0)
                result["output"] = "\n".join(ws_result.get("output_data", []))
                    
        except Exception as e:
            result["error"] = f"Exception: {type(e).__name__}: {str(e)}"
            result["duration"] = time.time() - test_start
        finally:
            monitor_task.cancel()
            result["resources"]["end"] = self.get_system_resources()
            result["resources"]["peak"] = peak_resources
            
        return result
    
    async def _monitor_resources(self, peak_resources: Dict[str, float]) -> None:
        """Monitor and track peak resource usage."""
        while True:
            try:
                current = self.get_system_resources()
                for key in peak_resources:
                    if current[key] > peak_resources[key]:
                        peak_resources[key] = current[key]
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
    
    async def run_all_tests(self) -> None:
        """Execute all tests from configuration."""
        self.start_time = time.time()
        await self.load_config()
        
        print(f"🚀 Starting Complex Stress Tests - {EXECUTION_MARKER}")
        print(f"📋 Running {len(self.config['tests'])} complex tests")
        print(f"⏱️  Timeout: {self.config.get('timeout', 300)}s per test")
        print(f"💾 Initial Memory: {self.process.memory_info().rss / 1024 / 1024:.1f} MB")
        
        # Run tests sequentially with resource monitoring
        for i, test in enumerate(self.config["tests"], 1):
            print(f"\n[{i}/{len(self.config['tests'])}] Running: {test['name']}")
            print(f"   Description: {test['description']}")
            print(f"   Expected duration: 90-300s")
            
            result = await self.execute_test(test)
            self.results.append(result)
            
            # Show result with resource usage
            if result["success"]:
                print(f"✅ PASSED in {result['duration']:.2f}s")
            else:
                print(f"❌ FAILED: {result['error']}")
                
            print(f"   Output: {result['output_length']:,} chars in {result['chunks_received']} chunks")
            print(f"   Peak Memory: {result['resources']['peak']['memory_mb']:.1f} MB")
            print(f"   Peak CPU: {result['resources']['peak']['cpu_percent']:.1f}%")
            
            # Brief pause between complex tests
            if i < len(self.config['tests']):
                print("   Pausing 5s before next test...")
                await asyncio.sleep(5)
        
        # Cleanup WebSocket client
        await self.client.cleanup()
                    
        # Generate report
        await self.generate_report()
        
    async def generate_report(self) -> None:
        """Generate comprehensive markdown report with resource analysis."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - passed
        
        report = f"""# Complex Stress Test Report

**Generated**: {datetime.now().isoformat()}  
**Execution ID**: {EXECUTION_MARKER}  
**Total Duration**: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)  
**Configuration**: {CONFIG_PATH}

## Summary

- **Total Tests**: {len(self.results)}
- **Passed**: {passed} ✅
- **Failed**: {failed} ❌
- **Success Rate**: {(passed/len(self.results)*100):.1f}%
- **Average Duration**: {sum(r['duration'] for r in self.results)/len(self.results):.2f}s
- **Total Output Generated**: {sum(r['output_length'] for r in self.results):,} characters

## Resource Usage Summary

| Metric | Average | Peak |
|--------|---------|------|
"""
        # Calculate resource statistics
        avg_memory = sum(r['resources']['peak']['memory_mb'] for r in self.results) / len(self.results)
        peak_memory = max(r['resources']['peak']['memory_mb'] for r in self.results)
        avg_cpu = sum(r['resources']['peak']['cpu_percent'] for r in self.results) / len(self.results)
        peak_cpu = max(r['resources']['peak']['cpu_percent'] for r in self.results)
        
        report += f"| Memory (MB) | {avg_memory:.1f} | {peak_memory:.1f} |\n"
        report += f"| CPU (%) | {avg_cpu:.1f} | {peak_cpu:.1f} |\n"
        
        report += "\n## Test Results\n\n"
        
        for result in self.results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            report += f"""### {result['name']} - {status}

- **ID**: `{result['id']}`
- **Description**: {result['description']}
- **Duration**: {result['duration']:.2f}s
- **Output Size**: {result['output_length']:,} characters
- **Chunks Received**: {result['chunks_received']}
- **Peak Memory**: {result['resources']['peak']['memory_mb']:.1f} MB
- **Peak CPU**: {result['resources']['peak']['cpu_percent']:.1f}%
- **Command**: `{result['command']}`
"""
            
            if result.get("patterns_found") is not None:
                expected_count = len(result.get("expected_patterns", [])) if "expected_patterns" in result else 0
                if expected_count > 0:
                    found_ratio = len(result['patterns_found']) / expected_count
                    report += f"- **Patterns Found**: {len(result['patterns_found'])}/{expected_count} ({found_ratio*100:.0f}%)\n"
                if result['patterns_found']:
                    report += f"  - Found: {', '.join(result['patterns_found'][:5])}"
                    if len(result['patterns_found']) > 5:
                        report += f" ... and {len(result['patterns_found'])-5} more"
                    report += "\n"
                
            if result["error"]:
                report += f"- **Error**: {result['error']}\n"
                
            if result["output"]:
                # Show first 2000 chars for complex tests
                truncated = result['output'][:2000] + f"\n... (truncated, showing 2000/{result['output_length']:,} chars)" if len(result['output']) > 2000 else result['output']
                report += f"\n<details>\n<summary>Output Preview</summary>\n\n```\n{truncated}\n```\n\n</details>\n\n"
            else:
                report += "\n"
                
        # Performance Analysis
        report += """## Performance Analysis

### Duration Distribution
"""
        durations = [r['duration'] for r in self.results]
        report += f"- **< 2 minutes**: {sum(1 for d in durations if d < 120)} tests\n"
        report += f"- **2-3 minutes**: {sum(1 for d in durations if 120 <= d < 180)} tests\n"
        report += f"- **3-4 minutes**: {sum(1 for d in durations if 180 <= d < 240)} tests\n"
        report += f"- **> 4 minutes**: {sum(1 for d in durations if d >= 240)} tests\n"
        
        report += f"\n### Output Size Distribution\n"
        sizes = [r['output_length'] for r in self.results]
        report += f"- **< 10K chars**: {sum(1 for s in sizes if s < 10000)} tests\n"
        report += f"- **10K-50K chars**: {sum(1 for s in sizes if 10000 <= s < 50000)} tests\n"
        report += f"- **50K-100K chars**: {sum(1 for s in sizes if 50000 <= s < 100000)} tests\n"
        report += f"- **> 100K chars**: {sum(1 for s in sizes if s >= 100000)} tests\n"
        
        # Write report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, 'w') as f:
            f.write(report)
            
        print(f"\n📄 Report written to: {REPORT_PATH}")
        print(f"📊 Success Rate: {(passed/len(self.results)*100):.1f}% ({passed}/{len(self.results)})")
        print(f"⏱️  Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")

if __name__ == "__main__":
    # Self-verification mode
    runner = ComplexStressTestRunner()
    
    # Run a simple verification
    print("🔍 Running self-verification...")
    
    # Check configuration exists
    assert CONFIG_PATH.exists(), f"Configuration not found: {CONFIG_PATH}"
    
    # Load and validate configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    assert "tests" in config, "Configuration missing 'tests' array"
    assert len(config["tests"]) > 0, "No tests defined"
    assert all("id" in t for t in config["tests"]), "All tests must have an 'id'"
    assert all("command" in t for t in config["tests"]), "All tests must have a 'command'"
    assert config.get("timeout", 300) >= 180, "Timeout must be at least 180 seconds for complex tests"
    
    # Verify psutil is available
    try:
        import psutil
        print("✅ psutil available for resource monitoring")
    except ImportError:
        print("⚠️  psutil not available - resource monitoring disabled")
    
    print("✅ Configuration valid")
    print(f"📋 Found {len(config['tests'])} complex tests")
    print(f"⏱️  Timeout: {config.get('timeout', 300)}s per test")
    print(f"⚠️  Estimated total runtime: {len(config['tests']) * 3}-{len(config['tests']) * 5} minutes")
    
    # Run the actual tests
    asyncio.run(runner.run_all_tests())
```

### **Task Execution Plan & Log**

#### **Step 1: Validate Configuration**
*   **Goal:** Ensure configuration is suitable for complex tests
*   **Action:** Validate JSON and check timeout settings
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_complex_stress_tests.py --verify-only`
*   **Expected Output:** Configuration validation with runtime estimates

#### **Step 2: Execute Complex Tests**
*   **Goal:** Run all complex tests with resource monitoring
*   **Action:** Execute runner with progress tracking
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_complex_stress_tests.py`
*   **Expected Output:** Progress updates every 10s, resource usage stats

---
## 🎓 GRADUATION & VERIFICATION

### 1. Component Integration Test
*   **Success Criteria**: 
    - All 7 complex tests must complete without timeout errors
    - At least 60% of tests must pass (complex tests are challenging)
    - Resource usage must stay within reasonable bounds
    - Detailed performance analysis must be generated

### 2. Self-Verification
*   Validates configuration and estimates runtime
*   Monitors system resources throughout execution
*   Generates comprehensive report with performance analysis