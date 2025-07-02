# Claude Code Prompt Rules and Best Practices

## Overview

This document contains essential rules and advice for crafting prompts that work reliably with Claude CLI, based on extensive testing and debugging experience.

## Critical Startup Overhead Warning

**⚠️ IMPORTANT**: Claude CLI has significant startup overhead (30-60 seconds). This is NOT the model thinking time - it's the CLI initialization. Plan timeouts accordingly.

## Critical Rules

### 1. ALWAYS Use `--output-format stream-json` for Non-Interactive Usage

**⚠️ CRITICAL**: When using Claude CLI programmatically (WebSocket handlers, subprocess calls, automation):

```bash
# ❌ WRONG - Will cause buffer overflows on large outputs
claude -p "Generate a 5000 word essay..."

# ✅ CORRECT - Prevents buffer overflow (but see warning below)
claude -p "Generate a 5000 word essay..." --output-format stream-json
```

**Why This Matters:**
- Without JSON streaming: Large outputs create single massive text blocks that overflow subprocess buffers (typically 64KB)
- With JSON streaming: Output is broken into small JSON events that won't overflow buffers
- Prevents deadlocks when output exceeds buffer size

**⚠️ CRITICAL LIMITATION - No Token-by-Token Streaming**:
Despite the name, `--output-format stream-json` does NOT provide real-time token streaming:
- You get only 3 events: init, complete message, result
- The entire response arrives at once after Claude finishes thinking
- This means 30+ second delays for complex prompts are EXPECTED
- WebSockets cannot fix this - it's a Claude CLI limitation
- Only text mode supports true streaming, JSON mode does not

**Always include these flags for programmatic usage:**
```bash
claude -p "Your prompt" \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --allowedTools none
```

### 2. Use Question Format, Not Commands

**❌ AVOID Imperative Commands:**
```bash
# These patterns may hang or timeout:
claude -p "Write a Python function to calculate factorial"
claude -p "Create a web scraper in Python"
claude -p "Generate 20 haikus about programming"
claude -p "Find me a recipe for chicken curry"
claude -p "Calculate the sum of these numbers: 1,2,3,4,5"
```

**✅ USE Question Format:**
```bash
# These patterns work reliably:
claude -p "What is a Python function that calculates factorial?"
claude -p "What is a Python web scraper example?"
claude -p "What are 20 haikus about programming?"
claude -p "What is a good chicken curry recipe?"
claude -p "What is the sum of 1,2,3,4,5?"
```

### 3. Test Every Prompt Manually First

Before adding ANY prompt to automated tests or scripts:

```bash
# Test with timeout to catch hangs (with JSON streaming for programmatic use)
timeout 180 claude -p "Your prompt here" \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --allowedTools none

# If it times out, rephrase as a question
timeout 180 claude -p "What is [rephrased request]?" \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --allowedTools none

# Check the response quality
# - Should be > 10 words for explanation prompts
# - Should not contain "Execution error"
# - Should include expected patterns/concepts
```

**Testing Checklist:**
- [ ] Prompt returns within timeout (180s)
- [ ] Response is appropriately detailed (not just "55" or one word)
- [ ] No execution errors or file creation attempts
- [ ] Contains expected keywords/patterns
- [ ] Clear and unambiguous response

### 4. Add Safety Flags

Always include these flags for reliability:
```bash
# For interactive/terminal use:
claude -p "What is 2 + 2?" \
  --dangerously-skip-permissions \
  --allowedTools none

# For programmatic/non-interactive use:
claude -p "What is 2 + 2?" \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --allowedTools none
```

## Prompt Patterns That Work

### Simple Math
```bash
claude -p "What is 25 + 37?"
claude -p "What is the square root of 144?"
claude -p "What is 15% of 200?"
```

### Code Generation
```bash
claude -p "What is a Python function that sorts a list?"
claude -p "What is an example of recursion in Python?"
claude -p "What is a JavaScript async/await example?"
```

### Information Queries
```bash
claude -p "What is the capital of France?"
claude -p "What is machine learning?"
claude -p "What are the benefits of unit testing?"
```

