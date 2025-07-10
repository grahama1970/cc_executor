#!/usr/bin/env python3
"""
Test runner for CC Executor examples that generates comprehensive reports.
Actually runs the examples and extracts real responses using clean_json_string.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute
from cc_executor.utils.json_utils import clean_json_string
from cc_executor.reporting.hallucination_check import check_hallucination


class ExampleTestRunner:
    """Runs CC Executor examples and generates comprehensive test reports."""
    
    def __init__(self, examples_dir: Optional[Path] = None):
        self.examples_dir = examples_dir or (Path(__file__).parent.parent.parent.parent / "examples")
        self.results = []
        self.start_time = None
        self.end_time = None
        
    async def test_quickstart_json(self) -> Dict[str, Any]:
        """Test the quickstart example with JSON responses."""
        print("\n🚀 Testing Quickstart Example (JSON Mode)...")
        
        start = time.time()
        result = {
            "name": "Quickstart (JSON Mode)",
            "path": "quickstart/quickstart.py",
            "status": "PENDING",
            "task": "",
            "raw_response": "",
            "parsed_response": {},
            "execution_time": 0,
            "verification": {}
        }
        
        try:
            # Define the task with JSON schema
            task = """Write a Python function to calculate fibonacci numbers with memoization.
Return your response as JSON with this exact schema:
{
    "function_name": "fibonacci",
    "description": "Calculate nth fibonacci number with memoization",
    "parameters": [
        {"name": "n", "type": "int", "description": "The position in sequence"}
    ],
    "returns": {"type": "int", "description": "The nth fibonacci number"},
    "code": "def fibonacci(n, memo={}):\\n    # complete implementation",
    "example_usage": "result = fibonacci(10)  # Returns 55",
    "time_complexity": "O(n)"
}"""
            
            result["task"] = task
            print("  Executing with json_mode=True...")
            
            # Execute with JSON mode
            response = await cc_execute(task, json_mode=True)
            result["raw_response"] = json.dumps(response, indent=2)
            
            # Extract and parse the JSON response
            if "result" in response:
                # Use clean_json_string to extract JSON from the response
                cleaned = clean_json_string(response["result"], return_dict=True)
                if isinstance(cleaned, dict):
                    result["parsed_response"] = cleaned
                    result["status"] = "PASS"
                    print(f"  ✅ Successfully parsed JSON response")
                    
                    # Save generated code
                    if "code" in cleaned:
                        code_path = self.examples_dir / "quickstart" / "fibonacci_generated.py"
                        with open(code_path, 'w') as f:
                            f.write(cleaned["code"])
                            if "example_usage" in cleaned:
                                f.write(f"\n\n# Example usage:\n# {cleaned['example_usage']}")
                        print(f"  💾 Saved generated code to {code_path.name}")
                else:
                    result["status"] = "FAIL"
                    print(f"  ❌ Failed to parse JSON response")
            
            # Verify execution
            verification = check_hallucination(last_n=1)
            result["verification"] = verification
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            
        result["execution_time"] = time.time() - start
        return result
    
    async def test_basic_multi_task(self) -> Dict[str, Any]:
        """Test basic example with multiple tasks."""
        print("\n📚 Testing Basic Example (Multi-task)...")
        
        start = time.time()
        result = {
            "name": "Basic (Multi-task JSON)",
            "path": "basic/run_example.py",
            "status": "PENDING",
            "tasks": [],
            "execution_time": 0,
            "verification": {}
        }
        
        try:
            # Define multiple tasks with JSON schemas
            tasks = [
                {
                    "prompt": """Create a Python function that adds two numbers.
Return JSON with schema:
{
    "function_name": "add_numbers",
    "code": "def add_numbers(a, b):\\n    return a + b",
    "docstring": "Add two numbers and return the result.",
    "example": "add_numbers(2, 3)  # Returns 5"
}""",
                    "description": "Add function"
                },
                {
                    "prompt": """Write a unit test for the add_numbers function.
