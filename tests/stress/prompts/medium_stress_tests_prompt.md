# Medium Stress Tests — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial implementation for medium stress tests.      | TBD    |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Execute medium complexity stress tests that validate cc_executor's ability to handle code generation, creative writing, and multi-step responses (30-90s). These tests bridge simple arithmetic and complex analytical tasks.

### 2. Core Principles & Constraints
- Each test must complete within 180 seconds
- Focus on code generation, creative tasks, and moderate-length responses
- Test streaming capabilities with longer outputs
- Verify proper handling of multi-line code blocks
- All tests must handle Unicode and special characters

### 3. API Contract & Dependencies
- **Input**: JSON configuration file at `/home/graham/workspace/experiments/cc_executor/tests/stress/configs/medium_stress_tests.json`
- **Output**: Markdown report at `/home/graham/workspace/experiments/cc_executor/tests/stress/reports/medium_stress_tests_report.md`
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
Medium Stress Test Runner for cc_executor

Executes medium complexity tests including code generation and creative tasks.
"""
import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
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
CONFIG_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/configs/medium_stress_tests.json")
REPORT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/reports/medium_stress_tests_report.md")
EXECUTION_MARKER = f"MEDIUM_STRESS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class MediumStressTestRunner:
    """Runs medium complexity stress tests against cc_executor."""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.config = None
        self.client = WebSocketClient(host="localhost", port=8004)
        
    async def load_config(self) -> Dict[str, Any]:
        """Load test configuration from JSON."""
        with open(CONFIG_PATH, 'r') as f:
            self.config = json.load(f)
        return self.config
        
    async def execute_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
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
            "patterns_found": [],
            "output_length": 0,
            "chunks_received": 0
        }
        
        try:
            # Execute command via WebSocket client
            ws_result = await self.client.execute_command(
                command=test["command"],
                timeout=self.config.get("timeout", 180),
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
                
                # Override success if patterns don't match
                if test.get("expected_patterns") and len(result["patterns_found"]) != len(test.get("expected_patterns", [])):
                    result["success"] = False
                    result["error"] = f"Pattern mismatch: found {len(result['patterns_found'])}/{len(test.get('expected_patterns', []))} patterns"
            else:
                result["error"] = ws_result.get("error", "Unknown error")
                result["duration"] = ws_result.get("duration", 0)
                result["output"] = "\n".join(ws_result.get("output_data", []))
                    
        except Exception as e:
            result["error"] = f"Exception: {str(e)}"
            result["duration"] = time.time() - test_start
            
        return result
    
    async def run_all_tests(self) -> None:
        """Execute all tests from configuration."""
        self.start_time = time.time()
        await self.load_config()
        
        print(f"🚀 Starting Medium Stress Tests - {EXECUTION_MARKER}")
        print(f"📋 Running {len(self.config['tests'])} tests")
        print(f"⏱️  Timeout: {self.config.get('timeout', 180)}s per test")
        
        # Run tests sequentially to avoid overwhelming the system
        for i, test in enumerate(self.config["tests"], 1):
            print(f"\n[{i}/{len(self.config['tests'])}] Running: {test['name']}")
            print(f"   Description: {test['description']}")
            result = await self.execute_test(test)
            self.results.append(result)
            
            # Show result
            if result["success"]:
                print(f"✅ PASSED in {result['duration']:.2f}s")
                print(f"   Output: {result['output_length']} chars, {result['chunks_received']} chunks")
            else:
                print(f"❌ FAILED: {result['error']}")
                
        # Cleanup WebSocket client
        await self.client.cleanup()
                    
        # Generate report
        await self.generate_report()
        
    async def generate_report(self) -> None:
        """Generate markdown report of test results."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - passed
        
        report = f"""# Medium Stress Test Report

**Generated**: {datetime.now().isoformat()}  
**Execution ID**: {EXECUTION_MARKER}  
**Total Duration**: {total_duration:.2f} seconds  
**Configuration**: {CONFIG_PATH}

## Summary

- **Total Tests**: {len(self.results)}
- **Passed**: {passed} ✅
- **Failed**: {failed} ❌
- **Success Rate**: {(passed/len(self.results)*100):.1f}%
- **Average Duration**: {sum(r['duration'] for r in self.results)/len(self.results):.2f}s

## Test Results

"""
        
        for result in self.results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            report += f"""### {result['name']} - {status}

- **ID**: `{result['id']}`
- **Description**: {result['description']}
- **Duration**: {result['duration']:.2f}s
- **Output Size**: {result['output_length']} characters
- **Chunks Received**: {result['chunks_received']}
- **Command**: `{result['command']}`
"""
            
            if result.get("patterns_found") is not None:
                # Get expected patterns from the test config, not the result
                test_config = next((t for t in self.config['tests'] if t['id'] == result['id']), {})
                expected = test_config.get('expected_patterns', [])
                if expected:
                    report += f"- **Patterns Found**: {len(result['patterns_found'])}/{len(expected)}\n"
                if result['patterns_found']:
                    report += f"  - Found: {', '.join(result['patterns_found'])}\n"
                
            if result["error"]:
                report += f"- **Error**: {result['error']}\n"
                
            if result["output"]:
                # Show first 1500 chars for medium tests (they produce more output)
                truncated = result['output'][:1500] + "..." if len(result['output']) > 1500 else result['output']
                report += f"\n<details>\n<summary>Output Preview</summary>\n\n```\n{truncated}\n```\n\n</details>\n\n"
            else:
                report += "\n"
                
        # Performance Statistics
        report += """## Performance Statistics

| Metric | Value |
|--------|-------|
"""
        report += f"| Total Runtime | {total_duration:.2f}s |\n"
        report += f"| Average Test Duration | {sum(r['duration'] for r in self.results)/len(self.results):.2f}s |\n"
        report += f"| Longest Test | {max(r['duration'] for r in self.results):.2f}s |\n"
        report += f"| Shortest Test | {min(r['duration'] for r in self.results):.2f}s |\n"
        report += f"| Total Output Generated | {sum(r['output_length'] for r in self.results):,} chars |\n"
        
        # Write report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, 'w') as f:
            f.write(report)
            
        print(f"\n📄 Report written to: {REPORT_PATH}")
        print(f"📊 Success Rate: {(passed/len(self.results)*100):.1f}% ({passed}/{len(self.results)})")