### Creative Tasks (Rephrased)
```bash
claude -p "What is a haiku about coding?"
claude -p "What is a good name for a task management app?"
claude -p "What are some ideas for a Python project?"
```

## System Load Considerations

### Check System Load Before Running
```bash
# Get current load
uptime | awk -F'load average:' '{print $2}' | awk '{print $1}'

# If load > 14, expect 3x slower performance
# Consider postponing non-critical prompts
```

### Timeout Recommendations
- **Normal load (< 5)**: 30-60 second timeout
- **Moderate load (5-14)**: 60-120 second timeout  
- **High load (> 14)**: 180+ second timeout (3x normal)

## Structured Prompts for Testing

### Include Metadata Tags
```bash
# For test categorization and Redis timing
claude -p "[category:test][complexity:simple][type:math] What is 2 + 2?"
```

### Include UUID for Verification
```bash
UUID=$(uuidgen)
claude -p "What is 2 + 2? Please include UUID: $UUID in your response"
# Then verify UUID appears in output
```

## Common Pitfalls to Avoid

### 1. Long Multi-Step Prompts
**❌ AVOID:**
```bash
claude -p "First analyze this code, then refactor it, then write tests, then optimize performance"
```

**✅ BETTER:**
```bash
claude -p "What is an analysis of this code's structure?"
# Then in separate calls:
claude -p "What is a refactored version of this code?"
claude -p "What are unit tests for this code?"
```

### 2. Ambiguous Requests
**❌ AVOID:**
```bash
claude -p "Explain this" # No context
claude -p "Fix the bug" # No code provided
```

**✅ BETTER:**
```bash
claude -p "What is the purpose of this Python decorator: @cache?"
claude -p "What is the bug in this code: [provide code]?"
```

### 3. Assuming Complex Features Work
**❌ AVOID:**
```bash
claude -p "Use the MCP tools to search GitHub for Python examples"
# MCP tools may not be available or may cause hangs
```

**✅ BETTER:**
```bash
claude -p "What are some Python code examples for web scraping?"
```

## Performance Optimization

### 1. Batch Similar Prompts
If running multiple prompts, group by complexity:
```bash
# Run simple prompts first (likely to succeed quickly)
for prompt in "What is 1+1?" "What is 2+2?" "What is 3+3?"; do
    claude -p "$prompt" --allowedTools none
done

# Then run complex prompts
claude -p "What is a Python web server example?" --allowedTools none
```

### 2. Use Redis for Timeout Prediction
```bash
# Store execution times for similar prompts
# Use BM25 search to predict optimal timeouts
source redis_timing.md
TIMEOUT=$(get_bm25_timeout "python function sort" 60)
```

### 3. Monitor Resource Usage
```bash
# Check if Ollama or other AI tools are consuming resources
nvidia-smi  # GPU usage
htop        # CPU/Memory usage
```

## Emergency Procedures

### If Claude CLI Hangs
1. Try `Ctrl+C` to interrupt
2. If unresponsive, kill the process:
   ```bash
   pkill -f "claude -p"
   ```
3. Check system load - high load may cause legitimate slowness
4. Restart terminal if needed

### If All Prompts Fail
1. Check API key: `echo $ANTHROPIC_API_KEY`
2. Test simplest possible prompt: `claude -p "Hi"`
3. Check Claude Code logs: `~/.claude/logs/`
4. Restart Claude Code server if running

## Testing Checklist

Before deploying any prompt in production:

- [ ] Test manually with timeout
- [ ] Verify it works under normal load
- [ ] Rephrase as question if it's a command
- [ ] Add appropriate timeout based on complexity
- [ ] Include verification markers (UUID)
- [ ] Document expected output patterns
- [ ] Test under high load conditions
- [ ] Add to Redis timing database

## Problematic Patterns to Avoid

### 1. Interactive Prompts
**❌ NEVER USE:**
- "Ask me about..."
- "Guide me through..."
- "Help me write..." (when it implies back-and-forth)

### 2. Excessive Length Requests
**❌ AVOID:**
- "What is a 5000 word story..."
- "What is a 10,000 word guide..."
- "What are 100 different Python scripts..."

