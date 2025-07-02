# Simple Stress Test Report

**Generated**: 2025-06-30T21:45:41.322447  
**Execution ID**: SIMPLE_STRESS_TEST_20250630_214505  
**Total Duration**: 35.69 seconds  
**Configuration**: /home/graham/workspace/experiments/cc_executor/tests/stress/configs/simple_stress_tests.json

## Summary

- **Total Tests**: 5
- **Passed**: 4 ✅
- **Failed**: 1 ❌
- **Success Rate**: 80.0%

## Test Results

### Basic Math - ❌ FAILED

- **ID**: `simple_math`
- **Description**: Basic arithmetic
- **Duration**: 4.72s
- **Command**: `claude -p "What is 2+2?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none`
- **Patterns Found**: 1/2
- **Error**: Pattern mismatch: found 1/2 patterns

<details>
<summary>Output</summary>

```
{"type":"system","subtype":"init","cwd":"/home/graham/workspace/experiments/cc_executor","session_id":"2261818e-b778-4418-a27d-6d0676ea5223","tools":["Task","Bash","Glob","Grep","LS","exit_plan_mode","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[],"model":"claude-opus-4-20250514","permissionMode":"bypassPermissions","apiKeySource":"none"}

{"type":"assistant","message":{"id":"msg_01SEgDGuebk6VGgGcemNdY7P","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"text","text":"4"}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":0,"cache_read_input_tokens":28252,"output_tokens":1,"service_tier":"standard"}},"parent_tool_use_id":null,"session_id":"2261818e-b778-4418-a27d-6d0676ea5223"}

{"type":"result","subtype":"success","is_error":false,"duration_ms":3657,"duration_api_ms":3582,"num_turns":1,"result":"4","session_id":"2261818e-b
```

</details>

### Multiple Calculations - ✅ PASSED

- **ID**: `calculations`
- **Description**: Multiple arithmetic operations
- **Duration**: 12.83s
- **Command**: `claude -p "What is the result of these calculations: 15+27, 83-46, 12*9, 144/12, 2^8?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none`
- **Patterns Found**: 5/5

<details>
<summary>Output</summary>

```
{"type":"system","subtype":"init","cwd":"/home/graham/workspace/experiments/cc_executor","session_id":"72caaa6a-cabf-4328-b090-e8e83b731811","tools":["Task","Bash","Glob","Grep","LS","exit_plan_mode","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[],"model":"claude-opus-4-20250514","permissionMode":"bypassPermissions","apiKeySource":"none"}

{"type":"assistant","message":{"id":"msg_013nnViU3xDYBshmsh5XazXh","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"text","text":"I'll calculate each of these for you:"}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":5623,"cache_read_input_tokens":22655,"output_tokens":1,"service_tier":"standard"}},"parent_tool_use_id":null,"session_id":"72caaa6a-cabf-4328-b090-e8e83b731811"}

{"type":"assistant","message":{"id":"msg_013nnViU3xDYBshmsh5XazXh","type":"message","role":"assistant","mode
```

</details>

### Fibonacci Number - ✅ PASSED

- **ID**: `fibonacci`
- **Description**: Calculate Fibonacci sequence
- **Duration**: 17.84s
- **Command**: `claude -p "What is the 10th Fibonacci number?" --output-format stream-json --verbose --dangerously-skip-permissions --allowedTools none`
- **Patterns Found**: 2/2

<details>
<summary>Output</summary>

```
{"type":"system","subtype":"init","cwd":"/home/graham/workspace/experiments/cc_executor","session_id":"ed88f223-fb18-46f6-9626-9a1eafb67b22","tools":["Task","Bash","Glob","Grep","LS","exit_plan_mode","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[],"model":"claude-opus-4-20250514","permissionMode":"bypassPermissions","apiKeySource":"none"}

{"type":"assistant","message":{"id":"msg_016ddD8kYs1UeWJV2EG2GqS6","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"text","text":"I'll calculate the 10th Fibonacci number for you."}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":5600,"cache_read_input_tokens":22655,"output_tokens":3,"service_tier":"standard"}},"parent_tool_use_id":null,"session_id":"ed88f223-fb18-46f6-9626-9a1eafb67b22"}

{"type":"assistant","message":{"id":"msg_016ddD8kYs1UeWJV2EG2GqS6","type":"message","role":"assi
```

</details>

### Echo Test - ✅ PASSED

- **ID**: `echo_test`
- **Description**: Basic echo command
- **Duration**: 0.15s
- **Command**: `echo "Testing basic echo command"`
- **Patterns Found**: 1/1

<details>
<summary>Output</summary>

```
Testing basic echo command

```

</details>

### Date Command - ✅ PASSED

- **ID**: `date_test`
- **Description**: System date command
- **Duration**: 0.15s
- **Command**: `date`
- **Patterns Found**: 1/1

<details>
<summary>Output</summary>

```
Mon Jun 30 09:45:41 PM EDT 2025

```

</details>

