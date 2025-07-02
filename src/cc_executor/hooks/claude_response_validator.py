#!/usr/bin/env python3
"""
Post-execution validation hook for Claude Code instances.
Ensures Claude actually completed the requested task and didn't hallucinate.

Similar to structured outputs in LiteLLM/OpenAI, this hook:
1. Parses Claude's response for evidence of task completion
2. Validates against expected patterns
3. Forces self-reflection if response is inadequate
4. Logs hallucination patterns for improvement
"""

import os
import sys
import json
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class ResponseQuality(Enum):
    """Response quality assessment levels."""
    COMPLETE = "complete"          # Task fully completed with evidence
    PARTIAL = "partial"            # Some work done but incomplete
    ACKNOWLEDGED = "acknowledged"   # Only acknowledged, no work done
    HALLUCINATED = "hallucinated"  # Claims completion without evidence
    ERROR = "error"                # Execution error
    
@dataclass
class ValidationResult:
    """Structured validation result similar to Pydantic model."""
    quality: ResponseQuality
    evidence: List[str]
    missing: List[str]
    hallucination_score: float
    needs_retry: bool
    suggestions: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "quality": self.quality.value,
            "evidence": self.evidence,
            "missing": self.missing,
            "hallucination_score": self.hallucination_score,
            "needs_retry": self.needs_retry,
            "suggestions": self.suggestions
        }

