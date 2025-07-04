#!/usr/bin/env python3
"""
Pre-flight validation hook for task lists.
Evaluates all tasks before execution to predict failure risks and suggest improvements.

This hook prevents wasted execution time by:
1. Calculating total complexity
2. Predicting failure probability
3. Identifying high-risk tasks
4. Suggesting task decomposition
5. Optionally blocking execution
"""

import os
import sys
import json
import re
import redis
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"          # <20% failure probability
    MEDIUM = "medium"    # 20-50% failure probability  
    HIGH = "high"        # 50-80% failure probability
    CRITICAL = "critical" # >80% failure probability

@dataclass
class TaskAssessment:
    """Assessment of a single task."""
    task_number: int
    description: str
    complexity_score: float
    predicted_failure_rate: float
    risk_level: RiskLevel
    issues: List[str]
    suggestions: List[str]
    estimated_duration: float
    
@dataclass
class TaskListAssessment:
    """Overall task list assessment."""
    total_tasks: int
    total_complexity: float
    average_complexity: float
    predicted_success_rate: float
    overall_risk: RiskLevel
    high_risk_tasks: List[int]
    estimated_total_time: float
    should_proceed: bool
    blocking_issues: List[str]
    improvement_suggestions: List[str]
    task_assessments: List[TaskAssessment]

