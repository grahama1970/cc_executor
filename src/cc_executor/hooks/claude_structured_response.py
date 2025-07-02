#!/usr/bin/env python3
"""
Structured response enforcement for Claude Code instances.
Similar to LiteLLM/OpenAI structured outputs using Pydantic models.

This module provides response templates that Claude must follow,
ensuring consistent, verifiable, and non-hallucinated responses.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import sys

class TaskStatus(Enum):
    """Status of task execution."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class ExecutionStep:
    """A single execution step with evidence."""
    action: str              # What was done
    command: Optional[str]   # Command executed
    output: Optional[str]    # Output received
    file_path: Optional[str] # File created/modified
    success: bool           # Whether step succeeded
    
@dataclass
class TaskResponse:
    """Structured response format for Claude instances."""
    task_description: str
    status: TaskStatus
    steps_completed: List[ExecutionStep] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    verification_performed: bool = False
    verification_output: Optional[str] = None
    next_steps: List[str] = field(default_factory=list)
    
    def to_prompt_format(self) -> str:
        """Convert to a format Claude should follow."""
        return f"""# Task Execution Report

## Task: {self.task_description}
## Status: {self.status.value}

### Steps Completed:
{self._format_steps()}

### Files Created:
{self._format_list(self.files_created)}

### Files Modified:
{self._format_list(self.files_modified)}

### Commands Executed:
{self._format_list(self.commands_executed)}

### Errors:
{self._format_list(self.errors_encountered)}

### Verification:
Performed: {self.verification_performed}
{f"Output: {self.verification_output}" if self.verification_output else ""}

### Next Steps:
{self._format_list(self.next_steps)}
"""

    def _format_steps(self) -> str:
        if not self.steps_completed:
            return "- None"
        
        formatted = []
        for i, step in enumerate(self.steps_completed, 1):
            formatted.append(f"{i}. {step.action}")
            if step.command:
                formatted.append(f"   Command: `{step.command}`")
            if step.output:
                formatted.append(f"   Output: {step.output[:100]}...")
            if step.file_path:
                formatted.append(f"   File: {step.file_path}")
            formatted.append(f"   Success: {'✓' if step.success else '✗'}")
            
        return '\n'.join(formatted)
        
    def _format_list(self, items: List[str]) -> str:
        if not items:
            return "- None"
        return '\n'.join(f"- {item}" for item in items)
        
    def validate(self) -> List[str]:
        """Validate the response structure."""
        issues = []
        
        # Must have at least one completed step for COMPLETED status
        if self.status == TaskStatus.COMPLETED and not self.steps_completed:
            issues.append("Status is COMPLETED but no steps recorded")
            
        # Must have evidence of work
        if self.status == TaskStatus.COMPLETED:
            has_evidence = (self.files_created or self.files_modified or 
                          self.commands_executed or self.verification_performed)
            if not has_evidence:
                issues.append("No evidence of work (files/commands/verification)")
                
        # Failed status should have errors
        if self.status == TaskStatus.FAILED and not self.errors_encountered:
            issues.append("Status is FAILED but no errors recorded")
            
        # Blocked status should have next steps
        if self.status == TaskStatus.BLOCKED and not self.next_steps:
            issues.append("Status is BLOCKED but no next steps provided")
            
        return issues


def create_response_template(task: str) -> str:
    """Create a response template for Claude to follow."""
    template = f"""You must structure your response according to this format:

# Task Execution Report

## Task: {task}
## Status: [Choose: not_started | in_progress | completed | failed | blocked]

### Steps Completed:
List each action taken with evidence:
1. [Action description]
   Command: `[exact command if applicable]`
   Output: [first 100 chars of output]
   File: [file path if applicable]
   Success: [✓ or ✗]

### Files Created:
- [Full path to each created file]
- [or "None" if no files created]

### Files Modified:
- [Full path to each modified file]
- [or "None" if no files modified]

### Commands Executed:
- [Each command executed]
- [or "None" if no commands run]

### Errors:
- [Any errors encountered]
- [or "None" if no errors]

### Verification:
Performed: [Yes/No]
Output: [Verification command output, e.g., "ls -la" showing the file exists]

### Next Steps:
- [What remains to be done]
- [or "None" if task is complete]

IMPORTANT: 
- Only claim COMPLETED if you have evidence (files/output)
- Include actual command outputs, not descriptions
- Run verification commands to prove completion
"""
    return template


