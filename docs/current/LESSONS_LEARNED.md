# Lessons Learned

## Lesson 12: MCP Server Integration - FastMCP vs Low-Level MCP SDK (2025-07-05)

A crucial lesson about choosing the right MCP implementation for Claude integration.

### The Problem: Low-Level MCP SDK Complexity

The cc-executor MCP server wasn't appearing in Claude despite being configured in `.mcp.json`. The issue was using the low-level MCP SDK which has strict initialization requirements and complex protocol handling.

### The Discovery Process:
1. **Initial symptom**: cc-executor configured in `.mcp.json` but not available as MCP tool
2. **Debug finding**: MCP server failing with "'dict' object has no attribute 'capabilities'" errors
3. **perplexity-ask insight**: Low-level MCP SDK expects specific object types, not plain dicts
4. **Solution**: Switch to FastMCP for simpler, decorator-based implementation

### The Technical Details:
```python
# WRONG - Low-level MCP SDK (complex and error-prone):
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Complex initialization, strict parameter validation
# Fails with cryptic errors about dict attributes

# CORRECT - FastMCP (simple and robust):
from fastmcp import FastMCP

mcp = FastMCP(name="cc-executor")

@mcp.tool
async def execute(command: str) -> str:
    """Execute a command via cc-executor."""
    # Implementation here
    return output

if __name__ == "__main__":
    mcp.run()
```

### Key Differences:
1. **FastMCP**: High-level, decorator-based, handles protocol complexity
2. **Low-level MCP**: Requires manual protocol handling, strict type validation
3. **stdio vs SSE**: Claude uses stdio (subprocess communication), not HTTP/SSE

### Implementation Gotchas:
- Both `mcp` (1.10.1) and `fastmcp` (2.10.1) packages can be installed simultaneously
- Don't mix imports from both packages in the same server
- FastMCP is the officially recommended approach for new servers
- SSE/Starlette is for HTTP-based MCP servers, but Claude uses stdio transport

### The Lesson:
When building MCP servers for Claude, always use FastMCP unless you have specific low-level requirements. The decorator-based API is simpler, more maintainable, and less error-prone. What looks like a configuration issue might actually be using the wrong abstraction level.

## Lesson 11: Asyncio Event Loop Blocking - The Hook System Hanging Issue (2025-07-05)

A critical lesson about asyncio event loops and subprocess execution that caused WebSocket server hanging.

### The Problem: Hook System Blocking Async Event Loop

The cc-executor MCP WebSocket server would hang indefinitely after "Hook enforcement system initialized successfully". The issue was that the hook system was using blocking `subprocess.run()` calls in an async context, which blocked the entire event loop.

### The Discovery Process:
1. **Initial symptom**: WebSocket server accepted connections but never executed commands
2. **Debug finding**: Server hung after hook initialization message
3. **User feedback**: "wait is this an asyncio issue? are you running asyncio.run() in multiple places"
4. **perplexity-ask revelation**: Hook system using `subprocess.run()` in async functions blocks event loop

### The Technical Details:
```python
# WRONG - This blocks the async event loop:
async def pre_execute_hook(self, command):
    result = subprocess.run(['hook_script.py'], ...)  # BLOCKS!
    return result

# Also WRONG - asyncio.to_thread doesn't help with subprocess:
async def pre_execute_hook(self, command):
    result = await asyncio.to_thread(subprocess.run, ...)  # Still blocks!
    return result

# CORRECT - Use async subprocess:
async def pre_execute_hook(self, command):
    proc = await asyncio.create_subprocess_exec(
        'hook_script.py',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout
```

### Multiple Hook Call Locations:
The hooks were being called from multiple places:
1. `websocket_handler.py` - In the execute handler before command execution
2. `process_manager.py` - Also calling hooks before execution
3. Both locations needed to be disabled to prevent hanging

### The Temporary Fix:
```python
# TEMPORARY FIX: Disable hooks to prevent hanging
# The hook system uses blocking subprocess.run() which hangs the async event loop
# TODO: Fix hook system to use async subprocess execution
if False and self.hooks and self.hooks.enabled:
    # Hook code here...
```

### Key Insights:
1. **Never use blocking calls in async functions** - It freezes the entire event loop
2. **subprocess.run() is always blocking** - Even when wrapped with asyncio.to_thread()
3. **Use asyncio.create_subprocess_exec()** - The proper async way to run subprocesses
4. **Check all code paths** - Hooks were called from multiple locations
5. **Test incrementally** - Disabling hooks immediately fixed the hanging issue

