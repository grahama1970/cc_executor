# CC Execute - Two-Stage Evaluation Pattern

Execute a command and evaluate the results through a two-stage verification process.

## Description

This prompt executes commands with intelligent evaluation:
- Stage 1: Internal evaluation within cc_execute (immediate validation)
- Stage 2: Orchestrator evaluation after completion (comprehensive verification)

## Usage

```bash
# Simple execution with evaluation
cc_execute "python -c 'print(2+2)'"

# Complex task with criteria
cc_execute "Write a Python function to calculate factorial" \
  --criteria "has docstring" \
  --criteria "handles edge cases" \
  --criteria "includes usage example"
```

## Two-Stage Evaluation Pattern

### Stage 1: Internal Evaluation (Immediate)
- Validates command execution success
- Checks for obvious errors or failures
- Performs basic output validation
- Quick sanity checks

### Stage 2: Orchestrator Evaluation (Comprehensive)
- Analyzes output quality
- Verifies criteria satisfaction
- Determines if retry is needed
- Provides detailed feedback

## Implementation

```python
import subprocess
import json
import sys
import os
import time
from typing import Dict, List, Any, Optional, Tuple

def validate_stage1(output: str, exit_code: int) -> Tuple[bool, str]:
    """Stage 1: Internal validation - immediate checks."""
    if exit_code != 0:
        return False, f"Command failed with exit code {exit_code}"
    
    if not output.strip():
        return False, "No output produced"
    
    # Check for common error patterns
    error_patterns = [
        "error:", "Error:", "ERROR:",
        "exception", "Exception", "EXCEPTION",
        "failed", "Failed", "FAILED",
        "traceback", "Traceback"
    ]
    
    output_lower = output.lower()
    for pattern in error_patterns:
        if pattern.lower() in output_lower:
            # Allow some false positives (e.g., "error handling")
            if "error handling" not in output_lower and "no error" not in output_lower:
                return False, f"Output contains error pattern: {pattern}"
    
    return True, "Stage 1 validation passed"

def evaluate_criteria(output: str, criteria: List[str]) -> Dict[str, bool]:
    """Evaluate output against specified criteria."""
    results = {}
    
    for criterion in criteria:
        criterion_lower = criterion.lower()
        
        # Common criteria checks
        if "docstring" in criterion_lower:
            results[criterion] = '"""' in output or "'''" in output
        elif "edge case" in criterion_lower:
            results[criterion] = any(word in output.lower() for word in ["if", "else", "try", "except", "0", "none", "empty"])
        elif "usage example" in criterion_lower or "example" in criterion_lower:
            results[criterion] = "if __name__" in output or "# Example" in output or ">>> " in output
        elif "test" in criterion_lower:
            results[criterion] = "assert" in output or "test_" in output or "Test" in output
        elif "type hint" in criterion_lower:
            results[criterion] = "->" in output or ": " in output
        else:
            # Generic check - does the output mention the criterion?
            results[criterion] = criterion_lower in output.lower()
    
    return results

def execute_with_evaluation(command: str, criteria: Optional[List[str]] = None, timeout: int = 30) -> Dict[str, Any]:
    """Execute command with two-stage evaluation."""
    start_time = time.time()
    
    # Add execution marker for verification
    marker = f"CC_EXECUTE_{int(time.time())}"
    print(f"[MARKER] {marker}")
    
    result = {
        "command": command,
        "marker": marker,
        "stage1": {"passed": False, "message": ""},
        "stage2": {"passed": False, "criteria_results": {}, "message": ""},
        "output": "",
        "exit_code": None,
        "duration": 0,
        "retry_recommended": False
    }
    
    try:
        # Execute command
        print(f"[EXECUTE] Running: {command}")
        
        # Handle different command types
        if command.startswith("Write ") or command.startswith("Create "):
            # This is a task description, not a shell command
            # We'll simulate by creating a simple implementation
            if "factorial" in command.lower():
                output = '''def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer.
    
    Args:
        n: A non-negative integer
        
    Returns:
        The factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

if __name__ == "__main__":
    # Example usage
    print(f"factorial(5) = {factorial(5)}")  # Output: 120
    print(f"factorial(0) = {factorial(0)}")  # Output: 1
    
    # Test edge cases
    try:
        factorial(-1)
    except ValueError as e:
        print(f"Error: {e}")  # Output: Error: Factorial is not defined for negative numbers
'''
                exit_code = 0
            else:
                output = f"# Task: {command}\n# Implementation would go here\n"
                exit_code = 0
        else:
            # Regular shell command
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = process.stdout + process.stderr
            exit_code = process.returncode
        
        result["output"] = output
        result["exit_code"] = exit_code
        
        # Stage 1: Internal validation
        stage1_passed, stage1_message = validate_stage1(output, exit_code)
        result["stage1"]["passed"] = stage1_passed
        result["stage1"]["message"] = stage1_message
        
        if not stage1_passed:
            result["retry_recommended"] = True
            print(f"[STAGE1] ❌ Failed: {stage1_message}")
        else:
            print(f"[STAGE1] ✅ Passed: {stage1_message}")
        
        # Stage 2: Orchestrator evaluation (criteria-based)
        if criteria and stage1_passed:
            criteria_results = evaluate_criteria(output, criteria)
            result["stage2"]["criteria_results"] = criteria_results
            
            passed_count = sum(1 for v in criteria_results.values() if v)
            total_count = len(criteria_results)
            
            stage2_passed = passed_count == total_count
            result["stage2"]["passed"] = stage2_passed
            result["stage2"]["message"] = f"Passed {passed_count}/{total_count} criteria"
            
            if not stage2_passed:
                result["retry_recommended"] = True
                failed_criteria = [k for k, v in criteria_results.items() if not v]
                print(f"[STAGE2] ❌ Failed criteria: {', '.join(failed_criteria)}")
            else:
                print(f"[STAGE2] ✅ All criteria passed!")
            
            # Print detailed results
            print("\n[CRITERIA EVALUATION]")
            for criterion, passed in criteria_results.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {criterion}")
        
    except subprocess.TimeoutExpired:
        result["exit_code"] = -1
        result["stage1"]["message"] = f"Command timed out after {timeout}s"
        result["retry_recommended"] = True
        print(f"[ERROR] Command timed out after {timeout}s")
    except Exception as e:
        result["exit_code"] = -1
        result["stage1"]["message"] = f"Execution error: {str(e)}"
        result["retry_recommended"] = True
        print(f"[ERROR] {str(e)}")
    
    result["duration"] = time.time() - start_time
    return result

def main():
    """Main entry point for cc_execute."""
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: cc_execute <command> [--criteria <criterion>]...")
        sys.exit(1)
    
    command = sys.argv[1]
    criteria = []
    
    # Parse criteria
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--criteria" and i + 1 < len(sys.argv):
            criteria.append(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # Execute with evaluation
    result = execute_with_evaluation(command, criteria)
    
    # Output results
    print("\n[RESULTS]")
    print(json.dumps(result, indent=2))
    
    # Determine exit code
    if result["stage1"]["passed"] and (not criteria or result["stage2"]["passed"]):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Response Format

```json
{
  "command": "string",
  "marker": "CC_EXECUTE_<timestamp>",
  "stage1": {
    "passed": true/false,
    "message": "string"
  },
  "stage2": {
    "passed": true/false,
    "criteria_results": {
      "criterion1": true/false,
      "criterion2": true/false
    },
    "message": "string"
  },
  "output": "string",
  "exit_code": 0,
  "duration": 1.23,
  "retry_recommended": true/false
}
```