# Simple Stress Tests — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial implementation for simple stress tests.      | TBD    |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Execute simple stress tests that validate basic cc_executor functionality with quick-running commands (5-30s). These tests form the foundation for more complex test suites.

### 2. Core Principles & Constraints
- Each test must complete within 120 seconds
- Focus on basic arithmetic, echo commands, and simple Claude queries
- Verify stream handling and websocket functionality
- No file system modifications
- All tests must be independently runnable

### 3. API Contract & Dependencies
- **Input**: JSON configuration file at `/home/graham/workspace/experiments/cc_executor/tests/stress/configs/simple_stress_tests.json`
- **Output**: Markdown report at `/home/graham/workspace/experiments/cc_executor/tests/stress/reports/simple_stress_tests_report.md`
- **Dependencies**:
  - cc_executor server running on localhost:8000
  - Claude CLI available in PATH
  - Python 3.10+ with asyncio support

---
## 🤖 IMPLEMENTER'S WORKSPACE

### **Implementation Code Block**
```python
#!/usr/bin/env python3
"""
Simple Stress Test Runner for cc_executor

Executes simple, quick-running tests to validate basic functionality.
"""
import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp
from pathlib import Path

# Configuration
CONFIG_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/configs/simple_stress_tests.json")
REPORT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/reports/simple_stress_tests_report.md")
CC_EXECUTOR_URL = "http://localhost:8000"
EXECUTION_MARKER = f"SIMPLE_STRESS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class SimpleStressTestRunner:
    """Runs simple stress tests against cc_executor."""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.config = None
        
    async def load_config(self) -> Dict[str, Any]:
        """Load test configuration from JSON."""
        with open(CONFIG_PATH, 'r') as f:
            self.config = json.load(f)
        return self.config
        
    async def execute_test(self, session: aiohttp.ClientSession, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test and return results."""
        test_start = time.time()
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
            "patterns_found": []
        }
        
        try:
            # Prepare request payload
            payload = {
                "command": test["command"],
                "timeout": self.config.get("timeout", 120),
                "stream": True,
                "execution_id": f"{EXECUTION_MARKER}_{test['id']}"
            }
            
            # Execute command via cc_executor
            async with session.post(f"{CC_EXECUTOR_URL}/execute", json=payload) as response:
                if response.status != 200:
                    result["error"] = f"HTTP {response.status}: {await response.text()}"
                    return result
                    
                # Collect streamed output
                output_lines = []
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode().strip())
                            if data.get("type") == "output":
                                output_lines.append(data.get("data", ""))
                            elif data.get("type") == "error":
                                result["error"] = data.get("error", "Unknown error")
                            elif data.get("type") == "complete":
                                result["exit_code"] = data.get("exit_code", -1)
                                result["success"] = data.get("exit_code") == 0
                        except json.JSONDecodeError:
                            output_lines.append(line.decode().strip())
                
                result["output"] = "\n".join(output_lines)
                
                # Check for expected patterns
                for pattern in test.get("expected_patterns", []):
                    if pattern.lower() in result["output"].lower():
                        result["patterns_found"].append(pattern)
                
                # Mark as successful if all patterns found
                if len(result["patterns_found"]) == len(test.get("expected_patterns", [])):
                    result["success"] = True
                    
        except asyncio.TimeoutError:
            result["error"] = f"Test timed out after {self.config.get('timeout', 120)} seconds"
        except Exception as e:
            result["error"] = f"Exception: {str(e)}"
        finally:
            result["duration"] = time.time() - test_start
            
        return result
    
    async def run_all_tests(self) -> None:
        """Execute all tests from configuration."""
        self.start_time = time.time()
        await self.load_config()
        
        print(f"🚀 Starting Simple Stress Tests - {EXECUTION_MARKER}")
        print(f"📋 Running {len(self.config['tests'])} tests")
        
        async with aiohttp.ClientSession() as session:
            # First verify cc_executor is running
            try:
                async with session.get(f"{CC_EXECUTOR_URL}/health") as resp:
                    if resp.status != 200:
                        print(f"❌ cc_executor not healthy: {resp.status}")
                        sys.exit(1)
            except Exception as e:
                print(f"❌ Cannot connect to cc_executor: {e}")
                sys.exit(1)
                
            # Run tests sequentially to avoid overwhelming the system
            for i, test in enumerate(self.config["tests"], 1):
                print(f"\n[{i}/{len(self.config['tests'])}] Running: {test['name']}")
                result = await self.execute_test(session, test)
                self.results.append(result)
                
                # Show result
                if result["success"]:
                    print(f"✅ PASSED in {result['duration']:.2f}s")
                else:
                    print(f"❌ FAILED: {result['error']}")
                    
        # Generate report
        await self.generate_report()
        
    async def generate_report(self) -> None:
        """Generate markdown report of test results."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - passed
        
        report = f"""# Simple Stress Test Report

**Generated**: {datetime.now().isoformat()}  
**Execution ID**: {EXECUTION_MARKER}  
**Total Duration**: {total_duration:.2f} seconds  
**Configuration**: {CONFIG_PATH}

## Summary

- **Total Tests**: {len(self.results)}
- **Passed**: {passed} ✅
- **Failed**: {failed} ❌
- **Success Rate**: {(passed/len(self.results)*100):.1f}%

## Test Results

"""
        
        for result in self.results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            report += f"""### {result['name']} - {status}

- **ID**: `{result['id']}`
- **Description**: {result['description']}
- **Duration**: {result['duration']:.2f}s
- **Command**: `{result['command']}`
"""
            
            if result["expected_patterns"]:
                report += f"- **Patterns Found**: {len(result['patterns_found'])}/{len(result.get('expected_patterns', []))}\n"
                
            if result["error"]:
                report += f"- **Error**: {result['error']}\n"
                
            if result["output"]:
                report += f"\n<details>\n<summary>Output</summary>\n\n```\n{result['output'][:1000]}\n```\n\n</details>\n\n"
            else:
                report += "\n"
                
        # Write report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, 'w') as f:
            f.write(report)
            
        print(f"\n📄 Report written to: {REPORT_PATH}")
        print(f"📊 Success Rate: {(passed/len(self.results)*100):.1f}% ({passed}/{len(self.results)})")

if __name__ == "__main__":
    # Self-verification mode
    runner = SimpleStressTestRunner()
    
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
    
    print("✅ Configuration valid")
    print(f"📋 Found {len(config['tests'])} tests to run")
    
    # Run the actual tests
    asyncio.run(runner.run_all_tests())
```

### **Task Execution Plan & Log**

#### **Step 1: Validate Configuration**
*   **Goal:** Ensure test configuration file exists and is valid
*   **Action:** Load and validate the JSON configuration
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_simple_stress_tests.py --verify-only`
*   **Expected Output:** Configuration validation messages

#### **Step 2: Execute Tests**
*   **Goal:** Run all simple stress tests against cc_executor
*   **Action:** Execute the runner script
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_simple_stress_tests.py`
*   **Expected Output:** Test execution progress and final report

---
## 🎓 GRADUATION & VERIFICATION

### 1. Component Integration Test
*   **Success Criteria**: 
    - All 5 simple tests must execute without infrastructure errors
    - At least 80% of tests must pass pattern matching
    - Report must be generated successfully

### 2. Self-Verification
*   The `if __name__ == "__main__"` block validates configuration and runs tests
*   Output includes success rate and detailed results
*   Report is automatically generated in markdown format