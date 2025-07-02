# Token-Aware Timeout Calculation

## Current Gap
The existing Redis timing system tracks execution times but doesn't factor in token count, which is a critical variable for accurate timeout estimation.

## Token-Based Timeout Formula

### Base Formula
```
timeout = base_time + (estimated_tokens * time_per_token) + complexity_buffer
```

### Components

1. **Base Time**: Overhead for Claude CLI startup (~30s)
2. **Token Estimation**: 
   - Input tokens from prompt
   - Expected output tokens based on task type
3. **Time Per Token**: ~50-100ms per token (varies by model)
4. **Complexity Buffer**: Additional time for reasoning

### Token Estimation Heuristics

```python
def estimate_tokens(prompt: str, task_type: Dict) -> Dict[str, int]:
    """Estimate input and output tokens for timeout calculation"""
    
    # Input tokens (rough estimation: ~0.75 tokens per character)
    input_tokens = len(prompt) * 0.75
    
    # Output token estimation based on task type
    output_estimates = {
        # Question type -> expected output tokens
        "yes_no": 50,              # Simple yes/no answers
        "calculation": 100,        # Math calculations
        "explanation": 500,        # Concept explanations
        "code_snippet": 300,       # Small code examples
        "code_generation": 1000,   # Full implementations
        "creative_writing": 2000,  # Stories, haikus
        "architecture": 1500,      # System designs
        "comprehensive": 3000,     # Detailed guides
        "list": 200,              # Simple lists
        "refactor": 800,          # Code refactoring
    }
    
    # Check for specific patterns that indicate length
    if "500-word" in prompt or "500 word" in prompt:
        output_tokens = 750  # ~1.5 tokens per word
    elif "1000-word" in prompt or "1000 word" in prompt:
        output_tokens = 1500
    elif "5000-word" in prompt or "5000 word" in prompt:
        output_tokens = 7500
    elif "10 haikus" in prompt:
        output_tokens = 400  # ~40 tokens per haiku
    elif "20 haikus" in prompt:
        output_tokens = 800
    elif "100 questions" in prompt:
        output_tokens = 2000  # ~20 tokens per Q&A
    elif "list of 10" in prompt:
        output_tokens = 300
    else:
        # Use task type heuristic
        output_tokens = output_estimates.get(
            task_type.get('question_type', 'general'),
            500  # default
        )
    
    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(input_tokens + output_tokens)
    }
```

### Enhanced Timeout Calculation

```python
async def calculate_token_aware_timeout(self, command: str, task_type: Dict) -> Dict:
    """Calculate timeout with token awareness"""
    
    # Get base timing from Redis history
    base_estimate = await self.estimate_complexity(command)
    
    # Estimate tokens
    token_estimate = estimate_tokens(command, task_type)
    
    # Model-specific token rates (tokens per second)
    token_rates = {
        "claude-3-5-sonnet": 50,     # ~50 tokens/second
        "claude-3-5-haiku": 100,     # Faster model
        "claude-3-opus": 30,         # Slower but more capable
        "default": 40                # Conservative default
    }
    
    # Detect model from command (if specified)
    model = "default"
    if "--model" in command:
        # Extract model from command
        import re
        model_match = re.search(r'--model\s+(\S+)', command)
        if model_match:
            model_name = model_match.group(1)
            for key in token_rates:
                if key in model_name:
                    model = key
                    break
    
    # Calculate token-based time
    tokens_per_second = token_rates[model]
    token_time = token_estimate["total_tokens"] / tokens_per_second
    
    # Claude CLI overhead
    cli_overhead = 30  # seconds
    
    # Complexity multipliers
    complexity_multipliers = {
        "simple": 1.2,   # 20% buffer
        "medium": 1.5,   # 50% buffer
        "complex": 2.0   # 100% buffer
    }
    
    complexity_mult = complexity_multipliers.get(
        task_type.get('complexity', 'medium'), 
        1.5
    )
    
    # Calculate final timeout
    calculated_timeout = (cli_overhead + token_time) * complexity_mult
    
    # Apply system load multiplier
    system_load = self.get_system_load()
    if system_load['cpu_load'] > 14.0:
        calculated_timeout *= 3.0
    
    # Compare with historical data
    historical_timeout = base_estimate.get('max_time', calculated_timeout)
    
    # Use the maximum of calculated and historical
    final_timeout = max(calculated_timeout, historical_timeout)
    
    # Apply bounds
    min_timeout = 60   # Never less than 1 minute
    max_timeout = 1800 # Never more than 30 minutes
    final_timeout = max(min_timeout, min(max_timeout, final_timeout))
    
    return {
        "timeout": int(final_timeout),
        "token_estimate": token_estimate,
        "token_time": token_time,
        "cli_overhead": cli_overhead,
        "complexity_multiplier": complexity_mult,
        "system_load_multiplier": 3.0 if system_load['cpu_load'] > 14.0 else 1.0,
        "historical_timeout": historical_timeout,
        "calculation_method": "token_aware",
        "model": model,
        "tokens_per_second": tokens_per_second
    }
```

