#!/usr/bin/env python3
"""
Run all examples with JSON mode and generate a comprehensive test report.

This script:
1. Runs all example files with JSON mode enabled
2. Collects all JSON responses
3. Generates a single EXAMPLES_TEST_REPORT.md using the JSON report generator
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cc_executor.client.cc_execute import cc_execute
from cc_executor.reporting.json_report_generator import JSONReportGenerator
from cc_executor.utils.json_utils import clean_json_string


async def run_example_with_json(example_name: str, task: str, timeout: int = 120) -> Dict[str, Any]:
    """
    Run a single example with JSON mode enabled.
    
    Args:
        example_name: Name of the example for tracking
        task: The task to execute
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with execution results
    """
    print(f"\n🔄 Running: {example_name}")
    print("-" * 60)
    
    # Ensure task requests JSON output
    if "json" not in task.lower() and "return" not in task.lower():
        task += "\nReturn your response as JSON with fields: result, summary, and any relevant data."
    
    try:
        # Create config with timeout
        from cc_executor.client.cc_execute import CCExecutorConfig
        config = CCExecutorConfig(timeout=timeout)
        
        result = await cc_execute(
            task=task,
            config=config,
            json_mode=True
        )
        
        print(f"✅ Completed: {example_name}")
        
        # Extract execution info
        return {
            "example_name": example_name,
            "task": task,
            "success": True,
            "result": result,
            "execution_uuid": result.get("execution_uuid", ""),
            "execution_time": result.get("execution_time", 0),
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Failed: {example_name} - {str(e)}")
        return {
            "example_name": example_name,
            "task": task,
            "success": False,
            "result": None,
            "execution_uuid": "",
            "execution_time": 0,
            "error": str(e)
        }


async def run_all_examples() -> List[Dict[str, Any]]:
    """Run all example tasks and collect results."""
    
    examples = [
        # Quickstart examples
        {
            "name": "Quickstart - Basic Math",
            "task": "Calculate 2 + 2. Return JSON: {\"calculation\": \"2 + 2\", \"result\": 4}"
        },
        {
            "name": "Quickstart - Fibonacci",
            "task": """Write a Python function to calculate Fibonacci numbers.
Return JSON with:
{
    "function_name": "fibonacci",
    "code": "def fibonacci(n):\\n    ...",
    "example_output": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34],
    "time_complexity": "O(n)"
}"""
        },
        
        # Basic examples
        {
            "name": "Basic - Hello World",
            "task": """Write a simple Python hello world program.
Return JSON: {
    "code": "print('Hello, World!')",
    "output": "Hello, World!",
    "language": "Python"
}"""
        },
        {
            "name": "Basic - List Operations",
            "task": """Create a Python function to sort a list of numbers.
Return JSON: {
    "function_name": "sort_numbers",
    "code": "def sort_numbers(nums):\\n    return sorted(nums)",
    "test_input": [3, 1, 4, 1, 5, 9],
    "test_output": [1, 1, 3, 4, 5, 9]
}"""
        },
        
        # Medium complexity examples
        {
            "name": "Medium - Prime Number Checker",
            "task": """Write an efficient Python function to check if a number is prime.
Return JSON: {
    "function_name": "is_prime",
    "code": "complete implementation here",
    "algorithm": "trial division with sqrt optimization",
    "time_complexity": "O(sqrt(n))",
    "test_cases": [
        {"input": 2, "output": true},
        {"input": 17, "output": true},
        {"input": 100, "output": false}
    ]
}"""
        },
        {
            "name": "Medium - File Operations",
            "task": """Create a Python function to count lines in a text file.
Return JSON: {
    "function_name": "count_lines",
    "code": "complete implementation",
    "handles_errors": true,
    "test_scenario": "counting lines in a 1000-line file",
    "expected_behavior": "returns integer count or raises FileNotFoundError"
}"""
        },
        
        # Advanced examples
        {
            "name": "Advanced - Async Web Scraper",
            "task": """Design a Python async function to fetch multiple URLs concurrently.
Return JSON: {
    "function_name": "fetch_urls",
    "imports": ["aiohttp", "asyncio"],
    "code": "async def implementation here",
    "features": ["concurrent requests", "error handling", "timeout support"],
    "max_concurrency": 10
}"""
        },
        {
            "name": "Advanced - Data Processing Pipeline",
            "task": """Create a data processing pipeline that reads CSV, transforms data, and outputs JSON.
Return JSON: {
    "pipeline_stages": ["read", "validate", "transform", "output"],
    "main_function": "process_csv_to_json",
    "code_snippet": "key implementation details",
    "error_handling": ["invalid CSV", "missing columns", "type errors"],
    "performance_notes": "uses pandas for efficient processing"
}"""
        },
        
        # Validation and testing patterns
        {
            "name": "Validation - Input Sanitization",
            "task": """Create a simple function to sanitize user input by removing HTML tags.
