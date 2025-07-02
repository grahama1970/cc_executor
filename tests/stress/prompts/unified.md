# Run Unified Stress Tests — Self-Improving Prompt

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 0:0 (Requires 10:1 to graduate)
- **Last Updated**: 2025-06-30
- **Evolution History**:
  | Version | Change & Reason | Result |
  | :------ | :-------------- | :----- |
  | v1      | Initial implementation with comprehensive pre-flight checklist | TBD |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Execute unified stress tests for cc_executor through the WebSocket handler, ensuring all critical requirements from CLAUDE_CODE_PROMPT_RULES.md are followed.

### 2. Core Principles & Constraints
- MUST use WebSocket handler (not direct CLI calls)
- MUST include --output-format stream-json flag
- MUST validate JSON streaming output
- MUST handle buffer overflow protection
- MUST track success/failure ratio for graduation
- MUST learn from failures and update prompts

### 3. Critical Pre-Flight Checklist
Before running ANY tests, validate ALL of these requirements:
□ Claude CLI is installed and available
□ WebSocket port 8004 is free (kill existing processes if needed)
□ Working directory is project root (contains .mcp.json)
□ System load is checked (adjust timeouts if > 5)
□ Test JSON file exists at src/cc_executor/tasks/unified_stress_test_tasks.json
□ ANTHROPIC_API_KEY is properly handled (removed for Claude Max)
□ All commands include required flags:
  - --output-format stream-json (CRITICAL)
  - --dangerously-skip-permissions
  - --allowedTools none (or MCP config)
  - --verbose (for debugging)

---
## 🤖 IMPLEMENTER'S WORKSPACE

### Step 1: Validate Environment
```bash
# Check Claude CLI
which claude || echo "ERROR: Install with npm install -g @anthropic-ai/claude-cli"

# Check WebSocket port
lsof -i:8004 && echo "Port in use, killing..." && lsof -ti:8004 | xargs kill -9

# Check working directory
ls .mcp.json || echo "ERROR: Not in project root"

# Check system load
uptime | grep -o "load average:.*" | awk '{print $3}'

# Check test file
ls src/cc_executor/tasks/unified_stress_test_tasks.json || echo "ERROR: Test file missing"
```

### Step 2: Start WebSocket Handler
```bash
# From project root
cd /home/graham/workspace/experiments/cc_executor
source .venv/bin/activate

# Start handler
python -m cc_executor.core.websocket_handler &
HANDLER_PID=$!

# Wait for startup
sleep 5

# Verify it's running
curl -s http://localhost:8004/health || echo "ERROR: Handler not responding"
```

### Step 3: Run Tests with Proper Flags
```python
#!/usr/bin/env python3
import asyncio
import json
import websockets
import uuid
from datetime import datetime

async def run_single_test(ws, test_id, prompt):
    """Execute a single test with all required flags"""
    
    # Build command with ALL required flags
    command = (
        f'claude -p "[marker:{test_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}] {prompt}" '
        f'--output-format stream-json '  # CRITICAL: prevents buffer overflow
        f'--dangerously-skip-permissions '
        f'--allowedTools none '
        f'--verbose'
    )
    
    # Send request
    request = {
        "jsonrpc": "2.0",
        "method": "execute",
        "params": {"command": command},
        "id": str(uuid.uuid4())
    }
    
    await ws.send(json.dumps(request))
    
    # Track JSON streaming
    has_json_streaming = False
    output_lines = []
    
    while True:
        response = await ws.recv()
        data = json.loads(response)
        
        if "error" in data:
            return {"success": False, "error": data["error"]}
            
        if data.get("method") == "process.output":
            output = data.get("params", {}).get("data", "")
            output_lines.append(output)
            
            # Validate JSON streaming
            if '{"type":' in output or '"event":' in output:
                has_json_streaming = True
                
        elif data.get("method") == "process.completed":
            exit_code = data.get("params", {}).get("exit_code")
            return {
                "success": exit_code == 0,
                "has_json_streaming": has_json_streaming,
                "output": "\n".join(output_lines)
            }

async def main():
    # Connect to WebSocket
    async with websockets.connect("ws://localhost:8004/ws", ping_timeout=None) as ws:
        # Run test
        result = await run_single_test(ws, "test_1", "What is 2+2?")
        
        # Validate JSON streaming
        if not result.get("has_json_streaming"):
            print("❌ CRITICAL: No JSON streaming detected! Check --output-format flag")
        else:
            print("✅ JSON streaming validated")
```

### Step 4: Self-Reflection and Learning

After EACH test failure:
1. Check if prompt uses question format ("What is...?")
2. Verify all flags are included
3. Check for buffer overflow (large outputs without streaming)
4. Document lesson in CLAUDE_CODE_PROMPT_RULES.md
5. Update prompt and retry

**Success/Failure Tracking:**
- Current ratio: 0:0
- Target: 10:1 for graduation
- Each failure is a learning opportunity
- Document ALL lessons learned

### Step 5: Cleanup
```bash
# Kill WebSocket handler
kill $HANDLER_PID

# Verify cleanup
lsof -i:8004 || echo "✅ Port cleaned up"
```

---
## 🎓 GRADUATION CRITERIA

1. **Success/Failure Ratio**: Must achieve 10:1
2. **All Tests Pass**: 100% with proper flags
3. **JSON Streaming Validated**: All tests show streaming
4. **Lessons Documented**: All failures analyzed
5. **No Buffer Overflows**: Large outputs handled

---
## 🔍 DEBUGGING PATTERNS

When tests fail:
```bash
# Check if command has all flags
echo "$command" | grep -E "(--output-format stream-json|--dangerously-skip-permissions|--allowedTools)"

# Verify WebSocket handler logs
tail -f ~/.claude/projects/*/websocket_handler.log

# Check for buffer overflow
# If output > 64KB without streaming = deadlock

# Research using both tools concurrently
# perplexity-ask: "Claude CLI subprocess buffer overflow fix"
# gemini: "asyncio subprocess pipe buffer deadlock prevention"
```

Remember: EVERY test MUST use --output-format stream-json or it WILL fail on large outputs!