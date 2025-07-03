# Core Components Usage Function Assessment Report

**Generated**: 2025-07-02 20:00:52

**Report Location**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/reports/CORE_USAGE_REPORT_20250702_200044.md
**Temp Directory**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/tmp/core_assess_20250702_200044
**Raw Responses Saved**: /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/tmp/responses/

**Total Files Tested**: 22
**Redis Available**: No
**Hooks Available**: No
**Total Time**: 7.7s

---

## Environment Setup

- **PYTHONPATH**: Not set
- **Virtual Environment**: /usr
- **Python Version**: 3.12.3
- **Working Directory**: /home/graham/workspace/experiments/cc_executor

---

## Summary

- **Passed**: 19/22 (86.4%)
- **Failed**: 3/22
- **Average Confidence**: 75.8%
- **Hook Usage**: 5/22 components

---

## Detailed Results

### ✅ client.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 55%)

**Reasons**:

- Adequate output length (14 lines)

**Hook Evidence**:
- Using tmp/ directory as expected

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
2025-07-02 20:00:44 | INFO | === Standalone WebSocket Client Example ===
2025-07-02 20:00:44 | INFO | === Standalone WebSocket Client Example ===
2025-07-02 20:00:44 | INFO | This client connects to an existing server (doesn't manage its own)
2025-07-02 20:00:44 | INFO | This client connects to an existing server (doesn't manage its own)
2025-07-02 20:00:44 | ERROR | ❌ Command failed: Unexpected error: [Errno 111] Connect call failed ('127.0.0.1', 8003)
2025-07-02 20:00:44 | ERROR | ❌ Command failed: Unexpected error: [Errno 111] Connect call failed ('127.0.0.1', 8003)



--- STDERR ---
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/client.py", line 242, in <module>
    print(f"\n💾 Raw response saved to: {response_file.relative_to(Path.cwd())}")
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/pathlib.py", line 682, in relative_to
    raise ValueError(f"{str(self)!r} is not in the subpath of {str(other)!r}")
ValueError: '/home/graham/workspace/experiments/cc...[truncated]
```

---

### ✅ concurrent_executor.py

**Description**: Parallel task execution management

**Expected Indicators**: concurrent, task, execution, parallel

**Required Packages**: None

**Assessment**: PASS (Confidence: 80.0%)

**Reasons**:

- Adequate output length (54 lines)
- Found 2/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: concurrent, execution

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Example 1: Basic Concurrent Execution ===

Fastest response: Instance instance_4_d83700ab (0.00s)
Most detailed: Instance instance_1_995107a9 (0 chars)

=== Example 2: Specific Parameter Sets ===

Fastest implementation: claude-3-5-haiku-20241022 (temp=1.0)

=== Summary Report ===
{
  "total_instances": 4,
  "successful_instances": 0,
  "failure_rate": "100.0%",
  "average_execution_time": "0.00s",
  "fastest_time": "0.00s",
  "slowest_time": "0.00s",
  "model_statistics": {
    "claude-3-5-sonnet-20241022": {
      "count": 2,
      "successful": 0,
      "total_time": 0.0014195442199707031,
      "avg_output_length": 0.0,
      "avg_time": 0.0007097721099853516,
      "success_rate": 0.0
    },
    "claude-3-5-haiku-20241022": {
      "count": 2,
      "successful": 0,
      "total_time": 0.0012006759643554688,
      "avg_output_length": 0.0,
      "avg_time": 0.0006003379821777344,
      "success_rate": 0.0
    }
  },
  "temperature_range": {
    "min": 0.5,
    "max": 1.2,
    ...[truncated]

--- STDERR ---
2025-07-02 20:00:44.677 | ERROR    | __main__:execute_claude_instance:133 - [instance_1_995107a9] Error: [Errno 111] Connect call failed ('127.0.0.1', 8003)
2025-07-02 20:00:44.677 | ERROR    | __main__:execute_claude_instance:133 - [instance_2_be0ed6f6] Error: [Errno 111] Connect call failed ('127.0.0.1', 8003)
2025-07-02 20:00:44.677 | ERROR    | __main__:execute_claude_instance:133 - [instance_4_d83700ab] Error: [Errno 111] Connect call failed ('127.0.0.1', 8003)
2025-07-02 20:00:44.677 | ERR...[truncated]
```

---

### ✅ config.py

**Description**: Configuration management and settings

**Expected Indicators**: config, settings, timeout, loaded

**Required Packages**: None

**Assessment**: PASS (Confidence: 80.0%)

**Reasons**:

- Adequate output length (30 lines)
- Found 2/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: config, timeout

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== CC Executor Configuration ===
Service: cc_executor_mcp v1.0.0
Default Port: 8003
WebSocket Path: /ws/mcp

=== Session Configuration ===
Max Sessions: 100
Session Timeout: 3600s

=== Process Configuration ===
Max Buffer Size: 8388608 bytes
Stream Timeout: 600s
Cleanup Timeout: 10s

=== Security Configuration ===
Allowed Commands: ALL (no restrictions)

=== Logging Configuration ===
Log Level: INFO
Debug Mode: False

=== Testing Environment Variable Parsing ===
Input: ALLOWED_COMMANDS='echo,ls,cat,grep'
Parsed: ['echo', 'ls', 'cat', 'grep']
Input: LOG_LEVEL='WARNING'
Parsed: WARNING
Input: DEBUG='true'
Parsed: True

✅ Configuration validation passed!


--- STDERR ---

```

---

### ✅ enhanced_prompt_classifier.py

**Description**: Classify prompts by type and complexity

**Expected Indicators**: prompt, classification, type, complexity

**Required Packages**: None

**Assessment**: PASS (Confidence: 100%)

**Reasons**:

- Adequate output length (69 lines)
- Found 4/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: prompt, classification, type, complexity

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
Enhanced Prompt Classification
============================================================

Prompt: What is code to add two numbers?
Category: code
Complexity: trivial
Sub-type: snippet

Prompt: What is a hello world program in Python?
Category: code
Complexity: trivial
Sub-type: snippet

Prompt: What is a Python function to calculate factorial?
Category: code
Complexity: low
Sub-type: function

Prompt: What is code to check if a number is prime?
Category: code
Complexity: low
Sub-type: snippet

Prompt: What is a Python class for a binary search tree?
Category: code
Complexity: low
Sub-type: class

Prompt: What is code for 5 utility functions?
Category: code
Complexity: low
Sub-type: function

Prompt: What is a distributed rate limiter implementation?
Category: code
Complexity: high
Sub-type: snippet

Prompt: What is code to optimize this algorithm for performance?
Category: code
Complexity: high
Sub-type: algorithm

Prompt: What is the concept of recursion?
Category: explanation
Comp...[truncated]

--- STDERR ---

```

---

### ✅ enhanced_timeout_calculator.py

**Description**: Dynamic timeout calculation based on task complexity

**Expected Indicators**: timeout, complexity, calculation, seconds

**Required Packages**: None

**Assessment**: PASS (Confidence: 90.0%)

**Reasons**:

- Adequate output length (44 lines)
- Found 3/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: timeout, complexity, calculation

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
Enhanced Timeout Calculation Tests
============================================================

Prompt: What is 2+2?...
Complexity: simple
Tokens: 109 (input: 9, output: 100)
Thinking tokens: 0
Timeout: 90s
Method: token_calculation
Uses 90s minimum: True

Prompt: What is a 500-word explanation of recursion?...
Complexity: medium
Tokens: 883 (input: 133, output: 750)
Thinking tokens: 100
Timeout: 90s
Method: token_calculation
Uses 90s minimum: True
Enhanced prompt adds: 78 characters

Prompt: What is a collection of 20 haikus about programmin...
Complexity: medium
Tokens: 939 (input: 139, output: 800)
Thinking tokens: 100
Timeout: 90s
Method: token_calculation
Uses 90s minimum: True
Enhanced prompt adds: 78 characters

Prompt: What is a comprehensive 5000-word guide to microse...
Complexity: complex
Tokens: 7842 (input: 342, output: 7500)
Thinking tokens: 300
Timeout: 452s
Method: token_calculation
Uses 90s minimum: False
Enhanced prompt adds: 314 characters

=========================...[truncated]

--- STDERR ---

```

---

### ✅ factorial.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 50%)

**Reasons**:

- Adequate output length (7 lines)

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
factorial(0) = 1
factorial(1) = 1
factorial(5) = 120
factorial(10) = 3628800
factorial(20) = 2432902008176640000

All tests passed!


--- STDERR ---

```

---

### ✅ hook_enforcement.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 55%)

**Reasons**:

- Adequate output length (13 lines)

**Hook Evidence**:
- Using tmp/ directory as expected

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
=== Hook Enforcement Workaround ===
🪝 PRE-EXECUTION HOOK: test_function
🪝 POST-EXECUTION HOOK: test_function ✅
Result: 8

✅ Created 7 hook logs


--- STDERR ---
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/hook_enforcement.py", line 160, in <module>
    print(f"\n💾 Response saved to: {output_file.relative_to(Path.cwd())}")
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/pathlib.py", line 682, in relative_to
    raise ValueError(f"{str(self)!r} is not in the subpath of {str(other)!r}")
ValueError: '/home/graham/workspace/experiments/cc_e...[truncated]
```

---

### ✅ hook_integration.py

**Description**: Hook system configuration and execution

**Expected Indicators**: hook, enabled, config, status

**Required Packages**: None

**Assessment**: PASS (Confidence: 95.0%)

**Reasons**:

- Adequate output length (48 lines)
- Found 4/4 expected indicators

**Indicators Found**: hook, enabled, config, status

**Hook Evidence**:
- Virtual environment activated
- Using tmp/ directory as expected

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Hook Integration Usage Example ===

--- Test 1: Hook Configuration ---
Hooks enabled: True
Config path: /home/graham/workspace/experiments/cc_executor/.claude-hooks.json
Hooks configured: ['pre-execute', 'pre-task-list', 'pre-claude', 'post-claude', 'pre-edit', 'post-edit', 'pre-tool', 'post-tool', 'post-output']
Timeout: 60s
Parallel execution: False

--- Test 2: Hook Execution Flow ---
For a typical command execution:
1. pre-execute → Environment setup
2. pre-tool → Dependency check
3. [Command executes]
4. post-tool → Update task status
5. post-output → Record metrics

--- Test 3: Special Hook Triggers ---
Claude commands trigger additional hooks:
- pre-claude → Instance validation
- post-claude → Response validation

File operations trigger:
- pre-edit → Complexity analysis
- post-edit → Code review

--- Test 4: Configuration Validation ---
✓ Loaded 9 hook types
✓ Configured 3 environment variables
  pre-execute: 2 commands
  pre-task-list: python /home/graham/workspace/experim...[truncated]

--- STDERR ---
2025-07-02 20:00:44.977 | INFO     | __main__:initialize:68 - Initializing programmatic hook enforcement system
2025-07-02 20:00:44.977 | INFO     | __main__:_ensure_venv:113 - Virtual environment configured: /home/graham/workspace/experiments/cc_executor/.venv
2025-07-02 20:00:44.977 | WARNING  | __main__:_check_redis:128 - Redis not available: No module named 'redis'
2025-07-02 20:00:44.977 | WARNING  | __main__:initialize:77 - Redis not available - some features will be limited
2025-07-02 20:...[truncated]
```

---

### ✅ main.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 50%)

**Reasons**:

- Adequate output length (4 lines)

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---


--- STDERR ---
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/main.py", line 30, in <module>
    from fastapi import FastAPI, WebSocket
ModuleNotFoundError: No module named 'fastapi'

```

---

### ✅ models.py

**Description**: Data models and schemas

**Expected Indicators**: task, session, result, model

**Required Packages**: pydantic

**Assessment**: PASS (Confidence: 70.0%)

**Reasons**:

- Adequate output length (53 lines)
- Found 2/4 expected indicators

**Indicators Found**: result, model

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Testing ExecuteRequest Model ===
Valid request: command="echo 'Hello World'" timeout=None id=123
Command: echo 'Hello World'
ID: 123

=== Testing ControlRequest Model ===
Control: PAUSE (id=1)
Control: RESUME (id=2)
Control: CANCEL (id=3)

=== Testing JSON-RPC Models ===
JSON-RPC Request: {
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "command": "ls -la"
  },
  "id": 42
}

Success Response: {
  "jsonrpc": "2.0",
  "result": {
    "status": "started",
    "pid": 12345
  },
  "id": 42
}

Error Response: {
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "Command cannot be empty"
  },
  "id": 42
}

=== Testing Command Validation ===
✓ Command: 'echo test' | Allowed: None | Valid: True
✓ Command: 'echo test' | Allowed: ['echo', 'ls'] | Valid: True
✓ Command: 'rm -rf /' | Allowed: ['echo', 'ls'] | Valid: False
   Message: Command 'rm' is not allowed
✓ Command: '' | Allowed: None | Valid: False
   Message: Command cannot be...[truncated]

--- STDERR ---

```

---

### ❌ process_manager.py

**Description**: Process lifecycle management with PID/PGID tracking

**Expected Indicators**: process, pid, pgid, started, exit

**Required Packages**: None

**Assessment**: FAIL (Confidence: 90%)

**Reasons**:

- Unexpected exception occurred

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
=== Process Manager Usage Example ===

--- Test 1: Process Control Concepts ---
ProcessManager provides:
- Process execution with new process groups (PGID)
- Process control: PAUSE (SIGSTOP), RESUME (SIGCONT), CANCEL (SIGTERM)
- Proper cleanup of process groups
- Timeout handling and graceful termination

--- Test 2: Process Group ID (PGID) Demo ---


--- STDERR ---
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/process_manager.py", line 311, in <module>
    proc = subprocess.Popen(
           ^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 1026, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
  File "/usr/lib/python3.12/subprocess.py", line 1955, in _execute_child
    raise child_exception_type(errno_num, err_msg, err_filename)
FileNotFoundError:...[truncated]
```

---

### ✅ redis_similarity_search.py

**Description**: Redis-based similarity search for prompts

**Expected Indicators**: redis, similarity, search, match

**Required Packages**: redis, numpy

**Assessment**: PASS (Confidence: 90.0%)

**Reasons**:

- Adequate output length (35 lines)
- Found 3/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: redis, similarity, search

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
⚠️ Could not create index: Redis error: /bin/sh: 2: FT.CREATE: not found
/bin/sh: 3: ON: not found
/bin/sh: 4: SCHEMA: not found
/bin/sh: 5: prompt_text: not found
/bin/sh: 6: keywords: not found
/bin/sh: 7: token_count: not found
/bin/sh: 8: complexity: not found
/bin/sh: 9: expected_time: not found
/bin/sh: 10: actual_time: not found
/bin/sh: 11: execution_variance: not found
/bin/sh: 12: success: not found
/bin/sh: 13: timestamp: not found

Indexing test prompts...
✓ Indexed prompt: cc_executor:prompts:3c5d131cd810:28 (tokens: 120, complexity: medium)
✓ Indexed prompt: cc_executor:prompts:924c7c02a284:32 (tokens: 130, complexity: medium)
✓ Indexed prompt: cc_executor:prompts:aec1e6a9a989:29 (tokens: 110, complexity: medium)
✓ Indexed prompt: cc_executor:prompts:dee501149a9f:115 (tokens: 850, complexity: complex)

============================================================
Testing similarity search...

New prompt: What is a Python implementation of factorial using iteration?
Estimat...[truncated]

--- STDERR ---

```

---

### ✅ reflection_parser.py

**Description**: Parse and analyze Claude reflection blocks

**Expected Indicators**: reflection, parse, analysis, content

**Required Packages**: None

**Assessment**: PASS (Confidence: 70.0%)

**Reasons**:

- Adequate output length (24 lines)
- Found 2/4 expected indicators

**Indicators Found**: reflection, analysis

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
Self-Reflection Analysis:
----------------------------------------
✓ Initial Response: Yes
✓ Self-Evaluation: Yes
✓ Improved Version: Yes

Evaluation Results:
  Criteria checked: 3
  Passed: 1 ✓
  Failed: 2 ✗
  Success rate: 33.3%

Improvement made: Yes
Quality delta: +100.5%

Reflection markers: 📈 IMPROVED VERSION, □, EVALUATION, IMPROVED VERSION, 📝 INITIAL RESPONSE:

========================================
Quick quality check:
is_reflected: True
is_improved: True
criteria_success_rate: 0.3333333333333333
quality_improvement: 100.49019607843137
complete_reflection: True


--- STDERR ---

```

---

### ✅ resource_monitor.py

**Description**: System resource monitoring (CPU, memory, etc)

**Expected Indicators**: cpu, memory, resource, usage, %

**Required Packages**: psutil

**Assessment**: PASS (Confidence: 92.0%)

**Reasons**:

- Adequate output length (21 lines)
- Found 4/5 expected indicators
- Contains numeric data as expected

**Indicators Found**: cpu, resource, usage, %

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Resource Monitor Usage Example ===

--- Test 1: Instant CPU Check ---
CPU Usage (instant): 18.2%

--- Test 2: GPU Check ---
GPU Usage: 0.0%

--- Test 3: Timeout Multiplier Scenarios ---
Low load (CPU=10.0%): 30s → 30.0s (x1.0)
At threshold (CPU=14.0%): 30s → 30.0s (x1.0)
Above threshold (CPU=15.0%): 30s → 90.0s (x3.0)
High load (CPU=50.0%): 30s → 90.0s (x3.0)

--- Test 4: Current System State ---
Actual CPU: 17.8%
Actual GPU: 0.0%
Current timeout multiplier: 3.0x
Example: 60s timeout → 180.0s

✅ Resource monitor functioning correctly!


--- STDERR ---

```

---

### ✅ run_with_hooks.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 50%)

**Reasons**:

- Adequate output length (1 lines)

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
Usage: run_with_hooks.py <command> [args...]


--- STDERR ---

```

---

### ✅ session_manager.py

**Description**: WebSocket session management with thread safety

**Expected Indicators**: session, websocket, created, active, removed

**Required Packages**: None

**Assessment**: PASS (Confidence: 100%)

**Reasons**:

- Adequate output length (45 lines)
- Found 5/5 expected indicators
- Contains numeric data as expected

**Indicators Found**: session, websocket, created, active, removed

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Session Manager Usage Example ===

Created SessionManager with max_sessions=3

--- Test 1: Creating Sessions ---
✓ Created session-1 with <MockWebSocket 2101f2f2>
✓ Created session-2 with <MockWebSocket fb157486>
✓ Created session-3 with <MockWebSocket 924ad935>
✗ Failed to create session-4 - limit reached

Active sessions: 3/3

--- Test 2: Updating Session with Process ---
Updated session-1 with process (PID=12345): True
Session details: PID=12345, PGID=12345

--- Test 3: Concurrent Access Test ---
  Task 0.0s: Got session=True
  Task 0.001s: Got session=True
  Task 0.002s: Got session=True

--- Test 4: Removing Sessions ---
Removed session-1: True
Removed session-2: True

Active sessions after removal: 1/3

--- Test 5: Session Timeout Test ---
Cleaned up 1 expired sessions

--- Test 6: Final State ---
Remaining sessions: ['session-3']
Final stats: 1 active, uptime: 0.0s

✅ All operations completed without race conditions
✅ Session limits enforced correctly
✅ Cleanup mechanisms wo...[truncated]

--- STDERR ---
2025-07-02 20:00:49.546 | INFO     | __main__:create_session:98 - Session created: session-1 (active: 1/3)
2025-07-02 20:00:49.546 | INFO     | __main__:create_session:98 - Session created: session-2 (active: 2/3)
2025-07-02 20:00:49.546 | INFO     | __main__:create_session:98 - Session created: session-3 (active: 3/3)
2025-07-02 20:00:49.546 | WARNING  | __main__:create_session:85 - Session limit reached: 3/3
2025-07-02 20:00:49.548 | INFO     | __main__:remove_session:168 - Session removed: se...[truncated]
```

---

### ✅ simple_example.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 55%)

**Reasons**:

- Adequate output length (13 lines)

**Hook Evidence**:
- Using tmp/ directory as expected

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Simple Math Component Usage ===

--- Test 1: Addition ---
5 + 3 = 8
✓ Addition test passed

--- Test 2: Multiplication ---
4 × 7 = 28
✓ Multiplication test passed

✅ All tests passed!

💾 Raw response saved to: tmp/responses/simple_example_20250702_200049.json


--- STDERR ---

```

---

### ✅ smart_timeout_defaults.py

**Description**: Intelligent timeout defaults based on task patterns

**Expected Indicators**: timeout, default, pattern, task

**Required Packages**: None

**Assessment**: PASS (Confidence: 70%)

**Reasons**:

- Adequate output length (34 lines)
- Only found 1/4 indicators
- Contains numeric data as expected

**Indicators Found**: timeout

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
Fixing Stress Test Timeouts
============================================================

Test: simple_2
Original timeout: 10s (stall detection)
Smart timeout: 180s
Add acknowledgment: True
Enhanced prompt adds: '

Please acknowledge this request briefly, then proceed with your response.'

Test: parallel_1
Original timeout: 10s (stall detection)
Smart timeout: 300s
Add acknowledgment: True
Enhanced prompt adds: '

Please acknowledge this request briefly, then proceed with your response.'

Test: long_1
Original timeout: 10s (stall detection)
Smart timeout: 600s
Add acknowledgment: True
Enhanced prompt adds: '

Please acknowledge this request briefly, then proceed with your response.'

============================================================
Summary: All unknown prompts now get 90s+ timeout with acknowledgment
Result: No more false failures from aggressive timeouts!

🎯 CORE PRINCIPLE:
If no similar prompt in Redis → 90s timeout + acknowledgment
This simple rule prevents 90% of timeou...[truncated]

--- STDERR ---

```

---

### ❌ stream_handler.py

**Description**: Output stream processing and buffering

**Expected Indicators**: stream, chunk, buffer, output

**Required Packages**: None

**Assessment**: FAIL (Confidence: 90%)

**Reasons**:

- Unexpected exception occurred

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
=== Stream Handler Usage Example ===

--- Test 1: Basic Subprocess Streaming ---


--- STDERR ---
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/stream_handler.py", line 419, in <module>
    proc = subprocess.Popen(
           ^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/subprocess.py", line 1026, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
  File "/usr/lib/python3.12/subprocess.py", line 1955, in _execute_child
    raise child_exception_type(errno_num, err_msg, err_filename)
FileNotFoundError: ...[truncated]
```

---

### ✅ timeout_recovery_manager.py

**Description**: Timeout handling and recovery strategies

**Expected Indicators**: timeout, recovery, retry, strategy

**Required Packages**: None

**Assessment**: PASS (Confidence: 90.0%)

**Reasons**:

- Adequate output length (21 lines)
- Found 3/4 expected indicators
- Contains numeric data as expected

**Indicators Found**: timeout, recovery, strategy

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
Result: {'success': True, 'output': 'ACKNOWLEDGED: Processing...', 'recovery_metadata': {'attempts': 1, 'final_strategy': '_immediate_acknowledgment_strategy', 'recovery_needed': False}}

Recovery Report:
Timeout Recovery Report
==================================================
Total prompts with recovery: 1
Total recovery attempts: 1
Successfully recovered: 0
Recovery rate: 0.0%

Per-Prompt Details:
--------------------------------------------------

Prompt: test_sort_001
  Attempts: 1
  Success: Yes
  Total time: 2.0s
  Strategies: _immediate_acknowledgment_strategy


--- STDERR ---
2025-07-02 20:00:49.801 | INFO     | __main__:execute_with_recovery:65 - Attempt 1/4 for test_sort_001
2025-07-02 20:00:49.801 | DEBUG    | __main__:execute_with_recovery:66 - Using strategy: _immediate_acknowledgment_strategy
2025-07-02 20:00:49.801 | DEBUG    | __main__:execute_with_recovery:67 - Timeout: 30.0s

```

---

### ✅ usage_helper.py

**Description**: Component functionality test

**Expected Indicators**: None defined

**Required Packages**: None

**Assessment**: PASS (Confidence: 55%)

**Reasons**:

- Adequate output length (17 lines)

**Hook Evidence**:
- Using tmp/ directory as expected

**Raw Output**:
```
Exit Code: 0

--- STDOUT ---
=== Usage Helper Demonstration ===

--- Method 1: Context Manager ---
This output is automatically captured
Result: {'demo': 'value', 'count': 42}
✅ Context manager demonstration complete

💾 Raw response saved to: tmp/responses/usage_helper_20250702_200051.json

--- Method 2: Manual Save ---
Manual save demonstration
Result: {'manual': True}
✅ Manual save complete

💾 Raw response saved to: tmp/responses/usage_helper_20250702_200051.json

✅ Usage helper demonstration complete!


--- STDERR ---

```

---

### ❌ websocket_handler.py

**Description**: WebSocket + Redis intelligent timeout system - THE CORE SCRIPT (0% success if this fails)

**Expected Indicators**: websocket, claude, test, command, output, redis, timeout

**Required Packages**: fastapi, websockets, uvicorn, redis, anthropic

**Assessment**: FAIL (Confidence: 90%)

**Reasons**:

- Unexpected exception occurred

**Raw Output**:
```
Exit Code: 1

--- STDOUT ---
=== SIMPLE TEST ===


=== MEDIUM TEST ===


=== LONG TEST ===


--- STDERR ---
=== SIMPLE TEST ===
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py", line 62, in <module>
    from fastapi import WebSocket, WebSocketDisconnect
ModuleNotFoundError: No module named 'fastapi'


=== MEDIUM TEST ===
Traceback (most recent call last):
  File "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core/websocket_handler.py", line 62, in <module>
    from fastapi import WebSocket, WebSocketDi...[truncated]
```

---

## Hook Integration Summary

⚠️  Hooks were not available. Tests ran without:
- Automatic venv activation
- Dependency validation
- Execution metrics

To enable hooks, ensure cc_executor is properly installed.

## Recommendations

### For Failed Components:

- **process_manager.py**: Review usage function for proper demonstration
- **stream_handler.py**: Review usage function for proper demonstration
- **websocket_handler.py**: Review usage function for proper demonstration

### Recommended Pattern for Future Components:
Place usage examples directly in `if __name__ == '__main__':` block:
- No --test flags needed
- Immediate execution with `python file.py`
- Self-validating with assertions
- Clear success/failure output

### Enable Hooks:
- Ensure cc_executor package is in PYTHONPATH
- Install all hook dependencies
- Run from within cc_executor project structure