class TaskListValidator:
    """Validates task lists before execution."""
    
    def __init__(self):
        # Add connection timeout to prevent infinite blocking
        timeout_seconds = int(os.environ.get('REDIS_TIMEOUT', '5'))
        self.r = redis.Redis(
            decode_responses=True,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds
        )
        self.failure_thresholds = self._load_failure_thresholds()
        
    def _load_failure_thresholds(self) -> Dict[int, float]:
        """Load historical failure rates by complexity."""
        thresholds = {}
        
        for complexity in range(6):
            # Get failure rate from Redis
            rate_str = self.r.get(f"claude:failure_rate:complexity:{complexity}")
            if rate_str:
                thresholds[complexity] = float(rate_str)
            else:
                # Default estimates if no data
                thresholds[complexity] = complexity * 15.0  # 0%, 15%, 30%, 45%, 60%, 75%
                
        return thresholds
        
    def calculate_task_complexity(self, task_description: str) -> float:
        """Calculate complexity score for a task."""
        complexity = 0.0
        
        # Length factor
        complexity += len(task_description) / 500.0
        
        # Keyword complexity
        complex_keywords = [
            'implement', 'create', 'design', 'refactor', 'optimize',
            'websocket', 'concurrent', 'async', 'api', 'endpoint',
            'authentication', 'validation', 'integration', 'database',
            'architecture', 'framework', 'deployment', 'production'
        ]
        
        task_lower = task_description.lower()
        for keyword in complex_keywords:
            if keyword in task_lower:
                complexity += 0.3
                
        # Multi-step indicators
        if any(indicator in task_lower for indicator in ['then', 'after that', 'also', 'and then', 'finally']):
            complexity += 0.5
            
        # File operations
        if any(op in task_lower for op in ['create file', 'modify file', 'update file']):
            complexity += 0.2
            
        # Testing complexity
        if 'test' in task_lower and any(word in task_lower for word in ['concurrent', 'all', 'comprehensive']):
            complexity += 0.4
            
        # Code generation
        if any(word in task_lower for word in ['function', 'class', 'endpoint', 'service']):
            complexity += 0.3
            
        return min(complexity, 5.0)
        
    def predict_failure_rate(self, complexity: float) -> float:
        """Predict failure rate based on complexity."""
        complexity_bucket = int(complexity)
        
        # Get historical rate
        base_rate = self.failure_thresholds.get(complexity_bucket, complexity_bucket * 15.0)
        
        # Interpolate for fractional complexity
        if complexity_bucket < 5 and complexity > complexity_bucket:
            next_rate = self.failure_thresholds.get(complexity_bucket + 1, (complexity_bucket + 1) * 15.0)
            fraction = complexity - complexity_bucket
            base_rate = base_rate + (next_rate - base_rate) * fraction
            
        return min(base_rate, 95.0)  # Cap at 95%
        
    def estimate_duration(self, complexity: float) -> float:
        """Estimate task duration based on complexity."""
        # Get historical execution times
        complexity_bucket = int(complexity)
        
        times_str = self.r.lrange(f"claude:exec_time:complexity:{complexity_bucket}", 0, -1)
        
        if times_str and len(times_str) >= 5:
            times = [float(t) for t in times_str]
            avg_time = sum(times) / len(times)
        else:
            # Default estimates: 15s, 30s, 60s, 120s, 240s, 480s
            avg_time = 15 * (2 ** complexity_bucket)
            
        # Add buffer for safety
        return avg_time * 1.3
        
    def assess_task(self, task_number: int, task_description: str) -> TaskAssessment:
        """Assess a single task."""
        issues = []
        suggestions = []
        
        # Calculate complexity
        complexity = self.calculate_task_complexity(task_description)
        
        # Predict failure rate
        failure_rate = self.predict_failure_rate(complexity)
        
        # Estimate duration
        duration = self.estimate_duration(complexity)
        
        # Determine risk level
        if failure_rate < 20:
            risk = RiskLevel.LOW
        elif failure_rate < 50:
            risk = RiskLevel.MEDIUM
        elif failure_rate < 80:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.CRITICAL
            
        # Check for specific issues
        if complexity >= 3:
            issues.append(f"High complexity score: {complexity:.1f}")
            suggestions.append("Consider breaking into smaller subtasks")
            
        if failure_rate >= 50:
            issues.append(f"High failure probability: {failure_rate:.0f}%")
            suggestions.append("Simplify or use more explicit instructions")
            
        if 'create' in task_description.lower() and 'test' in task_description.lower():
            issues.append("Multiple concerns in single task")
            suggestions.append("Separate creation and testing into different tasks")
            
        if duration > 300:  # 5 minutes
            issues.append(f"Long estimated duration: {duration/60:.1f} minutes")
            suggestions.append("Consider setting explicit timeout or breaking down")
            
        # Check for vague language
        vague_terms = ['something', 'somehow', 'some kind of', 'etc', 'and so on']
        if any(term in task_description.lower() for term in vague_terms):
            issues.append("Vague or ambiguous language detected")
            suggestions.append("Use specific, concrete requirements")
            
        return TaskAssessment(
            task_number=task_number,
            description=task_description[:100] + "..." if len(task_description) > 100 else task_description,
            complexity_score=complexity,
            predicted_failure_rate=failure_rate,
            risk_level=risk,
            issues=issues,
            suggestions=suggestions,
            estimated_duration=duration
        )
        
    def assess_task_list(self, tasks: List[Tuple[int, str]]) -> TaskListAssessment:
        """Assess entire task list."""
        task_assessments = []
        total_complexity = 0
        total_duration = 0
        high_risk_tasks = []
        blocking_issues = []
        suggestions = []
        
        # Assess each task
        for task_num, task_desc in tasks:
            assessment = self.assess_task(task_num, task_desc)
            task_assessments.append(assessment)
            
            total_complexity += assessment.complexity_score
            total_duration += assessment.estimated_duration
            
            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                high_risk_tasks.append(task_num)
                
        # Calculate overall metrics
        avg_complexity = total_complexity / len(tasks) if tasks else 0
        
        # Calculate overall success probability (assuming independent tasks)
        overall_success_prob = 1.0
        for assessment in task_assessments:
            task_success_prob = (100 - assessment.predicted_failure_rate) / 100
            overall_success_prob *= task_success_prob
            
        predicted_success_rate = overall_success_prob * 100
        
        # Determine overall risk
        if predicted_success_rate >= 80:
            overall_risk = RiskLevel.LOW
        elif predicted_success_rate >= 50:
            overall_risk = RiskLevel.MEDIUM
        elif predicted_success_rate >= 20:
            overall_risk = RiskLevel.HIGH
        else:
            overall_risk = RiskLevel.CRITICAL
            
        # Check for blocking issues
        critical_count = sum(1 for a in task_assessments if a.risk_level == RiskLevel.CRITICAL)
        
        if critical_count >= 3:
            blocking_issues.append(f"{critical_count} tasks have critical failure risk")
            
        if predicted_success_rate < 10:
            blocking_issues.append(f"Overall success rate too low: {predicted_success_rate:.1f}%")
            
        if total_duration > 3600:  # 1 hour
            blocking_issues.append(f"Total execution time too long: {total_duration/60:.0f} minutes")
            
        # Sequential dependency risks
        if len(high_risk_tasks) >= 2:
            # Check if high-risk tasks are sequential
            sequential_risks = []
            for i in range(len(high_risk_tasks) - 1):
                if high_risk_tasks[i+1] == high_risk_tasks[i] + 1:
                    sequential_risks.append(high_risk_tasks[i])
                    
            if sequential_risks:
                blocking_issues.append(f"Sequential high-risk tasks: {sequential_risks}")
                
        # Generate improvement suggestions
        if avg_complexity > 2.5:
            suggestions.append("Overall complexity is high - consider simplifying all tasks")
            
        if critical_count > 0:
            suggestions.append(f"Rewrite {critical_count} critical-risk tasks before execution")
            
        if len(tasks) > 10 and avg_complexity > 2:
            suggestions.append("Long task list with complex tasks - consider batching")
            
        # Determine if should proceed
        should_proceed = len(blocking_issues) == 0 and overall_risk != RiskLevel.CRITICAL
        
        return TaskListAssessment(
            total_tasks=len(tasks),
            total_complexity=total_complexity,
            average_complexity=avg_complexity,
            predicted_success_rate=predicted_success_rate,
            overall_risk=overall_risk,
            high_risk_tasks=high_risk_tasks,
            estimated_total_time=total_duration,
            should_proceed=should_proceed,
            blocking_issues=blocking_issues,
            improvement_suggestions=suggestions,
            task_assessments=task_assessments
        )


