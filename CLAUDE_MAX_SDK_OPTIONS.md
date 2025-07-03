# Claude Max SDK Options - Official Analysis

## The Reality: No Official SDK Support for Claude Max

Based on research and testing, here's the definitive answer:

### ❌ Anthropic Python SDK
- **Requires API key** - Not available with Max subscription
- **Cannot use OAuth tokens** - The SDK explicitly rejects them
- **Error**: "Could not resolve authentication method"

### ✅ Claude Code SDK
- **Works with Max** - Uses Claude CLI internally
- **Uses browser auth** - Leverages Max's OAuth tokens
- **Limited scope** - Only for Claude conversations, not general API

### ✅ Claude CLI (subprocess)
- **Works with Max** - Uses browser authentication
- **Full featured** - All Claude capabilities
- **Your current approach** - What cc_executor uses

## Official Anthropic Position

According to Perplexity's research of Anthropic docs:

1. **Max subscriptions are consumer-focused** - Not meant for programmatic access
2. **API access requires separate account** - Pay-as-you-go with API keys
3. **No OAuth SDK exists** - OAuth is only for web/CLI, not SDKs

## Available Options for Max Users

### Option 1: Claude Code SDK (Limited)
```python
from claude_code_sdk import query, ClaudeCodeOptions

async for message in query(
    prompt="Your prompt",
    options=ClaudeCodeOptions(max_turns=3)
):
    # Process message
```

**Pros:**
- Works with Max subscription
- Structured message objects
- Async iteration

**Cons:**
- Only for Claude conversations
- Has async cleanup bugs
- Not suitable for general command execution

### Option 2: Subprocess CLI (Current Approach)
```python
process = await asyncio.create_subprocess_shell(
    "claude -p 'Your prompt'",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

**Pros:**
- Works with Max subscription
- Full control over execution
- Can execute any command
- Real-time streaming

**Cons:**
- More complex to implement
- Need to parse text output

### Option 3: Unofficial Workarounds (NOT Recommended)
- Browser automation
- Session token scraping
- Reverse engineering OAuth

**Why not:**
- Violates ToS
- Unreliable
- Will break with updates

## Recommendation for cc_executor

**Stick with the subprocess approach** because:

1. **It's the only reliable option** for Max users
2. **cc_executor needs more than Claude** - It executes any command
3. **You already have working code** - Don't fix what isn't broken
4. **Claude Code SDK doesn't fit** - Too limited for your use case

## If You Need API Access

The only official way to get SDK access:

1. Sign up for API access (separate from Max)
2. Pay per token usage
3. Use the Anthropic Python SDK with API key

But this means:
- Paying twice (Max + API)
- Different rate limits
- Separate billing

## Conclusion

For Claude Max users who want programmatic access:
- **Claude CLI via subprocess is the best option**
- **Claude Code SDK works but is limited**
- **No official Python SDK supports Max**

Your current implementation in cc_executor is the correct approach.