## Integration Example

### Stress Test with Token-Aware Timeouts

```python
# In stress test execution
async def execute_test_with_smart_timeout(self, test):
    """Execute test with token-aware timeout"""
    
    # Get task classification
    task_type = self.timer.classify_command(test['natural_language_request'])
    
    # Calculate token-aware timeout
    timeout_info = await self.timer.calculate_token_aware_timeout(
        test['natural_language_request'],
        task_type
    )
    
    print(f"Token-aware timeout calculation:")
    print(f"  - Estimated tokens: {timeout_info['token_estimate']['total_tokens']}")
    print(f"  - Token time: {timeout_info['token_time']:.1f}s")
    print(f"  - CLI overhead: {timeout_info['cli_overhead']}s")
    print(f"  - Final timeout: {timeout_info['timeout']}s")
    
    # Use calculated timeout
    actual_timeout = timeout_info['timeout']
    
    # Execute with smart timeout
    result = await self.execute_with_timeout(test, actual_timeout)
```

## Example Calculations

### Example 1: Simple Math
```
Prompt: "What is 2+2?"
- Input tokens: ~10
- Output tokens: ~50 (simple calculation)
- Token time: 60/40 = 1.5s
- CLI overhead: 30s
- Total: (30 + 1.5) * 1.2 = ~38s timeout
```

### Example 2: 20 Haikus
```
Prompt: "What is a collection of 20 haikus about programming?"
- Input tokens: ~40
- Output tokens: ~800 (20 haikus)
- Token time: 840/40 = 21s
- CLI overhead: 30s
- Total: (30 + 21) * 1.5 = ~77s timeout
```

### Example 3: 5000-word Story
```
Prompt: "What is a 5000-word story about AI?"
- Input tokens: ~30
- Output tokens: ~7500
- Token time: 7530/40 = 188s
- CLI overhead: 30s
- Total: (30 + 188) * 2.0 = ~436s timeout
```

## Benefits

1. **Accurate Timeouts**: Based on actual work required
2. **No Premature Timeouts**: Long responses get adequate time
3. **Efficient Resource Use**: Short tasks don't wait unnecessarily
4. **Model-Aware**: Different speeds for different Claude models
5. **Load-Aware**: Adjusts for system load automatically

## Testing Token Estimation

```python
# Test various prompts
test_prompts = [
    "What is 2+2?",
    "What is a 500-word explanation of recursion?",
    "What is a collection of 20 haikus?",
    "What is a comprehensive 5000-word guide to Python?"
]

for prompt in test_prompts:
    task_type = timer.classify_command(prompt)
    tokens = estimate_tokens(prompt, task_type)
    timeout = await timer.calculate_token_aware_timeout(prompt, task_type)
    
    print(f"\nPrompt: {prompt[:50]}...")
    print(f"Tokens: {tokens}")
    print(f"Timeout: {timeout['timeout']}s")
```