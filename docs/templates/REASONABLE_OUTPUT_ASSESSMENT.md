# Self-Improving Prompt: Reasonable Output Assessment

## Purpose
This template helps assess whether a program's output is reasonable without using regex or exact string matching. It provides a structured approach to evaluating test results based on sensible expectations.

## Core Assessment Principles

### 1. Presence Check
Output should exist and have meaningful content:
- **Not empty**: len(output.strip()) > 0
- **Sufficient length**: Indicates the program actually ran
- **Has structure**: Not just random characters

### 2. Error Detection
Look for obvious failure indicators:
```
NEGATIVE_INDICATORS = [
    "Traceback",
    "Exception:", 
    "Error:",
    "FAILED",
    "No such file",
    "Permission denied",
    "ImportError",
    "ModuleNotFoundError",
    "KeyError",
    "ValueError",
    "TypeError",
    "AttributeError"
]
```

### 3. Success Markers
Look for positive indicators:
```
POSITIVE_INDICATORS = [
    "✓", "✅",
    "PASS", "passed",
    "SUCCESS", "successful",
    "completed", "complete",
    "OK", "ok",
    "All tests passed",
    "Working correctly",
    "Test passed"
]
```

### 4. Context-Specific Validation

#### For Test Outputs
```python
def assess_test_output(output):
    # Should have test results
    has_test_markers = any(marker in output for marker in ['Test', 'test', 'Testing'])
    
    # Should show some form of completion
    has_completion = any(word in output for word in ['completed', 'finished', 'done'])
    
    # Should have results (numbers are good indicators)
    has_results = any(char.isdigit() for char in output)
    
    return has_test_markers and (has_completion or has_results)
```

#### For JSON Outputs
```python
def assess_json_output(output):
    try:
        data = json.loads(output)
        # Should be dict or list
        if not isinstance(data, (dict, list)):
            return False
        # Should not be empty
        if not data:
            return False
        # Dict should have keys
        if isinstance(data, dict) and len(data.keys()) == 0:
            return False
        return True
    except:
        return False
```

#### For Hook Outputs
```python
def assess_hook_output(output, hook_type):
    expectations = {
        'setup_environment': ['venv', 'activation', 'wrapped'],
        'analyze_complexity': ['complexity', 'timeout', 'score'],
        'response_validator': ['quality', 'hallucination', 'evidence'],
        'truncate_logs': ['truncated', 'bytes', 'reduction']
    }
    
    expected_words = expectations.get(hook_type, [])
    found_count = sum(1 for word in expected_words if word.lower() in output.lower())
    
    # Should find at least half of expected words
    return found_count >= len(expected_words) / 2
```

## Assessment Algorithm

```python
def is_output_reasonable(output, context=None):
    """
    Assess if output is reasonable without regex.
    
    Args:
        output: The program output to assess
        context: Optional context about what kind of output to expect
        
    Returns:
        (is_reasonable, explanation)
    """
    # Step 1: Basic sanity checks
    if not output or not output.strip():
        return False, "Empty output"
    
    # Step 2: Check for errors
    for error_indicator in NEGATIVE_INDICATORS:
        if error_indicator in output:
            # Some errors might be OK in test scenarios
            if context and 'test_errors' in context:
                continue
            return False, f"Found error indicator: {error_indicator}"
    
    # Step 3: Look for success markers
    has_positive = any(marker in output for marker in POSITIVE_INDICATORS)
    
    # Step 4: Context-specific checks
    if context:
        if context.get('type') == 'json':
            if not assess_json_output(output):
                return False, "Invalid JSON structure"
        
        if context.get('type') == 'test':
            if not assess_test_output(output):
                return False, "Missing test indicators"
        
        if context.get('min_length'):
            if len(output) < context['min_length']:
                return False, f"Output too short (< {context['min_length']})"
        
        if context.get('must_contain'):
            for required in context['must_contain']:
                if required not in output:
                    return False, f"Missing required content: {required}"
    
    # Step 5: Heuristic assessment
    # Output with 100+ chars and no errors is probably reasonable
    if len(output) > 100 and not any(err in output for err in NEGATIVE_INDICATORS):
        return True, "Substantial output without errors"
    
    # Output with positive markers is reasonable
    if has_positive:
        return True, "Contains success indicators"
    
    # Short output might be OK for simple commands
    if len(output) < 50 and context and context.get('allow_short'):
        return True, "Short but acceptable output"
    
    # Default: be conservative
    return False, "No clear indicators of success"
```

