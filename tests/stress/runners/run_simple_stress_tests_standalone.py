#!/usr/bin/env python3
"""
Simple Stress Test Runner for cc_executor (Standalone Version)

Executes simple, quick-running tests to validate basic functionality.
"""
import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import the standalone WebSocket client (doesn't manage its own server)
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))
from cc_executor.client.websocket_client_standalone import WebSocketClient

# Configuration
CONFIG_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/configs/simple_stress_tests.json")
REPORT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/reports/simple_stress_tests_report.md")
EXECUTION_MARKER = f"SIMPLE_STRESS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class SimpleStressTestRunner:
    """Runs simple stress tests against cc_executor."""
    
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
            "expected_patterns": test.get("expected_patterns", [])
        }
        
        try:
            # Execute command via WebSocket client
            ws_result = await self.client.execute_command(
                command=test["command"],
                timeout=self.config.get("timeout", 120),
                restart_handler=True  # Restart for each test to ensure clean state
            )
            
            # Process WebSocket result
            if ws_result["success"]:
                result["success"] = True
                result["exit_code"] = ws_result.get("exit_code", 0)
                result["output"] = "\n".join(ws_result.get("output_data", []))
                result["duration"] = ws_result["duration"]
                
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
        
        print(f"🚀 Starting Simple Stress Tests - {EXECUTION_MARKER}")
        print(f"📋 Running {len(self.config['tests'])} tests")
        
        # Run tests sequentially to avoid overwhelming the system
        for i, test in enumerate(self.config["tests"], 1):
            print(f"\n[{i}/{len(self.config['tests'])}] Running: {test['name']}")
            result = await self.execute_test(test)
            self.results.append(result)
            
            # Show result
            if result["success"]:
                print(f"✅ PASSED in {result['duration']:.2f}s")
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
    # Handle --verify-only flag
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-only":
        runner = SimpleStressTestRunner()
        
        # Check configuration exists
        if not CONFIG_PATH.exists():
            print(f"❌ Configuration not found: {CONFIG_PATH}")
            sys.exit(1)
            
        # Load and validate configuration
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            assert "tests" in config, "Configuration missing 'tests' array"
            assert len(config["tests"]) > 0, "No tests defined"
            assert all("id" in t for t in config["tests"]), "All tests must have an 'id'"
            assert all("command" in t for t in config["tests"]), "All tests must have a 'command'"
            
            print("✅ Configuration valid")
            print(f"📋 Found {len(config['tests'])} tests to run")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
    
    # Run the actual tests
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