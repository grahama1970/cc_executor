# WebSocket Reality Check: Why It Can't Fix Claude CLI's Limitations

## The Promise vs Reality

### What WebSockets Were Supposed to Solve:
- ✅ Bidirectional communication
- ✅ Keep connections alive during long operations  
- ✅ Real-time progress updates
- ✅ Prevent timeouts through heartbeats
- ✅ Stream output as it's generated

### What Actually Happens:
- ❌ Claude CLI doesn't stream tokens
- ❌ 30+ second "stalls" are NORMAL
- ❌ WebSockets can't forward what doesn't exist
- ❌ Complex prompts block until complete
- ❌ No intermediate progress possible

## The Core Problem

**Claude CLI's `--output-format stream-json` is misleadingly named:**

```json
// What you expect (token-by-token streaming):
{"type": "init", ...}
{"type": "content", "delta": "Once upon"}
{"type": "content", "delta": " a time"}
{"type": "content", "delta": " there was"}
...
{"type": "complete", ...}

// What you actually get:
{"type": "init", ...}
// ... 30+ second wait ...
{"type": "assistant", "message": {"content": [{"text": "Once upon a time there was... [entire 5000 word story]"}]}}
{"type": "result", ...}
```

## Why This Matters

1. **WebSockets become pointless** - If there's no streaming to forward, bidirectional communication doesn't help

2. **Timeouts are unavoidable** - You must wait for the entire response, no matter how long

3. **User experience suffers** - No progress indicators, just waiting

4. **Stress tests will "fail"** - But they're actually working correctly

## Verified Through Research

Using perplexity-ask MCP tool, we confirmed:
- This is a known limitation of Claude CLI
- Anthropic's API supports token streaming, but CLI doesn't expose it
- JSON mode specifically doesn't support streaming (even in the API)
- Only text mode has true streaming, but not with structured output

## Implications

### For cc_executor:
- WebSocket handler is working correctly
- The "stalls" in stress tests are expected behavior
- No amount of buffering fixes will help
- Need to adjust expectations and timeouts

### For Users:
- Complex prompts WILL take 30+ seconds with no feedback
- Breaking prompts into smaller parts is the only workaround
- Consider using the API directly for true streaming
- WebSockets provide connection management, not progress updates

## Recommendations

1. **Update Documentation**: Make it clear that "streaming" means "won't buffer overflow", not "real-time tokens"

2. **Adjust Timeouts**: 
   - Simple prompts: 120s
   - Medium prompts: 300s  
   - Complex prompts: 600s+

3. **Set Expectations**: Add messages like "Processing complex request, this may take several minutes..."

4. **Consider Alternatives**:
   - Use Anthropic's API directly for true streaming
   - Implement polling with partial results
   - Break complex prompts into smaller chunks

## The Bottom Line

WebSockets solve the connection management problem, but they can't solve the fundamental limitation that Claude CLI doesn't stream tokens. This is not a bug in cc_executor - it's a limitation of the tool we're wrapping.

The stress test "failures" are actually the system working as designed. The WebSocket handler keeps the connection alive during the long wait, which is its job. It just can't provide progress updates that don't exist.