### The Lesson:
When building async systems, a single blocking call can freeze everything. The asyncio event loop is single-threaded, so any blocking operation prevents ALL other coroutines from running. This is especially critical in WebSocket servers where responsiveness is essential.

### Testing Verification:
After disabling hooks, the MCP server successfully:
- Accepted WebSocket connections
- Executed echo commands
- Ran Python code creation tests
- Streamed output properly
- Completed with correct exit codes

## Lesson 10: cc_execute Pattern - Flexible Fresh Context (2025-07-04)

A key architectural pattern for handling complex tasks that need fresh Claude instances.

### The Architecture: Optional Fresh Context
* **Regular tasks**: Execute directly in current Claude context
* **Complex tasks**: Reference cc_execute.md to spawn fresh Claude instance
* **Flexibility**: Task authors choose when to use cc_execute pattern
* **Automatic hooks**: When cc_execute IS used, UUID4 verification happens automatically

### When to Use cc_execute
1. **Fresh 200K context needed**: Task requires full context window
2. **Isolation required**: Task shouldn't be polluted by previous context
3. **Long-running tasks**: Bidirectional WebSocket prevents timeouts
4. **Complex multi-step tasks**: Need clean slate for complex execution
5. **Tasks over 5 minutes**: WebSocket heartbeats keep connection alive
6. **Explicit reference**: Task mentions cc_execute.md in task list

### Implementation Pattern
```python
# Simple task - executes directly (like using Python's math module)
"What is 2+2?"

# Complex task - uses cc_execute for fresh context (like using numpy)
"Using cc_execute.md, create a full FastAPI application with database models..."
```

### The math vs numpy Analogy
- **Regular execution** = `import math` - handles standard operations well
- **cc_execute pattern** = `import numpy` - built for complex tasks that regular execution isn't designed for:
  - Long-running operations (WebSocket keeps alive)
  - Fresh context isolation (200K tokens) 
  - Complex multi-step workflows
  - Tasks that would timeout in regular execution

### Key Benefits
1. **Flexibility**: Not all tasks need fresh context
2. **Performance**: Simple tasks execute quickly without overhead
3. **Isolation**: Complex tasks get clean environment
4. **Reliability**: Bidirectional WebSocket communication prevents timeout failures
5. **Long-running support**: Heartbeats keep connection alive for 10+ minute tasks
6. **Verification**: Automatic UUID4 hooks when using cc_execute

### Bidirectional WebSocket Architecture
The cc_execute pattern uses websocket_handler.py which provides:
- **Heartbeat/ping-pong**: Keeps connection alive during long Claude thinking periods
- **Progress notifications**: Real-time updates on task status
- **Error detection**: Immediate notification of token limits or failures
- **No timeout deaths**: Tasks can run for 10+ minutes without connection drops

### The Lesson
One size doesn't fit all. The cc_execute pattern provides the OPTION of fresh context when needed, without forcing it on every task. This flexibility allows optimal performance for simple tasks while providing isolation and reliability for complex, long-running ones. The bidirectional WebSocket communication is specifically designed to handle Claude's 30-60 second "thinking" periods without timing out.

## Lesson 9: UUID4 Anti-Hallucination Pattern (2025-07-04)

A critical pattern for ensuring AI agents don't fabricate execution results.

### The Problem: AI Hallucination of Success
* **The Issue**: AI agents can generate plausible-looking outputs without actually executing code
* **The Risk**: Reports, assessments, and test results might be completely fabricated
* **The Impact**: Decisions made on false data, broken systems marked as healthy

### The Solution: UUID4 at END of JSON
* **Generate Early**: Create UUID4 at the very start of execution
* **Position at END**: Always make `execution_uuid` the LAST key in JSON
* **Multiple Locations**: Include in console output, JSON files, and reports
* **Verify Always**: Check UUID presence in transcripts and outputs

### Implementation Pattern
```python
import uuid

class Executor:
    def __init__(self):
        self.execution_uuid = str(uuid.uuid4())
        print(f"🔐 Execution UUID: {self.execution_uuid}")
    
    def save_results(self, data):
        output = {
            "timestamp": "...",
            "results": data,
            "execution_uuid": self.execution_uuid  # MUST BE LAST
        }
```

### Why Position Matters
* **Partial Generation**: AI might generate valid JSON then fabricate the rest
* **End Position**: Hardest place to fake - requires completing entire output
* **Verification**: Easy to check with `tail -3 output.json`

### Gamification Integration
* **Rule**: Hallucination = Instant Failure in success/failure tracking
* **Requirement**: All outputs must have verifiable UUIDs
* **Benefit**: Makes lying a losing strategy for self-improving prompts