def extract_tasks_from_file(file_content: str) -> List[Tuple[int, str]]:
    """Extract task definitions from markdown file."""
    tasks = []
    
    # Pattern for task definitions
    patterns = [
        r'###\s*Task\s*(\d+):\s*(.+?)(?=###|$)',
        r'\*\*Task\s*(\d+)\*\*:\s*(.+?)(?=\*\*Task|\n\n|$)',
        r'Task\s*(\d+):\s*(.+?)(?=Task\s*\d+:|$)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, file_content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            task_num = int(match[0])
            task_desc = match[1].strip()
            
            # Clean up task description
            task_desc = re.sub(r'\n\s*', ' ', task_desc)  # Remove newlines
            task_desc = re.sub(r'\s+', ' ', task_desc)    # Normalize spaces
            
            if task_desc and len(task_desc) > 10:  # Minimum meaningful length
                tasks.append((task_num, task_desc))
                
    return sorted(tasks, key=lambda x: x[0])


def format_assessment_report(assessment: TaskListAssessment) -> str:
    """Format assessment as readable report."""
    report = []
    
    # Header
    report.append("=" * 70)
    report.append("TASK LIST PRE-FLIGHT ASSESSMENT")
    report.append("=" * 70)
    
    # Summary
    report.append(f"\n📊 SUMMARY")
    report.append(f"Total Tasks: {assessment.total_tasks}")
    report.append(f"Average Complexity: {assessment.average_complexity:.1f}/5.0")
    report.append(f"Predicted Success Rate: {assessment.predicted_success_rate:.1f}%")
    report.append(f"Overall Risk: {assessment.overall_risk.value.upper()}")
    report.append(f"Estimated Time: {assessment.estimated_total_time/60:.0f} minutes")
    report.append(f"Should Proceed: {'✅ YES' if assessment.should_proceed else '❌ NO'}")
    
    # Blocking issues
    if assessment.blocking_issues:
        report.append(f"\n🚫 BLOCKING ISSUES")
        for issue in assessment.blocking_issues:
            report.append(f"   - {issue}")
            
    # High risk tasks
    if assessment.high_risk_tasks:
        report.append(f"\n⚠️  HIGH RISK TASKS: {assessment.high_risk_tasks}")
        
    # Task details
    report.append(f"\n📋 TASK ANALYSIS")
    report.append("-" * 70)
    
    for task in assessment.task_assessments:
        risk_emoji = {
            RiskLevel.LOW: "✅",
            RiskLevel.MEDIUM: "⚡",
            RiskLevel.HIGH: "⚠️",
            RiskLevel.CRITICAL: "🚨"
        }[task.risk_level]
        
        report.append(f"\nTask {task.task_number}: {task.description}")
        report.append(f"   Risk: {risk_emoji} {task.risk_level.value} "
                     f"(Complexity: {task.complexity_score:.1f}, "
                     f"Failure: {task.predicted_failure_rate:.0f}%, "
                     f"Time: {task.estimated_duration:.0f}s)")
        
        if task.issues:
            report.append("   Issues:")
            for issue in task.issues:
                report.append(f"      - {issue}")
                
        if task.suggestions:
            report.append("   Suggestions:")
            for suggestion in task.suggestions:
                report.append(f"      → {suggestion}")
                
    # Overall suggestions
    if assessment.improvement_suggestions:
        report.append(f"\n💡 RECOMMENDATIONS")
        for suggestion in assessment.improvement_suggestions:
            report.append(f"   → {suggestion}")
            
    # Risk mitigation
    report.append(f"\n🛡️  RISK MITIGATION")
    if assessment.overall_risk == RiskLevel.CRITICAL:
        report.append("   1. DO NOT EXECUTE - Rewrite task list first")
        report.append("   2. Break down all tasks with complexity > 3")
        report.append("   3. Add explicit success criteria to each task")
    elif assessment.overall_risk == RiskLevel.HIGH:
        report.append("   1. Consider rewriting high-risk tasks")
        report.append("   2. Enable retry mechanism for all tasks")
        report.append("   3. Add checkpoints between critical tasks")
    elif assessment.overall_risk == RiskLevel.MEDIUM:
        report.append("   1. Monitor execution closely")
        report.append("   2. Be prepared to intervene on high-risk tasks")
        report.append("   3. Consider adding verification steps")
    else:
        report.append("   ✓ Low risk - proceed with standard execution")
        
    report.append("\n" + "=" * 70)
    
    return "\n".join(report)


def main():
    """Main hook entry point."""
    # Get task list file from environment
    file_path = os.environ.get('CLAUDE_FILE', '')
    
    if not file_path or not file_path.endswith('.md'):
        logger.info("Not a task list file, skipping pre-flight check")
        sys.exit(0)
        
    # Check if this is a task list
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        if 'task' not in content.lower() or 'Task 1:' not in content:
            logger.info("File doesn't appear to be a task list")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Could not read file: {e}")
        sys.exit(0)
        
    logger.info("=== Task List Pre-Flight Check ===")
    
    # Extract tasks
    tasks = extract_tasks_from_file(content)
    
    if not tasks:
        logger.warning("No tasks found in file")
        sys.exit(0)
        
    logger.info(f"Found {len(tasks)} tasks to assess")
    
    # Validate task list
    validator = TaskListValidator()
    assessment = validator.assess_task_list(tasks)
    
    # Generate report
    report = format_assessment_report(assessment)
    
    # Log report
    for line in report.split('\n'):
        logger.info(line)
        
    # Store assessment in Redis
    try:
        session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
        assessment_key = f"task_list:preflight:{session_id}"
        
        assessment_data = {
            'file_path': file_path,
            'total_tasks': assessment.total_tasks,
            'predicted_success_rate': assessment.predicted_success_rate,
            'overall_risk': assessment.overall_risk.value,
            'should_proceed': assessment.should_proceed,
            'blocking_issues': assessment.blocking_issues,
            'high_risk_tasks': assessment.high_risk_tasks,
            'report': report
        }
        
        validator.r.setex(assessment_key, 3600, json.dumps(assessment_data))
        
    except Exception as e:
        logger.error(f"Could not store assessment: {e}")
        
    # Exit with appropriate code
    if not assessment.should_proceed:
        logger.error("❌ Task list failed pre-flight check - execution blocked")
        sys.exit(1)  # Block execution
    else:
        logger.info("✅ Task list passed pre-flight check - safe to proceed")
        sys.exit(0)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Task List Pre-Flight Check Test ===\n")
        
        # Test task extraction
        print("1. Testing task extraction from markdown:\n")
        
        test_content = """# Project Tasks

### Task 1: Set up the development environment
Install all dependencies and configure the project.

**Task 2**: Create a WebSocket server with message broadcasting
Implement a full WebSocket server that can handle multiple clients.

Task 3: Write comprehensive tests for all endpoints
Ensure 100% code coverage with proper error handling tests.

### Task 4: Deploy to production and monitor performance
Set up CI/CD pipeline and deploy the application."""
        
        tasks = extract_tasks_from_file(test_content)
        print(f"Extracted {len(tasks)} tasks:")
        for num, desc in tasks:
            print(f"  Task {num}: {desc[:50]}...")
        
        # Test complexity calculation
        print("\n\n2. Testing complexity calculation:\n")
        
        validator = TaskListValidator()
        
        test_tasks = [
            "Add a comment to the code",
            "Create a simple print function",
            "Implement authentication with JWT tokens",
            "Refactor the entire codebase to use async/await patterns",
            "Deploy a microservices architecture with Kubernetes and monitoring"
        ]
        
        for task in test_tasks:
            complexity = validator.calculate_task_complexity(task)
            failure_rate = validator.predict_failure_rate(complexity)
            duration = validator.estimate_duration(complexity)
            
            print(f"Task: {task[:50]}...")
            print(f"  Complexity: {complexity:.1f}/5.0")
            print(f"  Failure rate: {failure_rate:.0f}%")
            print(f"  Est. duration: {duration:.0f}s")
            print()
        
        # Test individual task assessment
        print("\n3. Testing individual task assessment:\n")
        
        assessment = validator.assess_task(1, "Create a concurrent WebSocket handler with authentication and rate limiting")
        
        print(f"Task assessment:")
        print(f"  Risk level: {assessment.risk_level.value}")
        print(f"  Complexity: {assessment.complexity_score:.1f}")
        print(f"  Failure probability: {assessment.predicted_failure_rate:.0f}%")
        print(f"  Duration: {assessment.estimated_duration:.0f}s")
        
        if assessment.issues:
            print(f"  Issues:")
            for issue in assessment.issues:
                print(f"    - {issue}")
                
        if assessment.suggestions:
            print(f"  Suggestions:")
            for suggestion in assessment.suggestions:
                print(f"    → {suggestion}")
        
        # Test task list assessment
        print("\n\n4. Testing full task list assessment:\n")
        
        test_task_lists = [
            {
                "name": "Simple task list",
                "tasks": [
                    (1, "Create a hello world function"),
                    (2, "Add a print statement"),
                    (3, "Test the function")
                ]
            },
            {
                "name": "Complex task list",
                "tasks": [
                    (1, "Design and implement a microservices architecture"),
                    (2, "Create WebSocket server with authentication"),
                    (3, "Implement real-time data synchronization"),
                    (4, "Deploy to production with zero downtime"),
                    (5, "Set up comprehensive monitoring and alerting")
                ]
            },
            {
                "name": "Mixed complexity",
                "tasks": [
                    (1, "Set up project structure"),
                    (2, "Implement complex async processing pipeline"),
                    (3, "Add logging"),
                    (4, "Create comprehensive test suite with 100% coverage"),
                    (5, "Deploy and monitor")
                ]
            }
        ]
        
        for test_list in test_task_lists:
            print(f"\n{test_list['name']}:")
            assessment = validator.assess_task_list(test_list['tasks'])
            
            print(f"  Total tasks: {assessment.total_tasks}")
            print(f"  Average complexity: {assessment.average_complexity:.1f}")
            print(f"  Success rate: {assessment.predicted_success_rate:.1f}%")
            print(f"  Overall risk: {assessment.overall_risk.value}")
            print(f"  Should proceed: {'✅ Yes' if assessment.should_proceed else '❌ No'}")
            
            if assessment.blocking_issues:
                print(f"  Blocking issues:")
                for issue in assessment.blocking_issues:
                    print(f"    - {issue}")
        
        # Test report generation
        print("\n\n5. Testing report generation:\n")
        
        # Create a realistic task list
        realistic_tasks = [
            (1, "Initialize the project with proper structure and dependencies"),
            (2, "Create a REST API with FastAPI including user authentication"),
            (3, "Implement WebSocket support for real-time notifications"),
            (4, "Add comprehensive error handling and logging"),
            (5, "Write unit and integration tests"),
            (6, "Deploy to production using Docker and Kubernetes")
        ]
        
        assessment = validator.assess_task_list(realistic_tasks)
        report = format_assessment_report(assessment)
        
        print("Generated report preview (first 1000 chars):")
        print("-" * 70)
        print(report[:1000] + "...")
        
        # Test Redis storage
        print("\n\n6. Testing Redis storage (if available):\n")
        
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Store test assessment
            test_session = "test_preflight_123"
            assessment_key = f"task_list:preflight:{test_session}"
            
            assessment_data = {
                'file_path': 'test_tasks.md',
                'total_tasks': assessment.total_tasks,
                'predicted_success_rate': assessment.predicted_success_rate,
                'overall_risk': assessment.overall_risk.value,
                'should_proceed': assessment.should_proceed,
                'blocking_issues': assessment.blocking_issues,
                'high_risk_tasks': assessment.high_risk_tasks,
                'report': report[:500]  # Truncate for test
            }
            
            r.setex(assessment_key, 60, json.dumps(assessment_data))
            
            # Retrieve and verify
            stored = r.get(assessment_key)
            if stored:
                data = json.loads(stored)
                print("✓ Assessment stored successfully")
                print(f"  Success rate: {data['predicted_success_rate']:.1f}%")
                print(f"  Risk level: {data['overall_risk']}")
                print(f"  Can proceed: {data['should_proceed']}")
            
            # Cleanup
            r.delete(assessment_key)
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Demonstrate edge cases
        print("\n\n7. Testing edge cases:\n")
        
        edge_cases = [
            ("Empty task", ""),
            ("Vague task", "Do something with the code somehow etc"),
            ("Ultra complex", "Refactor the entire codebase to implement a new architecture using microservices, event sourcing, CQRS, and deploy it with zero downtime while maintaining backwards compatibility and ensuring 99.99% uptime"),
            ("Multiple steps", "First create the function, then test it, after that deploy it, and finally monitor the results")
        ]
        
        for name, task in edge_cases:
            assessment = validator.assess_task(1, task)
            print(f"{name}:")
            print(f"  Risk: {assessment.risk_level.value}")
            print(f"  Issues: {len(assessment.issues)}")
            print()
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()