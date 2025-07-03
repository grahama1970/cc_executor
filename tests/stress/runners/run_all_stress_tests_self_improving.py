#!/usr/bin/env python3
"""
Comprehensive Stress Test Runner — Self-Improving Prompt
This follows the template from SELF_IMPROVING_PROMPT_TEMPLATE.md but is adapted for test execution
"""

# 📊 TASK METRICS & HISTORY
# - **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
# - **Last Updated**: 2025-06-30
# - **Evolution History**:
#   | Version | Change & Reason                                           | Result |
#   | :------ | :------------------------------------------------------- | :----- |
#   | v1      | Initial implementation to run ALL stress tests           | TBD    |

import asyncio
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.core.client import WebSocketClient
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add("comprehensive_stress_test_full.log", format="{time} | {level} | {message}", level="DEBUG")

class ComprehensiveStressTestExecutor:
    """
    Executes ALL stress tests from various sources:
    1. unified_stress_test_tasks.json (if exists)
    2. extended_preflight_stress_test_tasks.json
    3. All test files in tests/stress/
    4. Any other stress test configurations
    """
    
    def __init__(self):
        self.client = WebSocketClient()
        self.test_outputs_dir = Path("test_outputs") / f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {
            "success": 0,
            "failure": 0,
            "tests": [],
            "start_time": datetime.now().isoformat(),
            "sources": {}
        }
        
        # Find all stress test sources
        self.test_sources = self._find_all_test_sources()
    
    def _find_all_test_sources(self) -> Dict[str, Path]:
        """Find all available stress test sources"""
        sources = {}
        
        # Check for unified_stress_test_tasks.json
        unified_path = Path("src/cc_executor/tasks/unified_stress_test_tasks.json")
        if unified_path.exists():
            sources["unified_stress_test_tasks"] = unified_path
        
        # Check for extended_preflight_stress_test_tasks.json
        extended_path = Path("src/cc_executor/tasks/extended_preflight_stress_test_tasks.json")
        if extended_path.exists():
            sources["extended_preflight_stress_test_tasks"] = extended_path
        
        # Find all JSON task files
        task_dir = Path("src/cc_executor/tasks")
        if task_dir.exists():
            for json_file in task_dir.glob("*.json"):
                if "stress" in json_file.name.lower() or "test" in json_file.name.lower():
                    sources[json_file.stem] = json_file
        
        # Find all stress test Python files
        stress_dir = Path("tests/stress")
        if stress_dir.exists():
            for py_file in stress_dir.glob("*.py"):
                if "test" in py_file.name:
                    sources[f"python_{py_file.stem}"] = py_file
        
        logger.info(f"Found {len(sources)} test sources:")
        for name, path in sources.items():
            logger.info(f"  - {name}: {path}")
        
        return sources
    
    async def run_all_tests(self):
        """Run ALL stress tests from all sources"""
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("COMPREHENSIVE STRESS TEST EXECUTION - ALL TESTS")
        logger.info("="*80)
        logger.info(f"Start: {datetime.now()}")
        logger.info(f"Test sources: {len(self.test_sources)}")
        logger.info("")
        
        # Run tests from each source
        for source_name, source_path in self.test_sources.items():
            await self._run_tests_from_source(source_name, source_path)
        
        # Also run hardcoded essential tests
        await self._run_essential_stress_tests()
        
        # Generate comprehensive report
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = time.time() - start_time
        
        self._generate_comprehensive_report()
    
    async def _run_tests_from_source(self, source_name: str, source_path: Path):
        """Run tests from a specific source file"""
        logger.info(f"\n{'='*70}")
        logger.info(f"SOURCE: {source_name}")
        logger.info(f"Path: {source_path}")
        logger.info(f"{'='*70}")
        
        source_results = {
            "path": str(source_path),
            "tests": [],
            "success": 0,
            "failure": 0
        }
        
        if source_path.suffix == ".json":
            # Load and run JSON-based tests
            try:
                with open(source_path) as f:
                    test_data = json.load(f)
                
                # Handle different JSON formats
                if "categories" in test_data:
                    # Format like extended_preflight_stress_test_tasks.json
                    for category_name, category_data in test_data.get("categories", {}).items():
                        for task in category_data.get("tasks", []):
                            await self._run_json_task(task, category_name, source_results)
                
                elif "tests" in test_data:
                    # Format like unified_stress_test_tasks.json
                    for test in test_data["tests"]:
                        await self._run_json_task(test, "general", source_results)
                
                else:
                    logger.warning(f"Unknown JSON format in {source_name}")
                    
            except Exception as e:
                logger.error(f"Error loading {source_name}: {e}")
        
        elif source_path.suffix == ".py":
            # Run Python test files
            await self._run_python_test_file(source_path, source_results)
        
        self.results["sources"][source_name] = source_results
    
    async def _run_json_task(self, task: Dict, category: str, source_results: Dict):
        """Run a single task from JSON configuration"""
        task_id = task.get("id", task.get("name", str(uuid.uuid4())))
        full_id = f"{category}_{task_id}"
        
        logger.info(f"\n--- Task: {full_id} ---")
        
        # Build command
        if "command_template" in task:
            # Build command from template
            command = task["command_template"]
            if "natural_language_request" in task:
                command = command.replace("${REQUEST}", task["natural_language_request"])
            if "metatags" in task:
                command = command.replace("${METATAGS}", task["metatags"])
            command = command.replace("${TIMESTAMP}", datetime.now().strftime("%Y%m%d_%H%M%S"))
        elif "command" in task:
            command = task["command"]
        else:
            logger.warning(f"No command found for task {task_id}")
            return
        
        # Get timeout
        timeout = 300  # Default 5 minutes
        if "verification" in task:
            timeout = task["verification"].get("timeout", timeout)
        elif "timeout" in task:
            timeout = task["timeout"]
        
        # Execute
        await self._execute_and_record(full_id, command, timeout, source_results)
    
    async def _run_python_test_file(self, test_file: Path, source_results: Dict):
        """Run a Python test file"""
        logger.info(f"\nRunning Python test: {test_file.name}")
        
        # Execute as subprocess
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.test_outputs_dir.parent / 'src')
            
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for test files
                env=env
            )
            
            success = result.returncode == 0
            
            # Save output
            output_file = self.test_outputs_dir / f"python_{test_file.stem}_output.txt"
            with open(output_file, 'w') as f:
                f.write(f"Test: {test_file.name}\n")
                f.write(f"Exit code: {result.returncode}\n")
                f.write("\n--- STDOUT ---\n")
                f.write(result.stdout)
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
            
            # Record result
            test_result = {
                "id": f"python_{test_file.stem}",
                "command": f"python {test_file.name}",
                "success": success,
                "exit_code": result.returncode,
                "output_file": str(output_file)
            }
            
            source_results["tests"].append(test_result)
            if success:
                source_results["success"] += 1
                self.results["success"] += 1
                logger.success(f"✅ Python test passed")
            else:
                source_results["failure"] += 1
                self.results["failure"] += 1
                logger.error(f"❌ Python test failed with exit code {result.returncode}")
            
            self.results["tests"].append(test_result)
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Python test timed out")
            source_results["failure"] += 1
            self.results["failure"] += 1
        except Exception as e:
            logger.error(f"❌ Error running Python test: {e}")
            source_results["failure"] += 1
            self.results["failure"] += 1
    
    async def _run_essential_stress_tests(self):
        """Run essential hardcoded stress tests"""
        logger.info(f"\n{'='*70}")
        logger.info("ESSENTIAL STRESS TESTS")
        logger.info(f"{'='*70}")
        
        essential_tests = [
            # Simple tests
            ("simple_math", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 120),
            ("calculations", 'claude -p "What is the result of these calculations: 15+27, 83-46, 12*9, 144/12, 2^8?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 120),
            ("fibonacci", 'claude -p "What is the 10th Fibonacci number?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 120),
            
            # Code generation
            ("reverse_string", 'claude -p "What is a Python function to reverse a string?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 180),
            ("recursion", 'claude -p "What is recursion in programming with one simple Python example?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 180),
            ("five_functions", 'claude -p "What is Python code for 5 functions: area of circle, celsius to fahrenheit, prime check, string reverse, and factorial?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 180),
            
            # Creative tasks
            ("haikus", 'claude -p "What is a collection of 5 haikus about programming: variables, loops, functions, debugging, and git?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 240),
            ("recipe", 'claude -p "What is a quick chicken and rice recipe that takes 30 minutes?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 240),
            ("story_outline", 'claude -p "What is a 500-word outline for a story about a programmer discovering sentient code?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 240),
            
            # Complex tasks
            ("python_checklist", 'claude -p "What is a 500-word checklist for Python best practices in production?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 300),
            ("todo_architecture", 'claude -p "What is the architecture for a todo app with database schema, REST API, and frontend overview?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 300),
            ("hello_world_prod", 'claude -p "What is a production-ready hello world in Python with logging and error handling?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 300),
            
            # Heavy stress tests
            ("large_essay", 'claude -p "What is a 2000 word essay about the history of programming languages?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 300),
            ("comparison_table", 'claude -p "What is a detailed comparison table of Python vs JavaScript for web development?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none', 300),
            
            # Edge cases
            ("echo_test", 'echo "Testing basic echo command"', 10),
            ("unicode_test", 'echo "Unicode test: 🚀 émojis ñ spéçiål"', 10),
        ]
        
        essential_results = {
            "tests": [],
            "success": 0,
            "failure": 0
        }
        
        for test_id, command, timeout in essential_tests:
            await self._execute_and_record(f"essential_{test_id}", command, timeout, essential_results)
        
        self.results["sources"]["essential_tests"] = essential_results
    
    async def _execute_and_record(self, test_id: str, command: str, timeout: int, source_results: Dict):
        """Execute a command and record results"""
        logger.info(f"\nExecuting: {test_id}")
        logger.debug(f"Command: {command[:100]}...")
        
        start_time = time.time()
        
        try:
            result = await self.client.execute_command(
                command=command,
                timeout=timeout,
                restart_handler=True  # Always restart for reliability
            )
            
            duration = time.time() - start_time
            
            # Save output
            output_file = self.test_outputs_dir / f"{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(output_file, 'w') as f:
                f.write(f"Test: {test_id}\n")
                f.write(f"Command: {command}\n")
                f.write(f"Duration: {duration:.1f}s\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Exit Code: {result.get('exit_code', 'N/A')}\n")
                f.write(f"Restart Overhead: {result.get('restart_overhead', 0):.1f}s\n")
                f.write("\n--- Output ---\n")
                for output in result.get('output_data', []):
                    f.write(output + "\n")
            
            # Record result
            test_result = {
                "id": test_id,
                "command": command,
                "success": result["success"],
                "duration": duration,
                "exit_code": result.get("exit_code"),
                "output_file": str(output_file),
                "restart_overhead": result.get("restart_overhead", 0)
            }
            
            if result["success"]:
                logger.success(f"✅ PASSED in {duration:.1f}s")
                source_results["success"] += 1
                self.results["success"] += 1
            else:
                logger.error(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                source_results["failure"] += 1
                self.results["failure"] += 1
                test_result["error"] = result.get("error", "Unknown error")
            
            source_results["tests"].append(test_result)
            self.results["tests"].append(test_result)
            
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            source_results["failure"] += 1
            self.results["failure"] += 1
            source_results["tests"].append({
                "id": test_id,
                "command": command,
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            })
    
    def _generate_comprehensive_report(self):
        """Generate the final comprehensive report following the stress test prompt format"""
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE STRESS TEST REPORT")
        print(f"{'='*80}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary statistics
        total = self.results["success"] + self.results["failure"]
        success_rate = self.results["success"] / max(1, total) * 100
        
        print("📈 SUMMARY")
        print("-"*40)
        print(f"Total Tests:    {total}")
        print(f"✅ Passed:      {self.results['success']} ({success_rate:.1f}%)")
        print(f"❌ Failed:      {self.results['failure']} ({100-success_rate:.1f}%)")
        
        # Calculate total time and success ratio
        total_time = self.results.get("total_duration", 0)
        ratio = self.results["success"] / max(1, self.results["failure"])
        
        print(f"⏱️  Total Time:   {self._format_duration(total_time)}")
        print(f"📊 Success Ratio: {ratio:.1f}:1 (need 10:1 to graduate)")
        print()
        
        # Results by source
        print("📂 RESULTS BY SOURCE")
        print("-"*80)
        for source_name, source_data in self.results["sources"].items():
            if "tests" in source_data:
                source_total = source_data["success"] + source_data["failure"]
                source_rate = source_data["success"] / max(1, source_total) * 100
                print(f"\n{source_name}:")
                print(f"  Path: {source_data.get('path', 'N/A')}")
                print(f"  Results: {source_data['success']}/{source_total} passed ({source_rate:.1f}%)")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-"*80)
        print(f"{'Test ID':<50} {'Status':<10} {'Duration':<12} {'Info'}")
        print("-"*80)
        
        for test in self.results["tests"][:50]:  # Show first 50
            test_id = test["id"][:50]
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            duration = self._format_duration(test.get("duration", 0))
            
            if test["success"]:
                info = f"Exit: {test.get('exit_code', 'N/A')}"
            else:
                info = test.get("error", "Failed")[:30]
                
            print(f"{test_id:<50} {status:<10} {duration:<12} {info}")
        
        if len(self.results["tests"]) > 50:
            print(f"\n... and {len(self.results['tests']) - 50} more tests")
        
        # Failed tests analysis
        if self.results["failure"] > 0:
            print("\n⚠️  FAILED TESTS ANALYSIS")
            print("-"*40)
            failed_tests = [t for t in self.results["tests"] if not t["success"]]
            
            # Show first 10 failed tests
            for test in failed_tests[:10]:
                print(f"\n❌ {test['id']}")
                print(f"   Duration: {self._format_duration(test.get('duration', 0))}")
                print(f"   Error: {test.get('error', 'Unknown')[:60]}")
            
            if len(failed_tests) > 10:
                print(f"\n... and {len(failed_tests) - 10} more failed tests")
        
        # Save reports
        json_report = self.test_outputs_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_report, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        markdown_report = self.test_outputs_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_markdown_report(markdown_report)
        
        print(f"\n{'='*80}")
        print("💡 QUICK ACTIONS")
        print("-"*40)
        print(f"📂 All outputs: file://{self.test_outputs_dir.absolute()}")
        print(f"📊 JSON report: file://{json_report.absolute()}")
        print(f"📝 Markdown report: file://{markdown_report.absolute()}")
        
        if self.results["failure"] > 0:
            print("\n🔧 Debug commands:")
            print("   tail -n 50 logs/websocket_handler_*.log | grep ERROR")
            print(f"   grep 'FAILED\\|ERROR' {self.test_outputs_dir}/*.txt")
        
        # Final verdict
        print(f"\n{'='*80}")
        if ratio >= 10:
            print("🎉 GRADUATED! Success ratio >= 10:1")
            print("The stress test suite has achieved the required success ratio!")
        elif success_rate == 100:
            print("✅ PERFECT SCORE! All tests passed")
        elif success_rate >= 95:
            print("✅ EXCELLENT! Nearly all tests passed")
        elif success_rate >= 80:
            print("⚠️  GOOD: Most tests passed but needs improvement")
        else:
            print("❌ NEEDS WORK: Many tests failed")
        
        print(f"{'='*80}\n")
    
    def _save_markdown_report(self, path: Path):
        """Save comprehensive markdown report"""
        with open(path, 'w') as f:
            f.write("# Comprehensive Stress Test Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Duration**: {self._format_duration(self.results.get('total_duration', 0))}\n\n")
            
            # Summary
            total = self.results["success"] + self.results["failure"]
            success_rate = self.results["success"] / max(1, total) * 100
            ratio = self.results["success"] / max(1, self.results["failure"])
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests**: {total}\n")
            f.write(f"- **Passed**: {self.results['success']} ({success_rate:.1f}%)\n")
            f.write(f"- **Failed**: {self.results['failure']}\n")
            f.write(f"- **Success Ratio**: {ratio:.1f}:1 (need 10:1 to graduate)\n\n")
            
            # Results by source
            f.write("## Results by Source\n\n")
            for source_name, source_data in self.results["sources"].items():
                if "tests" in source_data:
                    source_total = source_data["success"] + source_data["failure"]
                    source_rate = source_data["success"] / max(1, source_total) * 100
                    
                    f.write(f"### {source_name}\n")
                    if "path" in source_data:
                        f.write(f"*Path: {source_data['path']}*\n\n")
                    f.write(f"- Tests: {source_total}\n")
                    f.write(f"- Passed: {source_data['success']} ({source_rate:.1f}%)\n")
                    f.write(f"- Failed: {source_data['failure']}\n\n")
            
            # Test results table
            f.write("## Test Results\n\n")
            f.write("| Test ID | Status | Duration | Exit Code | Error |\n")
            f.write("|---------|--------|----------|-----------|-------|\n")
            
            # Show all tests
            for test in self.results["tests"]:
                status = "✅ PASS" if test["success"] else "❌ FAIL"
                duration = self._format_duration(test.get("duration", 0))
                exit_code = test.get("exit_code", "N/A")
                error = test.get("error", "-")[:50]
                
                f.write(f"| {test['id'][:40]} | {status} | {duration} | {exit_code} | {error} |\n")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            return f"{int(seconds//60)}m {seconds%60:.1f}s"
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.cleanup()


async def main():
    """Run all comprehensive stress tests"""
    executor = ComprehensiveStressTestExecutor()
    try:
        await executor.run_all_tests()
    finally:
        await executor.cleanup()


if __name__ == "__main__":
    # This is a self-improving prompt that tracks success/failure ratio
    # Current ratio: 0:0 (need 10:1 to graduate)
    asyncio.run(main())