**✅ SAFE ALTERNATIVES:**
- "What is a 500-word outline..."
- "What is a 1000-word checklist..."
- "What is a list of 10 Python script ideas..."

### 3. Step-by-Step or Iterative Requests
**❌ PROBLEMATIC:**
- "What is a step-by-step guide..."
- "Improve this code 10 times..."
- "First do X, then Y, then Z..."

**✅ BETTER:**
- "What is an overview of..."
- "What is the best version of this code..."
- "What is a solution that includes X, Y, and Z..."

### 4. Vague Continuations
**❌ AVOID:**
- "[... continue with 95 more examples]"
- "and so on..."
- "etc..."

**✅ BE SPECIFIC:**
- List exact number of items needed
- Provide complete context

## Safe Prompt Formula

The safest prompts follow this pattern:

```
What is [specific thing] [with optional constraints]?
```

Examples:
- "What is a Python function that sorts a list?"
- "What is a 500-word explanation of recursion?"
- "What is the answer to these 5 math problems: 1+1, 2+2, 3+3, 4+4, 5+5?"

## Timeout Guidelines by Prompt Type

**CRITICAL UPDATE**: Claude CLI has significant startup overhead. All timeouts must account for this.

| Prompt Type | Example | Minimum Timeout | Recommended Timeout |
|------------|---------|-----------------|---------------------|
| Simple calculation | "What is 2+2?" | 60s | 120s |
| Code snippet | "What is a Python function for X?" | 90s | 180s |
| Short explanation | "What is recursion?" | 90s | 180s |
| Medium content | "What is a 500-word outline?" | 120s | 240s |
| Complex code | "What is a todo app architecture?" | 180s | 300s |
| Long content | "What is a 1000-word guide?" | 240s | 600s |

**Notes**: 
- Multiply by 3 if system load > 14
- Claude CLI startup can take 30-60 seconds alone
- First call after idle is always slower
- Consider using WebSocket handler for better performance

## Learned from Failures

These patterns were discovered through timeouts and errors:

### 🔴 Failed → ✅ Fixed: Execution Confusion
```bash
# FAILED: "Execution error" 
claude -p "What is recursion in programming with one simple Python example?"

# FIXED: Clarified we want explanation
claude -p "What is the concept of recursion in programming? Please provide an explanation (not code execution) that includes: 1) A definition in 2-3 sentences, 2) How it works conceptually, 3) An example in Python with comments."
```
**Learning**: Ambiguous phrasing like "with example" can trigger code execution attempts.

### 🔴 Failed → ✅ Fixed: Too Terse Response
```bash
# FAILED: Response was just "55"
claude -p "What is the 10th Fibonacci number?"

# FIXED: Asked for explanation too
claude -p "What is the 10th Fibonacci number and how is it calculated? Please show the number and explain the Fibonacci sequence briefly."
```
**Learning**: Ultra-specific questions get ultra-specific answers. Ask for context!

### 🔴 Failed → ✅ Fixed: Command Timeout
```bash
# FAILED: Timeout after 180s
claude -p "Write a Python function to calculate factorial"

# FIXED: Rephrased as question
claude -p "What is a Python function that calculates factorial?"
```
**Learning**: Commands starting with verbs like "Write", "Create", "Generate" often hang.

### 🔴 Failed → ✅ Fixed: Missing Structure
```bash
# FAILED: Rambling response missing key parts
claude -p "What is a todo app architecture?"

# FIXED: Specified structure
claude -p "What is the architecture for a todo app? Include: 1) Database schema, 2) REST API endpoints, 3) Frontend components overview."
```
**Learning**: Complex topics need structured prompts to get organized responses.

## Verified Working Examples

Based on extensive testing, these prompts have been verified to work reliably:

### ✅ Simple Tasks (8-20s typical execution)
- "What is 2+2?" (8.0s)
- "What is the result of these calculations: 15+27, 83-46, 12*9, 144/12, 2^8?" (5.0s)
- "What is a haiku about programming?" (4.3s)
- "What is a Python function to reverse a string?" (4.5s)
- "What is the 10th Fibonacci number?" (19.1s)