def parse_claude_response(response: str) -> Optional[TaskResponse]:
    """Parse Claude's response into structured format."""
    try:
        # Extract sections using regex
        import re
        
        # Extract status
        status_match = re.search(r'## Status: (\w+)', response)
        if not status_match:
            return None
            
        status_str = status_match.group(1).lower()
        status = TaskStatus(status_str) if status_str in [s.value for s in TaskStatus] else TaskStatus.NOT_STARTED
        
        # Extract task
        task_match = re.search(r'## Task: (.+)', response)
        task = task_match.group(1) if task_match else "Unknown task"
        
        # Create response object
        task_response = TaskResponse(
            task_description=task,
            status=status
        )
        
        # Extract files created
        files_created_section = re.search(r'### Files Created:\n((?:- .+\n)*)', response)
        if files_created_section:
            files = re.findall(r'- (.+)', files_created_section.group(1))
            task_response.files_created = [f for f in files if f.lower() != 'none']
            
        # Extract commands
        commands_section = re.search(r'### Commands Executed:\n((?:- .+\n)*)', response)
        if commands_section:
            commands = re.findall(r'- (.+)', commands_section.group(1))
            task_response.commands_executed = [c for c in commands if c.lower() != 'none']
            
        # Extract verification
        verification_match = re.search(r'Performed: (Yes|No)', response, re.IGNORECASE)
        if verification_match:
            task_response.verification_performed = verification_match.group(1).lower() == 'yes'
            
        return task_response
        
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None


def enforce_structured_response(command: str) -> str:
    """Modify command to enforce structured response."""
    # Add response template to the command
    template = create_response_template(command)
    
    enhanced_command = f"""{command}

IMPORTANT: You MUST follow this exact response format:

{template}

Remember:
1. Execute the task first, then report using this format
2. Include real output/evidence, not descriptions
3. Run verification commands to confirm completion
4. Only mark as COMPLETED with concrete evidence"""
    
    return enhanced_command


# Example usage for WebSocket integration
class StructuredClaudeExecutor:
    """Executor that enforces structured responses."""
    
    @staticmethod
    def prepare_command(original_command: str) -> str:
        """Prepare command with structured response requirements."""
        return enforce_structured_response(original_command)
        
    @staticmethod
    def validate_response(response: str) -> Tuple[bool, List[str], Optional[TaskResponse]]:
        """Validate Claude's response against structure."""
        parsed = parse_claude_response(response)
        
        if not parsed:
            return False, ["Response does not follow required structure"], None
            
        issues = parsed.validate()
        
        return len(issues) == 0, issues, parsed
        
    @staticmethod
    def create_retry_prompt(original_task: str, issues: List[str]) -> str:
        """Create a retry prompt addressing validation issues."""
        return f"""Your previous response had these issues:
{chr(10).join(f'- {issue}' for issue in issues)}

Please retry the task: {original_task}

This time:
1. Actually execute the required commands
2. Include real output as evidence
3. Follow the structured format exactly
4. Mark as COMPLETED only with proof

{create_response_template(original_task)}"""


