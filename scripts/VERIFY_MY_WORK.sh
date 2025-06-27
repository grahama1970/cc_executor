#!/bin/bash
# Direct verification commands - no hiding, just facts

echo "=== VERIFYING EACH FIX ==="
echo "Current directory: $(pwd)"
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress

echo -e "\n=== Fix 1: WebSocket Handshake Format ==="
echo "CLAIM: Service already sends correct format, no fix needed"
echo "VERIFY: Testing actual handshake..."
python3 -c "
import asyncio, websockets, json
async def test():
    try:
        async with websockets.connect('ws://localhost:8003/ws/mcp') as ws:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f'Handshake received: {json.dumps(data, indent=2)}')
            if data.get('method') == 'connected' and 'session_id' in data.get('params', {}):
                print('✅ VERIFIED: Correct handshake format')
            else:
                print('❌ FAILED: Wrong handshake format')
    except Exception as e:
        print(f'❌ FAILED: {e}')
asyncio.run(test())
"

echo -e "\n=== Fix 2: WebSocket Test Notification Names ==="
echo "CLAIM: Fixed notification names from 'output' to 'process.output'"
echo "VERIFY: Checking the actual code changes..."
echo "Line 67 (should show 'process.output'):"
sed -n '67p' websocket_test_executor.py | grep -n "process.output" || echo "❌ NOT FOUND"
echo "Line 71 (should show 'process.completed'):"
sed -n '71p' websocket_test_executor.py | grep -n "process.completed" || echo "❌ NOT FOUND"
echo "Line 160 (should show 'process.output' in extract method):"
sed -n '160p' websocket_test_executor.py | grep -n "process.output" || echo "❌ NOT FOUND"

echo -e "\n=== Fix 3: Unified Test Uses WebSocket ==="
echo "CLAIM: Replaced aiohttp with websockets"
echo "VERIFY: Checking imports..."
echo "Should NOT find aiohttp:"
grep -n "import aiohttp" unified_stress_test_executor_v3.py && echo "❌ FAILED: aiohttp still present" || echo "✅ VERIFIED: aiohttp removed"
echo "Should find websockets:"
grep -n "import websockets" unified_stress_test_executor_v3.py && echo "✅ VERIFIED: websockets added" || echo "❌ FAILED: websockets not found"
echo "Check WebSocket connection code (line 83):"
sed -n '83p' unified_stress_test_executor_v3.py | grep "websockets.connect" && echo "✅ VERIFIED: Using WebSocket" || echo "❌ FAILED: Not using WebSocket"

echo -e "\n=== Fix 4: Pattern Matching Trailing Spaces ==="
echo "CLAIM: Removed trailing spaces from patterns"
echo "VERIFY: Searching for bad patterns..."
cd ../../tasks
echo "Checking for 'def ' with trailing space:"
grep -n '"def "' unified_stress_test_tasks.json && echo "❌ FAILED: Still has trailing space" || echo "✅ VERIFIED: No trailing space"
echo "Checking for 'def test_':"
grep -n '"def test_"' unified_stress_test_tasks.json && echo "❌ FAILED: Still has underscore" || echo "✅ VERIFIED: Underscore removed"
echo "Showing corrected patterns:"
grep -n '"def"' unified_stress_test_tasks.json | head -3

echo -e "\n=== Fix 5: Redis Timeout Scripts ==="
echo "CLAIM: Scripts exist and are executable"
echo "VERIFY: Checking files..."
ls -la /home/graham/.claude/commands/check-task-timeout 2>&1
ls -la /home/graham/.claude/commands/record-task-time 2>&1
echo "Testing if executable:"
[[ -x /home/graham/.claude/commands/check-task-timeout ]] && echo "✅ VERIFIED: check-task-timeout is executable" || echo "❌ FAILED: Not executable"
[[ -x /home/graham/.claude/commands/record-task-time ]] && echo "✅ VERIFIED: record-task-time is executable" || echo "❌ FAILED: Not executable"

echo -e "\n=== Fix 6: Recovery Tests Added ==="
echo "CLAIM: Added 3 recovery test methods to websocket_stress_test.md"
echo "VERIFY: Checking the prompts file..."
cd ../prompts
echo "Looking for recovery test methods:"
grep -n "async def recovery_test" websocket_stress_test.md | head -5
echo "Checking if they're called in run_all_tests:"
grep -n "recovery_test_" websocket_stress_test.md | grep "await" | head -5

echo -e "\n=== Fix 7: Docker Documentation ==="
echo "CLAIM: Added comment about endpoints"
echo "VERIFY: Checking docker-compose.yml..."
cd ..
head -8 docker-compose.yml | grep -E "(WebSocket|health|HTTP)" && echo "✅ VERIFIED: Documentation added" || echo "❌ FAILED: No documentation"

echo -e "\n=== RUNNING ACTUAL WEBSOCKET TEST ==="
echo "This should pass if fixes work..."
cd tests/stress
timeout 30 python websocket_test_executor.py 2>&1 | grep -E "(Success Rate:|Failed:|✅|❌)" | tail -10

echo -e "\n=== CHECKING IF SERVICE IS ACTUALLY RUNNING ==="
curl -s http://localhost:8003/health | jq . || echo "❌ Service not responding"

echo -e "\n=== VERIFICATION COMPLETE ==="