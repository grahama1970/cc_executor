# Orchestrator Decision Flow: Real-Time Ambiguity Reduction

## Overview

As an orchestration agent, I receive continuous updates via WebSocket and make decisions about what commands to execute next. This document shows my actual decision-making process during self-improvement cycles.

## Core Decision Loop

```python
class IntelligentOrchestrator:
    """My real decision-making process as Claude"""
    
    def __init__(self):
        self.websocket_uri = "ws://localhost:8003/ws/mcp"
        self.ambiguities = {}  # Track what I don't know yet
        self.learned_facts = {}  # Track what I've discovered
        self.recovery_tests = []  # Tests to prevent future failures
    
    async def reduce_ambiguity_loop(self, initial_task):
        """Main loop: Execute, observe, decide, repeat"""
        
        # Start with high ambiguity
        self.ambiguities = {
            "environment": "unknown",
            "dependencies": "unchecked",
            "correct_command": "guessing",
            "expected_output": "uncertain"
        }
        
        current_command = initial_task
        iteration = 0
        
        while self.ambiguities:
            iteration += 1
            print(f"\n=== Iteration {iteration} ===")
            print(f"Ambiguities: {list(self.ambiguities.keys())}")
            print(f"Executing: {current_command}")
            
            # Execute and observe
            result = await self.execute_and_observe(current_command)
            
            # Make decisions based on output
            next_command = await self.decide_next_action(result)
            
            if not next_command:
                print("✓ All ambiguities resolved!")
                break
                
            current_command = next_command
    
    async def execute_and_observe(self, command):
        """Execute command and extract learnings"""
        
        async with websockets.connect(self.websocket_uri) as ws:
            await ws.recv()  # Skip connection
            
            # Execute
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "execute",
                "params": {"command": command}
            }))
            
            # Collect all output
            output = ""
            exit_code = None
            patterns_found = []
            
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data.get('method') == 'process.output':
                    chunk = data['params']['data']
                    output += chunk
                    
                    # Real-time pattern detection
                    patterns_found.extend(self.detect_patterns(chunk))
                    
                elif data.get('method') == 'process.completed':
                    exit_code = data['params']['exit_code']
                    break
            
            return {
                "command": command,
                "output": output,
                "exit_code": exit_code,
                "patterns": patterns_found
            }
    
    def detect_patterns(self, output):
        """Detect patterns that reduce ambiguity"""
        patterns = []
        
        # Environment detection
        if "Python" in output and "version" in output:
            patterns.append(("python_version", output))
        
        # Error patterns
        if "ModuleNotFoundError" in output:
            missing_module = output.split("'")[1]
            patterns.append(("missing_module", missing_module))
        
        if "command not found" in output:
            missing_cmd = output.split(":")[0].strip()
            patterns.append(("missing_command", missing_cmd))
        
        if "Connection refused" in output:
            patterns.append(("service_down", output))
        
        if "AssertionError" in output:
            patterns.append(("assertion_failed", output))
        
        # Success patterns
        if '{"status": "ok"}' in output:
            patterns.append(("health_check_success", True))
        
        if "All tests passed" in output:
            patterns.append(("tests_passed", True))
        
        return patterns
    
    async def decide_next_action(self, result):
        """Decide what to do based on observations"""
        
        print(f"\nObserved patterns: {result['patterns']}")
        
        # Process each pattern to reduce ambiguity
        for pattern_type, value in result['patterns']:
            
            if pattern_type == "missing_module":
                # Ambiguity: Missing dependency
                self.learned_facts['missing_modules'] = self.learned_facts.get('missing_modules', [])
                self.learned_facts['missing_modules'].append(value)
                
                # Decision: Install it
                return f"uv pip install {value}"
            
            elif pattern_type == "missing_command":
                # Ambiguity: Command not in PATH
                if value == "claude":
                    # Decision: Use full path
                    self.learned_facts['claude_path'] = "/home/graham/.nvm/versions/node/v22.15.0/bin/claude"
                    return 'bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH claude --version"'
                
            elif pattern_type == "service_down":
                # Ambiguity: Service not running
                self.learned_facts['service_status'] = "down"
                
                # Decision: Start the service
                return "cd src/cc_executor && docker-compose up -d"
            
            elif pattern_type == "assertion_failed":
                # Ambiguity: Expected output doesn't match
                self.analyze_assertion_failure(result['output'])
                
                # Decision: Add recovery test
                return self.create_recovery_test(result)
            
            elif pattern_type == "health_check_success":
                # Ambiguity resolved: Service is healthy
                del self.ambiguities['environment']
                self.learned_facts['service_healthy'] = True
        
        # Check exit code patterns
        if result['exit_code'] == 127:
            # Command not found
            return self.find_correct_command(result['command'])
        
        elif result['exit_code'] != 0:
            # General failure - need more info
            return self.create_diagnostic_command(result)
        
        # If we still have ambiguities, probe further
        if 'dependencies' in self.ambiguities:
            del self.ambiguities['dependencies']
            return "pip list | grep -E 'fastapi|requests|websockets'"
        
        if 'environment' in self.ambiguities:
            del self.ambiguities['environment']
            return "python3 --version && node --version && claude --version"
        
        return None  # All ambiguities resolved
    
    def analyze_assertion_failure(self, output):
        """Extract details from assertion failure"""
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if "AssertionError" in line and i > 0:
                # Previous line often has the comparison
                comparison = lines[i-1]
                self.learned_facts['failed_assertion'] = comparison
                
                # Extract expected vs actual
                if "!=" in comparison:
                    parts = comparison.split("!=")
                    self.learned_facts['expected'] = parts[0].strip()
                    self.learned_facts['actual'] = parts[1].strip()
    
    def create_recovery_test(self, result):
        """Create a test to prevent this failure"""
        test_name = f"test_recovery_{len(self.recovery_tests)}"
        
        # Generate test based on failure
        if 'actual' in self.learned_facts:
            test_code = f'''
def {test_name}():
    """Recovery test for: {result['command'][:50]}..."""
    # This failed with: {self.learned_facts.get('actual', 'unknown')}
    # Expected: {self.learned_facts.get('expected', 'unknown')}
    
    # Add defensive check
    result = execute_command("{result['command']}")
    assert result != {self.learned_facts.get('actual', 'unknown')}, \\
        "Still getting the wrong result"
'''
            self.recovery_tests.append(test_code)
        
        # Return command to verify fix
        return result['command']  # Retry original command
    
    def create_diagnostic_command(self, result):
        """Create command to diagnose failure"""
        
        # Based on exit code and output, decide what to check
        if "port" in result['output'].lower():
            return "netstat -tuln | grep 8000"
        
        if "permission" in result['output'].lower():
            return f"ls -la {result['command'].split()[-1]}"
        
        if "timeout" in result['output'].lower():
            return "curl -v http://localhost:8000/health"
        
        # Default: check environment
        return "env | grep -E 'PATH|PYTHONPATH|PORT'"

# Example: Self-Improvement Execution
async def self_improve_with_ambiguity_reduction():
    """Real example of how I self-improve"""
    
    orchestrator = IntelligentOrchestrator()
    
    # Start with basic health check
    await orchestrator.reduce_ambiguity_loop(
        'python3 -c "import requests; assert requests.get(\'http://localhost:8000/health\').json() == {\'status\': \'ok\'}"'
    )
    
    print("\n=== Final State ===")
    print(f"Learned facts: {orchestrator.learned_facts}")
    print(f"Recovery tests: {len(orchestrator.recovery_tests)}")

# Real execution trace
if __name__ == "__main__":
    asyncio.run(self_improve_with_ambiguity_reduction())
```

