#!/usr/bin/env python3
"""
Comprehensive Stress Test Runner - Runs ALL stress tests and generates complete report
Following the format dictated by the stress test prompt in tests/stress/prompts/main.md
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.core.client import WebSocketClient
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add("comprehensive_stress_test_log.txt", format="{time} | {level} | {message}", level="DEBUG")

class ComprehensiveStressTestRunner:
    def __init__(self):
        self.client = WebSocketClient()
        self.test_outputs_dir = Path("test_outputs/comprehensive")
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {
            "success": 0,
            "failure": 0,
            "tests": [],
            "start_time": datetime.now().isoformat(),
            "categories": {}
        }
        
        # Define all stress test categories based on main.md
        self.test_categories = {
            "simple": {
                "description": "Simple calculations and basic operations",
                "timeout": 120,
                "tests": [
                    ("simple_math", 'claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("calculations", 'claude -p "What is the result of these calculations: 15+27, 83-46, 12*9, 144/12, 2^8?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("fibonacci", 'claude -p "What is the 10th Fibonacci number?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            },
            "code_generation": {
                "description": "Code generation tasks",
                "timeout": 180,
                "tests": [
                    ("reverse_string", 'claude -p "What is a Python function to reverse a string?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("recursion", 'claude -p "What is recursion in programming with one simple Python example?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("five_functions", 'claude -p "What is Python code for 5 functions: area of circle, celsius to fahrenheit, prime check, string reverse, and factorial?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("ten_functions", 'claude -p "What is Python code for 10 basic math functions?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            },
            "creative": {
                "description": "Creative content generation",
                "timeout": 240,
                "tests": [
                    ("haikus", 'claude -p "What is a collection of 5 haikus about programming: variables, loops, functions, debugging, and git?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("recipe", 'claude -p "What is a quick chicken and rice recipe that takes 30 minutes?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("story_outline", 'claude -p "What is a 500-word outline for a story about a programmer discovering sentient code?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            },
            "complex": {
                "description": "Complex analysis and architecture tasks",
                "timeout": 300,
                "tests": [
                    ("python_checklist", 'claude -p "What is a 500-word checklist for Python best practices in production?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("todo_architecture", 'claude -p "What is the architecture for a todo app with database schema, REST API, and frontend overview?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("hello_world_prod", 'claude -p "What is a production-ready hello world in Python with logging and error handling?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            },
            "stress": {
                "description": "Heavy stress tests",
                "timeout": 300,
                "tests": [
                    ("large_essay", 'claude -p "What is a 2000 word essay about the history of programming languages?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("comparison_table", 'claude -p "What is a detailed comparison table of Python vs JavaScript for web development?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                    ("async_research", 'claude -p "What is a comprehensive guide to async/await in Python with 5 examples?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            },
            "edge_cases": {
                "description": "Edge cases and error handling",
                "timeout": 120,
                "tests": [
                    ("empty_prompt", 'echo "Testing empty response"'),
                    ("unicode", 'echo "Test Unicode: 🚀 émojis ñ spéçiål"'),
                    ("long_prompt", f'claude -p "What is the answer to this: {" and ".join([f"item{i}" for i in range(50)])}" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none'),
                ]
            }
        }
    
    def check_prerequisites(self):
        """Check system requirements"""
        logger.info("Checking prerequisites...")
        
        # Check Claude CLI
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Claude CLI not found! Install with: npm install -g @anthropic-ai/claude-cli")
                return False
            logger.success("✓ Claude CLI found")
        except Exception as e:
            logger.error(f"Error checking Claude CLI: {e}")
            return False
        
        # Check system load
        try:
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            if result.returncode == 0:
                load_output = result.stdout
                # Extract load average
                if 'load average:' in load_output:
                    load_str = load_output.split('load average:')[1].strip()
                    load_1min = float(load_str.split(',')[0])
                    logger.info(f"System load: {load_1min}")
                    if load_1min > 14:
                        logger.warning("High system load detected - tests may be slower")
        except:
            pass
        
        # Check port
        try:
            result = subprocess.run(['lsof', '-ti:8004'], capture_output=True, text=True)
            if result.stdout.strip():
                logger.warning(f"Port 8004 in use by PID: {result.stdout.strip()}")
        except:
            pass
        
        return True
    
    async def run_all_tests(self):
        """Run all stress tests comprehensively"""
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed!")
            return
        
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("COMPREHENSIVE STRESS TEST SUITE")
        logger.info("="*80)
        logger.info(f"Start: {datetime.now()}")
        logger.info(f"Categories: {len(self.test_categories)}")
        logger.info(f"Total tests: {sum(len(cat['tests']) for cat in self.test_categories.values())}")
        logger.info("")
        
        # Run each category
        for category_name, category_data in self.test_categories.items():
            await self.run_category(category_name, category_data)
        
        # Generate final report
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = time.time() - start_time
        
        self.generate_report()
    
    async def run_category(self, category_name: str, category_data: Dict):
        """Run all tests in a category"""
        logger.info(f"\n{'='*70}")
        logger.info(f"CATEGORY: {category_name.upper()}")
        logger.info(f"{'='*70}")
        logger.info(f"Description: {category_data['description']}")
        logger.info(f"Tests: {len(category_data['tests'])}")
        logger.info(f"Timeout: {category_data['timeout']}s\n")
        
        category_results = {
            "description": category_data["description"],
            "tests": [],
            "success": 0,
            "failure": 0
        }
        
        for test_id, command in category_data["tests"]:
            full_test_id = f"{category_name}_{test_id}"
            logger.info(f"\n--- Test: {full_test_id} ---")
            
            # Execute test
            test_start = time.time()
            try:
                result = await self.client.execute_command(
                    command=command,
                    timeout=category_data["timeout"],
                    restart_handler=True  # Always restart for reliability
                )
                
                test_duration = time.time() - test_start
                
                # Save output
                output_file = self.test_outputs_dir / f"{full_test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(output_file, 'w') as f:
                    f.write(f"Test: {full_test_id}\n")
                    f.write(f"Command: {command}\n")
                    f.write(f"Duration: {test_duration:.1f}s\n")
                    f.write(f"Success: {result['success']}\n")
                    f.write(f"Exit Code: {result.get('exit_code', 'N/A')}\n")
                    f.write("\n--- Output ---\n")
                    for output in result.get('output_data', []):
                        f.write(output + "\n")
                
                # Record result
                test_result = {
                    "id": full_test_id,
                    "command": command,
                    "success": result["success"],
                    "duration": test_duration,
                    "exit_code": result.get("exit_code"),
                    "output_file": str(output_file),
                    "restart_overhead": result.get("restart_overhead", 0)
                }
                
                if result["success"]:
                    logger.success(f"✅ PASSED in {test_duration:.1f}s")
                    self.results["success"] += 1
                    category_results["success"] += 1
                else:
                    logger.error(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                    self.results["failure"] += 1
                    category_results["failure"] += 1
                    test_result["error"] = result.get("error", "Unknown error")
                
                self.results["tests"].append(test_result)
                category_results["tests"].append(test_result)
                
            except Exception as e:
                logger.error(f"❌ Exception: {e}")
                self.results["failure"] += 1
                category_results["failure"] += 1
                self.results["tests"].append({
                    "id": full_test_id,
                    "command": command,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - test_start
                })
        
        # Summary for category
        total = category_results["success"] + category_results["failure"]
        if total > 0:
            success_rate = category_results["success"] / total * 100
            logger.info(f"\nCategory Summary: {category_results['success']}/{total} passed ({success_rate:.1f}%)")
        
        self.results["categories"][category_name] = category_results
    
    def generate_report(self):
        """Generate comprehensive test report following main.md format"""
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
        
        # Results by category
        print("📂 RESULTS BY CATEGORY")
        print("-"*80)
        for category_name, category_data in self.results["categories"].items():
            cat_total = category_data["success"] + category_data["failure"]
            cat_rate = category_data["success"] / max(1, cat_total) * 100
            print(f"\n{category_name.upper()}: {category_data['description']}")
            print(f"  Results: {category_data['success']}/{cat_total} passed ({cat_rate:.1f}%)")
            
            # Show failed tests in category
            failed = [t for t in category_data["tests"] if not t["success"]]
            if failed:
                print("  Failed tests:")
                for test in failed:
                    print(f"    ❌ {test['id']}: {test.get('error', 'Unknown error')}")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-"*80)
        print(f"{'Test ID':<40} {'Status':<10} {'Duration':<12} {'Info'}")
        print("-"*80)
        
        for test in self.results["tests"]:
            test_id = test["id"]
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            duration = self._format_duration(test.get("duration", 0))
            
            if test["success"]:
                info = f"Exit: {test.get('exit_code', 'N/A')}"
            else:
                info = test.get("error", "Failed")[:40]
                
            print(f"{test_id:<40} {status:<10} {duration:<12} {info}")
        
        # Performance analysis
        print("\n⚡ PERFORMANCE ANALYSIS")
        print("-"*40)
        total_restart_overhead = sum(t.get("restart_overhead", 0) for t in self.results["tests"])
        avg_restart = total_restart_overhead / len(self.results["tests"]) if self.results["tests"] else 0
        print(f"Total restart overhead: {self._format_duration(total_restart_overhead)}")
        print(f"Average restart time: {avg_restart:.2f}s")
        print(f"Overhead percentage: {(total_restart_overhead/total_time*100):.1f}%" if total_time > 0 else "N/A")
        
        # Failed tests analysis
        if self.results["failure"] > 0:
            print("\n⚠️  FAILED TESTS ANALYSIS")
            print("-"*40)
            failed_tests = [t for t in self.results["tests"] if not t["success"]]
            
            # Group by error type
            error_types = {}
            for test in failed_tests:
                error = test.get("error", "Unknown error")
                error_type = error.split(":")[0] if ":" in error else error
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append(test["id"])
            
            for error_type, tests in error_types.items():
                print(f"\n{error_type}: {len(tests)} tests")
                for test_id in tests[:5]:  # Show first 5
                    print(f"  - {test_id}")
                if len(tests) > 5:
                    print(f"  ... and {len(tests) - 5} more")
        
        # Save reports
        json_report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        markdown_report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.save_markdown_report(markdown_report_path)
        
        print(f"\n{'='*80}")
        print("💡 QUICK ACTIONS")
        print("-"*40)
        print(f"📂 All outputs: file://{self.test_outputs_dir.absolute()}")
        print(f"📊 JSON report: file://{json_report_path.absolute()}")
        print(f"📝 Markdown report: file://{markdown_report_path.absolute()}")
        
        if self.results["failure"] > 0:
            print("\n🔧 Debug commands:")
            print("   tail -n 50 logs/websocket_handler_*.log | grep ERROR")
            print("   grep 'TIMEOUT\\|FAILED' test_outputs/comprehensive/*.txt")
        
        # Final verdict
        print(f"\n{'='*80}")
        if ratio >= 10:
            print("🎉 GRADUATED! Success ratio >= 10:1")
        elif success_rate == 100:
            print("✅ PERFECT SCORE! All tests passed")
        elif success_rate >= 95:
            print("✅ EXCELLENT! Nearly all tests passed")
        elif success_rate >= 80:
            print("⚠️  GOOD: Most tests passed but needs improvement")
        else:
            print("❌ NEEDS WORK: Many tests failed")
        print(f"{'='*80}\n")
    
    def save_markdown_report(self, path: Path):
        """Save detailed markdown report"""
        with open(path, 'w') as f:
            f.write("# Comprehensive Stress Test Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            total = self.results["success"] + self.results["failure"]
            success_rate = self.results["success"] / max(1, total) * 100
            ratio = self.results["success"] / max(1, self.results["failure"])
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests**: {total}\n")
            f.write(f"- **Passed**: {self.results['success']} ({success_rate:.1f}%)\n")
            f.write(f"- **Failed**: {self.results['failure']}\n")
            f.write(f"- **Duration**: {self._format_duration(self.results.get('total_duration', 0))}\n")
            f.write(f"- **Success Ratio**: {ratio:.1f}:1\n\n")
            
            # Category results
            f.write("## Results by Category\n\n")
            for category_name, category_data in self.results["categories"].items():
                cat_total = category_data["success"] + category_data["failure"]
                cat_rate = category_data["success"] / max(1, cat_total) * 100
                
                f.write(f"### {category_name.title()}\n")
                f.write(f"*{category_data['description']}*\n\n")
                f.write(f"- Tests: {cat_total}\n")
                f.write(f"- Passed: {category_data['success']} ({cat_rate:.1f}%)\n")
                f.write(f"- Failed: {category_data['failure']}\n\n")
            
            # Detailed results table
            f.write("## Detailed Results\n\n")
            f.write("| Test ID | Status | Duration | Exit Code | Error |\n")
            f.write("|---------|--------|----------|-----------|-------|\n")
            
            for test in self.results["tests"]:
                status = "✅ PASS" if test["success"] else "❌ FAIL"
                duration = self._format_duration(test.get("duration", 0))
                exit_code = test.get("exit_code", "N/A")
                error = test.get("error", "-")[:50]
                
                f.write(f"| {test['id']} | {status} | {duration} | {exit_code} | {error} |\n")
            
            # Performance metrics
            total_restart = sum(t.get("restart_overhead", 0) for t in self.results["tests"])
            f.write("\n## Performance Metrics\n\n")
            f.write(f"- **Total Restart Overhead**: {self._format_duration(total_restart)}\n")
            f.write(f"- **Average Restart Time**: {total_restart/len(self.results['tests']):.2f}s\n")
            f.write(f"- **Overhead Percentage**: {(total_restart/self.results.get('total_duration', 1)*100):.1f}%\n")
    
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
    """Run comprehensive stress tests"""
    runner = ComprehensiveStressTestRunner()
    try:
        await runner.run_all_tests()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())