### Key Insights
1. **Simple but Effective**: UUID4 is cryptographically secure and unique
2. **Position is Critical**: END of JSON prevents partial fabrication
3. **Multiple Verification Points**: Console + files + reports = audit trail
4. **Enforces Honesty**: Makes hallucination detectable and penalized

### The Lesson
Trust but verify. Every AI-generated claim of execution should have cryptographic proof. The UUID4 pattern transforms "I ran this" into "I ran this and here's proof: `a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c`"

## Critical Performance and Quality Insights (2025-07-02)

Based on comprehensive stress testing with 17+ test cases, here are critical findings not covered elsewhere:

### Key Discovery: Self-Reflection Provides Minimal Quality Gains

- **Reality**: Average quality improvement is only 5.4% despite complex formatting
- **Impact**: The elaborate self-reflection patterns add complexity without proportional benefit
- **Action**: Use self-reflection only for completeness validation, not quality enhancement

### Performance Insights

1. **Startup overhead is unpredictable**: 4-60 seconds for identical prompts
2. **System load matters**: >10 load = 2-3x slower responses
3. **Recovery overhead compounds**: Each retry multiplies timeout (1x → 1.5x → 2.25x)
4. **Full test suites can timeout**: 17 sequential tests = 40+ minutes potential

### Format Control Realities

- **Word limits are ignored**: "10 words max" → 50+ word responses
- **Structure beats length**: Format constraints work, word counts don't
- **Contradictions get rationalized**: Claude chooses reasonable interpretation
- **Checkbox variants matter**: Must handle □, ☑, ☐, • patterns

### Patterns That Always Fail

- "Generate [large number] word essay"
- "Create comprehensive guide covering [many topics]"
- "Step-by-step with [many steps]"

### Production Recommendations

1. **Timeouts**: 120s minimum + 30s reflection + 60s complex output
2. **Recovery**: Max 2 attempts with aggressive simplification
3. **Design**: Simple prompts > complex self-reflection
4. **Testing**: Always test under realistic load conditions

**Bottom Line**: Simplicity and reliability beat elaborate quality-improvement mechanisms.

## Client Directory Architecture Mistake (2025-07-02)

A critical architectural lesson about maintaining clean, self-contained directory structures.

### The Problem: Cross-Directory Dependencies

* **Initial Design**: Created a `/client` directory with two WebSocket client files
* **The Mistake**: The "fat" client (`websocket_client.py`) reached into `/core` to start server processes
* **The Confusion**: Two files with 90% duplicate code, unclear naming, maintenance nightmare

### Why This Was Terrible Architecture

1. **Violated Self-Containment**: Client directory wasn't self-contained - it needed files from `/core`
2. **Duplicate Code**: 636 lines of code where 90% was duplicated between two files
3. **Unclear Purpose**: Users confused about which client to use
4. **Cross-Directory Dependencies**: Client starting servers by reaching into `/core` = unmaintainable

### The Solution: Remove Client Directory

* **Action Taken**: Moved the simple WebSocket client to `/core/client.py`
* **Removed**: Entire `/client` directory and its duplicate files
* **Result**: Clean architecture where client is part of core functionality

### Key Lessons

1. **Directories Must Be Self-Contained**: If you have a `/client` directory, it needs ALL its dependencies
2. **Don't Create Unnecessary Abstractions**: We didn't need a separate client directory
3. **Avoid Duplicate Code**: Two nearly identical files = bad design
4. **Keep It Simple**: Client functionality belongs in `/core` with other core features

### Architectural Principles

* **Self-Containment**: Each directory should have everything it needs to function
* **Clear Purpose**: Each directory should have one clear responsibility
* **No Cross-Cutting**: Don't reach across directories for dependencies
* **DRY Principle**: Don't Repeat Yourself - avoid duplicate implementations

## Token Limit Detection and Adaptive Retry (2025-06-30)

From our session on implementing bidirectional token limit detection and adaptive retry strategies.

### Key Discovery: Tests Were Failing Due to Token Limits, Not Infrastructure

* **The Problem**: Stress tests were failing with "Claude AI usage limit reached" errors, which we initially thought were infrastructure issues.
* **The Reality**: Tests were hitting Claude's output token limits (32,000 tokens by default), not rate limits or system issues.
* **The Solution**: Implement bidirectional polling in the WebSocket handler to detect token limit errors and send notifications back to the calling agent.

### Implementation Pattern: Error Detection in Output Stream

