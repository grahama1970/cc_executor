# Acknowledgment and Progress Prompt Templates

## Overview

These templates solve the WebSocket timeout issue by ensuring Claude provides immediate acknowledgment and periodic progress updates, preventing the 10-second stall detection from triggering.

## Complexity-Based Templates

### Simple Tasks (< 30s expected)
No special acknowledgment needed - these complete quickly enough.

### Medium Tasks (30-180s expected)
```
What is [topic]?

Begin with a brief acknowledgment of this request, then provide your answer.

After providing your answer, evaluate it against these criteria:
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as "Initial Response:" and "Improved Response:" if needed.
Maximum self-improvements: 2
```

### Complex Tasks (> 180s expected)
```
What is [topic]?

Start by confirming what you understand from this request in one sentence, then work through it systematically.

Provide brief progress updates as you work through major sections:
- Analysis phase
- Solution design  
- Implementation details

After completing your response, evaluate it against these criteria:
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as "Initial Response:" and "Improved Response:" if needed.
Maximum self-improvements: 2
```

## Integration with Redis Timing

### WebSocket Message Structure
```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "command": "claude -p \"[prompt]\" --dangerously-skip-permissions --allowedTools none",
    "expected_complexity": "medium",  // from Redis timing estimation
    "expected_duration": 120,         // seconds from Redis history
    "require_acknowledgment": true,   // for medium/complex tasks
    "progress_interval": 30           // seconds between progress updates
  },
  "id": 1
}
```

### Example Prompts with Acknowledgment

#### Example 1: Todo Architecture (Complex)
```
What is the architecture for a todo app with database schema, REST API, and frontend overview?

I'll design this todo app architecture systematically.

First, let me outline the main components:
- Database layer with schema design
- REST API endpoints and structure
- Frontend architecture overview

Now working through each section...

[Database Schema]
...

[REST API Design] 
...

[Frontend Architecture]
...

After completing this design, evaluating against criteria:
1. All three layers are clearly defined
2. Relationships between components are explained
3. Technology choices are justified

The response satisfies all criteria.
```

#### Example 2: Code Refactoring (Medium)
```
What is an improved version of this function: def double_positives(data): return [x*2 for x in data if x > 0]?

Acknowledging: I'll analyze and improve this function that doubles positive numbers.

[Immediate analysis and improved code...]

Evaluating against criteria:
1. Code is more readable
2. Performance considerations addressed
3. Edge cases handled

All criteria met.
```

## Implementation in Stress Test

### Updated Prompt Generator
```python
def create_acknowledged_prompt(base_request, criteria, complexity="medium", max_iterations=2):
    """
    Create a prompt with acknowledgment pattern based on complexity
    """
    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    
    if complexity == "simple":
        # No acknowledgment needed for simple tasks
        return create_self_reflecting_prompt(base_request, criteria, max_iterations)
    
    elif complexity == "medium":
        prompt = f"""{base_request}

Begin with a brief acknowledgment of this request, then provide your answer.

After providing your answer, evaluate it against these criteria:
{criteria_text}

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as "Initial Response:" and "Improved Response:" if needed.
Maximum self-improvements: {max_iterations}"""

    else:  # complex
        prompt = f"""{base_request}

Start by confirming what you understand from this request in one sentence, then work through it systematically.

Provide brief progress updates as you work through major sections.

After completing your response, evaluate it against these criteria:
{criteria_text}

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as "Initial Response:" and "Improved Response:" if needed.
Maximum self-improvements: {max_iterations}"""
    
    return prompt
```

### WebSocket Handler Enhancement
```python
async def handle_acknowledged_execution(self, command, expected_duration):
    """Handle execution with acknowledgment detection"""
    
    last_output_time = time.time()
    acknowledgment_received = False
    progress_updates = []
    
    async for output in self.stream_process_output(command):
        current_time = time.time()
        
        # Detect acknowledgment in first 5 seconds
        if not acknowledgment_received and current_time - start_time < 5:
            if any(pattern in output.lower() for pattern in [
                "acknowledging", "i'll", "let me", "working through",
                "systematically", "i understand", "confirming"
            ]):
                acknowledgment_received = True
                await self.send_notification("acknowledgment_received", {
                    "timestamp": current_time,
                    "preview": output[:100]
                })
        
        # Detect progress updates
        if any(pattern in output for pattern in [
            "Phase", "Section", "Step", "Now working", "Moving to",
            "[Database", "[API", "[Frontend"  # Section markers
        ]):
            progress_updates.append({
                "timestamp": current_time,
                "update": output[:200]
            })
            await self.send_notification("progress_update", {
                "count": len(progress_updates),
                "latest": output[:200]
            })
        
        last_output_time = current_time
        
        # No stall if we're getting output
        yield output
```

## Benefits

1. **Immediate Feedback**: User sees Claude is working within 2-5 seconds
2. **Progress Visibility**: Updates show Claude is making progress
3. **No False Timeouts**: Continuous output prevents stall detection
4. **Better UX**: Users understand what's happening during long operations
5. **Redis Integration**: Complexity estimation informs acknowledgment requirements

## Testing

### Test Acknowledgment Patterns
```bash
# Test medium complexity with acknowledgment
claude -p "What is an improved version of this function: def sum(a,b): return a+b?

Begin with a brief acknowledgment of this request, then provide your answer."

# Test complex with progress updates  
claude -p "What is the architecture for a microservices system?

Start by confirming what you understand, then work through it systematically with progress updates."
```

### Verify No Timeouts
1. Run stress test with acknowledged prompts
2. Monitor for "No activity for 10s" messages
3. Check acknowledgment detection in logs
4. Verify progress update notifications