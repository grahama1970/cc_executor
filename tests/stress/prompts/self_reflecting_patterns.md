# Self-Reflecting Prompt Templates

## Overview

These prompts include built-in self-reflection mechanisms where Claude evaluates its own response and iterates to improve it, with a configurable maximum number of iterations.

## Template Structure

```
[Initial Request]
After providing your answer, evaluate it against these criteria: [criteria list]
If any criteria are not met, provide an improved version.
Maximum iterations: [N]
Current iteration: [1]
```

## Implementation Examples

### Example 1: Fibonacci with Self-Reflection (N=2)

```bash
claude -p "What is the 10th Fibonacci number?

After answering, check:
1. Did I provide the specific number (55)?
2. Did I explain how the Fibonacci sequence works?
3. Did I show at least 5 terms of the sequence?

If missing any of these, provide an improved answer.
Maximum self-improvements: 2"
```

### Example 2: Recursion with Self-Reflection (N=3)

```bash
claude -p "What is recursion in programming?

After your response, evaluate:
1. Did I provide a clear definition (2-3 sentences)?
2. Did I explain the key concepts (base case, recursive case)?
3. Did I include a Python example with comments?
4. Is my example simple and easy to understand?

If any criteria are not fully met, revise your answer. 
Maximum self-revisions: 3"
```

### Example 3: Complex Task with Iterative Improvement

```bash
claude -p "What is the architecture for a todo app?

After your response, self-evaluate:
1. Did I include database schema?
2. Did I describe the API endpoints?
3. Did I mention the frontend components?
4. Is my explanation well-organized?

Rate each criterion (yes/partial/no). If any are 'partial' or 'no', provide an enhanced version.
Maximum iterations: 2"
```

## Python Implementation for Test Runner

```python
def create_self_reflecting_prompt(base_request, criteria, max_iterations=2):
    """
    Create a prompt with built-in self-reflection
    
    Args:
        base_request: The main question/request
        criteria: List of evaluation criteria
        max_iterations: Maximum self-improvement cycles
    
    Returns:
        Formatted prompt with self-reflection instructions
    """
    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    
    prompt = f"""{base_request}

After providing your answer, evaluate it against these criteria:
{criteria_text}

If your response doesn't fully satisfy all criteria, provide an improved version.
Label each version clearly (Version 1, Version 2, etc.).
Maximum self-improvements: {max_iterations}
Stop when all criteria are met or after {max_iterations} versions."""
    
    return prompt

# Example usage:
recursion_prompt = create_self_reflecting_prompt(
    base_request="What is recursion in programming?",
    criteria=[
        "Clear definition in 2-3 sentences",
        "Explanation of base case and recursive case",
        "Simple Python example with comments",
        "Step-by-step trace of how the recursion unfolds"
    ],
    max_iterations=2
)
```

## Benefits of Self-Reflection

1. **Higher Quality Responses**: Claude catches its own omissions
2. **Fewer External Retries**: Improvement happens within one call
3. **Explicit Criteria**: Clear expectations for complete answers
4. **Bounded Iteration**: Prevents infinite loops with max iterations

## Test Results Format

When using self-reflecting prompts, responses typically include:

```
Version 1:
[Initial response]

Self-evaluation:
- Criterion 1: ✓ Met
- Criterion 2: ✗ Missing
- Criterion 3: ~ Partial

Version 2 (Improved):
[Enhanced response addressing gaps]

Final self-evaluation:
- All criteria met ✓
```

## Integration with Stress Tests

```python
# In unified_stress_test_tasks_safe.json
{
  "id": "model_1_self_reflect",
  "name": "recursion_with_reflection",
  "natural_language_request": "What is recursion? After answering, check: 1) Definition provided? 2) Example included? 3) Clear explanation? If missing any, improve. Max 2 iterations.",
  "verification": {
    "expected_patterns": ["recursion", "base case", "example", "Version"],
    "timeout": 240  // Longer timeout for iterations
  }
}
```

## Measuring Self-Reflection Effectiveness

Track these metrics:
- How often does Version 1 meet all criteria?
- How much does Version 2 improve over Version 1?
- Does self-reflection reduce external retry attempts?
- What's the optimal max_iterations for different task types?

## Guidelines

1. **Keep Criteria Specific**: Vague criteria lead to poor self-evaluation
2. **Limit Iterations**: 2-3 is usually sufficient
3. **Match Timeout**: Add ~30s per expected iteration
4. **Clear Versioning**: Request labeled versions for easy parsing
5. **Measurable Criteria**: Use checkable facts, not subjective quality