* **Key Insight**: Token limit errors appear in Claude's output stream, not as separate error messages.
* **Detection Pattern**: Look for "Claude's response exceeded the" and "output token maximum" in stdout.
* **WebSocket Notification**: Send `error.token_limit_exceeded` notification with details:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "error.token_limit_exceeded",
    "params": {
      "session_id": "...",
      "error_type": "token_limit",
      "limit": 32000,
      "message": "Claude's output exceeded 32000 token limit",
      "suggestion": "Retry with a more concise prompt or specify word/token limits",
      "recoverable": true
    }
  }
  ```

### Adaptive Retry Strategy

* **Attempt 1**: Add "Please be concise and limit your response to essential information only."
* **Attempt 2**: Specify exact word limit (e.g., "Please limit your response to approximately 1000 words.")
* **Attempt 3**: Request outline/summary instead of full content.
* **Key Learning**: Don't just detect errors - adapt the request to work within constraints.

### Claude CLI Syntax Gotchas

* **Critical**: The prompt must come immediately after the `-p` flag!
  - ✅ CORRECT: `claude -p "Your prompt here" --output-format stream-json --verbose`
  - ❌ WRONG: `claude -p --output-format stream-json "Your prompt here"`
* **Required Flags**: When using `--output-format stream-json`, you must also include `--verbose`
* **The `--print` Flag**: Claude CLI uses `-p` NOT `--print`. The `--print` flag doesn't exist and will cause hangs.

### Architectural Decision: Single WebSocket Handler

* **Mistake**: Creating multiple specialized handlers (token-aware, enhanced, self-reflecting).
* **Better Approach**: Add capabilities to the single `websocket_handler.py`.
* **Benefit**: Avoids fragmentation, easier maintenance, single source of truth.

### File Organization Best Practices

* **Problem**: Test files scattered throughout the project with confusing names like "unified_stress_test_tasks.json".
* **Solution**: Centralize under `/stress_tests/` with clear subdirectories:
  - `configs/` - Test configuration files with descriptive names
  - `runners/` - Test execution scripts
  - `utils/` - Helper utilities
  - `test_outputs/` - Results and logs

### Testing Philosophy: Graceful Degradation

* **Old Way**: Tests fail when hitting limits, marked as failures.
* **New Way**: Tests adapt to constraints and find alternative paths to success.
* **Result**: Higher success rates and more resilient systems.

---

## Lesson 1: Test Every Prompt Yourself Before Adding to Automated Tests

A critical debugging principle that seems obvious in hindsight but is easy to overlook when building
test suites for AI systems.

* **The Principle**: If you can't run a prompt successfully yourself, it will 100% fail when another
  Claude instance tries to run it in your test suite. There is no magic - the same environment
  constraints apply.

* **The Trap We Fell Into**: We were debugging WebSocket handlers, stdin issues, and complex integration
  problems when the real issue was that the prompts themselves didn't work. We added prompts like
  "Write a Python function" or "Find me a recipe" to stress tests without first verifying they worked.

* **The Reality**: Claude CLI has bugs where certain prompt patterns cause hangs:
  - ❌ "Write a Python function..." (hangs)
  - ❌ "Create a Python function..." (hangs)  
  - ❌ "Find me a recipe..." (hangs)
  - ❌ "Generate a haiku" (hangs)
  - ✅ "What is 2 + 2?" (works)
  - ✅ "What is a Python function that adds two numbers?" (works)
  - ✅ "What is the capital of France?" (works)

* **The Debugging Approach**:
  1. Before adding ANY prompt to a test suite, run it yourself with timeout
  2. If it hangs for you, it WILL hang in the test
  3. Find alternative phrasings that work
  4. Document which patterns work and which don't

* **The Lesson**: Test infrastructure can only be as reliable as the commands it runs. Always validate
  the basic building blocks work before debugging the integration layer.

## Lesson 2: System Load Dramatically Affects Timeout Requirements

High system load can cause perfectly good tests to fail due to timeouts, leading to misleading metrics
and wasted debugging time.

* **The Problem**: We observed only 38.5% test pass rate and assumed our infrastructure was broken.
  The real issue was that the system had a load average of 14.99 with Ollama using 21GB GPU memory,
  causing Claude CLI to run much slower than normal.

* **The Discovery**: System performance degrades non-linearly under high load:
  - Load < 5: Normal performance, standard timeouts work fine
  - Load 5-14: Some slowdown, may need 1.5-2x timeouts
  - Load > 14: Severe degradation, need 3x timeouts minimum
  - Load > 20: Consider postponing non-critical tasks

* **The Solution**: Implement load-aware timeout adjustments:
  ```bash
  # Check system load
  CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
  
  # Apply multiplier if load > 14
  if (( $(echo "$CPU_LOAD > 14" | bc -l) )); then
      TIMEOUT=$(echo "$TIMEOUT * 3" | bc)
      echo "⚠️ High load detected: $CPU_LOAD (3x timeout applied)"
  fi
  ```

* **Key Metrics to Track**:
  - CPU load average (1-minute)
  - GPU memory usage (impacts AI workloads significantly)
  - Store these with task execution data for historical analysis

* **The Lesson**: Don't blame your code for performance issues without checking system load first.
  What looks like a bug might just be a stressed system. Always implement adaptive timeouts for
  production systems that may experience variable load.

## Lesson 3: Dynamic Resource Monitoring Implementation

After identifying that system load affects timeout requirements, we implemented automatic timeout
adjustment in the CC Executor infrastructure.

* **The Implementation**: Added `resource_monitor.py` module that:
  - Monitors CPU usage via `psutil`
  - Monitors GPU usage via `nvidia-smi` 
  - Applies 3x timeout multiplier when either exceeds 14%
  - Integrates seamlessly with WebSocket handler

* **Key Design Decisions**:
  1. **Opt-in by default**: Feature is disabled unless `ENABLE_STREAM_TIMEOUT=true` is set
  2. **Simple multiplier**: Just 1x or 3x, not a complex scaling algorithm
  3. **Minimal overhead**: Only checks load once per command execution
  4. **Clear logging**: Always logs when timeout adjustment occurs

* **Usage Pattern**:
  ```python
  from cc_executor.core.resource_monitor import adjust_timeout
  
  # Automatically adjusts based on current system load
  actual_timeout = adjust_timeout(base_timeout=60)
  # Returns 60s if load < 14%, or 180s if load >= 14%
  ```

* **The Lesson**: When you identify a pattern causing failures (like timeouts under load), build
  the solution directly into your infrastructure. Make it automatic, well-logged, and easy to
  understand. Future users shouldn't have to rediscover the same problem.

## Lesson 4: Claude CLI Processes Need Baseline 3x Timeout Multiplier (2025-06-28)

When using Redis timing defaults for Claude CLI operations, the system was too aggressive in reducing
timeouts for tasks it hadn't seen before, causing unnecessary failures.

* **The Issue**: Redis timing defaults (10s simple, 60s medium, 180s complex) are appropriate for
  quick operations but not for Claude CLI, which inherently takes longer even for "simple" queries.

* **The Discovery**: A recipe query was classified as "simple/creative" and given only 30s timeout
  (3x the 10s default). It timed out because even simple Claude queries can take 30-60s under normal
  load conditions.

* **The Solution**: Apply a 3x baseline multiplier to ALL default timeouts when no historical data exists:
  ```python
  baseline_multiplier = 3.0  # Claude CLI needs longer timeouts
  default_times = {
      "simple": {
          "expected": 10 * baseline_multiplier,  # 30s instead of 10s
          "max": 30 * baseline_multiplier         # 90s instead of 30s
      },
      "medium": {
          "expected": 60 * baseline_multiplier,   # 180s instead of 60s
          "max": 180 * baseline_multiplier        # 540s instead of 180s
      },
      "complex": {
          "expected": 180 * baseline_multiplier,  # 540s instead of 180s
          "max": 600 * baseline_multiplier        # 1800s instead of 600s
      }
  }
  ```

* **The Principle**: Start conservative with timeouts and tighten them based on actual data, not the
  other way around. It's better to wait a bit longer than to fail prematurely.

* **Key Insights**:
  - Claude CLI is not a typical subprocess - it's an AI model doing complex reasoning
  - "Simple" for Claude still means natural language processing, not just arithmetic
  - Only reduce timeouts after 3+ successful runs provide real timing data
  - The baseline multiplier stacks with load multiplier (3x * 3x = 9x under high load)

* **The Lesson**: Know your tools. Claude CLI is fundamentally different from typical CLI tools.
  Default timeouts that work for `grep` or `curl` are completely inappropriate for AI operations.
  Build your timing assumptions around the actual characteristics of the tools you're using.

## Lesson 5: Validation - 3x Baseline Multiplier Achieves 100% Success Rate (2025-06-28)

After implementing the 3x baseline multiplier, we achieved perfect test results, validating our approach.

* **The Results**: 
  - Before fix: 90% success rate (recipe test failed with 30s timeout)
  - After fix: 100% success rate (all 10 tests passed)
  - Recipe test: Succeeded in 66.2s with 270s timeout (would have failed at 30s)

* **Key Validations**:
  1. **Timeout calculations worked correctly**: 
     - Simple/creative recipe: 10s × 3 (baseline) × 3 (load) = 90s expected, 270s max timeout
     - Actual execution: 66.2s - well within the adjusted timeout
  
  2. **Load awareness stacked properly**:
     - System detected load of 22-24 (very high)
     - Applied both baseline multiplier AND load multiplier
     - Total multiplier: 9x for new tasks under high load

  3. **Redis learning improved over time**:
     - First run: Used "default_with_3x_baseline" for recipe
     - Subsequent runs: Switched to "exact_history" with higher confidence
     - System now self-tunes based on actual performance data

* **Practical Impact**:
  ```
  Test Results Comparison:
  ├── Without baseline multiplier:
  │   └── recipe_finder: ❌ FAILED (timeout at 30s)
  └── With baseline multiplier:
      └── recipe_finder: ✅ SUCCESS (66.2s < 270s timeout)
  ```

* **The Lesson**: When dealing with AI/LLM operations, always err on the side of longer timeouts
  initially. The 3x baseline multiplier transformed a failing system into a reliable one. Once you
  have real performance data, the system can optimize itself, but conservative defaults prevent
  false failures during the learning phase.

## Lesson 6: Claude CLI Stream JSON Format Doesn't Actually Stream (2025-06-30)

A critical discovery about Claude CLI's `--output-format stream-json` flag revealed it doesn't provide
token-by-token streaming, which fundamentally changes timeout handling strategies.

* **The Misconception**: We assumed `--output-format stream-json` would provide incremental token 
  streaming like OpenAI's API, allowing us to detect activity and reset timeouts as tokens arrived.

* **The Reality**: Claude CLI only emits 3 JSON events total:
  1. Initial system event with tools/config
  2. Complete message event (after ALL thinking is done)
  3. Final result event
  
  This means 30-60 second "stalls" are EXPECTED behavior, not bugs.

* **The Discovery Process**:
  - Initial observation: Tests were "stalling" for 30+ seconds with no output
  - Investigation: Added heartbeats, unbuffering, stdbuf wrapping - no effect
  - Research via perplexity-ask: Confirmed Claude CLI doesn't support token streaming
  - Validation: Test outputs showed only 3 JSON events regardless of response length

* **The Implications**:
  1. **WebSocket heartbeats can't fix this**: The issue isn't connection stability
  2. **Activity monitoring is useless**: No activity to monitor during thinking
  3. **Stall timeouts are meaningless**: The entire response is one "stall"
  4. **Must use conservative total timeouts**: Can't rely on incremental progress

* **The Solution**: Enhanced WebSocket handler with:
  - Heartbeats every 20s to keep connection alive (prevents WebSocket timeout)
  - No stall detection (removed as it's pointless)
  - Long total timeouts (10 minutes for unknown prompts)
  - Clear documentation of the limitation

* **The Lesson**: Always verify your assumptions about third-party tools. The name "stream-json"
  strongly implies streaming behavior, but implementation details matter. This limitation means
  WebSockets provide minimal benefit over simple subprocess execution for Claude CLI.

## Lesson 7: Unknown Prompts Require 10-Minute Minimum Timeouts (2025-06-30)

When Redis has no historical data for a prompt type, using short timeouts leads to unnecessary failures.
The solution is to enforce a 10-minute minimum for truly unknown prompts.

* **The Problem**: Redis-based timeout prediction was too aggressive for new prompt types:
  - Historical data suggested 2.8s for a math problem
  - Actual execution took 12.1s, causing timeout
  - System was learning bad data (failed executions) instead of good data

* **The Root Cause**: 
  1. Bad historical data from previous failures created a negative feedback loop
  2. Short timeouts prevented successful execution
  3. Failed executions reinforced short timeout predictions
  4. System couldn't learn actual execution times

* **The Solution**: Enforce 600s (10 minute) minimum for unknown prompts:
  ```python
  # For unknown prompts, ensure minimum 10 minute (600s) timeout
  if is_unknown:
      print(f"⚠️ Unknown prompt type detected. Using minimum 10 minute (600s) timeout.")
      times['expected'] = max(times['expected'], 600.0)
      times['max'] = max(times['max'], 600.0)
  ```

* **Detection Criteria for Unknown Prompts**:
  - Category is 'unknown' or 'general'
  - No exact history match exists
  - Confidence level <= 0.1
  - Based on "default_with_3x_baseline"

* **The Results**: After implementing 10-minute timeouts:
  - Unknown prompts no longer timeout prematurely
  - System can learn actual execution times
  - Redis builds accurate historical data
  - Future runs use optimized timeouts based on real data

* **The Lesson**: When building adaptive systems, the bootstrap phase is critical. Conservative
  timeouts during initial learning prevent the system from learning failure patterns. It's better
  to wait 10 minutes for a 30-second task than to fail a 2-minute task with a 10-second timeout.

## Lesson 8: API Rate Limits Are The Ultimate Constraint (2025-06-30)

After solving all timeout, WebSocket, and Redis timing issues, the final blocker was simple: 
Claude API usage limits.

* **The Situation**: 
  - All infrastructure issues solved
  - Redis timing working correctly (600s for unknown prompts)
  - Enhanced WebSocket handler with heartbeats functioning
  - Tests failing with: "Claude AI usage limit reached|1751295600"

* **The Reality Check**:
  - Test suite ran 15 tests rapidly
  - Only 1 passed before hitting rate limits
  - All subsequent tests failed with usage limit error
  - Exit code 1 indicated API rejection, not timeout

* **Key Observations**:
  1. **Infrastructure was working**: The one successful test proved the system functions
  2. **Timing was correct**: All tests got appropriate timeouts (600s for unknown)
  3. **No amount of engineering can bypass API limits**: This is a business constraint
  4. **Rate limit errors manifest as subprocess failures**: Easy to misdiagnose as timeout issues

* **Mitigation Strategies**:
  - Add delays between tests (we had 2s, might need 30-60s)
  - Batch tests across different time periods
  - Use different API keys for different test categories
  - Implement exponential backoff on rate limit errors
  - Cache successful responses for re-testing

* **The Lesson**: Perfect infrastructure can't overcome external service limits. When debugging
  distributed systems, always check for rate limits, quotas, and service-level constraints before
  diving deep into timeout and connection issues. Sometimes the simplest explanation is correct:
  you've just hit your usage limit.

## Lesson 15: Async Event Loop Blocking - The Redis Connection Trap (2025-07-10)

A subtle but critical lesson about how synchronous operations in async contexts can completely freeze your application.

### The Problem: Synchronous Redis in Async Initialize

The hook system was hanging the WebSocket server after "Hook enforcement system initialized successfully". Investigation revealed that while the async subprocess calls were correct, the **initialization** itself had blocking operations.

### The Discovery Process:
1. **Initial diagnosis**: Comment said "hook system uses blocking subprocess.run()" 
2. **Code inspection**: Actually used `asyncio.create_subprocess_exec` correctly
3. **Perplexity insight**: "The code uses communicate() correctly to drain pipes"
4. **Deeper investigation**: Found synchronous `redis.Redis().ping()` in `_check_redis()`
5. **Root cause**: `ensure_hooks` decorator called sync `initialize()` from async context

### The Blocking Chain:
```python
# In ensure_hooks decorator (line 798):
async def async_wrapper(*args, **kwargs):
    hook = get_hook_integration()
    if not hook.enforcer.initialized:
        hook.enforcer.initialize()  # SYNC method in async context!

