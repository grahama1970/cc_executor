"""
Example: Validation Pattern for CC Executor

Shows best practices for using validation_prompt feature:
1. Simple validation without retry
2. Orchestrator-controlled retry pattern
3. Custom retry strategies
"""

import asyncio
from cc_executor.client.cc_execute import cc_execute


async def simple_validation_example():
    """Simple validation - no retry, just check result."""
    result = await cc_execute(
        "Create a function to calculate factorial",
        json_mode=True,
        validation_prompt="Check if this code is correct: {response}. Return JSON with 'is_valid' (bool) and 'issues' (list of strings)."
    )
    
    print(f"Code generated: {result['result']}")
    print(f"Validation passed: {result.get('is_valid', True)}")
    
    if not result.get('is_valid', True):
        print(f"Issues found: {result['validation']['issues']}")


async def orchestrator_retry_pattern():
    """Orchestrator handles retry logic - more flexible."""
    max_attempts = 3
    task = "Create a REST API endpoint for user registration with proper validation"
    
    for attempt in range(max_attempts):
        result = await cc_execute(
            task,
            json_mode=True,
            validation_prompt="""
            Validate this API code: {response}
            
            Check for:
            1. Input validation
            2. Error handling
            3. Security considerations
            
            Return JSON: {{"is_valid": bool, "issues": [list of issues], "score": 0-100}}
            """
        )
        
        if result.get('is_valid', True):
            print(f"✅ Validation passed on attempt {attempt + 1}")
            return result
            
        # Orchestrator can customize retry behavior
        print(f"❌ Attempt {attempt + 1} failed validation")
        print(f"Issues: {result['validation'].get('issues', [])}")
        
        if attempt < max_attempts - 1:
            # Could modify the task based on validation feedback
            task = f"{task}\n\nPrevious attempt had these issues: {result['validation']['issues']}"
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    print("Failed validation after all attempts")
    return result


async def custom_validation_strategy():
    """Example with custom validation strategies based on context."""
    
    # Different validation for different types of tasks
    validation_strategies = {
        "security": """
            Perform security audit on this code: {response}
            Check for: SQL injection, XSS, authentication bypasses
            Return: {{"is_valid": bool, "vulnerabilities": [], "severity": "low|medium|high|critical"}}
        """,
        "performance": """
            Analyze performance of this code: {response}
            Check for: O(n²) operations, unnecessary loops, memory leaks
            Return: {{"is_valid": bool, "issues": [], "complexity": "O(?)"}}
        """,
        "style": """
            Check code style: {response}
            Verify: PEP8 compliance, meaningful names, proper comments
            Return: {{"is_valid": bool, "violations": []}}
        """
    }
    
    # Task with multiple validation passes
    result = await cc_execute(
        "Implement a rate limiter using Redis",
        json_mode=True
    )
    
    # Run different validations
    for val_type, val_prompt in validation_strategies.items():
        print(f"\nRunning {val_type} validation...")
        
        val_result = await cc_execute(
            val_prompt.format(response=result['result']),
            json_mode=True
        )
        
        if val_result.get('is_valid', True):
            print(f"✅ {val_type} validation passed")
        else:
            print(f"❌ {val_type} validation failed: {val_result}")


# Best practices summary
BEST_PRACTICES = """
VALIDATION BEST PRACTICES:

1. Keep validation simple - single responsibility
2. Let orchestrator control retry logic
3. Default to is_valid=True on validation errors (don't block execution)
4. Use structured validation prompts that return consistent JSON
5. Consider different validation strategies for different contexts

DON'T:
- Hide retry complexity inside cc_execute
- Make validation mandatory (it's optional)
- Over-engineer the validation system

DO:
- Keep validation transparent
- Let callers decide retry strategy
- Make validation results predictable
"""


if __name__ == "__main__":
    print(BEST_PRACTICES)
    
    # Run examples
    asyncio.run(simple_validation_example())