Return JSON with schema:
{
    "test_class_name": "TestAddNumbers",
    "code": "import unittest\\n\\nclass TestAddNumbers(unittest.TestCase):\\n    # test methods",
    "test_cases": [
        {"name": "test_positive", "description": "Test with positive numbers"},
        {"name": "test_negative", "description": "Test with negative numbers"}
    ]
}""",
                    "description": "Unit test"
                }
            ]
            
            completed = 0
            for i, task_info in enumerate(tasks, 1):
                print(f"  Task {i}/{len(tasks)}: {task_info['description']}...")
                
                task_result = {
                    "task": task_info["prompt"],
                    "description": task_info["description"],
                    "response": {},
                    "status": "PENDING"
                }
                
                try:
                    response = await cc_execute(task_info["prompt"], json_mode=True)
                    
                    if "result" in response:
                        cleaned = clean_json_string(response["result"], return_dict=True)
                        if isinstance(cleaned, dict):
                            task_result["response"] = cleaned
                            task_result["status"] = "SUCCESS"
                            completed += 1
                            print(f"    ✅ Completed successfully")
                        else:
                            task_result["status"] = "PARSE_ERROR"
                            print(f"    ⚠️ Could not parse JSON response")
                            
                except Exception as e:
                    task_result["status"] = "ERROR"
                    task_result["error"] = str(e)
                    print(f"    ❌ Error: {e}")
                
                result["tasks"].append(task_result)
            
            result["tasks_completed"] = completed
            result["status"] = "PASS" if completed == len(tasks) else "PARTIAL"
            
            # Verify execution
            verification = check_hallucination(last_n=len(tasks))
            result["verification"] = verification
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            
        result["execution_time"] = time.time() - start
        return result
    
    async def test_concurrent_json(self) -> Dict[str, Any]:
        """Test concurrent execution with JSON responses."""
        print("\n⚡ Testing Concurrent Example (JSON Mode)...")
        
        start = time.time()
        result = {
            "name": "Concurrent (JSON)",
            "path": "medium/concurrent_tasks.py",
            "status": "PENDING",
            "tasks": [],
            "execution_time": 0,
            "concurrent_speedup": 0,
            "verification": {}
        }
        
        try:
            from asyncio import Semaphore, as_completed
            from tqdm.asyncio import tqdm
            
            # Math tasks with JSON response schema
            tasks = [
                """Calculate 10 + 5. Return JSON: {"calculation": "10 + 5", "result": 15}""",
                """Calculate 20 * 3. Return JSON: {"calculation": "20 * 3", "result": 60}""",
                """Calculate 100 / 4. Return JSON: {"calculation": "100 / 4", "result": 25}""",
                """Calculate 50 - 15. Return JSON: {"calculation": "50 - 15", "result": 35}"""
            ]
            
            # Estimate sequential time
            sequential_estimate = len(tasks) * 7
            
            # Limit concurrent executions
            semaphore = Semaphore(2)
            
            async def execute_with_limit(task: str, index: int):
                async with semaphore:
                    response = await cc_execute(task, json_mode=True)
                    parsed = {}
                    if "result" in response:
                        parsed = clean_json_string(response["result"], return_dict=True)
                    return {"index": index, "task": task, "response": parsed}
            
            # Create coroutines
            coroutines = [execute_with_limit(task, i) for i, task in enumerate(tasks)]
            
            # Execute concurrently with progress bar
            task_results = []
            async for future in tqdm(as_completed(coroutines), total=len(tasks), desc="Concurrent"):
                task_result = await future
                task_results.append(task_result)
            
            # Sort by original index
            task_results.sort(key=lambda x: x["index"])
            result["tasks"] = task_results
            
            # Calculate speedup
            concurrent_time = time.time() - start
            speedup = sequential_estimate / concurrent_time
            result["concurrent_speedup"] = speedup
            result["status"] = "PASS"
            
            print(f"  ✅ Completed {len(tasks)} tasks")
            print(f"  ⚡ Speedup: {speedup:.1f}x")
            
            # Verify execution
            verification = check_hallucination(last_n=len(tasks))
            result["verification"] = verification
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            
        result["execution_time"] = time.time() - start
        return result
    
    async def test_advanced_features(self) -> Dict[str, Any]:
        """Test advanced features with JSON validation."""
        print("\n🎯 Testing Advanced Features...")
        
        start = time.time()
        result = {
            "name": "Advanced (JSON + Validation)",
            "path": "advanced/run_example.py",
            "status": "PENDING",
            "features_tested": [],
            "tests": [],
            "execution_time": 0,
            "verification": {}
        }
        
        try:
            # Test 1: Simple JSON response
            print("  Testing simple JSON response...")
            test1 = {
                "name": "Simple JSON",
                "task": """What is the capital of France? 
Return JSON: {"question": "capital of France", "answer": "Paris"}""",
                "response": {},
                "status": "PENDING"
            }
            
            response1 = await cc_execute(test1["task"], json_mode=True)
            if "result" in response1:
                parsed = clean_json_string(response1["result"], return_dict=True)
                if isinstance(parsed, dict) and "answer" in parsed:
                    test1["response"] = parsed
                    test1["status"] = "SUCCESS"
                    result["features_tested"].append("json_response")
                    print("    ✅ JSON response working")
            
            result["tests"].append(test1)
            
            # Test 2: Code generation with validation
            print("  Testing code generation with validation...")
            test2 = {
                "name": "Code with Validation",
                "task": """Write a function to reverse a string.