### ✅ Medium Complexity (15-30s typical execution)
- "What is a quick chicken and rice recipe that takes 30 minutes?" (20.7s)
- "What is recursion in programming with one simple Python example?" (15.1s)
- "What is Python code for 5 functions: area of circle, celsius to fahrenheit, prime check, string reverse, and factorial?" (23.8s)
- "What is a template for a daily standup update with sections for yesterday, today, and blockers?" (17.0s)

### ✅ Long-Form Content (45-100s typical execution)
- "What is a 500-word outline for a story about a programmer discovering sentient code?" (52.7s)
- "What is a 500-word checklist for Python best practices in production?" (47.0s)
- "What is the architecture for a todo app with database schema, REST API, and frontend overview?" (99.5s)
- "What is a production-ready hello world in Python with logging and error handling?" (59.6s)

## Real-World Performance Data

From our stress testing (100% success rate with proper timeouts):
- Startup overhead: 30-60 seconds (included in all timings)
- Simple prompts: 4-20 seconds total
- Medium prompts: 15-60 seconds total  
- Complex prompts: 45-100 seconds total
- Always add buffer for system load

## Avoiding Ambiguous Prompts

### Problem: Code Execution vs. Explanation
Claude may interpret ambiguous prompts as requests to execute code rather than explain concepts.

**❌ AMBIGUOUS:**
```bash
claude -p "What is recursion in programming with one simple Python example?"
# May result in: "Execution error" as Claude tries to run code
```

**✅ CLEAR:**
```bash
claude -p "What is the concept of recursion in programming? Please provide an explanation (not code execution) that includes: 1) A definition in 2-3 sentences, 2) How it works conceptually, 3) An example in Python with comments."
```

### Recovery Pattern for Unclear Responses

If a response is too short, has errors, or misses expected content:

1. **Initial Response Check**:
   - "Execution error" → Add "(not code execution)" 
   - Response < 10 words → Add "Please provide a comprehensive explanation"
   - Missing patterns → Add "Please include information about: [missing items]"

2. **Recovery Examples**:
   ```bash
   # If you get "55" for Fibonacci:
   claude -p "What is the 10th Fibonacci number and how is it calculated? Please show the number and explain the Fibonacci sequence briefly."
   
   # If you get execution errors:
   claude -p "[Original prompt] Please provide a detailed explanation with examples, not code execution."
   ```

### Self-Reflection Pattern (Recommended)

Build self-reflection directly into prompts to get better responses in a single call:

```bash
# Basic self-reflection template:
claude -p "[Your question here]

After providing your answer, evaluate it against these criteria:
1. [First criterion]
2. [Second criterion]
3. [Third criterion]

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as 'Initial Response:' and 'Improved Response:' if needed.
Maximum self-improvements: 2"
```

**Example with Self-Reflection:**
```bash
claude -p "What is recursion in programming?

After providing your answer, evaluate it against these criteria:
1. Clear definition in 2-3 sentences
2. Explanation of base case and recursive case
3. Simple Python example with comments
4. Step-by-step trace of how the recursion unfolds

If your response doesn't fully satisfy all criteria, provide an improved version.
Maximum self-improvements: 2"
```

**Benefits:**
- Higher quality first responses
- Fewer failed tests due to missing content
- Claude catches its own omissions
- Single API call instead of multiple retries

## Learning from Failures

### Timeouts and Errors are Valuable

**IMPORTANT**: Failures are learning opportunities! When a prompt times out or returns an error:

1. **Analyze the failure pattern**
   - Timeout → Prompt might be too complex or ambiguous
   - "Execution error" → Claude tried to run code instead of explaining
   - Short response → Prompt was too vague or minimal
   - Missing patterns → Prompt didn't specify what to include

2. **Amend and retry**
   ```bash
   # Original (fails):
   claude -p "What is recursion with example?"
   # → "Execution error"
   
   # Amended (succeeds):
   claude -p "What is recursion? Explain the concept and show a Python example with comments (not execution)."
   ```