class ClaudeResponseValidator:
    """Validates Claude Code instance responses."""
    
    # Common hallucination patterns
    HALLUCINATION_PATTERNS = [
        r"I(?:'ve| have) (?:created|implemented|added|written) (?:the|a) .+",
        r"The .+ (?:is|are) now (?:ready|complete|implemented)",
        r"Successfully (?:created|implemented|added)",
        r"I've (?:set up|configured) .+",
        r"Here(?:'s| is) (?:the|your) .+",
        r"This (?:will|should) .+",
    ]
    
    # Evidence of actual work
    EVIDENCE_PATTERNS = {
        "file_created": r"(?:Created|Writing) .+ at: (.+)",
        "file_modified": r"(?:Modified|Updated|Edited) .+: (.+)",
        "command_executed": r"(?:Running|Executing|Output): (.+)",
        "test_passed": r"(?:\d+) (?:passed|tests? passed)",
        "code_block": r"```(?:python|javascript|bash|json)\n(.+?)```",
        "error_handled": r"(?:Error|Exception|Failed): (.+)",
        "verification": r"(?:Verified|Confirmed|Checked): (.+)"
    }
    
    # Task completion indicators
    COMPLETION_INDICATORS = {
        "create_file": ["file created", "wrote to", "saved as"],
        "modify_file": ["updated", "modified", "changed"],
        "run_test": ["tests passed", "test results", "pytest output"],
        "install_package": ["installed", "requirement satisfied"],
        "implement_function": ["def ", "class ", "function implemented"],
        "fix_bug": ["fixed", "resolved", "corrected"]
    }
    
    def __init__(self, output: str, command: str):
        self.output = output
        self.command = command.lower()
        self.task_type = self._identify_task_type()
        
    def _identify_task_type(self) -> str:
        """Identify what type of task was requested."""
        task_keywords = {
            "create_file": ["create", "write", "new file"],
            "modify_file": ["update", "modify", "change", "edit"],
            "run_test": ["test", "pytest", "verify"],
            "install_package": ["install", "pip", "uv"],
            "implement_function": ["implement", "function", "class", "endpoint"],
            "fix_bug": ["fix", "debug", "resolve", "error"]
        }
        
        for task_type, keywords in task_keywords.items():
            if any(kw in self.command for kw in keywords):
                return task_type
                
        return "general"
        
    def extract_evidence(self) -> List[str]:
        """Extract concrete evidence of work completion."""
        evidence = []
        
        for evidence_type, pattern in self.EVIDENCE_PATTERNS.items():
            matches = re.findall(pattern, self.output, re.MULTILINE | re.DOTALL)
            for match in matches:
                evidence.append(f"{evidence_type}: {match[:100]}")
                
        return evidence
        
    def check_hallucination(self) -> Tuple[bool, float]:
        """Check for hallucination patterns."""
        hallucination_count = 0
        total_patterns = len(self.HALLUCINATION_PATTERNS)
        
        for pattern in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, self.output, re.IGNORECASE):
                hallucination_count += 1
                
        # High hallucination score if claims without evidence
        hallucination_score = hallucination_count / total_patterns
        
        # Check if claims are backed by evidence
        has_claims = hallucination_count > 0
        has_evidence = len(self.extract_evidence()) > 0
        
        is_hallucinated = has_claims and not has_evidence
        
        return is_hallucinated, hallucination_score
        
    def check_acknowledgment_only(self) -> bool:
        """Check if Claude only acknowledged without doing work."""
        ack_patterns = [
            r"(?:Sure|Certainly|I'll|I will) (?:help|do|create|implement)",
            r"Let me (?:help|create|implement)",
            r"I (?:can|will) (?:help|assist) (?:you )?with",
            r"(?:Understood|Got it|Okay)",
            r"I'll (?:now|start|begin)"
        ]
        
        # Check if response is mostly acknowledgment
        ack_matches = sum(1 for p in ack_patterns if re.search(p, self.output, re.IGNORECASE))
        
        # Short response with acknowledgment patterns = likely acknowledgment only
        is_short = len(self.output.split('\n')) < 10
        has_ack = ack_matches >= 2
        no_evidence = len(self.extract_evidence()) == 0
        
        return is_short and has_ack and no_evidence
        
    def check_task_completion(self) -> List[str]:
        """Check what's missing for task completion."""
        missing = []
        
        if self.task_type in self.COMPLETION_INDICATORS:
            required_indicators = self.COMPLETION_INDICATORS[self.task_type]
            
            for indicator in required_indicators:
                if indicator not in self.output.lower():
                    missing.append(indicator)
                    
        # Universal requirements
        if "```" not in self.output and any(kw in self.command for kw in ["code", "implement", "function"]):
            missing.append("code block")
            
        if "error" in self.output.lower() and "resolved" not in self.output.lower():
            missing.append("error resolution")
            
        return missing
        
    def generate_self_reflection_prompt(self, validation: ValidationResult) -> str:
        """Generate a self-reflection prompt for Claude."""
        prompt = f"""Please review your previous response and verify:

1. Did you actually complete the requested task: "{self.command}"?
2. Can you point to specific evidence of completion?
3. If not fully completed, what remains to be done?

Your response quality assessment: {validation.quality.value}
Evidence found: {len(validation.evidence)}
Missing elements: {validation.missing}

Please either:
a) Provide evidence that the task was completed (file paths, command outputs, etc.)
b) Complete any missing work now
c) Explain what prevented completion

Be specific and factual. Do not claim completion without evidence."""
        
        return prompt
        
    def validate(self) -> ValidationResult:
        """Perform comprehensive validation."""
        evidence = self.extract_evidence()
        is_hallucinated, hall_score = self.check_hallucination()
        is_ack_only = self.check_acknowledgment_only()
        missing = self.check_task_completion()
        
        # Determine quality
        if is_hallucinated:
            quality = ResponseQuality.HALLUCINATED
        elif is_ack_only:
            quality = ResponseQuality.ACKNOWLEDGED
        elif "error" in self.output.lower() and "traceback" in self.output.lower():
            quality = ResponseQuality.ERROR
        elif missing:
            quality = ResponseQuality.PARTIAL
        elif evidence:
            quality = ResponseQuality.COMPLETE
        else:
            quality = ResponseQuality.ACKNOWLEDGED
            
        # Generate suggestions
        suggestions = []
        if quality != ResponseQuality.COMPLETE:
            if is_hallucinated:
                suggestions.append("Provide concrete evidence of work done")
            if is_ack_only:
                suggestions.append("Execute the task, don't just acknowledge")
            if missing:
                suggestions.append(f"Complete missing: {', '.join(missing)}")
            if not evidence:
                suggestions.append("Show command outputs or file modifications")
                
        return ValidationResult(
            quality=quality,
            evidence=evidence,
            missing=missing,
            hallucination_score=hall_score,
            needs_retry=quality not in [ResponseQuality.COMPLETE, ResponseQuality.ERROR],
            suggestions=suggestions
        )