## Real Example: Fixing the Stress Test

Here's my actual decision flow when fixing the stress test:

```python
async def fix_stress_test_decision_flow():
    """My actual thought process fixing the stress test"""
    
    decisions = []
    
    # Iteration 1: Try to run the test
    result1 = await execute_and_observe(
        "python src/cc_executor/tests/stress/unified_stress_test_executor_v3.py"
    )
    # Output: "Sending echo commands..."
    # Decision: Test is using echo instead of claude
    decisions.append("Need to modify test to use actual claude command")
    
    # Iteration 2: Check if claude is available
    result2 = await execute_and_observe("which claude")
    # Output: "/home/graham/.nvm/versions/node/v22.15.0/bin/claude"
    # Decision: Claude exists but may not be in PATH for subprocess
    decisions.append("Use full path or modify PATH")
    
    # Iteration 3: Test claude directly
    result3 = await execute_and_observe(
        'claude --print "test" --output-format stream-json'
    )
    # Output: JSON events streaming
    # Decision: Claude works, need to integrate into stress test
    decisions.append("Modify stress test to use this exact command")
    
    # Iteration 4: Run modified test via WebSocket
    result4 = await execute_and_observe(
        'python src/cc_executor/tests/stress/unified_stress_test_executor_v3.py'
    )
    # Output: "Command not allowed"
    # Decision: WebSocket server is blocking the command
    decisions.append("Check ALLOWED_COMMANDS in docker-compose.yml")
    
    # Iteration 5: Update allowed commands
    result5 = await execute_and_observe(
        "grep ALLOWED_COMMANDS src/cc_executor/docker-compose.yml"
    )
    # Output: Missing 'bash'
    # Decision: Add bash to allowed commands
    decisions.append("Update docker-compose.yml to include bash")
    
    # Iteration 6: Test with bash wrapper
    result6 = await execute_and_observe(
        'bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH claude --print \\"Hello\\""'
    )
    # Output: "Hello" from Claude
    # Decision: This pattern works!
    decisions.append("Use bash -c with PATH for all claude executions")
    
    return decisions
```

