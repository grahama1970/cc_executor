# MCP Verification Tool

## Overview

CC Executor now includes an MCP-exposed verification tool that allows clients to verify that cc_execute calls are not hallucinated. This is part of the anti-hallucination system that ensures all executions leave physical evidence on disk.

## MCP Tool: verify_execution

The `verify_execution` tool is available via the CC Executor MCP server and provides the following functionality:

### Parameters

- `execution_uuid` (optional): Specific UUID to verify
- `last_n` (default: 1): Number of recent executions to check  
- `generate_report` (default: true): Whether to generate a markdown report

### Response

The tool returns a dictionary with:
- `success`: Whether the verification succeeded
- `is_hallucination`: True if results appear fabricated
- `status`: PASS or FAIL
- `verifications`: List of verified executions with details
- `report_path`: Path to generated report (if requested)

### Example Usage

```python
# Via MCP protocol
result = await mcp_client.call_tool(
    "verify_execution",
    {
        "last_n": 5,
        "generate_report": True
    }
)

# Check if hallucinated
if result["is_hallucination"]:
    print("⚠️ WARNING: Execution appears to be hallucinated!")
else:
    print("✅ Execution verified as real")
```

## How It Works

1. **Every cc_execute call creates two files:**
   - JSON response file in `client/tmp/responses/`
   - Markdown receipt in `client/tmp/responses/receipts/`

2. **Verification checks for:**
   - Physical existence of JSON files
   - Valid JSON structure
   - Matching execution UUIDs
   - Corresponding receipt files

3. **Anti-hallucination proof:**
   - Files exist on disk with timestamps
   - UUIDs are cryptographically unique
   - Receipts provide human-readable summaries

## Integration with Claude Code

When Claude Code has the CC Executor MCP server configured, it can use the `verify_execution` tool to:

1. Verify its own cc_execute calls aren't hallucinated
2. Generate verification reports for users
3. Provide proof of actual execution

## Manual Verification

Users can also manually verify executions:

```bash
# Check recent executions
ls -la src/cc_executor/client/tmp/responses/cc_execute_*.json

# View a specific response
cat src/cc_executor/client/tmp/responses/cc_execute_*.json | jq

# Generate verification report
python -m cc_executor.reporting.hallucination_check report
```

## Benefits

1. **Trust**: Users can verify AI agents aren't fabricating results
2. **Auditability**: Every execution leaves a permanent trail
3. **Debugging**: Response files help diagnose issues
4. **Compliance**: Receipts provide audit logs