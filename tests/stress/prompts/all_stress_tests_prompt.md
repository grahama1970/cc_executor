# All Stress Tests — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason                                     | Result |
  | :------ | :---------------------------------------------------- | :----- |
  | v1      | Initial implementation for complete stress test suite. | TBD    |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Execute the complete stress test suite including simple, medium, complex, edge cases, and stress tests. This comprehensive test validates cc_executor's full capabilities and stability across all test categories.

### 2. Core Principles & Constraints
- Tests are organized by category with appropriate timeouts
- Must handle the full range from 5-second echo tests to 5-minute analysis tasks
- Edge cases test Unicode, empty responses, and boundary conditions
- Stress tests push concurrent processing and system limits
- Generate comprehensive report with category breakdowns

### 3. API Contract & Dependencies
- **Input**: JSON configuration file at `/home/graham/workspace/experiments/cc_executor/tests/stress/configs/all_stress_tests.json`
- **Output**: Markdown report at `/home/graham/workspace/experiments/cc_executor/tests/stress/reports/all_stress_tests_report.md`
- **Dependencies**:
  - cc_executor server running on localhost:8000
  - Claude CLI available in PATH
  - Python 3.10+ with asyncio support
  - psutil for resource monitoring
  - Sufficient system resources for ~30 minute test run

---
## 🤖 IMPLEMENTER'S WORKSPACE

