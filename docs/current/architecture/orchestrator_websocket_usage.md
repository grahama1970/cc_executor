# How Orchestration Agents Use WebSocket MCP

## Overview

This document shows how I (Claude, as an orchestration agent) use the WebSocket MCP protocol to execute and control Claude instances during the self-improvement cycle.

## Real-World Example: Self-Improving Prompt Execution

When implementing a self-improving prompt, I need to:
1. Execute verification commands
2. Monitor their output
3. Make decisions based on results
4. Cancel if something goes wrong

### My Actual Implementation Pattern

```python
import asyncio
import json
import websockets
import time

class OrchestrationAgent:
    """This is how I, Claude, orchestrate executions"""
    
    def __init__(self):
        self.websocket_uri = "ws://localhost:8003/ws/mcp"
        self.current_task = None
        self.output_buffer = ""
        self.markers = []
    
    async def execute_verification_step(self, step_name, command, expected_output):
        """Execute a single verification step from self-improving prompt"""
        
        # Generate unique marker for transcript verification
        marker = f"MARKER_{step_name}_{int(time.time())}"
        print(f"\n{marker}")
        
        async with websockets.connect(self.websocket_uri) as ws:
            # Skip connection message
            await ws.recv()
            
            # Execute verification command
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "execute",
                "params": {"command": command}
            }))
            
            # Monitor execution
            success = await self._monitor_execution(ws, expected_output)
            
            if not success:
                # Update metrics: FAILURE++
                await self._update_failure_metrics(step_name)
                # Fix the code based on output
                await self._analyze_and_fix(self.output_buffer, expected_output)
                # Add recovery test
                await self._add_recovery_test(step_name)
            else:
                # Update metrics: SUCCESS++
                await self._update_success_metrics(step_name)
            
            return success, marker
    
    async def _monitor_execution(self, ws, expected_output):
        """Monitor execution and make real-time decisions"""
        
        start_time = time.time()
        last_output_time = time.time()
        self.output_buffer = ""
        
        while True:
            try:
                # Check for timeout or stall
                if time.time() - start_time > 300:  # 5 minute timeout
                    await self._cancel_execution(ws, "Timeout exceeded")
                    return False
                
                if time.time() - last_output_time > 120:  # 2 minute stall
                    await self._cancel_execution(ws, "No output for 2 minutes")
                    return False
                
                # Receive message with short timeout
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                
                # Handle different message types
                if data.get('method') == 'process.output':
                    output = data['params']['data']
                    self.output_buffer += output
                    last_output_time = time.time()
                    
                    # Check for error patterns
                    if self._detect_error_patterns(output):
                        await self._cancel_execution(ws, "Error pattern detected")
                        return False
                    
                    # Show progress
                    print(output, end='', flush=True)
                
                elif data.get('method') == 'process.completed':
                    exit_code = data['params']['exit_code']
                    
                    # Verify output matches expectation
                    if exit_code == 0 and expected_output in self.output_buffer:
                        return True
                    else:
                        return False
                
                elif 'error' in data:
                    print(f"WebSocket error: {data['error']}")
                    return False
                    
            except asyncio.TimeoutError:
                # Continue monitoring
                continue
    
    async def _cancel_execution(self, ws, reason):
        """Cancel a running execution"""
        print(f"\nCancelling: {reason}")
        
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "control",
            "params": {"type": "CANCEL"}
        }))
        
        # Wait for cancellation
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get('method') == 'process.completed':
                break
    
    def _detect_error_patterns(self, output):
        """Detect common error patterns in output"""
        error_patterns = [
            "Traceback",
            "AssertionError",
            "ModuleNotFoundError",
            "SyntaxError",
            "NameError",
            "TypeError",
            "FAILURE",
            "command not found",
            "No such file or directory"
        ]
        return any(pattern in output for pattern in error_patterns)
    
    async def _update_success_metrics(self, step_name):
        """Update success count in prompt file"""
        # This would update the prompt's metrics section
        print(f"\n✓ {step_name} SUCCESS - Updating metrics")
    
    async def _update_failure_metrics(self, step_name):
        """Update failure count in prompt file"""
        # This would update the prompt's metrics section
        print(f"\n✗ {step_name} FAILURE - Updating metrics")
    
    async def _analyze_and_fix(self, output, expected):
        """Analyze failure and fix the code"""
        print(f"\nAnalyzing failure:")
        print(f"Expected: {expected}")
        print(f"Got: {output[:200]}...")
        # This would modify the implementation code block
    
    async def _add_recovery_test(self, step_name):
        """Add a new test to prevent this failure"""
        print(f"\nAdding recovery test for {step_name}")
        # This would add a new step to the prompt

# Example: How I use this during self-improvement
async def self_improve_component():
    agent = OrchestrationAgent()
    
    # Step 1: Basic Health Check
    success, marker = await agent.execute_verification_step(
        "health_check",
        "python3 -c \"import requests; assert requests.get('http://localhost:8000/health').json() == {'status': 'ok'}\"",
        "{'status': 'ok'}"
    )
    
    # Verify in transcript
    print(f"\nVerifying {marker} in transcript...")
    # rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl
    
    if not success:
        print("Step 1 failed, retrying after fix...")
        # Retry after fixing
        success, marker = await agent.execute_verification_step(
            "health_check_retry",
            "python3 -c \"import requests; assert requests.get('http://localhost:8000/health').json() == {'status': 'ok'}\"",
            "{'status': 'ok'}"
        )
    
    # Continue with more steps...

# Run the self-improvement cycle
if __name__ == "__main__":
    asyncio.run(self_improve_component())
```