## Decision Patterns

### 1. Error-Driven Decisions

```python
ERROR_TO_ACTION = {
    "ModuleNotFoundError": lambda module: f"uv pip install {module}",
    "command not found": lambda cmd: f"which {cmd} || echo 'Need to install {cmd}'",
    "Connection refused": lambda _: "docker-compose ps && docker-compose up -d",
    "Permission denied": lambda file: f"chmod +x {file}",
    "No such file": lambda file: f"ls -la $(dirname {file})",
    "ALLOWED_COMMANDS": lambda cmd: "Update docker-compose.yml ALLOWED_COMMANDS",
}

def decide_from_error(output):
    for error, action in ERROR_TO_ACTION.items():
        if error in output:
            return action(extract_context(output, error))
    return None
```

### 2. Success-Driven Decisions

```python
SUCCESS_PATTERNS = {
    '{"status": "ok"}': "Health check passed, proceed to next test",
    "All tests passed": "Ready to graduate component",
    "Process started: PID": "Monitor for output patterns",
    "10:1 ratio achieved": "Convert prompt to Python file",
}

def decide_from_success(output):
    for pattern, next_step in SUCCESS_PATTERNS.items():
        if pattern in output:
            return next_step
    return None
```

### 3. Ambiguity Resolution Chain

```python
AMBIGUITY_CHAIN = [
    # (Check command, If contains, Resolution command)
    ("python3 --version", "not found", "apt-get install python3"),
    ("which claude", "not found", "echo 'Claude not installed'"),
    ("docker ps", "not running", "docker-compose up -d"),
    ("curl localhost:8000", "refused", "Start the service first"),
    ("env | grep PATH", "missing", "export PATH=/correct/path:$PATH"),
]

async def resolve_ambiguities():
    for check_cmd, error_pattern, fix_cmd in AMBIGUITY_CHAIN:
        result = await execute_and_observe(check_cmd)
        if error_pattern in result['output']:
            await execute_and_observe(fix_cmd)
```

## Recovery Test Generation

When I encounter failures, I automatically generate recovery tests:

```python
class RecoveryTestGenerator:
    def generate_from_failure(self, failure_info):
        """Generate test to prevent this failure"""
        
        test_template = '''
def test_prevents_{failure_type}():
    """
    Recovery test for: {original_command}
    Failed with: {error_message}
    Exit code: {exit_code}
    """
    # Defensive checks
    {defensive_checks}
    
    # Attempt original operation
    result = {test_operation}
    
    # Verify it doesn't fail the same way
    assert "{error_pattern}" not in result
    assert result.exit_code == 0
'''
        
        # Generate defensive checks based on failure
        defensive_checks = self.generate_defensive_checks(failure_info)
        
        return test_template.format(
            failure_type=self.classify_failure(failure_info),
            original_command=failure_info['command'],
            error_message=failure_info['error'],
            exit_code=failure_info['exit_code'],
            defensive_checks=defensive_checks,
            test_operation=self.safe_operation(failure_info),
            error_pattern=self.extract_error_pattern(failure_info)
        )
```

## Summary

As an orchestration agent, my decision flow is:

1. **Start with ambiguity** - I don't know what will work
2. **Execute and observe** - Try something and watch what happens
3. **Detect patterns** - Extract meaningful information from output
4. **Reduce ambiguity** - Each observation teaches me something
5. **Make decisions** - Choose next action based on learnings
6. **Add recovery tests** - Prevent the same failure twice
7. **Iterate until success** - Keep refining until it works

This approach ensures:
- **No hidden failures** - I see everything via WebSocket
- **Rapid learning** - Each execution reduces ambiguity
- **Defensive programming** - Recovery tests prevent regressions
- **Verifiable progress** - All decisions are logged and traceable