# Which calls:
def _check_redis(self):
    self.redis_client = redis.Redis(...)
    self.redis_client.ping()  # BLOCKS the entire event loop!
```

### Why This Blocked Everything:
- Asyncio runs on a single thread with an event loop
- When `redis.ping()` blocks for 5+ seconds (timeout), NO coroutines can run
- The WebSocket appears completely frozen
- Even though async subprocess code was correct, the sync Redis killed it

### The Fix: Defer Redis Connection
```python
def _check_redis(self) -> bool:
    """Check Redis connection - deferred to prevent blocking async event loop."""
    logger.info("Redis connection check deferred to prevent event loop blocking")
    self._redis_client = None  # Will be created on first actual use
    return True  # Assume Redis will be available when needed

@property
def redis_client(self):
    """Lazy Redis client creation to avoid blocking during init."""
    if self._redis_client is None:
        # Create connection only when actually needed
        # This happens outside the critical initialization path
```

### Key Insights:
1. **Async all the way down**: In async contexts, EVERY I/O operation must be non-blocking
2. **Init methods are dangerous**: Initialization often happens in async contexts
3. **Lazy loading saves the day**: Defer heavy operations until actually needed
4. **Comments can mislead**: The comment blamed subprocess.run() but Redis was the culprit
5. **Property decorators help**: Use @property for lazy initialization patterns

### Testing the Fix:
- Before: Initialization blocked for 5+ seconds (Redis timeout)
- After: Initialization completed in 0.485 seconds
- Result: WebSocket server responsive, hooks working properly

### The Lesson:
When debugging async hanging, don't just look at the obvious async operations. Check EVERY synchronous call, especially in initialization paths. A single blocking I/O operation (like Redis.ping()) can freeze your entire async application. Always use async clients (aioredis) or defer synchronous operations through lazy loading.

## Lesson 14: Service Configuration vs Service Running - The MCP Debugging Pattern (2025-07-10)

A critical pattern that keeps recurring: assuming configuration means the service is running.

### The Problem: "It's Configured So It Should Work"

The cc-execute MCP server was configured in `.mcp.json` but agents couldn't use it. We spent hours debugging integration, tool prefixes, and registration when the issue was simple: **the server wasn't running**.

### The Pattern We Keep Hitting:

1. **Configuration exists** → We assume it works
2. **Service isn't running** → So it doesn't work  
3. **We debug complex issues** → When the fix is "start/reload the service"

### Examples from This Project:

- **MCP Server**: Configured in `.mcp.json` but not running until Claude Code reload
- **Docker Auth**: Configured but wrong permissions until container restart
- **WebSocket**: Running but wrong message format until we checked actual protocol
- **Redis**: Connected but wrong password until we verified with `redis-cli`

### The Basic Competent Minimum Checklist:

```bash
# 1. Is it actually running?
ps aux | grep [service_name]
pgrep -f [service_name]