if __name__ == "__main__":
    # Self-verification mode
    runner = MediumStressTestRunner()
    
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
    assert config.get("timeout", 180) >= 60, "Timeout must be at least 60 seconds for medium tests"
    
    print("✅ Configuration valid")
    print(f"📋 Found {len(config['tests'])} medium complexity tests")
    print(f"⏱️  Timeout: {config.get('timeout', 180)}s per test")
    
    # Run the actual tests
    asyncio.run(runner.run_all_tests())
```

### **Task Execution Plan & Log**

#### **Step 1: Validate Configuration**
*   **Goal:** Ensure test configuration file exists and is valid for medium tests
*   **Action:** Load and validate the JSON configuration with timeout checks
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_medium_stress_tests.py --verify-only`
*   **Expected Output:** Configuration validation messages

#### **Step 2: Execute Tests**
*   **Goal:** Run all medium stress tests with proper timeout handling
*   **Action:** Execute the runner script with progress tracking
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_medium_stress_tests.py`
*   **Expected Output:** Test execution progress with chunk counts and final report

---
## 🎓 GRADUATION & VERIFICATION

### 1. Component Integration Test
*   **Success Criteria**: 
    - All 7 medium tests must execute without infrastructure errors
    - At least 70% of tests must pass pattern matching
    - Average test duration should be between 30-90 seconds
    - Report must include performance statistics

### 2. Self-Verification
*   The `if __name__ == "__main__"` block validates configuration including timeout requirements
*   Tracks output size and streaming chunks for performance analysis
*   Generates detailed performance statistics in the report