Return JSON: {
    "function_name": "sanitize_input",
    "validation_type": "HTML tag removal",
    "code": "def sanitize_input(text):\\n    import re\\n    return re.sub(r'<[^>]+>', '', text)",
    "example_input": "<script>alert('test')</script>Hello",
    "example_output": "Hello"
}""",
            "timeout": 60  # Reduced timeout for simpler task
        },
        {
            "name": "Testing - Unit Test Generator",
            "task": """Generate unit tests for a calculator class with add, subtract, multiply, divide methods.
Return JSON: {
    "test_framework": "pytest",
    "test_class": "TestCalculator",
    "test_methods": ["test_add", "test_subtract", "test_multiply", "test_divide", "test_divide_by_zero"],
    "sample_test": "complete test method implementation"
}"""
        }
    ]
    
    results = []
    
    print("🚀 Starting comprehensive example test run")
    print(f"Total examples to run: {len(examples)}")
    print("=" * 80)
    
    for example in examples:
        # Use custom timeout if specified
        timeout = example.get("timeout", 120)
        result = await run_example_with_json(
            example_name=example["name"],
            task=example["task"],
            timeout=timeout
        )
        results.append(result)
        
        # Small delay between executions
        await asyncio.sleep(2)
    
    return results


def generate_comprehensive_report(results: List[Dict[str, Any]]) -> None:
    """Generate the final EXAMPLES_TEST_REPORT.md from execution results."""
    
    print("\n" + "=" * 80)
    print("📊 Generating Comprehensive Report")
    print("=" * 80)
    
    # Get response files from successful executions
    response_dir = Path(__file__).parent.parent / "src/cc_executor/client/tmp/responses"
    
    # Collect UUIDs from successful executions
    successful_uuids = [
        r["execution_uuid"] 
        for r in results 
        if r["success"] and r["execution_uuid"]
    ]
    
    # Find corresponding response files
    response_files = []
    if response_dir.exists():
        for file_path in response_dir.glob("cc_execute_*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    if data.get("execution_uuid") in successful_uuids:
                        response_files.append(file_path)
            except:
                continue
    
    # Generate report using JSON report generator
    generator = JSONReportGenerator()
    
    # Custom output path for EXAMPLES_TEST_REPORT.md
    output_path = Path(__file__).parent / "EXAMPLES_TEST_REPORT.md"
    
    if response_files:
        # Sort by modification time
        response_files.sort(key=lambda x: x.stat().st_mtime)
        
        try:
            report_path = generator.generate_report_from_files(
                response_files=response_files,
                output_path=output_path
            )
            print(f"✅ Report generated: {report_path}")
        except Exception as e:
            print(f"❌ Failed to generate report from files: {e}")
            # Fall back to manual report generation
            _generate_fallback_report(results, output_path)
    else:
        print("⚠️  No response files found, generating fallback report")
        _generate_fallback_report(results, output_path)
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 Test Summary")
    print("=" * 80)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    print(f"Total Examples: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(successful/len(results)*100):.1f}%")
    
    if failed > 0:
        print("\nFailed Examples:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['example_name']}: {r['error']}")


def _generate_fallback_report(results: List[Dict[str, Any]], output_path: Path) -> None:
    """Generate a fallback report if JSON files are not available."""
    
    lines = []
    lines.append("# CC Executor Examples Test Report (Fallback)")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().isoformat()}")
    lines.append(f"**Total Examples**: {len(results)}")
    lines.append("")
    lines.append("⚠️ **Note**: This is a fallback report. Response files were not found.")
    lines.append("")
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total Examples: {len(results)}")
    lines.append(f"- Successful: {successful}")
    lines.append(f"- Failed: {failed}")
    lines.append(f"- Success Rate: {(successful/len(results)*100):.1f}%")
    lines.append("")
    
    lines.append("## Example Results")
    lines.append("")
    
    for i, result in enumerate(results, 1):
        lines.append(f"### {i}. {result['example_name']}")
        lines.append("")
        
        if result["success"]:
            lines.append("**Status**: ✅ Success")
            lines.append(f"**Execution Time**: {result['execution_time']:.1f}s")
            lines.append(f"**UUID**: `{result['execution_uuid']}`")
        else:
            lines.append("**Status**: ❌ Failed")
            lines.append(f"**Error**: {result['error']}")
        
        lines.append("")
        lines.append("**Task**:")
        lines.append("```")
        lines.append(result['task'])
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"📝 Fallback report written to: {output_path}")


async def main():
    """Main entry point."""
    print("🔧 CC Executor - Comprehensive Examples Test")
    print("=" * 80)
    print("This will run all examples with JSON mode and generate a report.")
    print("")
    
    # Run all examples
    results = await run_all_examples()
    
    # Generate comprehensive report
    generate_comprehensive_report(results)
    
    print("\n✅ Test run complete!")
    print(f"📄 Report saved to: examples/EXAMPLES_TEST_REPORT.md")


if __name__ == "__main__":
    asyncio.run(main())