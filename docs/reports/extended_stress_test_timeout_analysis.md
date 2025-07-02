# Extended Stress Test Timeout Analysis

## Summary

The extended stress test timed out after 10 minutes, completing only 11 out of 13 tests. The timeout was caused by two specific tests hanging:

1. **model_1** (gpt_vs_claude) - Attempted to use MCP tools
2. **long_1** (epic_story) - Requested a 5000-word story

## Root Cause Analysis

### 1. model_1 Test Failure (MCP Tool Integration)

The `model_1` test attempted to use the `ask-litellm.md` MCP tool:

```json
{
  "id": "model_1",
  "name": "gpt_vs_claude",
  "natural_language_request": "Use your ~/.claude/commands/ask-litellm.md command to call model='perplexity/sonar' with query='Explain recursion in programming with a simple example' and output_path='/tmp/litellm_recursion.txt'. Then explain recursion yourself and compare the two explanations."
}
```

**Issues identified:**
- No MCP configuration file found in the project
- The Claude CLI needs `--mcp-config` flag to access MCP tools
- Without MCP configuration, Claude cannot execute the ask-litellm.md command
- This caused the test to hang waiting for a response that would never come

### 2. long_1 Test Failure (5000-word Story)

The `long_1` test requested an extremely long output:

```json
{
  "id": "long_1",
  "name": "epic_story",
  "natural_language_request": "Write a 5000 word science fiction story about a programmer who discovers their code is sentient. Include dialogue, plot twists, and a surprising ending. Stream the entire story.",
  "timeout": 180,
  "stall_timeout": 60
}
```

**Issues identified:**
- 5000 words is a very large output that may exceed Claude's response limits
- The 180-second timeout might be insufficient for such a long generation
- Streaming JSON format adds overhead to already large output
- The test might have hit output buffer limits

### 3. Missing Test Results

Two tests were never reached due to the timeout:
- **concurrent_1** (fastapi_multiple_instances) - Complex concurrent execution test
- **concurrent_fastest** (concurrent_fastest_3) - Simple concurrent test

## Test Execution Timeline

```
1. easy_1 - PASSED (5.1s)
2. medium_1 - PASSED (7.0s) 
3. complex_1 - PASSED (10.2s)
4. simple_2 - PASSED (17.6s)
5. simple_3 - PASSED (40.8s)
6. parallel_1 - PASSED (58.2s)
7. parallel_2 - PASSED (16.6s)
8. model_1 - FAILED (hung, no output file)
9. long_1 - FAILED (hung, no output file)
10. complex_2 - PASSED (107.6s)
11. failure_3 - FAILED as expected (1.8s)
12. concurrent_1 - NOT REACHED
13. concurrent_fastest - NOT REACHED
```

## Configuration Issues

### 1. No Overall Timeout Configuration

The `extended_stress_test.py` script doesn't have an overall timeout mechanism. Each test has individual timeouts, but there's no global timeout to prevent the entire suite from hanging.

### 2. Individual Test Timeouts

Current timeout configuration:
- Most tests: 120 seconds timeout, 30 seconds stall timeout
- long_1: 180 seconds timeout, 60 seconds stall timeout
- failure_3: 5 seconds timeout, 2 seconds stall timeout

### 3. Missing MCP Configuration

The test command template includes MCP-related flags but no MCP configuration:
```python
"command_template": "claude -p \"${METATAGS} ${REQUEST}\" --output-format stream-json --verbose --dangerously-skip-permissions"
```

Missing: `--mcp-config path/to/mcp.json`

## Recommendations

### 1. Fix MCP Tool Tests

Either:
- Add proper MCP configuration file with tool definitions
- Modify model_1 test to not require MCP tools
- Skip MCP-dependent tests if configuration is missing

### 2. Adjust long_1 Test

Options:
- Reduce word count to 1000-2000 words
- Increase timeout to 300+ seconds
- Add chunking support for very long outputs
- Test with smaller story first, then scale up

### 3. Add Global Timeout

Implement overall test suite timeout:
```python
async def run_with_timeout(coro, timeout=600):  # 10 minutes
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"Overall test suite timeout after {timeout}s")
        return False
```

### 4. Improve Test Isolation

- Kill hanging processes between tests
- Add process group management for better cleanup
- Implement test retry logic for transient failures

### 5. Enhanced Monitoring

Add more detailed logging:
- Process start/stop times
- Memory usage per test
- Output buffer sizes
- Exact hang detection points

## Immediate Fixes

### Option 1: Skip Problematic Tests

Create a simplified test suite excluding model_1 and long_1:
```bash
# Remove or comment out model_1 and long_1 from extended_preflight_stress_test_tasks.json
```

### Option 2: Fix MCP Configuration

Create minimal MCP config:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--root", "/tmp"]
    }
  }
}
```

### Option 3: Reduce Test Complexity

Modify tests:
- model_1: Remove MCP tool requirement, just compare two Claude explanations
- long_1: Reduce to 1000-word story with 5-minute timeout

## Conclusion

The timeout was caused by:
1. MCP tool integration attempting to use non-existent configuration
2. Overly ambitious output size requirements
3. Lack of global timeout protection

The system itself (WebSocket handler, process management) appears stable - 9 out of 11 attempted tests passed successfully. The failures were due to test configuration issues rather than core system problems.