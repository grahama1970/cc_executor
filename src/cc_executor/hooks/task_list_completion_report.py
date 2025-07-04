#!/usr/bin/env python3
"""
Post-task-list hook that generates a comprehensive completion report.

This hook:
1. Collects all task execution results
2. Analyzes success/failure patterns
3. Verifies actual vs expected outcomes
4. Generates a detailed report following CORE_ASSESSMENT_REPORT_TEMPLATE format
5. Saves report to the task list's reports/ directory
"""

import os
import sys
import json
import redis
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger

# Import truncation utilities from existing hook
from .truncate_logs import truncate_large_value, detect_binary_content

class TaskStatus(Enum):
    """Task execution status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_number: int
    description: str
    status: TaskStatus
    exit_code: int
    duration: float
    output_lines: int
    error_message: Optional[str]
    files_created: List[str]
    files_modified: List[str]
    evidence: List[str]
    warnings: List[str]
    raw_output: str  # Store full output for JSON

@dataclass
class TaskListReport:
    """Complete task list execution report."""
    session_id: str
    task_list_path: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float
    total_duration: float
    task_results: List[TaskResult]
    system_health: str
    risk_assessment: str
    recommendations: List[str]
    
class TaskListReporter:
    """Generates comprehensive task list reports."""
    
    def __init__(self):
        # Add connection timeout to prevent infinite blocking
        timeout_seconds = float(os.environ.get('REDIS_TIMEOUT', '5'))
        self.r = redis.Redis(
            decode_responses=True,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds
        )
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
        
    def collect_task_results(self) -> List[TaskResult]:
        """Collect all task execution results from Redis."""
        task_results = []
        
        # Get all task keys for this session
        pattern = f"task:*:{self.session_id}:*"
        task_keys = self.r.keys(pattern)
        
        # Group by task number
        tasks_by_number = {}
        for key in task_keys:
            parts = key.split(':')
            if len(parts) >= 4 and parts[3].isdigit():
                task_num = int(parts[3])
                if task_num not in tasks_by_number:
                    tasks_by_number[task_num] = {}
                
                # Extract metric type
                if 'status' in key:
                    tasks_by_number[task_num]['status'] = self.r.get(key)
                elif 'duration' in key:
                    tasks_by_number[task_num]['duration'] = float(self.r.get(key) or 0)
                elif 'exit_code' in key:
                    tasks_by_number[task_num]['exit_code'] = int(self.r.get(key) or -1)
                elif 'output' in key:
                    tasks_by_number[task_num]['output'] = self.r.get(key)
                elif 'description' in key:
                    tasks_by_number[task_num]['description'] = self.r.get(key)
                    
        # Convert to TaskResult objects
        for task_num in sorted(tasks_by_number.keys()):
            data = tasks_by_number[task_num]
            
            # Parse output for details
            output = data.get('output', '')
            files_created = self._extract_files_created(output)
            files_modified = self._extract_files_modified(output)
            evidence = self._extract_evidence(output)
            warnings = self._extract_warnings(output)
            
            # Determine status
            status_str = data.get('status', 'unknown')
            if status_str == 'completed':
                status = TaskStatus.SUCCESS
            elif status_str == 'partial':
                status = TaskStatus.PARTIAL
            elif status_str == 'timeout':
                status = TaskStatus.TIMEOUT
            elif status_str == 'failed':
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.ERROR
                
            result = TaskResult(
                task_number=task_num,
                description=data.get('description', f'Task {task_num}'),
                status=status,
                exit_code=data.get('exit_code', -1),
                duration=data.get('duration', 0.0),
                output_lines=len(output.split('\n')) if output else 0,
                error_message=self._extract_error(output) if status != TaskStatus.SUCCESS else None,
                files_created=files_created,
                files_modified=files_modified,
                evidence=evidence,
                warnings=warnings,
                raw_output=output
            )
            
            task_results.append(result)
            
        return sorted(task_results, key=lambda x: x.task_number)
        
    def _truncate_output(self, output: str, max_size: int = 10240) -> tuple[str, bool]:
        """Truncate output to prevent memory issues.
        
        Args:
            output: Raw output string
            max_size: Maximum size in bytes (default 10KB)
            
        Returns:
            Tuple of (truncated_output, was_truncated)
        """
        if not output:
            return "", False
            
        # Check if it's binary content first
        if detect_binary_content(output):
            # Show a preview of the binary data in hex format
            preview_bytes = output[:32].encode('utf-8', errors='replace')
            hex_preview = ' '.join(f'{b:02x}' for b in preview_bytes[:16])
            if len(preview_bytes) > 16:
                hex_preview += '...'
            return f"[BINARY DATA - {len(output)} bytes total, preview: {hex_preview}]", True
            
        if len(output.encode('utf-8')) <= max_size:
            return output, False
            
        # Use the imported truncation function
        truncated = truncate_large_value(output, max_size)
        return truncated, True
        
    def _extract_files_created(self, output: str) -> List[str]:
        """Extract created file paths from output."""
        files = []
        patterns = [
            r'Created file at: (.+)',
            r'File created: (.+)',
            r'Writing to (.+)',
            r'Saved to (.+)'
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, output)
            files.extend(matches)
            
        return list(set(files))
        
    def _extract_files_modified(self, output: str) -> List[str]:
        """Extract modified file paths from output."""
        files = []
        patterns = [
            r'Modified (.+)',
            r'Updated (.+)',
            r'Changed (.+)'
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, output)
            files.extend(matches)
            
        return list(set(files))
        
    def _extract_evidence(self, output: str) -> List[str]:
        """Extract evidence of task completion."""
        evidence = []
        
        # Look for test results
        if 'passed' in output and 'failed' not in output:
            import re
            test_match = re.search(r'(\d+) passed', output)
            if test_match:
                evidence.append(f"Tests passed: {test_match.group(1)}")
                
        # Look for successful operations
        success_indicators = [
            'Successfully', 'Completed', 'Created', 'Generated',
            'Implemented', 'Added', 'Fixed', 'Resolved'
        ]
        
        for line in output.split('\n'):
            if any(indicator in line for indicator in success_indicators):
                evidence.append(line.strip())
                if len(evidence) >= 3:  # Limit evidence items
                    break
                    
        return evidence
        
    def _extract_warnings(self, output: str) -> List[str]:
        """Extract warnings from output."""
        warnings = []
        warning_patterns = [
            r'Warning: (.+)',
            r'WARN: (.+)',
            r'⚠️ (.+)'
        ]
        
        import re
        for pattern in warning_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            warnings.extend(matches)
            
        return list(set(warnings))[:5]  # Limit to 5 warnings
        
    def _extract_error(self, output: str) -> Optional[str]:
        """Extract error message from output."""
        error_patterns = [
            r'Error: (.+)',
            r'ERROR: (.+)',
            r'Failed: (.+)',
            r'Exception: (.+)'
        ]
        
        import re
        for pattern in error_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
                
        # Check for Python traceback
        if 'Traceback' in output:
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if 'Traceback' in line:
                    # Get the last line of traceback (error message)
                    for j in range(len(lines)-1, i, -1):
                        if lines[j].strip():
                            return lines[j].strip()
                            
        return None
        
    def assess_system_health(self, results: List[TaskResult]) -> str:
        """Assess overall system health based on results."""
        if not results:
            return "UNKNOWN"
            
        success_rate = sum(1 for r in results if r.status == TaskStatus.SUCCESS) / len(results)
        
        if success_rate >= 0.9:
            return "HEALTHY"
        elif success_rate >= 0.7:
            return "DEGRADED"
        else:
            return "FAILING"
            
    def assess_risks(self, results: List[TaskResult]) -> str:
        """Assess risks based on execution patterns."""
        failed_count = sum(1 for r in results if r.status != TaskStatus.SUCCESS)
        timeout_count = sum(1 for r in results if r.status == TaskStatus.TIMEOUT)
        
        if failed_count == 0:
            return "LOW"
        elif timeout_count >= 2:
            return "HIGH - Multiple timeouts indicate system stress"
        elif failed_count >= len(results) * 0.5:
            return "CRITICAL - High failure rate"
        else:
            return "MEDIUM"
            
    def generate_recommendations(self, results: List[TaskResult]) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        # Check for timeout patterns
        timeout_tasks = [r for r in results if r.status == TaskStatus.TIMEOUT]
        if timeout_tasks:
            recommendations.append(f"Increase timeout for complex tasks (Tasks {[t.task_number for t in timeout_tasks]})")
            
        # Check for repeated failures
        failed_tasks = [r for r in results if r.status == TaskStatus.FAILED]
        if len(failed_tasks) >= 2:
            recommendations.append("Review task definitions for clarity and specificity")
            
        # Check for partial completions
        partial_tasks = [r for r in results if r.status == TaskStatus.PARTIAL]
        if partial_tasks:
            recommendations.append("Break down complex tasks into smaller subtasks")
            
        # Performance recommendations
        slow_tasks = [r for r in results if r.duration > 120]
        if slow_tasks:
            recommendations.append(f"Optimize long-running tasks: {[t.task_number for t in slow_tasks]}")
            
        return recommendations
        
    def generate_report(self, task_list_path: str) -> TaskListReport:
        """Generate comprehensive task list report."""
        # Collect results
        task_results = self.collect_task_results()
        
        # Calculate metrics
        total_tasks = len(task_results)
        successful_tasks = sum(1 for r in task_results if r.status == TaskStatus.SUCCESS)
        failed_tasks = total_tasks - successful_tasks
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        total_duration = sum(r.duration for r in task_results)
        
        # Assessments
        system_health = self.assess_system_health(task_results)
        risk_assessment = self.assess_risks(task_results)
        recommendations = self.generate_recommendations(task_results)
        
        return TaskListReport(
            session_id=self.session_id,
            task_list_path=task_list_path,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            total_duration=total_duration,
            task_results=task_results,
            system_health=system_health,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
        
    def format_report_markdown(self, report: TaskListReport) -> str:
        """Format report as markdown following TASK_LIST_REPORT_TEMPLATE."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        lines = [
            f"# Task List Execution Report",
            f"Generated: {timestamp}",
            f"Session ID: {report.session_id}",
            f"Task List: {report.task_list_path}",
            f"Assessed by: Task Completion Hook (Awaiting Agent Analysis)",
            f"Template: docs/templates/TASK_LIST_REPORT_TEMPLATE.md v1.0",
            "",
            "## Summary",
            f"- Total Tasks Executed: {report.total_tasks}",
            f"- Success Rate: {report.success_rate:.1f}%",
            f"- Total Execution Time: {report.total_duration:.1f}s",
            f"- System Health: {report.system_health}",
            f"- Risk Assessment: {report.risk_assessment}",
            "",
            "## Task Execution Details",
            ""
        ]
        
        # Add individual task results
        for result in report.task_results:
            status_icon = {
                TaskStatus.SUCCESS: "✅",
                TaskStatus.PARTIAL: "⚡",
                TaskStatus.FAILED: "❌",
                TaskStatus.TIMEOUT: "⏱️",
                TaskStatus.ERROR: "🚨"
            }[result.status]
            
            lines.extend([
                f"### {status_icon} Task {result.task_number}: {result.description}",
                "",
                "#### Execution Results",
                f"- **Status**: {result.status.value}",
                f"- **Exit Code**: {result.exit_code}",
                f"- **Duration**: {result.duration:.1f}s",
                f"- **Output Lines**: {result.output_lines}",
                ""
            ])
            
            if result.files_created:
                lines.extend([
                    "#### Files Created",
                    *[f"- `{f}`" for f in result.files_created],
                    ""
                ])
                
            if result.files_modified:
                lines.extend([
                    "#### Files Modified", 
                    *[f"- `{f}`" for f in result.files_modified],
                    ""
                ])
                
            if result.evidence:
                lines.extend([
                    "#### Evidence of Completion",
                    *[f"✓ {e}" for e in result.evidence],
                    ""
                ])
                
            if result.warnings:
                lines.extend([
                    "#### Warnings",
                    *[f"⚠️ {w}" for w in result.warnings],
                    ""
                ])
                
            if result.error_message:
                lines.extend([
                    "#### Error Details",
                    f"```",
                    result.error_message,
                    f"```",
                    ""
                ])
                
            # Add placeholder for agent assessment
            lines.extend([
                "#### 🧠 Agent's Reasonableness Assessment",
                "**Verdict**: [PENDING AGENT REVIEW]",
                "",
                "**Task Intent Analysis**:",
                "- **What was requested**: [TO BE ANALYZED]",
                "- **What was delivered**: [TO BE ANALYZED]", 
                "- **Match percentage**: [TO BE CALCULATED]%",
                "",
                "**Evidence Verification**:",
                "- [AWAITING AGENT VERIFICATION]",
                "",
                "**Hallucination Check**:",
                "- [PENDING ANALYSIS]",
                "",
                "**Conclusion**: [AGENT ASSESSMENT REQUIRED]",
                ""
            ])
            
            # Add raw JSON data to prevent hallucination
            # Truncate raw output to prevent memory issues
            truncated_output, was_truncated = self._truncate_output(result.raw_output)
            
            json_data = {
                "task_number": result.task_number,
                "description": result.description,
                "status": result.status.value,
                "exit_code": result.exit_code,
                "duration": result.duration,
                "output_lines": result.output_lines,
                "files_created": result.files_created,
                "files_modified": result.files_modified,
                "evidence": result.evidence,
                "warnings": result.warnings,
                "error_message": result.error_message,
                "raw_output": truncated_output,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "execution_id": f"exec_{result.task_number:03d}_{self.session_id[:8]}",
                "output_truncated": was_truncated
            }
            
            lines.extend([
                "#### Complete Raw JSON Output",
                "```json",
                json.dumps(json_data, indent=2),
                "```",
                ""
            ])
            
            # Save full output to separate file if truncated
            if was_truncated:
                # Get task list directory from environment
                task_list_path = os.environ.get('CLAUDE_TASK_LIST_FILE', '')
                if task_list_path:
                    task_list_dir = Path(task_list_path).parent
                    full_output_dir = task_list_dir / "reports" / "full_outputs"
                    full_output_dir.mkdir(parents=True, exist_ok=True)
                    full_output_file = full_output_dir / f"task_{result.task_number:03d}_full_output.txt"
                    with open(full_output_file, 'w') as f:
                        f.write(result.raw_output)
                    lines.extend([
                        f"**Note**: Full output saved to: `reports/full_outputs/task_{result.task_number:03d}_full_output.txt`",
                        ""
                    ])
                
            lines.append("")
            
        # Overall assessment
        lines.extend([
            "## 🎯 Overall System Assessment",
            "",
            f"### System Health: {report.system_health}",
            "",
            "Based on the execution results, the task list execution is assessed as " +
            ("successful" if report.system_health == "HEALTHY" else 
             "partially successful" if report.system_health == "DEGRADED" else
             "problematic"),
            "",
            f"### Risk Assessment: {report.risk_assessment}",
            ""
        ])
        
        # Recommendations
        if report.recommendations:
            lines.extend([
                "## 📋 Recommendations",
                "",
                *[f"1. {rec}" for i, rec in enumerate(report.recommendations, 1)],
                ""
            ])
            
        # Metrics summary
        lines.extend([
            "## 📊 Execution Metrics",
            "",
            f"- Average task duration: {report.total_duration / report.total_tasks:.1f}s" if report.total_tasks > 0 else "- No tasks executed",
            f"- Longest task: Task {max(report.task_results, key=lambda x: x.duration).task_number} ({max(r.duration for r in report.task_results):.1f}s)" if report.task_results else "",
            f"- Files created: {sum(len(r.files_created) for r in report.task_results)}",
            f"- Files modified: {sum(len(r.files_modified) for r in report.task_results)}",
            ""
        ])
        
        return "\n".join(lines)
        