if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Claude Structured Response Test ===\n")
        
        # Test different task types
        test_tasks = [
            "Create a Python function that calculates fibonacci numbers",
            "Fix the bug in the login authentication module",
            "Implement a WebSocket server with message broadcasting",
            "Run all tests and fix any failures"
        ]
        
        print("1. Testing response templates for different tasks:\n")
        
        for i, task in enumerate(test_tasks, 1):
            print(f"Task {i}: {task}")
            print("-" * 60)
            template = create_response_template(task)
            print(template[:300] + "...\n")
        
        # Test response parsing with different scenarios
        print("\n2. Testing response parsing:\n")
        
        test_responses = [
            {
                "name": "Complete successful response",
                "response": """# Task Execution Report

## Task: Create a Python function that calculates fibonacci numbers
## Status: completed

### Steps Completed:
1. Created fibonacci.py with recursive and iterative implementations
   Command: `echo 'def fibonacci(n):...' > fibonacci.py`
   Output: File created successfully
   File: /tmp/fibonacci.py
   Success: ✓
2. Tested the function
   Command: `python -c "from fibonacci import fibonacci; print(fibonacci(10))"`
   Output: 55
   File: None
   Success: ✓

### Files Created:
- /tmp/fibonacci.py

### Files Modified:
- None

### Commands Executed:
- echo 'def fibonacci(n):...' > fibonacci.py
- python -c "from fibonacci import fibonacci; print(fibonacci(10))"

### Errors:
- None

### Verification:
Performed: Yes
Output: ls -la /tmp/fibonacci.py shows: -rw-r--r-- 1 user user 234 Nov 21 10:00 /tmp/fibonacci.py

### Next Steps:
- None"""
            },
            {
                "name": "Failed task with errors",
                "response": """# Task Execution Report

## Task: Fix the bug in the login authentication module
## Status: failed

### Steps Completed:
1. Attempted to locate authentication module
   Command: `find . -name "*auth*.py"`
   Output: No files found
   File: None
   Success: ✗

### Files Created:
- None

### Files Modified:
- None

### Commands Executed:
- find . -name "*auth*.py"
- grep -r "login" src/

### Errors:
- Could not locate authentication module
- No login-related code found in src directory

### Verification:
Performed: No
Output: None

### Next Steps:
- Need more information about project structure
- Locate the authentication module
- Identify the specific bug to fix"""
            },
            {
                "name": "Invalid response (hallucination)",
                "response": """# Task Execution Report

## Task: Implement a WebSocket server
## Status: completed

### Steps Completed:
- None

### Files Created:
- None

### Files Modified:
- None

### Commands Executed:
- None

### Errors:
- None

### Verification:
Performed: No

### Next Steps:
- None"""
            }
        ]
        
        for test_case in test_responses:
            print(f"{test_case['name']}:")
            print("-" * 60)
            
            parsed = parse_claude_response(test_case['response'])
            if parsed:
                print(f"Parsed successfully!")
                print(f"  Task: {parsed.task_description[:50]}...")
                print(f"  Status: {parsed.status.value}")
                print(f"  Steps: {len(parsed.steps_completed)}")
                print(f"  Files created: {len(parsed.files_created)}")
                print(f"  Commands: {len(parsed.commands_executed)}")
                print(f"  Errors: {len(parsed.errors_encountered)}")
                print(f"  Verified: {parsed.verification_performed}")
                
                # Validate
                issues = parsed.validate()
                if issues:
                    print(f"  Validation issues:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print(f"  ✓ Validation passed")
            else:
                print("Failed to parse response")
            print()
        
        # Test command enhancement
        print("\n3. Testing command enhancement:\n")
        
        original_command = "Create a REST API endpoint for user registration"
        enhanced = enforce_structured_response(original_command)
        print(f"Original command: {original_command}")
        print(f"\nEnhanced command preview (first 500 chars):")
        print("-" * 60)
        print(enhanced[:500] + "...")
        
        # Test StructuredClaudeExecutor
        print("\n\n4. Testing StructuredClaudeExecutor:\n")
        
        executor = StructuredClaudeExecutor()
        
        # Test validation
        for test_case in test_responses:
            print(f"Validating: {test_case['name']}")
            valid, issues, parsed = executor.validate_response(test_case['response'])
            print(f"  Valid: {valid}")
            if not valid:
                print(f"  Issues: {issues}")
            print()
        
        # Test retry prompt generation
        print("\n5. Testing retry prompt generation:\n")
        
        original_task = "Create a function to calculate prime numbers"
        validation_issues = [
            "Status is COMPLETED but no steps recorded",
            "No evidence of work (files/commands/verification)"
        ]
        
        retry_prompt = executor.create_retry_prompt(original_task, validation_issues)
        print("Retry prompt preview (first 400 chars):")
        print("-" * 60)
        print(retry_prompt[:400] + "...")
        
        # Demonstrate typical workflow
        print("\n\n6. Typical workflow demonstration:\n")
        
        print("Step 1: Prepare command with structure")
        task = "Write a hello world program in Python"
        prepared = executor.prepare_command(task)
        print(f"Task: {task}")
        print(f"Prepared: [command with {len(prepared)} chars]")
        
        print("\nStep 2: Claude executes and responds")
        print("(Claude would execute and respond with structured format)")
        
        print("\nStep 3: Validate response")
        mock_response = test_responses[0]['response']  # Use successful response
        valid, issues, parsed = executor.validate_response(mock_response)
        print(f"Valid: {valid}")
        print(f"Task status: {parsed.status.value if parsed else 'N/A'}")
        
        if not valid:
            print("\nStep 4: Generate retry if needed")
            retry = executor.create_retry_prompt(task, issues)
            print(f"Retry prompt generated: {len(retry)} chars")
            
        print("\n=== Test Complete ===")
    else:
        # Normal usage - demonstrate basic functionality
        test_task = "Create a Python function that calculates fibonacci numbers"
        
        print("=== Structured Response Template ===")
        print(create_response_template(test_task))
        
        # Test parsing
        sample_response = """# Task Execution Report

## Task: Create a Python function that calculates fibonacci numbers
## Status: completed

### Steps Completed:
1. Created fibonacci function
   Command: `None`
   Output: None
   File: fibonacci.py
   Success: ✓

### Files Created:
- fibonacci.py

### Files Modified:
- None

### Commands Executed:
- python fibonacci.py

### Errors:
- None

### Verification:
Performed: Yes
Output: fibonacci(10) = 55

### Next Steps:
- None
"""
        
        parsed = parse_claude_response(sample_response)
        if parsed:
            print("\n=== Parsed Response ===")
            print(f"Task: {parsed.task_description}")
            print(f"Status: {parsed.status.value}")
            print(f"Files created: {parsed.files_created}")
            print(f"Verification: {parsed.verification_performed}")
            
            issues = parsed.validate()
            print(f"\nValidation issues: {issues if issues else 'None'}")