## Key Patterns I Use

### 1. Real-Time Monitoring
I continuously monitor output to detect:
- Error patterns (Traceback, AssertionError, etc.)
- Stalled executions (no output for 2 minutes)
- Timeout conditions (5 minute max)

### 2. Intelligent Cancellation
When I detect problems, I immediately cancel to:
- Save resources
- Avoid runaway processes
- Get faster feedback

### 3. Transcript Verification
After every execution:
```bash
# I print a unique marker
MARKER_health_check_1737640800

# Then verify it exists in transcripts
rg "MARKER_health_check_1737640800" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl
```

### 4. Metric Updates
Based on execution results, I update the prompt's metrics:
- SUCCESS → increment success count
- FAILURE → increment failure count, fix code, add recovery test

## Integration with Self-Improving Prompts

### During Verification Steps

```python
# From SELF_IMPROVING_PROMPT_TEMPLATE.md
# Step 1: Basic Health Check
# Verification Command: python3 -c "import requests; assert requests.get('http://localhost:8000/health').json() == {'status': 'ok'}"

# I execute this via WebSocket:
async def verify_health_check():
    agent = OrchestrationAgent()
    
    # Execute and monitor
    success, marker = await agent.execute_verification_step(
        "health_check",
        command='python3 -c "import requests; assert requests.get(\'http://localhost:8000/health\').json() == {\'status\': \'ok\'}"',
        expected_output=""  # No output expected on success
    )
    
    # Update prompt based on result
    if success:
        # Update: Success: 1, Failure: 0
        await update_prompt_metrics(success=1)
    else:
        # Update: Success: 0, Failure: 1
        await update_prompt_metrics(failure=1)
        # Fix the implementation
        await fix_health_endpoint()
        # Add recovery test
        await add_recovery_test_for_health()
```

### During Integration Tests

```python
async def run_integration_test():
    """Run the component integration test"""
    
    test_command = "pytest tests/integration/test_state_manager.py -v"
    
    async with websockets.connect("ws://localhost:8003/ws/mcp") as ws:
        await ws.recv()  # Skip connection
        
        # Execute test
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {"command": test_command}
        }))
        
        # Monitor for specific patterns
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            
            if data.get('method') == 'process.output':
                output = data['params']['data']
                
                # Check for test results
                if "FAILED" in output:
                    # Cancel remaining tests
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "control",
                        "params": {"type": "CANCEL"}
                    }))
                    # Trigger recovery plan
                    await create_recovery_plan(output)
                
                elif "passed" in output and "failed" not in output:
                    # All tests passed!
                    print("Integration tests passed!")
```

## Real Example: Stress Test Execution

This is exactly what I did when fixing the stress test:

```python
async def run_stress_test():
    """Execute the stress test with real-time monitoring"""
    
    ws_uri = "ws://localhost:8003/ws/mcp"
    command = 'bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH python src/cc_executor/tests/stress/unified_stress_test_executor_v3.py src/cc_executor/tasks/haiku_single_task.json"'
    
    async with websockets.connect(ws_uri) as ws:
        await ws.recv()  # Connection message
        
        # Execute stress test
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {"command": command}
        }))
        
        # Monitor Claude's output
        claude_output = ""
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            
            if data.get('method') == 'process.output':
                output = data['params']['data']
                
                # Look for Claude's haiku
                if "syllables" in output or "nature" in output:
                    claude_output += output
                    print(f"Claude generating: {output}", end='', flush=True)
                
                # Check for errors
                elif "command not found" in output:
                    print("ERROR: Claude not in PATH!")
                    # Would trigger fix here
                
            elif data.get('method') == 'process.completed':
                exit_code = data['params']['exit_code']
                print(f"\nStress test completed with exit code: {exit_code}")
                print(f"Claude output length: {len(claude_output)} characters")
                break
```

## Summary

As an orchestration agent, I use the WebSocket MCP protocol to:

1. **Execute verification commands** from self-improving prompts
2. **Monitor output in real-time** to detect errors early
3. **Cancel failing executions** to save time and resources
4. **Update metrics** based on success/failure
5. **Verify executions** happened via transcript checks
6. **Make intelligent decisions** about when to retry, fix, or escalate

This bidirectional communication is essential for the self-improvement cycle, allowing me to:
- Get immediate feedback on code changes
- Detect and recover from failures quickly
- Maintain accurate success/failure metrics
- Ensure all executions are verifiable

The WebSocket MCP protocol is the foundation that enables me to orchestrate reliable, verifiable self-improvement cycles.