def main():
    """Main hook entry point."""
    # Get task list file from environment
    task_list_path = os.environ.get('CLAUDE_TASK_LIST_FILE', '')
    
    if not task_list_path:
        logger.info("No task list file specified, skipping report generation")
        return
        
    logger.info(f"Generating completion report for: {task_list_path}")
    
    # Generate report
    reporter = TaskListReporter()
    report = reporter.generate_report(task_list_path)
    
    # Format as markdown
    markdown_report = reporter.format_report_markdown(report)
    
    # Determine output location
    task_list_dir = Path(task_list_path).parent
    reports_dir = task_list_dir / "reports"
    
    try:
        reports_dir.mkdir(exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied creating reports directory: {reports_dir}")
        # Try alternative location in tmp
        reports_dir = Path("/tmp") / "cc_executor_reports"
        reports_dir.mkdir(exist_ok=True)
        logger.info(f"Using alternative location: {reports_dir}")
    except Exception as e:
        logger.error(f"Failed to create reports directory: {e}")
        return
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"task_list_report_{timestamp}.md"
    
    try:
        with open(report_file, 'w') as f:
            f.write(markdown_report)
        logger.info(f"✅ Report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
    
    # Also save JSON version for programmatic access
    json_file = reports_dir / f"task_list_report_{timestamp}.json"
    report_data = {
        'session_id': report.session_id,
        'task_list_path': report.task_list_path,
        'total_tasks': report.total_tasks,
        'successful_tasks': report.successful_tasks,
        'failed_tasks': report.failed_tasks,
        'success_rate': report.success_rate,
        'total_duration': report.total_duration,
        'system_health': report.system_health,
        'risk_assessment': report.risk_assessment,
        'recommendations': report.recommendations,
        'task_results': [
            {
                'task_number': r.task_number,
                'description': r.description,
                'status': r.status.value,
                'exit_code': r.exit_code,
                'duration': r.duration,
                'files_created': r.files_created,
                'files_modified': r.files_modified,
                'evidence': r.evidence,
                'warnings': r.warnings,
                'error_message': r.error_message
            }
            for r in report.task_results
        ]
    }
    
    with open(json_file, 'w') as f:
        json.dump(report_data, f, indent=2)
        
    logger.info(f"📊 JSON data saved to: {json_file}")
    
    # Log summary
    logger.info(f"Report Summary:")
    logger.info(f"  Success Rate: {report.success_rate:.1f}%")
    logger.info(f"  System Health: {report.system_health}")
    logger.info(f"  Risk Level: {report.risk_assessment}")
    

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Task List Completion Report Test ===\n")
        
        # Create test data in Redis
        r = redis.Redis(decode_responses=True)
        test_session = "test_report_123"
        
        # Simulate task results
        test_tasks = [
            {
                'num': 1,
                'desc': 'Initialize project structure',
                'status': 'completed',
                'exit_code': 0,
                'duration': 15.2,
                'output': 'Created file at: /project/setup.py\nSuccessfully initialized project'
            },
            {
                'num': 2,
                'desc': 'Create API endpoints',
                'status': 'completed', 
                'exit_code': 0,
                'duration': 45.8,
                'output': 'Created file at: /project/api/endpoints.py\nTests passed: 5'
            },
            {
                'num': 3,
                'desc': 'Deploy to production',
                'status': 'failed',
                'exit_code': 1,
                'duration': 120.5,
                'output': 'Error: Connection timeout\nFailed to deploy'
            }
        ]
        
        # Store in Redis
        for task in test_tasks:
            base_key = f"task:{{}}:{test_session}:{task['num']}"
            r.set(base_key.format('description'), task['desc'])
            r.set(base_key.format('status'), task['status'])
            r.set(base_key.format('exit_code'), task['exit_code'])
            r.set(base_key.format('duration'), task['duration'])
            r.set(base_key.format('output'), task['output'])
            
        # Test report generation
        os.environ['CLAUDE_SESSION_ID'] = test_session
        reporter = TaskListReporter()
        
        # Test result collection
        print("1. Testing result collection:")
        results = reporter.collect_task_results()
        print(f"   Collected {len(results)} task results")
        for result in results:
            print(f"   Task {result.task_number}: {result.status.value}")
            
        # Test report generation
        print("\n2. Testing report generation:")
        report = reporter.generate_report("test_tasks.md")
        print(f"   Success rate: {report.success_rate:.1f}%")
        print(f"   System health: {report.system_health}")
        print(f"   Risk assessment: {report.risk_assessment}")
        
        # Test markdown formatting
        print("\n3. Testing markdown formatting:")
        markdown = reporter.format_report_markdown(report)
        print("   Report preview (first 500 chars):")
        print("-" * 50)
        print(markdown[:500] + "...")
        
        # Cleanup
        for task in test_tasks:
            base_key = f"task:*:{test_session}:{task['num']}"
            for key in r.keys(base_key):
                r.delete(key)
                
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()