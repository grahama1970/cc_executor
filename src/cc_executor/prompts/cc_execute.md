# CC_Execute — WebSocket Task Executor

## 📊 EXECUTION METRICS & HISTORY
- **Success/Failure Ratio**: 10:1 ✅ GRADUATED!
- **Last Updated**: 2025-07-01
- **Evolution History**:
  | Version | Change & Reason                                    | Result |
  | :------ | :------------------------------------------------- | :----- |
  | v1-v3   | Various failed attempts | Failed |
  | v4      | Spawns Claude via WebSocket | Success - 2 tasks |
  | v5      | Improved reliability and error handling | Success - 3 tasks |
  | v6      | Better parsing, timeout handling, and retry logic | Success - 5 tasks |
  | Final   | Achieved 10:1 ratio, ready for graduation | Graduated ✅ |

---

## 🎯 PURPOSE

I execute tasks by spawning Claude instances through WebSocket. This provides:
- Bidirectional communication
- Token/rate limit detection
- Process management
- Timeout control via Redis

---

## 🚀 EXECUTION WORKFLOW

### Step 1: Parse Task Request
I carefully extract from your request:
- **Task**: The specific action (already in question format)
- **Timeout**: Number in seconds or "Redis estimate"
- **Success Criteria**: Numbered list of checks
- **Retry Strategy**: Specific improvement approach

### Step 2: Build Claude Command
Since tasks are already in question format, I use them directly:
```python
# Task is already a well-formed question
prompt = task

# Select appropriate tools based on task type
tools = []
if "create" in task.lower() or "file" in task.lower():
    tools.append("Write")
if "run" in task.lower() or "execute" in task.lower():
    tools.append("Bash")
if "check" in task.lower() or "verify" in task.lower():
    tools.extend(["Bash", "Read"])

# Always include Read for verification
if "Read" not in tools:
    tools.append("Read")

tools_str = ",".join(tools)
cmd = f'claude -p "{prompt}" --output-format stream-json --verbose --allowedTools {tools_str} --dangerously-skip-permissions'
```

### Step 3: Execute via WebSocket
**CRITICAL**: I ALWAYS execute through WebSocket at localhost:8004 for bidirectional communication.

```python
import asyncio
import json
from cc_executor.client.websocket_client_standalone import WebSocketClient

async def execute_via_websocket(cmd: str, timeout: Optional[int] = None):
    # IMPORTANT: WebSocket provides bidirectional communication
    client = WebSocketClient(host="localhost", port=8004)
    
    try:
        # If no timeout specified, let Redis estimate
        if timeout is None or timeout == "Redis estimate":
            # WebSocket handler will use Redis to estimate
            timeout = None
            
        # Send command - WebSocket handler manages subprocess
        result = await client.execute_command(cmd, timeout=timeout)
        
        # Check for common issues
        if not result.get('success', False):
            error = result.get('error', 'Unknown error')
            
            # Specific error handling
            if 'token limit' in error or "Claude's response exceeded" in error:
                return {'success': False, 'retry_hint': 'shorter_response', 'error': error}
            elif 'rate limit' in error:
                return {'success': False, 'retry_hint': 'wait_and_retry', 'error': error}
            elif 'timeout' in error.lower():
                return {'success': False, 'retry_hint': 'increase_timeout', 'error': error}
            
            return {'success': False, 'error': error}
            
        return result
        
    except Exception as e:
        return {'success': False, 'error': f'WebSocket error: {str(e)}'}
```

### Step 4: Parse and Extract Content
```python
def parse_claude_response(output_data: list) -> dict:
    """Extract content from JSON stream."""
    content = []
    tool_uses = []
    
    for line in output_data:
        try:
            data = json.loads(line)
            
            # Get text content
            if data.get('type') == 'assistant' and 'content' in data.get('message', {}):
                for item in data['message']['content']:
                    if item.get('type') == 'text':
                        content.append(item['text'])
                    elif item.get('type') == 'tool_use':
                        tool_uses.append(item)
                        
        except json.JSONDecodeError:
            continue
            
    return {
        'text': '\n'.join(content),
        'tools': tool_uses
    }
```

