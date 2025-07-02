#!/usr/bin/env python3
"""
Master Stress Test Runner — Self-Improving Prompt

This is the main stress test runner that executes ALL tests from unified_stress_test_tasks.json
following the self-improving prompt template requirements.

📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason                                           | Result |
  | :------ | :------------------------------------------------------- | :----- |
  | v1.0    | Initial implementation to run all unified stress tests   | TBD    |
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.client.websocket_client import WebSocketClient
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add("master_stress_test.log", format="{time} | {level} | {message}", level="DEBUG")


class MasterStressTestRunner:
    """
    Master runner for all stress tests.
    Executes tests from unified_stress_test_tasks.json with proper organization.
    """
    
    def __init__(self):
        self.client = WebSocketClient()
        self.stress_test_dir = Path(__file__).parent.parent
        self.tasks_file = self.stress_test_dir / "tasks" / "unified_stress_test_tasks.json"
        self.test_outputs_dir = self.stress_test_dir / "reports" / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_outputs_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {
            "success": 0,
            "failure": 0,
            "tests": [],
            "start_time": datetime.now().isoformat(),
            "categories": {}
        }
        
        # Load test tasks
        self.test_data = self._load_test_tasks()
    
    def _load_test_tasks(self) -> Dict:
        """Load test tasks from unified JSON file"""
        if not self.tasks_file.exists():
            logger.error(f"Test tasks file not found: {self.tasks_file}")
            raise FileNotFoundError(f"Missing {self.tasks_file}")
        
        with open(self.tasks_file) as f:
            return json.load(f)
    
    def check_prerequisites(self) -> bool:
        """Check all prerequisites before running tests"""
        logger.info("Checking prerequisites...")
        all_good = True
        
        # Check Claude CLI
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.success("✓ Claude CLI found")
            else:
                logger.error("✗ Claude CLI not found! Install with: npm install -g @anthropic-ai/claude-cli")
                all_good = False
        except Exception as e:
            logger.error(f"✗ Error checking Claude CLI: {e}")
            all_good = False
        
        # Check ANTHROPIC_API_KEY
        if 'ANTHROPIC_API_KEY' in os.environ:
            logger.warning("⚠️ ANTHROPIC_API_KEY is set - Claude CLI should manage its own auth")
            logger.info("  Unsetting for this session...")
            del os.environ['ANTHROPIC_API_KEY']
        
        # Check system load
        try:
            with open('/proc/loadavg', 'r') as f:
                load1 = float(f.read().split()[0])
                logger.info(f"System load: {load1:.2f}")
                if load1 > 14:
                    logger.warning("⚠️ High system load - tests may be slower")
        except:
            pass
        
        # Check port availability
        try:
            result = subprocess.run(['lsof', '-ti:8004'], capture_output=True, text=True)
            if result.stdout.strip():
                logger.warning(f"⚠️ Port 8004 in use by PID: {result.stdout.strip()}")
        except:
            pass
        
        return all_good
    
    async def run_all_tests(self):
        """Run all stress tests from unified task file"""
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed!")
            return
        
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("MASTER STRESS TEST EXECUTION")
        logger.info("="*80)
        logger.info(f"Start: {datetime.now()}")
        logger.info(f"Task file: {self.tasks_file}")
        logger.info(f"Test ID: {self.test_data.get('task_list_id', 'Unknown')}")
        logger.info(f"Description: {self.test_data.get('description', 'No description')}")
        
        # Count total tests
        total_tests = sum(len(cat_data.get('tests', [])) for cat_data in self.test_data.get('categories', {}).values())
        logger.info(f"Total tests: {total_tests}")
        logger.info("")
        
        # Run each category
        for category_name, category_data in self.test_data.get('categories', {}).items():
            await self._run_category(category_name, category_data)
        
        # Generate final report
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = time.time() - start_time
        
        self._generate_report()
    
    async def _run_category(self, category_name: str, category_data: Dict):
        """Run all tests in a category"""
        logger.info(f"\n{'='*70}")
        logger.info(f"CATEGORY: {category_name.upper()}")
        logger.info(f"{'='*70}")
        logger.info(f"Description: {category_data.get('description', 'No description')}")
        logger.info(f"Tests: {len(category_data.get('tests', []))}")
        logger.info(f"Timeout: {category_data.get('timeout', 300)}s\n")
        
        category_results = {
            "description": category_data.get("description", ""),
            "tests": [],
            "success": 0,
            "failure": 0
        }
        
        for test in category_data.get('tests', []):
            test_id = f"{category_name}_{test['id']}"
            logger.info(f"\n--- Test: {test_id} ---")
            logger.info(f"Name: {test.get('name', 'Unnamed')}")
            logger.info(f"Description: {test.get('description', 'No description')}")
            
            # Execute test
            test_start = time.time()
            try:
                command = test.get('command', '')
                timeout = category_data.get('timeout', 300)
                
                result = await self.client.execute_command(
                    command=command,
                    timeout=timeout,
                    restart_handler=True  # Always restart for reliability
                )
                
                test_duration = time.time() - test_start
                
                # Save output
                output_file = self.test_outputs_dir / f"{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(output_file, 'w') as f:
                    f.write(f"Test ID: {test_id}\n")
                    f.write(f"Name: {test.get('name', 'Unnamed')}\n")
                    f.write(f"Command: {command}\n")
                    f.write(f"Duration: {test_duration:.1f}s\n")
                    f.write(f"Success: {result['success']}\n")
                    f.write(f"Exit Code: {result.get('exit_code', 'N/A')}\n")
                    f.write(f"Restart Overhead: {result.get('restart_overhead', 0):.1f}s\n")
                    f.write("\n--- Output ---\n")
                    for output in result.get('output_data', []):
                        f.write(output + "\n")
                
                # Check expected patterns
                patterns_found = []
                if 'expected_patterns' in test and result.get('output_data'):
                    output_text = "\n".join(result.get('output_data', []))
                    for pattern in test['expected_patterns']:
                        if pattern.lower() in output_text.lower():
                            patterns_found.append(pattern)
                
                # Record result
                test_result = {
                    "id": test_id,
                    "name": test.get('name', 'Unnamed'),
                    "command": command,
                    "success": result["success"],
                    "duration": test_duration,
                    "exit_code": result.get("exit_code"),
                    "output_file": str(output_file),
                    "restart_overhead": result.get("restart_overhead", 0),
                    "patterns_found": patterns_found,
                    "expected_patterns": test.get('expected_patterns', [])
                }
                
                if result["success"]:
                    logger.success(f"✅ PASSED in {test_duration:.1f}s (patterns: {len(patterns_found)}/{len(test.get('expected_patterns', []))})")
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
                    "id": test_id,
                    "name": test.get('name', 'Unnamed'),
                    "command": test.get('command', ''),
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - test_start
                })
        
        # Category summary
        total = category_results["success"] + category_results["failure"]
        if total > 0:
            success_rate = category_results["success"] / total * 100
            logger.info(f"\nCategory Summary: {category_results['success']}/{total} passed ({success_rate:.1f}%)")
        
        self.results["categories"][category_name] = category_results
    
    def _generate_report(self):
        """Generate comprehensive test report following main.md format"""
        print(f"\n{'='*80}")
        print("📊 MASTER STRESS TEST REPORT")
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
                    print(f"    ❌ {test['name']}: {test.get('error', 'Unknown error')[:50]}")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS")
        print("-"*80)
        print(f"{'Test ID':<30} {'Status':<10} {'Duration':<12} {'Patterns':<15} {'Info'}")
        print("-"*80)
        
        for test in self.results["tests"]:
            test_id = test["id"][:30]
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            duration = self._format_duration(test.get("duration", 0))
            
            # Pattern info
            if "patterns_found" in test and "expected_patterns" in test:
                patterns = f"{len(test['patterns_found'])}/{len(test['expected_patterns'])}"
            else:
                patterns = "N/A"
            
            if test["success"]:
                info = f"Exit: {test.get('exit_code', 'N/A')}"
            else:
                info = test.get("error", "Failed")[:25]
                
            print(f"{test_id:<30} {status:<10} {duration:<12} {patterns:<15} {info}")
        
        # Failed tests analysis
        if self.results["failure"] > 0:
            print("\n⚠️  FAILED TESTS ANALYSIS")
            print("-"*40)
            failed_tests = [t for t in self.results["tests"] if not t["success"]]
            for test in failed_tests[:10]:
                print(f"\n❌ {test['id']}")
                print(f"   Name: {test.get('name', 'Unknown')}")
                print(f"   Duration: {self._format_duration(test.get('duration', 0))}")
                if "patterns_found" in test:
                    print(f"   Patterns found: {test['patterns_found']}")
                print(f"   Error: {test.get('error', 'Unknown')[:80]}")
                
                # Show output file for debugging
                if "output_file" in test:
                    print(f"   🔍 Debug: file://{Path(test['output_file']).absolute()}")
        
        # Save reports
        json_report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        markdown_report_path = self.test_outputs_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_markdown_report(markdown_report_path)
        
        print(f"\n{'='*80}")
        print("💡 QUICK ACTIONS")
        print("-"*40)
        print(f"📂 All outputs: file://{self.test_outputs_dir.absolute()}")
        print(f"📊 JSON report: file://{json_report_path.absolute()}")
        print(f"📝 Markdown report: file://{markdown_report_path.absolute()}")
        
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
        """Save detailed markdown report"""
        with open(path, 'w') as f:
            f.write("# Master Stress Test Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Test Suite**: {self.test_data.get('task_list_id', 'Unknown')}\n")
            f.write(f"**Description**: {self.test_data.get('description', 'No description')}\n\n")
            
            # Summary
            total = self.results["success"] + self.results["failure"]
            success_rate = self.results["success"] / max(1, total) * 100
            ratio = self.results["success"] / max(1, self.results["failure"])
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests**: {total}\n")
            f.write(f"- **Passed**: {self.results['success']} ({success_rate:.1f}%)\n")
            f.write(f"- **Failed**: {self.results['failure']}\n")
            f.write(f"- **Duration**: {self._format_duration(self.results.get('total_duration', 0))}\n")
            f.write(f"- **Success Ratio**: {ratio:.1f}:1 (need 10:1 to graduate)\n\n")
            
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
            f.write("| Test ID | Name | Status | Duration | Patterns | Exit Code | Error |\n")
            f.write("|---------|------|--------|----------|----------|-----------|-------|\n")
            
            for test in self.results["tests"]:
                status = "✅ PASS" if test["success"] else "❌ FAIL"
                duration = self._format_duration(test.get("duration", 0))
                exit_code = test.get("exit_code", "N/A")
                error = test.get("error", "-")[:40]
                
                # Pattern info
                if "patterns_found" in test and "expected_patterns" in test:
                    patterns = f"{len(test['patterns_found'])}/{len(test['expected_patterns'])}"
                else:
                    patterns = "N/A"
                
                f.write(f"| {test['id']} | {test.get('name', 'Unknown')} | {status} | {duration} | {patterns} | {exit_code} | {error} |\n")
    
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
    """Run master stress test suite"""
    runner = MasterStressTestRunner()
    try:
        await runner.run_all_tests()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    # This is a self-improving prompt implementation
    # Success/Failure Ratio: 0:0 (Requires 10:1 to graduate)
    asyncio.run(main())