## Self-Improvement Loop

### Collect Patterns
```python
LEARNED_PATTERNS = {
    'success_patterns': [],
    'failure_patterns': [],
    'context_expectations': {}
}

def learn_from_output(output, was_successful, context=None):
    """Learn from validated outputs to improve assessment."""
    if was_successful:
        # Extract new positive patterns
        words = output.split()
        for word in words:
            if len(word) > 3 and word not in LEARNED_PATTERNS['success_patterns']:
                LEARNED_PATTERNS['success_patterns'].append(word)
    else:
        # Learn failure patterns
        for line in output.split('\n'):
            if 'Error' in line or 'Failed' in line:
                LEARNED_PATTERNS['failure_patterns'].append(line[:50])
    
    # Learn context-specific expectations
    if context and context.get('type'):
        ctx_type = context['type']
        if ctx_type not in LEARNED_PATTERNS['context_expectations']:
            LEARNED_PATTERNS['context_expectations'][ctx_type] = {
                'typical_length': [],
                'common_words': []
            }
        LEARNED_PATTERNS['context_expectations'][ctx_type]['typical_length'].append(len(output))
```

## Usage Example

```python
# Basic usage
output = run_command("python test.py")
is_reasonable, reason = is_output_reasonable(output)
print(f"Output assessment: {is_reasonable} - {reason}")

# With context
output = run_hook("analyze_task_complexity")
is_reasonable, reason = is_output_reasonable(
    output,
    context={
        'type': 'json',
        'min_length': 50,
        'must_contain': ['complexity_score', 'timeout']
    }
)

# Learn from result
if manually_verified_as_correct:
    learn_from_output(output, True, {'type': 'hook'})
```

## Reasonable Output Checklist

✓ **Has content** - Not empty or just whitespace
✓ **No critical errors** - No tracebacks or exceptions (unless testing errors)
✓ **Appropriate length** - Not suspiciously short or long
✓ **Expected elements** - Contains words/patterns relevant to the task
✓ **Structured** - Has some organization (lines, sections, JSON, etc.)
✓ **Actionable** - Provides information that can be used

## Anti-Patterns to Avoid

❌ Using regex for validation - Too brittle
❌ Exact string matching - Prevents evolution
❌ Over-specific expectations - Blocks valid variations
❌ Ignoring context - One size doesn't fit all
❌ Binary pass/fail - Use confidence scores

## Confidence Scoring

```python
def output_confidence_score(output, context=None):
    """Return 0-100 confidence score for output quality."""
    score = 50  # Start neutral
    
    # Positive factors
    if len(output) > 100: score += 10
    if any(marker in output for marker in POSITIVE_INDICATORS): score += 20
    if '\n' in output: score += 5  # Multi-line is usually good
    if any(char.isdigit() for char in output): score += 5  # Numbers often indicate data
    
    # Negative factors  
    if len(output) < 10: score -= 20
    if any(err in output for err in NEGATIVE_INDICATORS): score -= 30
    if output.count('...') > 3: score -= 10  # Truncated?
    
    # Context bonuses
    if context:
        if context.get('type') == 'json' and assess_json_output(output):
            score += 15
        if all(req in output for req in context.get('must_contain', [])):
            score += 15
    
    return max(0, min(100, score))
```

## Continuous Improvement

1. **Log assessments**: Record (output, assessment, actual_result)
2. **Review failures**: Weekly review of false positives/negatives  
3. **Update patterns**: Add new indicators based on real data
4. **Adjust weights**: Tune confidence scoring based on accuracy
5. **Share learnings**: Update this template with discoveries