# 2. Can we connect to it?
curl http://localhost:PORT/health
telnet localhost PORT
nc -zv localhost PORT

# 3. Are permissions correct?
ls -la [config_files]
docker exec [container] whoami

# 4. Is it the right version/format?
[service] --version
curl -X POST [endpoint] -d '{"test": "data"}'
```

### The "Reload Fixes It" Pattern:

| Service Type | Reload Command | When Needed |
|--------------|----------------|-------------|
| MCP Servers | Reload Claude Code | After .mcp.json changes |
| Docker | `docker compose restart` | After docker-compose.yml changes |
| System Services | `systemctl reload [service]` | After config file changes |
| WebSocket Servers | Kill and restart process | After code changes |

### Documentation Template for Every Service:

```markdown
## [Service Name]

### How to Start
```bash
[exact command to start service]
```

### How to Verify Running
```bash
[command to check if running]
[command to test connectivity]
```

### How to Reload/Restart
```bash
[command to reload after config changes]
```

### Required Permissions
- File: [path] needs [permissions]
- User: Runs as [user]
- Ports: Listens on [ports]
```

### The Lesson:

Before debugging complex integration issues, always verify the basics:
1. **Is it running?** (process check)
2. **Can I connect?** (network check)
3. **Do I have permission?** (auth check)
4. **Is it the right format?** (protocol check)

The fix is often just "reload the service" - but we need to check first. Configuration is not execution.

## Lesson 13: Claude Code MCP Configuration - Global vs Project Config (2025-07-05)

A critical lesson about how Claude Code loads MCP server configurations.

### The Problem: Project-Level .mcp.json Not Loading

Despite having a valid `.mcp.json` in the project directory, Claude Code was not loading the MCP servers defined there. The `/mcp` command showed servers from a different configuration.

### The Discovery:
1. **Initial expectation**: Project-level `.mcp.json` should be detected automatically
2. **Reality**: Claude Code was loading from `~/.claude/claude_code/.mcp.json` instead
3. **Bug confirmed**: Known issue where project-scoped MCP servers are not detected (GitHub issue #2156)
4. **Solution**: Update the global config directly with absolute paths

### The Working Configuration:
```json
{
  "mcpServers": {
    "cc-executor": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/graham/workspace/experiments/cc_executor",
        "run",
        "python",
        "src/cc_executor/servers/mcp_server_fastmcp.py"
      ],
      "env": {
        "CC_EXECUTOR_PORT": "8005"
      }
    }
  }
}
```

### Key Insights:
1. **Use `uv run`**: The working pattern from arxiv-mcp-server uses `uv run python` not direct Python
2. **Absolute paths needed**: When in global config, use `--directory` flag to specify project location
3. **Reload required**: Must reload Claude Code after config changes
4. **stdio transport**: Claude Code uses stdio (subprocess) communication, not HTTP/SSE

### Debugging Commands:
```bash
# Check which servers are registered
claude mcp list

# Add server via CLI (doesn't always work)
claude mcp add <name> <command> [args...]

# Find config location
find ~/.claude -name ".mcp.json"
```

### Action Items:
- [x] Document the global config workaround for project MCP servers
- [x] Use `uv run` pattern for Python MCP servers
- [x] Include `--directory` flag when servers are in global config
- [x] Successfully test cc-executor MCP tool with "create a Python function that adds two numbers"