### **Implementation Code Block**
```python
#!/usr/bin/env python3
"""
All Stress Tests Runner for cc_executor

Executes the complete stress test suite across all categories.
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
from collections import defaultdict

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
CONFIG_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/configs/all_stress_tests.json")
REPORT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/reports/all_stress_tests_report.md")
EXECUTION_MARKER = f"ALL_STRESS_TESTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class AllStressTestRunner:
    """Runs complete stress test suite against cc_executor."""
    
    def __init__(self):
        self.results = defaultdict(list)  # Results by category
        self.start_time = None
        self.config = None
        self.process = psutil.Process()
        self.category_stats = defaultdict(lambda: {"passed": 0, "failed": 0, "duration": 0})
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
        
    async def execute_test(self, test: Dict[str, Any], 
                          category: str, timeout: int) -> Dict[str, Any]:
        """Execute a single test and return results."""
        test_start = time.time()
        resources_start = self.get_system_resources()
        
        result = {
            "id": test["id"],
            "name": test["name"],
            "category": category,
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
        
        # Resource monitoring for complex tests
        monitor_task = None
        peak_resources = resources_start.copy()
        if category in ["complex", "stress"]:
            monitor_task = asyncio.create_task(self._monitor_resources(peak_resources))
        
        try:
            # Execute command via WebSocket client
            ws_result = await self.client.execute_command(
                command=test["command"],
                timeout=timeout,
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
                expected_patterns = test.get("expected_patterns", [])
                if expected_patterns:
                    for pattern in expected_patterns:
                        if pattern.lower() in result["output"].lower():
                            result["patterns_found"].append(pattern)
                    
                    # Different success criteria by category
                    if category == "edge_cases":
                        # Edge cases might have no patterns or specific behavior
                        if test["id"] == "empty_response":
                            result["success"] = result["output"] == "" and result.get("exit_code") == 0
                        else:
                            result["success"] = len(result["patterns_found"]) > 0
                    elif category in ["complex", "stress"]:
                        # Complex tests: 80% of patterns
                        result["success"] = len(result["patterns_found"]) >= len(expected_patterns) * 0.8
                    else:
                        # Simple/medium: all patterns required
                        result["success"] = len(result["patterns_found"]) == len(expected_patterns)
            else:
                result["error"] = ws_result.get("error", "Unknown error")
                result["duration"] = ws_result.get("duration", 0)
                result["output"] = "\n".join(ws_result.get("output_data", []))
                    
        except Exception as e:
            result["error"] = f"Exception: {type(e).__name__}: {str(e)}"
        finally:
            if monitor_task:
                monitor_task.cancel()
            result["duration"] = time.time() - test_start
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
        
        # Count total tests
        total_tests = sum(len(cat_data["tests"]) for cat_data in self.config["categories"].values())
        
        print(f"🚀 Starting All Stress Tests - {EXECUTION_MARKER}")
        print(f"📋 Running {total_tests} tests across {len(self.config['categories'])} categories")
        print(f"⏱️  Estimated runtime: 20-30 minutes")
        print(f"💾 Initial Memory: {self.process.memory_info().rss / 1024 / 1024:.1f} MB")
        
        # Run tests by category
        test_num = 0
        for category, cat_data in self.config["categories"].items():
            print(f"\n{'='*60}")
            print(f"📁 Category: {category.upper()}")
            print(f"   {cat_data['description']}")
            print(f"   Timeout: {cat_data['timeout']}s per test")
            print(f"   Tests: {len(cat_data['tests'])}")
            print(f"{'='*60}")
            
            category_start = time.time()
            
            for test in cat_data["tests"]:
                test_num += 1
                print(f"\n[{test_num}/{total_tests}] {test['name']} ({category})")
                print(f"   {test['description']}")
                
                result = await self.execute_test(test, category, cat_data["timeout"])
                self.results[category].append(result)
                
                # Update category stats
                if result["success"]:
                    self.category_stats[category]["passed"] += 1
                    print(f"   ✅ PASSED in {result['duration']:.2f}s")
                else:
                    self.category_stats[category]["failed"] += 1
                    print(f"   ❌ FAILED: {result['error']}")
                
                if result["output_length"] > 0:
                    print(f"   Output: {result['output_length']:,} chars")
                
                # Pause between categories
                if category in ["complex", "stress"] and test != cat_data["tests"][-1]:
                    print("   Pausing 3s...")
                    await asyncio.sleep(3)
            
            self.category_stats[category]["duration"] = time.time() - category_start
            print(f"\n✨ {category} complete: {self.category_stats[category]['passed']}/{len(cat_data['tests'])} passed")
        
        # Cleanup WebSocket client
        await self.client.cleanup()
        
        # Generate report
        await self.generate_report()
    
    async def generate_report(self) -> None:
        """Generate comprehensive markdown report."""
        total_duration = time.time() - self.start_time
        all_results = []
        for results in self.results.values():
            all_results.extend(results)
        
        total_passed = sum(stats["passed"] for stats in self.category_stats.values())
        total_failed = sum(stats["failed"] for stats in self.category_stats.values())
        
        report = f"""# All Stress Tests Report

**Generated**: {datetime.now().isoformat()}  
**Execution ID**: {EXECUTION_MARKER}  
**Total Duration**: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)  
**Configuration**: {CONFIG_PATH}

## Executive Summary

- **Total Tests**: {len(all_results)}
- **Passed**: {total_passed} ✅
- **Failed**: {total_failed} ❌
- **Overall Success Rate**: {(total_passed/len(all_results)*100):.1f}%

## Category Breakdown

| Category | Tests | Passed | Failed | Success Rate | Duration |
|----------|-------|--------|--------|--------------|----------|
"""
        
        for category in ["simple", "medium", "complex", "edge_cases", "stress"]:
            if category in self.category_stats:
                stats = self.category_stats[category]
                total = stats["passed"] + stats["failed"]
                success_rate = (stats["passed"] / total * 100) if total > 0 else 0
                report += f"| {category.title()} | {total} | {stats['passed']} | {stats['failed']} | {success_rate:.1f}% | {stats['duration']:.1f}s |\n"
        
        # Resource usage summary
        if any(r.get("resources") for results in self.results.values() for r in results):
            report += "\n## Resource Usage Summary\n\n"
            
            # Calculate peaks across all tests
            all_memory_peaks = []
            all_cpu_peaks = []
            
            for results in self.results.values():
                for r in results:
                    if r.get("resources", {}).get("peak"):
                        all_memory_peaks.append(r["resources"]["peak"]["memory_mb"])
                        all_cpu_peaks.append(r["resources"]["peak"]["cpu_percent"])
            
            if all_memory_peaks:
                report += f"- **Peak Memory**: {max(all_memory_peaks):.1f} MB\n"
                report += f"- **Average Memory**: {sum(all_memory_peaks)/len(all_memory_peaks):.1f} MB\n"
            if all_cpu_peaks:
                report += f"- **Peak CPU**: {max(all_cpu_peaks):.1f}%\n"
                report += f"- **Average CPU**: {sum(all_cpu_peaks)/len(all_cpu_peaks):.1f}%\n"
        
        # Detailed results by category
        for category in ["simple", "medium", "complex", "edge_cases", "stress"]:
            if category not in self.results:
                continue
                
            report += f"\n## {category.title()} Tests\n\n"
            
            for result in self.results[category]:
                status = "✅" if result["success"] else "❌"
                report += f"### {result['name']} {status}\n\n"
                report += f"- **ID**: `{result['id']}`\n"
                report += f"- **Duration**: {result['duration']:.2f}s\n"
                
                if result.get("output_length", 0) > 0:
                    report += f"- **Output Size**: {result['output_length']:,} chars\n"
                
                if result.get("expected_patterns"):
                    report += f"- **Patterns**: {len(result['patterns_found'])}/{len(result.get('expected_patterns', []))}\n"
                
                if result["error"]:
                    report += f"- **Error**: {result['error']}\n"
                
                # Show output preview for failed tests
                if not result["success"] and result["output"]:
                    preview = result["output"][:500] + "..." if len(result["output"]) > 500 else result["output"]
                    report += f"\n<details>\n<summary>Output Preview</summary>\n\n```\n{preview}\n```\n\n</details>\n"
                
                report += "\n"
        
        # Performance insights
        report += """## Performance Insights

### Test Duration Distribution
"""
        durations = [r["duration"] for results in self.results.values() for r in results]
        report += f"- **< 30s**: {sum(1 for d in durations if d < 30)} tests\n"
        report += f"- **30s-1m**: {sum(1 for d in durations if 30 <= d < 60)} tests\n"
        report += f"- **1m-2m**: {sum(1 for d in durations if 60 <= d < 120)} tests\n"
        report += f"- **2m-3m**: {sum(1 for d in durations if 120 <= d < 180)} tests\n"
        report += f"- **> 3m**: {sum(1 for d in durations if d >= 180)} tests\n"
        
        report += f"\n### Key Findings\n\n"
        
        # Find slowest and fastest tests
        all_sorted = sorted(all_results, key=lambda x: x["duration"])
        report += f"- **Fastest Test**: {all_sorted[0]['name']} ({all_sorted[0]['duration']:.2f}s)\n"
        report += f"- **Slowest Test**: {all_sorted[-1]['name']} ({all_sorted[-1]['duration']:.2f}s)\n"
        
        # Category performance
        report += f"\n### Category Performance\n\n"
        for category, stats in self.category_stats.items():
            if stats["passed"] + stats["failed"] > 0:
                avg_time = stats["duration"] / (stats["passed"] + stats["failed"])
                report += f"- **{category.title()}**: {avg_time:.1f}s average per test\n"
        
        # Write report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report written to: {REPORT_PATH}")
        print(f"📊 Overall Success Rate: {(total_passed/len(all_results)*100):.1f}% ({total_passed}/{len(all_results)})")
        print(f"⏱️  Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")

if __name__ == "__main__":
    # Self-verification mode
    runner = AllStressTestRunner()
    
    print("🔍 Running self-verification...")
    
    # Check configuration exists
    assert CONFIG_PATH.exists(), f"Configuration not found: {CONFIG_PATH}"
    
    # Load and validate configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    assert "categories" in config, "Configuration missing 'categories'"
    
    # Validate each category
    required_categories = ["simple", "medium", "complex", "edge_cases", "stress"]
    for cat in required_categories:
        assert cat in config["categories"], f"Missing category: {cat}"
        assert "tests" in config["categories"][cat], f"Category {cat} missing tests"
        assert "timeout" in config["categories"][cat], f"Category {cat} missing timeout"
    
    # Count total tests
    total_tests = sum(len(cat["tests"]) for cat in config["categories"].values())
    
    print("✅ Configuration valid")
    print(f"📋 Found {total_tests} tests across {len(config['categories'])} categories:")
    
    for cat, data in config["categories"].items():
        print(f"   - {cat}: {len(data['tests'])} tests, {data['timeout']}s timeout")
    
    estimated_time = sum(len(data["tests"]) * data["timeout"] / 2 for data in config["categories"].values()) / 60
    print(f"\n⏱️  Estimated runtime: {estimated_time:.0f}-{estimated_time*2:.0f} minutes")
    print("\n⚠️  This will run ALL stress tests. Make sure cc_executor is running!")
    
    # Run the actual tests
    asyncio.run(runner.run_all_tests())
```

### **Task Execution Plan & Log**

#### **Step 1: Validate Complete Configuration**
*   **Goal:** Ensure all category configurations are present and valid
*   **Action:** Load and validate the complete test suite
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_all_stress_tests.py --verify-only`
*   **Expected Output:** Configuration validation with category breakdown

#### **Step 2: Execute Complete Test Suite**
*   **Goal:** Run all tests across all categories with monitoring
*   **Action:** Execute runner with category-based progress tracking
*   **Verification Command:** `python3 /home/graham/workspace/experiments/cc_executor/tests/stress/runners/run_all_stress_tests.py`
*   **Expected Output:** Category-by-category progress, comprehensive report

---
## 🎓 GRADUATION & VERIFICATION

### 1. Component Integration Test
*   **Success Criteria**: 
    - All categories must complete execution
    - Overall success rate must exceed 70%
    - No category should have 0% success rate
    - Comprehensive report with category breakdowns

### 2. Self-Verification
*   Validates all category configurations
*   Provides runtime estimates
*   Generates detailed report with performance insights