3. **Document the learning**
   - Add the successful pattern to this document
   - Include both the failing and working versions
   - Explain why the change fixed the issue

### Continuous Improvement Process

```
1. Run prompt → Timeout/Error
2. Analyze failure mode
3. Amend prompt with clarification
4. Test amended version
5. If success → Document pattern here
6. If fail → Return to step 2
```

This iterative process builds a comprehensive knowledge base of what works!

## Understanding Claude CLI Streaming Limitations

**CRITICAL**: Claude CLI has fundamental limitations that WebSockets CANNOT fix:

### What "stream-json" Actually Does
- **Expected**: Token-by-token streaming as Claude generates text
- **Reality**: Only 3 JSON events total (init → complete message → result)
- **Impact**: 30+ second "stalls" are NORMAL for complex prompts

### Why WebSockets Don't Help Here
The WebSocket handler was designed to solve timeout issues through:
- Bidirectional communication
- Heartbeat/ping-pong to keep connections alive
- Progress updates during generation

**BUT**: If Claude CLI doesn't stream tokens, WebSockets can't forward what doesn't exist!

### Implications for Stress Tests
- Long prompts (5000 word essays) WILL stall for 30+ seconds
- This is NOT a bug in the WebSocket handler
- This is NOT a buffering issue
- This is Claude CLI working as designed (unfortunately)

### Workarounds
1. **Adjust expectations**: Accept that complex prompts take time
2. **Increase timeouts**: Use 300-600s for complex prompts
3. **Add progress indicators**: "Processing complex request..." messages
4. **Use simpler prompts**: Break complex requests into smaller parts

## Non-Interactive Usage (WebSockets, Subprocess, Automation)

**CRITICAL**: When using Claude CLI programmatically, you MUST include `--output-format stream-json`:

### Why Non-Interactive Usage is Different

1. **Buffer Overflow Prevention**:
   - Subprocess pipes have limited buffers (typically 64KB)
   - Large outputs without streaming cause deadlocks
   - JSON streaming breaks output into manageable chunks

2. **Progress Tracking**:
   - JSON events allow real-time progress monitoring
   - WebSocket handlers can send intermediate updates
   - Timeouts can be managed more intelligently

3. **Error Recovery**:
   - Structured JSON makes error detection reliable
   - Partial responses can be captured before timeouts
   - Recovery strategies can parse incomplete outputs

### Complete Non-Interactive Command Template

```bash
claude -p "Your prompt here" \
  --output-format stream-json \
  --dangerously-skip-permissions \
  --allowedTools none \
  --verbose  # Optional: for debugging
```

### Example: Handling Large Outputs

```python
# ❌ WRONG - Will deadlock on large outputs
proc = await asyncio.create_subprocess_exec(
    'claude', '-p', 'Generate a 5000 word essay...',
    stdout=asyncio.subprocess.PIPE
)
stdout, _ = await proc.communicate()  # Deadlock if output > 64KB!

# ✅ CORRECT - Streams JSON events
proc = await asyncio.create_subprocess_exec(
    'claude', '-p', 'Generate a 5000 word essay...',
    '--output-format', 'stream-json',
    stdout=asyncio.subprocess.PIPE
)
# Now can process streaming JSON events without buffer overflow
```

## Summary

The golden rule: **If you can't run it successfully yourself, it won't work in automation**. Always phrase requests as questions ("What is...?") rather than commands ("Write...", "Create...", "Generate..."). Keep requests focused, specific, and reasonable in scope. Monitor system load and adjust timeouts accordingly.

**Key Findings:**
- **ALWAYS use `--output-format stream-json` for non-interactive usage**
- Question format ("What is...?") is essential - commands will hang
- Be explicit about wanting explanations vs. code execution
- Specify the format you want (e.g., "include 3 parts", "explain briefly")
- Minimum timeout should be 120s to account for startup overhead
- Real execution times range from 4-100 seconds with proper prompts
- 100% success rate is NOT the goal - learning from failures is!
- Each timeout/error teaches us how to write better prompts
- Recovery mechanisms can automatically clarify ambiguous prompts
- Self-reflection patterns improve response quality in single calls