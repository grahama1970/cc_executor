# Timeout Recovery and Re-Prompting Strategies

## The Last Line of Defense

When Claude instances timeout or fail to respond properly, we need built-in recovery mechanisms that work **within the prompt itself**.

## Strategy 1: Progressive Simplification

If a prompt times out, automatically simplify it:

```python
def create_timeout_recovery_prompt(original_request, attempt_number=1):
    """
    Create progressively simpler prompts for timeout recovery
    """
    if attempt_number == 1:
        # First attempt - full request
        return original_request
    
    elif attempt_number == 2:
        # Second attempt - simplified with acknowledgment
        return f"""SIMPLIFIED REQUEST (Previous attempt timed out):
        
{original_request.split('.')[0]}.

Please:
1. Acknowledge receipt immediately with "Processing..."
2. Provide a concise answer (under 200 words)
3. Focus on the core request only"""
    
    elif attempt_number == 3:
        # Third attempt - bare minimum
        return f"""URGENT - MINIMAL RESPONSE NEEDED:
        
{original_request[:100]}...

Reply with just the essential answer in 1-2 sentences."""
```

## Strategy 2: Built-in Timeout Awareness

Include timeout handling directly in prompts:

```bash
claude -p "What is a Python implementation of quicksort?

IMPORTANT: If you're taking too long to respond:
1. First output: 'Working on it...' 
2. Then provide a basic version
3. Note 'Full version available on request' if needed

Time limit awareness: Respond within 30 seconds or simplify."
```

## Strategy 3: Checkpoint-Based Responses

For complex requests, build in checkpoints:

```python
checkpoint_prompt = """What is the architecture for a distributed system?

Please respond using this checkpoint structure:
- [0-5 seconds] Acknowledge: "Designing distributed system architecture..."
- [5-15 seconds] Provide core components list
- [15-30 seconds] Add basic descriptions
- [30+ seconds] Include detailed explanations if time permits

If you sense you're running out of time, output what you have so far with '[PARTIAL]' marker."""
```

## Strategy 4: Self-Interrupting Patterns

Teach Claude to self-interrupt before timeout:

```python
self_interrupt_prompt = """Create a comprehensive Python web scraping script.

TIMEOUT PREVENTION:
- If your response will be long, break it into parts
- After every 10 lines of code, add: "Continuing..."
- If approaching complexity limit, write: "[TRUNCATED - Key parts shown]"
- Priority order: imports → main function → error handling → extras

Start with acknowledgment: "Building web scraper...""""
```

## Implementation in WebSocket Handler

```python
class TimeoutRecoveryHandler:
    def __init__(self, websocket_handler):
        self.ws = websocket_handler
        self.timeout_strategies = {
            30: "simplified",
            60: "checkpoint",
            90: "progressive"
        }
    
    async def execute_with_recovery(self, prompt, timeout=90):
        """Execute prompt with automatic recovery on timeout"""
        attempt = 1
        original_prompt = prompt
        
        while attempt <= 3:
            try:
                # Add timeout awareness to prompt
                timeout_aware_prompt = self._add_timeout_awareness(
                    prompt, timeout, attempt
                )
                
                # Execute with increasing timeouts
                current_timeout = timeout * attempt
                result = await self.ws.execute(
                    timeout_aware_prompt, 
                    timeout=current_timeout
                )
                
                if result['success']:
                    return result
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt} timed out")
                # Simplify prompt for next attempt
                prompt = self._simplify_prompt(original_prompt, attempt)
                attempt += 1
        
        return {'success': False, 'reason': 'All recovery attempts failed'}
    
    def _add_timeout_awareness(self, prompt, timeout, attempt):
        """Add timeout awareness to prompt"""
        if attempt == 1:
            return f"""{prompt}
            
Note: You have approximately {timeout} seconds. 
If complex, prioritize core elements first."""
        else:
            return f"""RECOVERY ATTEMPT {attempt} (Previous timeout):

{prompt[:200]}...

CRITICAL: Respond immediately with simplified answer."""
    
    def _simplify_prompt(self, prompt, attempt):
        """Progressive simplification"""
        if attempt == 2:
            # Extract key question
            lines = prompt.split('\n')
            key_line = next((l for l in lines if '?' in l), lines[0])
            return f"SIMPLIFIED: {key_line}\n\nProvide brief, direct answer."
        else:
            # Extreme simplification
            words = prompt.split()[:10]
            return f"URGENT: {' '.join(words)}... [Yes/No/Brief answer only]"
```

## Strategy 5: Stall Detection Override

Build stall detection override into prompts:

```python
stall_override_prompt = """What is async/await in Python?

STALL PREVENTION PROTOCOL:
Every 10 seconds, output one of these status markers:
- "ANALYZING: Understanding async/await patterns..."
- "BUILDING: Creating explanation structure..."  
- "WRITING: Composing detailed response..."
- "FINALIZING: Adding examples..."

This prevents false stall detection. Begin with first marker immediately."""
```

## Integration with Stress Tests

Update stress test prompts to include recovery:

```json
{
  "id": "complex_with_recovery",
  "natural_language_request": "Explain microservices architecture.\\n\\nTIMEOUT RECOVERY:\\nIf running long, output 'WORKING: [component]' every 15 seconds\\nIf timeout approaching, conclude with '[MORE AVAILABLE]'\\n\\nBegin with: 'Starting microservices explanation...'",
  "verification": {
    "expected_patterns": ["WORKING", "microservices", "Starting"],
    "timeout": 180,
    "recovery_enabled": true
  }
}
```

## Monitoring Recovery Success

Track recovery metrics:

```python
class RecoveryMetrics:
    def __init__(self):
        self.attempts = []
    
    def log_attempt(self, prompt_id, attempt_num, success, strategy):
        self.attempts.append({
            'prompt_id': prompt_id,
            'attempt': attempt_num,
            'success': success,
            'strategy': strategy,
            'timestamp': time.time()
        })
    
    def get_recovery_rate(self):
        """Calculate how often recovery succeeds"""
        by_prompt = {}
        for attempt in self.attempts:
            pid = attempt['prompt_id']
            if pid not in by_prompt:
                by_prompt[pid] = []
            by_prompt[pid].append(attempt)
        
        recovered = sum(
            1 for attempts in by_prompt.values()
            if any(a['success'] for a in attempts[1:])
        )
        
        return recovered / len(by_prompt) if by_prompt else 0
```

## Best Practices

1. **Immediate Acknowledgment**: Always start with a status message
2. **Progressive Complexity**: Build answers incrementally
3. **Time Awareness**: Include time estimates in prompts
4. **Graceful Degradation**: Have fallback responses ready
5. **Clear Markers**: Use consistent markers for parsing

## Example: Ultimate Recovery Prompt

```python
ultimate_recovery_template = """
{request}

RESPONSE PROTOCOL:
1. [0-2s] Output: "PROCESSING: {task_summary}"
2. [2-10s] Provide core answer (most important points)
3. [10-30s] Add supporting details
4. [30s+] Include examples/code if time allows

TIMEOUT RECOVERY:
- If you sense timeout approaching: Output "[PARTIAL RESPONSE]" and summarize
- Use "..." to indicate where you would expand given more time
- Priority: Correctness > Completeness

STALL PREVENTION:
- Every 15s output: "CONTINUING: [current section]"
- This maintains connection and prevents false stall detection

Begin immediately with step 1."""
```

This approach ensures that even if timeouts occur, we get:
1. Immediate acknowledgment (prevents early timeout)
2. Core information first (useful even if truncated)
3. Clear markers for parsing partial responses
4. Built-in recovery without external retry logic