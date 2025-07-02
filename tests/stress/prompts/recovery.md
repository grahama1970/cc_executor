# Stress Test with Recovery Mechanism

## Recovery Pattern for Robust Prompts

When Claude returns unexpected results (errors, too-short responses, or missing expected content), we should automatically retry with clarification.

### Recovery Strategy

1. **Initial Prompt**: Ask the question
2. **Check Response**: Look for:
   - Execution errors
   - Responses shorter than expected
   - Missing key patterns
3. **Recovery Prompt**: Re-ask with clarification

### Example Implementation

```python
async def run_test_with_recovery(test, max_retries=2):
    """Run a test with automatic recovery for unclear responses"""
    
    prompt = test['natural_language_request']
    timeout = test.get('verification', {}).get('timeout', 180)
    expected_patterns = test.get('verification', {}).get('expected_patterns', [])
    
    for attempt in range(max_retries + 1):
        # Run the test
        result = await run_single_test_attempt(prompt, timeout)
        
        # Check if response needs recovery
        if result['success'] and result['raw_stdout']:
            response = result['raw_stdout'].strip()
            
            # Check for execution errors
            if 'execution error' in response.lower() or 'error' in response.lower():
                # Clarify we want explanation, not execution
                prompt = f"{prompt} Please provide a detailed explanation with examples, not code execution."
                continue
            
            # Check for too-short responses
            if len(response.split()) < 10 and 'What is' in prompt:
                # Ask for more detail
                prompt = f"{prompt} Please provide a comprehensive explanation with at least 3-4 sentences."
                continue
            
            # Check for missing patterns
            patterns_found = sum(1 for p in expected_patterns if p.lower() in response.lower())
            if patterns_found < len(expected_patterns) * 0.6:
                # Be more specific about what we want
                missing = [p for p in expected_patterns if p.lower() not in response.lower()]
                prompt = f"{prompt} Please ensure your response includes information about: {', '.join(missing)}."
                continue
        
        # If we get here, either success or final attempt
        return result
    
    return result
```

## Improved Prompts with Built-in Clarity

### Fixed model_1 (recursion):
```
Original: What is recursion in programming with one simple Python example?
Improved: What is recursion in programming? Please explain the concept in 2-3 sentences and then show one simple Python example with comments.
```

### Fixed model_2 (fibonacci):
```
Original: What is the 10th Fibonacci number?
Improved: What is the 10th Fibonacci number and how is it calculated? Please show the number and explain the Fibonacci sequence briefly.
```

## Recovery Prompt Templates

### For "Execution Error" responses:
```
I notice there was an execution error. I'm looking for an explanation or description, not code execution. [Original question] - please provide a written response with examples if relevant.
```

### For too-short responses:
```
Thank you for the answer "{short_response}". Could you please elaborate with a more detailed explanation including [specific aspects from expected patterns]?
```

### For missing patterns:
```
Your response was helpful but didn't mention [missing patterns]. Could you please expand your answer to include information about these aspects?
```

## Implementation in stress tests

We could modify our stress test runner to:

1. **First attempt**: Run original prompt
2. **Analyze response**: Check for errors, length, patterns
3. **Recovery attempt**: If needed, generate clarified prompt
4. **Final result**: Return best response from attempts

This makes our stress tests more robust and educational - they learn what kinds of prompts work best!