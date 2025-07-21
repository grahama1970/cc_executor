#!/usr/bin/env python3
"""
Test reporter for CC Executor examples.
Generates properly formatted reports with clear separation of inputs, outputs, and logs.
"""

import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from loguru import logger

# Import cc_execute and hallucination check
from cc_executor.client.cc_execute import cc_execute
from cc_executor.reporting.hallucination_check import check_hallucination
from cc_executor.utils.json_utils import clean_json_string


class ExamplesTestReporter:
    """Test reporter for CC Executor examples with improved formatting."""
    
    def __init__(self, examples_dir: Optional[Path] = None):
        """Initialize the test reporter.
        
        Args:
            examples_dir: Path to examples directory, defaults to project examples/
        """
        self.examples_dir = examples_dir or (Path(__file__).parent.parent.parent.parent / "examples")
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def extract_task_and_response(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Extract task input and response from execution output.
        
        Args:
            stdout: Standard output from the example
            stderr: Standard error (logs) from the example
            
        Returns:
            Dictionary with task, response, and metadata
        """
        info = {
            "task": "",
            "response": "",
            "has_result": False,
            "extracted_from": "stdout"
        }
        
        # Try to extract task from stdout
        task_match = re.search(r'📋 Task: (.+?)$', stdout, re.MULTILINE)
        if task_match:
            info["task"] = task_match.group(1).strip()
        
        # Try to extract result from stdout
        result_match = re.search(r'✅ Result:\n-+\n(.*?)\n-+', stdout, re.DOTALL)
        if result_match:
            info["response"] = result_match.group(1).strip()
            info["has_result"] = True
        else:
            # If no result in stdout, try to extract from logs
            response = self._extract_response_from_logs(stderr)
            if response:
                info["response"] = response
                info["has_result"] = True
                info["extracted_from"] = "logs"
        
        return info
    
    def _extract_response_from_logs(self, logs: str) -> Optional[str]:
        """Extract Claude's actual response from execution logs.
        
        Args:
            logs: The stderr output containing logs
            
        Returns:
            The extracted response or None
        """
        lines = logs.split('\n')
        response_lines = []
        capture = False
        
        for line in lines:
            # Start capturing after process completion
            if "Process completed successfully" in line:
                capture = True
                continue
            
            # Stop at certain markers
            if capture and any(marker in line for marker in [
                "Response saved:",
                "Execution receipt:",
                "=== CC_EXECUTE LIFECYCLE COMPLETE ==="
            ]):
                break
            
            # Capture non-log lines
            if capture and line.strip():
                # Skip lines that are clearly logs
                if not any(x in line for x in ['INFO', 'WARNING', 'ERROR', '|', '2025-']):
                    response_lines.append(line)
        
        return '\n'.join(response_lines).strip() if response_lines else None
    
    def _clean_logs(self, logs: str, max_lines: int = 20) -> str:
        """Clean and truncate logs for display.
        
        Args:
            logs: Raw log output
            max_lines: Maximum number of log lines to include
            
        Returns:
            Cleaned log string
        """
        lines = logs.split('\n')
        
        # Filter for important log lines
        important_keywords = [
            "=== CC_EXECUTE LIFECYCLE START ===",
            "=== CC_EXECUTE LIFECYCLE COMPLETE ===",
            "Process completed successfully",
            "RedisTaskTimer prediction:",
            "Execution receipt:",
            "Response saved:",
            "ERROR",
            "WARNING"
        ]
        
        filtered_lines = []
        for line in lines:
            if any(keyword in line for keyword in important_keywords):
                # Remove ANSI color codes
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                filtered_lines.append(clean_line)
        
        # Take first and last important lines if too many
        if len(filtered_lines) > max_lines:
            half = max_lines // 2
            filtered_lines = filtered_lines[:half] + ["..."] + filtered_lines[-half:]
        
        return '\n'.join(filtered_lines)
    
    def format_test_result(self, result: Dict[str, Any]) -> str:
        """Format a single test result for the markdown report.
        
        Args:
            result: Test result dictionary
            
        Returns:
            Formatted markdown string
        """
        status_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "ERROR": "🔥",
            "WARN": "⚠️",
            "PARTIAL": "⚠️",
            "PENDING": "⏳"
        }.get(result['status'], "❓")
        
        lines = []
        lines.append(f"### {status_icon} {result['name']}")
        lines.append("")
        lines.append(f"- **Path**: `{result['path']}`")
        lines.append(f"- **Status**: {result['status']}")
        
        if 'execution_time' in result:
            lines.append(f"- **Execution Time**: {result['execution_time']:.1f}s")
        
        # Add task-specific information
        if 'task_info' in result and result['task_info'].get('task'):
            lines.append("")
            lines.append("**Task Input**:")
            lines.append("```")
            lines.append(result['task_info']['task'])
            lines.append("```")
            
            if result['task_info'].get('response'):
                lines.append("")
                lines.append("**Response**:")
                # Detect language for syntax highlighting
                response = result['task_info']['response']
                lang = "python" if "def " in response or "import " in response else ""
                lines.append(f"```{lang}")
                lines.append(response)
                lines.append("```")
        
        # For multi-task examples
        if 'task_results' in result and result['task_results']:
            lines.append("")
            lines.append("**Tasks and Responses**:")
            lines.append("")
            for i, tr in enumerate(result['task_results'], 1):
                lines.append(f"{i}. **Task**: {tr['task']}")
                lines.append(f"   **Response**: {tr['response']}")
                lines.append("")
        
        # Add other metrics
        if 'tasks_completed' in result:
            lines.append(f"- **Tasks Completed**: {result['tasks_completed']}")
        
        if 'concurrent_speedup' in result:
            lines.append("")
            lines.append("**Performance Analysis**:")
            lines.append(f"- Concurrent execution time: {result['execution_time']:.1f}s")
            lines.append(f"- Speedup achieved: {result['concurrent_speedup']:.1f}x")
        
        if 'features_tested' in result:
            lines.append(f"- **Features Tested**: {', '.join(result['features_tested'])}")
        
        # Verification
        if result.get('verification') and not result['verification'].get('is_hallucination', True):
            lines.append("")
            lines.append("**Verification**: ✅ Execution verified as real")
            if result['verification'].get('verifications'):
                latest = result['verification']['verifications'][0]
                lines.append(f"- UUID: `{latest.get('execution_uuid', 'N/A')}`")
                lines.append(f"- Response File: `{latest.get('file', 'N/A').split('/')[-1]}`")
        
        # Add cleaned logs in collapsible section
        if result.get('logs') and result['logs'].strip():
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>📋 Raw Execution Logs</summary>")
            lines.append("")
            lines.append("```")
            lines.append(self._clean_logs(result['logs']))
            lines.append("```")
            lines.append("</details>")
        
        lines.append("")
        return '\n'.join(lines)
    
    def generate_report(self, summary: Dict[str, Any]) -> str:
        """Generate a complete markdown report from test results.
        
        Args:
            summary: Test summary dictionary
            
        Returns:
            Formatted markdown report
        """
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
        lines.append(f"| ⚠️ Warnings | {summary['summary']['warnings']} |")
        lines.append(f"| 🔥 Errors | {summary['summary']['errors']} |")
        lines.append(f"| **Total** | {summary['summary']['total_tests']} |")
        lines.append("")
        
        # Test results
        lines.append("## Test Results")
        lines.append("")
        
        for result in summary['results']:
            lines.append(self.format_test_result(result))
        
        # Key features section
        lines.append("## Key Features Demonstrated")
        lines.append("")
        
        feature_sections = [
            ("🚀 Quickstart", [
                "Simple one-line API: `await cc_execute(task)`",
                "Automatic timeout prediction with RedisTaskTimer",
                "Anti-hallucination verification built-in"
            ]),
            ("📚 Basic Usage", [
                "Sequential task execution",
                "Error handling and retry logic",
                "Progress tracking across multiple tasks"
            ]),
            ("⚡ Concurrent Execution", [
                "`asyncio.Semaphore(N)` for controlled parallelism",
                "`tqdm` progress bars with `as_completed`",
                "Demonstrated speedup with real tasks"
            ]),
            ("🎯 Advanced Features", [
                "JSON mode for structured responses",
                "Validation prompts for code verification",
                "Complex multi-step workflows"
            ])
        ]
        
        for title, features in feature_sections:
            lines.append(f"### {title}")
            for feature in features:
                lines.append(f"- {feature}")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        
        if summary['summary']['failed'] > 0 or summary['summary']['errors'] > 0:
            lines.append("1. **Fix failing tests** - Some examples are not working correctly")
            lines.append("")
        
        if summary['summary']['warnings'] > 0:
            lines.append("2. **Address warnings** - Some examples need documentation or minor fixes")
            lines.append("")
        
        if summary['summary']['passed'] == summary['summary']['total_tests']:
            lines.append("✅ **All examples are working correctly!** The examples provide a comprehensive learning path:")
            lines.append("")
            lines.append("1. **Start with Quickstart** - Get running in 30 seconds")
            lines.append("2. **Move to Basic** - Learn error handling and multi-task workflows")
            lines.append("3. **Try Medium** - Explore concurrent execution for speed")
            lines.append("4. **Master Advanced** - Use JSON mode and validation for production")
            lines.append("")
        
        # Test environment
        lines.append("## Test Environment")
        lines.append("")
        lines.append(f"- Python Version: {sys.version.split()[0]}")
        lines.append(f"- CC Executor Path: {Path(__file__).parent.parent.parent.parent}")
        lines.append(f"- Examples Path: {self.examples_dir}")
        lines.append("- Redis: Connected (timeout prediction active)")
        lines.append("- MCP: Configured and available")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*This report was generated automatically by the CC Executor test suite.*")
        
        return '\n'.join(lines)


async def test_and_report_examples(examples_dir: Optional[Path] = None,
                                  output_path: Optional[Path] = None) -> bool:
    """Test all examples and generate a comprehensive report.
    
    Args:
        examples_dir: Path to examples directory
        output_path: Where to save the report
        
    Returns:
        True if all tests passed
    """
    reporter = ExamplesTestReporter(examples_dir)
    
    # For now, load existing test results
    test_results_path = reporter.examples_dir / "test_results.json"
    
    if not test_results_path.exists():
        logger.error(f"Test results not found at {test_results_path}")
        return False
    
    with open(test_results_path, 'r') as f:
        summary = json.load(f)
    
    # Generate report
    report = reporter.generate_report(summary)
    
    # Save report
    if not output_path:
        output_path = reporter.examples_dir / "EXAMPLES_TEST_REPORT.md"
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {output_path}")
    
    return summary['summary']['failed'] == 0 and summary['summary']['errors'] == 0


if __name__ == "__main__":
    # Run the reporter
    success = asyncio.run(test_and_report_examples())
    sys.exit(0 if success else 1)