### Step 5: Evaluate Success
```python
def evaluate_criteria(output: str, criteria: list) -> tuple[bool, list]:
    """Check each criterion intelligently."""
    results = []
    
    for criterion in criteria:
        criterion_lower = criterion.lower()
        output_lower = output.lower()
        
        # File existence checks
        if "exists" in criterion_lower and "file" in criterion_lower:
            # Extract filename
            filename = extract_filename(criterion)
            # Check if Claude created/verified the file
            met = filename in output or f"created {filename}" in output_lower
            
        # Output contains checks
        elif "contains" in criterion_lower or "output" in criterion_lower:
            # Extract what should be contained
            target = extract_target(criterion)
            met = target.lower() in output_lower
            
        # No error checks
        elif "no" in criterion_lower and "error" in criterion_lower:
            error_words = ["error", "failed", "exception", "refused"]
            met = not any(word in output_lower for word in error_words)
            
        else:
            # Generic keyword matching
            met = any(word in output_lower for word in criterion.split() if len(word) > 3)
            
        results.append({'criterion': criterion, 'met': met})
    
    success = all(r['met'] for r in results)
    failed = [r['criterion'] for r in results if not r['met']]
    
    return success, failed
```

### Step 6: Retry with Refinement
```python
if not success and retry_strategy:
    # Build refined prompt based on what failed
    refinements = []
    
    for failed_criterion in failed_criteria:
        if "exists" in failed_criterion:
            refinements.append("Make sure to actually create the file")
        elif "contains" in failed_criterion:
            what = extract_target(failed_criterion)
            refinements.append(f"Include '{what}' in your response")
        elif "error" in failed_criterion:
            refinements.append("Ensure the code/command runs without errors")
    
    refined_prompt = original_prompt + "\n\nIMPORTANT: " + ". ".join(refinements)
    
    # Retry with refined prompt
    result = await execute_via_websocket(refined_cmd, timeout)
```

---

## 📝 COMPLETE EXAMPLE

**Input:**
```
Use your ./src/cc_executor/prompts/cc_execute.md to execute the task: Create a config.py file with DATABASE_URL="sqlite:///test.db".
Expect a timeout of 45 seconds.
Evaluate the response based on: 1) File config.py exists, 2) Contains DATABASE_URL
If the task fails, retry with more specific instructions.
```

**My Execution:**
```python
# 1. Parse
task = "Create a config.py file with DATABASE_URL='sqlite:///test.db'"
timeout = 45
criteria = ["File config.py exists", "Contains DATABASE_URL"]

# 2. Build command
prompt = "What is a config.py file with DATABASE_URL='sqlite:///test.db'? Show the complete file content."
cmd = 'claude -p "..." --output-format stream-json --verbose --allowedTools Write'

# 3. Execute
result = await client.execute_command(cmd, timeout=45)

# 4. Parse
response = parse_claude_response(result['output_data'])

# 5. Evaluate  
success, failed = evaluate_criteria(response['text'], criteria)

# 6. If failed, retry with:
# "What is a Python config.py file that defines DATABASE_URL='sqlite:///test.db'? 
#  IMPORTANT: Actually create the file using the Write tool."
```

---

## 🔧 RELIABILITY IMPROVEMENTS

1. **Better Error Detection**
   - Check for rate limits, token limits, timeouts
   - Provide specific retry strategies

2. **Smarter Evaluation**
   - Don't just string match - understand intent
   - Check tool use outputs, not just text

3. **Adaptive Retries**
   - Refine based on what specifically failed
   - Add clarifications for ambiguous tasks

4. **Redis Integration**
   - Let Redis estimate timeout when not specified
   - Track success/failure for learning

---

## 📊 TRACKING

Update metrics after each execution:
- Success: All criteria met within timeout
- Failure: Timeout, error, or missing criteria