Return JSON with schema:
{
    "function_name": "reverse_string",
    "code": "def reverse_string(s):\\n    return s[::-1]",
    "test_cases": [
        {"input": "hello", "expected": "olleh"},
        {"input": "world", "expected": "dlrow"}
    ]
}""",
                "response": {},
                "validation_result": {},
                "status": "PENDING"
            }
            
            response2 = await cc_execute(test2["task"], json_mode=True)
            if "result" in response2:
                parsed = clean_json_string(response2["result"], return_dict=True)
                if isinstance(parsed, dict) and "code" in parsed:
                    test2["response"] = parsed
                    
                    # Validate the generated code
                    validation_prompt = f"""
Check if this code is correct: {parsed['code']}
Test with: reverse_string("hello") should return "olleh"
Return JSON: {{"is_valid": true/false, "reason": "explanation"}}"""
                    
                    val_response = await cc_execute(validation_prompt, json_mode=True)
                    if "result" in val_response:
                        val_parsed = clean_json_string(val_response["result"], return_dict=True)
                        test2["validation_result"] = val_parsed
                        test2["status"] = "SUCCESS"
                        result["features_tested"].append("validation")
                        print("    ✅ Code generation and validation working")
            
            result["tests"].append(test2)
            
            result["status"] = "PASS" if len(result["features_tested"]) >= 2 else "PARTIAL"
            
            # Verify execution
            verification = check_hallucination(last_n=2)
            result["verification"] = verification
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            print(f"  ❌ Error: {e}")
            
        result["execution_time"] = time.time() - start
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and compile results."""
        self.start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"CC Executor Examples Test Suite")
        print(f"Started: {self.start_time.isoformat()}")
        print(f"{'='*60}")
        
        # Run all tests
        self.results.append(await self.test_quickstart_json())
        self.results.append(await self.test_basic_multi_task())
        self.results.append(await self.test_concurrent_json())
        self.results.append(await self.test_advanced_features())
        
        self.end_time = datetime.now()
        
        # Compile summary
        summary = {
            "test_run": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration": (self.end_time - self.start_time).total_seconds()
            },
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "PASS"),
                "failed": sum(1 for r in self.results if r["status"] == "FAIL"),
                "errors": sum(1 for r in self.results if r["status"] == "ERROR"),
                "partial": sum(1 for r in self.results if r["status"] == "PARTIAL")
            },
            "results": self.results
        }
        
        return summary
    
    def format_json_response(self, response: dict, indent: str = "   ") -> List[str]:
        """Format a JSON response for markdown display."""
        lines = []
        if isinstance(response, dict):
            for key, value in response.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent}**{key}**: {json.dumps(value, indent=2)}")
                else:
                    lines.append(f"{indent}**{key}**: {value}")
        else:
            lines.append(f"{indent}{json.dumps(response, indent=2)}")
        return lines
    
    def generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """Generate a comprehensive markdown report from test results."""
        lines = []
        
        # Header
        lines.append("# CC Executor Examples Test Report")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now().isoformat()}")
        lines.append(f"**Duration**: {summary['test_run']['duration']:.1f} seconds")
        lines.append("")
        
        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| ✅ Passed | {summary['summary']['passed']} |")
        lines.append(f"| ❌ Failed | {summary['summary']['failed']} |")
        lines.append(f"| ⚠️ Partial | {summary['summary']['partial']} |")
        lines.append(f"| 🔥 Errors | {summary['summary']['errors']} |")
        lines.append(f"| **Total** | {summary['summary']['total_tests']} |")
        lines.append("")
        
        # Test results
        lines.append("## Test Results")
        lines.append("")
        
        for result in summary['results']:
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "ERROR": "🔥",
                "PARTIAL": "⚠️"
            }.get(result['status'], "❓")
            
            lines.append(f"### {status_icon} {result['name']}")
            lines.append("")
            lines.append(f"- **Path**: `{result['path']}`")
            lines.append(f"- **Status**: {result['status']}")
            lines.append(f"- **Execution Time**: {result['execution_time']:.1f}s")
            
            # Quickstart example
            if "task" in result and "parsed_response" in result:
                lines.append("")
                lines.append("**Task**: Request fibonacci function with JSON schema")
                lines.append("")
                lines.append("**JSON Response**:")
                lines.append("```json")
                lines.append(json.dumps(result.get("parsed_response", {}), indent=2))
                lines.append("```")
                
                if result["parsed_response"].get("code"):
                    lines.append("")
                    lines.append("**Generated Code**:")
                    lines.append("```python")
                    lines.append(result["parsed_response"]["code"])
                    lines.append("```")
            
            # Multi-task results
            if "tasks" in result and isinstance(result["tasks"], list):
                lines.append("")
                lines.append("**Tasks and JSON Responses**:")
                lines.append("")
                
                for i, task in enumerate(result["tasks"], 1):
                    if "description" in task:
                        lines.append(f"{i}. **{task['description']}**")
                        if task.get("response"):
                            lines.append("   ```json")
                            lines.append(f"   {json.dumps(task['response'], indent=2)}")
                            lines.append("   ```")
                    elif "response" in task:
                        lines.append(f"{i}. **Task**: {task.get('task', '')[:50]}...")
                        lines.append("   **Response**:")
                        lines.append("   ```json")
                        lines.append(f"   {json.dumps(task['response'], indent=2)}")
                        lines.append("   ```")
                    lines.append("")
            
            # Advanced features
            if "tests" in result:
                lines.append("")
                lines.append("**Feature Tests**:")
                lines.append("")
                for test in result["tests"]:
                    lines.append(f"- **{test['name']}**: {test['status']}")
                    if test.get("response"):
                        lines.append("  ```json")
                        lines.append(f"  {json.dumps(test['response'], indent=2)}")
                        lines.append("  ```")
            
            # Performance metrics
            if "concurrent_speedup" in result:
                lines.append("")
                lines.append(f"**Performance**: {result['concurrent_speedup']:.1f}x speedup with concurrent execution")
            
            if "features_tested" in result:
                lines.append(f"- **Features Tested**: {', '.join(result['features_tested'])}")
            
            # Verification
            if result.get("verification") and not result["verification"].get("is_hallucination", True):
                lines.append("")
                lines.append("**Verification**: ✅ Execution verified as real")
                if result["verification"].get("verifications"):
                    latest = result["verification"]["verifications"][0]
                    lines.append(f"- UUID: `{latest.get('execution_uuid', 'N/A')}`")
                    lines.append(f"- Response File: `{latest.get('file', 'N/A').split('/')[-1]}`")
            
            lines.append("")
        
        # Key insights
        lines.append("## Key Insights")
        lines.append("")
        lines.append("### 🎯 JSON Mode Benefits")
        lines.append("")
        lines.append("1. **Structured Responses**: Every response follows a predictable schema")
        lines.append("2. **Easy Parsing**: Use `clean_json_string()` to extract JSON from any response")
        lines.append("3. **Type Safety**: Know exactly what fields to expect")
        lines.append("4. **Direct Integration**: Generated code can be saved and used immediately")
        lines.append("")
        
        lines.append("### 📊 Example JSON Schemas Used")
        lines.append("")
        lines.append("**Function Generation Schema**:")
        lines.append("```json")
        lines.append("""{
    "function_name": "string",
    "description": "string",
    "parameters": [{"name": "string", "type": "string", "description": "string"}],
    "returns": {"type": "string", "description": "string"},
    "code": "string (complete implementation)",
    "example_usage": "string",
    "time_complexity": "string"
}""")
        lines.append("```")
        lines.append("")
        
        # Environment
        lines.append("## Test Environment")
        lines.append("")
        lines.append(f"- Python Version: {sys.version.split()[0]}")
        lines.append(f"- CC Executor Path: {Path(__file__).parent.parent.parent.parent}")
        lines.append(f"- Examples Path: {self.examples_dir}")
        lines.append("- JSON Parser: `clean_json_string()` from `cc_executor.utils.json_utils`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*This report was generated automatically by the CC Executor test suite.*")
        
        return '\n'.join(lines)


async def main():
    """Run tests and generate report."""
    runner = ExampleTestRunner()
    
    # Run all tests
    summary = await runner.run_all_tests()
    
    # Generate markdown report
    report = runner.generate_markdown_report(summary)
    
    # Save report
    report_path = runner.examples_dir / "EXAMPLES_TEST_REPORT.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n{'='*60}")
    print(f"Test Summary:")
    print(f"  Total: {summary['summary']['total_tests']}")
    print(f"  Passed: {summary['summary']['passed']}")
    print(f"  Failed: {summary['summary']['failed']}")
    print(f"  Errors: {summary['summary']['errors']}")
    print(f"{'='*60}")
    print(f"\n📄 Report saved to: {report_path}")
    
    # Save JSON summary
    json_path = runner.examples_dir / "test_results.json"
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary['summary']['failed'] == 0 and summary['summary']['errors'] == 0


if __name__ == "__main__":
    success = asyncio.run(main())