def extract_task_from_output(output: str) -> Optional[str]:
    """Extract the original task from Claude's output."""
    # Look for task acknowledgment patterns
    patterns = [
        r"(?:help|assist) (?:you )?(?:to |with )?(.+?)(?:\.|$)",
        r"(?:create|implement|write|fix) (.+?)(?:\.|$)",
        r"(?:task|request)(?:ed)?: (.+?)(?:\.|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
    return None


def calculate_complexity_score(command: str, output_length: int) -> float:
    """Calculate prompt complexity score."""
    # Factors that increase complexity
    complexity = 0.0
    
    # Length factor
    complexity += len(command) / 1000.0  # Normalize by 1000 chars
    
    # Keyword complexity
    complex_keywords = ['implement', 'create', 'design', 'refactor', 'optimize', 
                       'websocket', 'concurrent', 'async', 'api', 'endpoint',
                       'authentication', 'validation', 'integration']
    
    for keyword in complex_keywords:
        if keyword in command.lower():
            complexity += 0.2
            
    # Multi-step indicators
    if any(word in command for word in ['then', 'after', 'also', 'and']):
        complexity += 0.3
        
    # Output length factor (longer outputs = more complex)
    complexity += output_length / 10000.0
    
    return min(complexity, 5.0)  # Cap at 5.0

def main():
    """Main hook entry point."""
    output = os.environ.get('CLAUDE_OUTPUT', '')
    exit_code = int(os.environ.get('CLAUDE_EXIT_CODE', '0'))
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
    duration = float(os.environ.get('CLAUDE_DURATION', '0'))
    
    # Get original command from Redis
    command = ""
    pre_check_data = None
    try:
        import redis
        r = redis.Redis(decode_responses=True)
        
        # Get validation record
        val_key = f"hook:claude_validation:{session_id}"
        val_data = r.get(val_key)
        
        if val_data:
            pre_check_data = json.loads(val_data)
            # Try to extract command from enhanced_command or original
            command = pre_check_data.get('enhanced_command', os.environ.get('CLAUDE_COMMAND', ''))
            
    except Exception as e:
        logger.error(f"Could not get validation record: {e}")
        command = os.environ.get('CLAUDE_COMMAND', '')
        
    if not output:
        logger.warning("No output to validate")
        sys.exit(0)
        
    logger.info("=== Claude Response Validation ===")
    
    # Validate response
    validator = ClaudeResponseValidator(output, command)
    result = validator.validate()
    
    logger.info(f"Response quality: {result.quality.value}")
    logger.info(f"Evidence found: {len(result.evidence)}")
    logger.info(f"Hallucination score: {result.hallucination_score:.2f}")
    
    if result.missing:
        logger.warning(f"Missing elements: {result.missing}")
        
    if result.suggestions:
        logger.info("Improvement suggestions:")
        for suggestion in result.suggestions:
            logger.info(f"  - {suggestion}")
            
    # Calculate complexity score
    complexity_score = calculate_complexity_score(command, len(output))
    
    # Create comprehensive execution record
    execution_record = {
        "session_id": session_id,
        "command": command[:500],  # Truncate long commands
        "exit_code": exit_code,
        "duration": duration,
        "output_length": len(output),
        "complexity_score": complexity_score,
        "quality": result.quality.value,
        "hallucination_score": result.hallucination_score,
        "evidence_count": len(result.evidence),
        "missing_count": len(result.missing),
        "timestamp": time.time(),
        "success": result.quality == ResponseQuality.COMPLETE,
        "pre_check_passed": pre_check_data.get('ready', False) if pre_check_data else False
    }
    
    # Store validation result
    try:
        val_result_key = f"hook:claude_validation_result:{session_id}"
        r.setex(val_result_key, 600, json.dumps(result.to_dict()))
        
        # Store comprehensive execution record for ALL responses
        r.lpush("claude:execution_history", json.dumps(execution_record))
        r.ltrim("claude:execution_history", 0, 999)  # Keep last 1000
        
        # Store by success/failure for analysis
        if execution_record['success']:
            r.lpush("claude:successful_executions", json.dumps(execution_record))
            r.ltrim("claude:successful_executions", 0, 499)
        else:
            r.lpush("claude:failed_executions", json.dumps(execution_record))
            r.ltrim("claude:failed_executions", 0, 499)
            
        # Track by complexity bucket for analysis
        complexity_bucket = int(complexity_score)  # 0, 1, 2, 3, 4, 5
        r.hincrby(f"claude:complexity:{complexity_bucket}", result.quality.value, 1)
        
        # Store average execution time by complexity
        time_key = f"claude:exec_time:complexity:{complexity_bucket}"
        r.lpush(time_key, duration)
        r.ltrim(time_key, 0, 99)  # Keep last 100 times per bucket
        
        # Track patterns
        if result.quality == ResponseQuality.HALLUCINATED:
            r.lpush("claude:hallucination_examples", json.dumps({
                "command": command[:200],
                "output": output[:500],
                "evidence": result.evidence,
                "complexity_score": complexity_score,
                "duration": duration,
                "timestamp": time.time()
            }))
            r.ltrim("claude:hallucination_examples", 0, 99)
            
        # Update statistics
        r.hincrby("claude:response_quality", result.quality.value, 1)
        
        # Calculate and store failure rate by complexity
        total_at_complexity = r.hlen(f"claude:complexity:{complexity_bucket}")
        failed_at_complexity = int(r.hget(f"claude:complexity:{complexity_bucket}", "failed") or 0)
        failure_rate = (failed_at_complexity / total_at_complexity * 100) if total_at_complexity > 0 else 0
        r.set(f"claude:failure_rate:complexity:{complexity_bucket}", f"{failure_rate:.1f}")
        
        # Log complexity analysis
        logger.info(f"Complexity score: {complexity_score:.2f} "
                   f"(bucket: {complexity_bucket}, failure rate: {failure_rate:.1f}%)")
        
        # If needs retry, store self-reflection prompt
        if result.needs_retry:
            reflection_prompt = validator.generate_self_reflection_prompt(result)
            r.setex(f"hook:claude_reflection:{session_id}", 300, reflection_prompt)
            logger.info("Generated self-reflection prompt for retry")
            
    except Exception as e:
        logger.error(f"Could not store validation result: {e}")
        
    # Log validation summary
    if result.quality == ResponseQuality.COMPLETE:
        logger.info("✓ Task appears to be completed successfully")
    elif result.quality == ResponseQuality.HALLUCINATED:
        logger.warning("⚠️  Response contains hallucination - claims without evidence")
    elif result.quality == ResponseQuality.ACKNOWLEDGED:
        logger.warning("⚠️  Claude only acknowledged the task without executing")
    elif result.quality == ResponseQuality.PARTIAL:
        logger.warning("⚠️  Task partially completed - missing elements")
        
    # Don't block execution, but signal quality issues
    if result.quality in [ResponseQuality.HALLUCINATED, ResponseQuality.ACKNOWLEDGED]:
        # Could trigger a retry mechanism here
        logger.warning("Consider retrying with self-reflection prompt")
        
    sys.exit(0)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Claude Response Validator Test ===\n")
        
        # Test cases with different response types
        test_cases = [
            {
                "name": "Complete task with evidence",
                "command": "Create a function to calculate fibonacci numbers",
                "output": """I'll create a fibonacci function for you.

Created file at: /tmp/fibonacci.py

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def fibonacci_iterative(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n+1):
        a, b = b, a + b
    return b
```

Running tests:
```bash
$ python -m pytest test_fibonacci.py
======= 5 passed in 0.03s =======
```

The function is now ready to use."""
            },
            {
                "name": "Hallucination - claims without evidence",
                "command": "Implement a websocket server",
                "output": """I've successfully implemented the websocket server for you. The server is now ready and listening on port 8000. It includes all the features you requested including authentication, message broadcasting, and error handling.

The implementation is complete and fully tested. You can now connect to the server and start sending messages."""
            },
            {
                "name": "Acknowledgment only",
                "command": "Fix the bug in the login function",
                "output": """Sure, I'll help you fix the bug in the login function. Let me analyze the issue and provide a solution for you.

I can definitely help with debugging the login functionality."""
            },
            {
                "name": "Partial completion",
                "command": "Create a REST API endpoint for user registration",
                "output": """I'll create a user registration endpoint.

```python
@app.post("/register")
async def register_user(user: UserCreate):
    # TODO: Add validation
    # TODO: Hash password
    # TODO: Save to database
    return {"message": "User created"}
```

The basic structure is in place but needs implementation of validation, password hashing, and database storage."""
            },
            {
                "name": "Error in execution",
                "command": "Run the test suite",
                "output": """Running the test suite:

```bash
$ pytest
```

Error occurred:
```
Traceback (most recent call last):
  File "test_main.py", line 5, in <module>
    import main
ModuleNotFoundError: No module named 'main'
```

The tests failed due to missing module."""
            }
        ]
        
        print("Testing different response types:\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. {test_case['name']}")
            print(f"   Command: {test_case['command']}")
            print("   " + "-" * 60)
            
            validator = ClaudeResponseValidator(test_case['output'], test_case['command'])
            result = validator.validate()
            
            print(f"   Quality: {result.quality.value}")
            print(f"   Evidence: {len(result.evidence)} items")
            if result.evidence:
                for j, ev in enumerate(result.evidence[:2], 1):
                    print(f"     {j}. {ev}")
            print(f"   Hallucination Score: {result.hallucination_score:.2f}")
            print(f"   Missing: {result.missing or 'None'}")
            print(f"   Needs Retry: {result.needs_retry}")
            if result.suggestions:
                print(f"   Suggestions:")
                for sug in result.suggestions:
                    print(f"     - {sug}")
            print()
        
        # Test self-reflection prompt generation
        print("\n2. Testing self-reflection prompt generation:\n")
        
        hallucination_case = test_cases[1]  # The hallucination example
        validator = ClaudeResponseValidator(hallucination_case['output'], hallucination_case['command'])
        result = validator.validate()
        
        if result.needs_retry:
            reflection_prompt = validator.generate_self_reflection_prompt(result)
            print("Generated self-reflection prompt:")
            print("-" * 60)
            print(reflection_prompt)
            print("-" * 60)
        
        # Test complexity scoring
        print("\n3. Testing complexity scoring:\n")
        
        complexity_tests = [
            ("Write hello world", 100),
            ("Create a simple function to add two numbers", 200),
            ("Implement a concurrent websocket handler with authentication", 500),
            ("Design and implement a complete REST API with authentication, validation, and database integration", 1000),
        ]
        
        for cmd, out_len in complexity_tests:
            score = calculate_complexity_score(cmd, out_len)
            print(f"Command: {cmd[:50]}...")
            print(f"  Complexity Score: {score:.2f}")
            print(f"  Complexity Bucket: {int(score)}")
            print()
        
        # Test Redis storage (if available)
        print("\n4. Testing validation storage:\n")
        
        try:
            import redis
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Simulate a validation
            test_session = "test_validation_123"
            os.environ['CLAUDE_SESSION_ID'] = test_session
            os.environ['CLAUDE_OUTPUT'] = test_cases[0]['output']
            os.environ['CLAUDE_EXIT_CODE'] = "0"
            os.environ['CLAUDE_DURATION'] = "3.14"
            os.environ['CLAUDE_COMMAND'] = test_cases[0]['command']
            
            # Store a pre-check record
            pre_check = {
                "ready": True,
                "checks_passed": ["venv", "mcp", "deps"],
                "checks_failed": []
            }
            r.setex(f"hook:claude_validation:{test_session}", 60, json.dumps(pre_check))
            
            # Run main validation (without exiting)
            original_exit = sys.exit
            sys.exit = lambda x: None
            
            try:
                main()
                print("✓ Validation completed and stored")
                
                # Check stored results
                val_result = r.get(f"hook:claude_validation_result:{test_session}")
                if val_result:
                    stored_result = json.loads(val_result)
                    print(f"  Stored quality: {stored_result['quality']}")
                    print(f"  Evidence count: {len(stored_result['evidence'])}")
                
                # Check execution history
                history = r.lrange("claude:execution_history", 0, 0)
                if history:
                    latest = json.loads(history[0])
                    print(f"  Execution recorded: {latest['success']}")
                    print(f"  Complexity: {latest['complexity_score']:.2f}")
                
                # Cleanup
                r.delete(f"hook:claude_validation:{test_session}")
                r.delete(f"hook:claude_validation_result:{test_session}")
                
            finally:
                sys.exit = original_exit
                
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()