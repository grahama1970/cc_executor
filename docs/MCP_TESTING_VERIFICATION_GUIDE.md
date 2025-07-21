# MCP Testing and Verification Guide

This guide explains how Claude agents can test MCP tools and prove execution is not hallucinated.

## The Challenge

When Claude calls MCP tools, how can we verify:
1. The tools were actually called (not hallucinated)
2. The tools produced real results
3. The execution can be independently verified

## The Solution: Multi-Layer Verification

### 1. Unique Test Markers

Every test run generates a unique ID with timestamp and milliseconds:
```python
TEST_RUN_ID = f"MCP_ARANGO_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000)}"
# Example: MCP_ARANGO_TEST_20250718_073103_1752838263128
```

This ID is:
- Globally unique (timestamp + milliseconds)
- Easy to search for
- Appears in all logs and outputs

### 2. Verification Locations

When an MCP tool is called, evidence appears in THREE places:

#### A. MCP Logs (`~/.claude/mcp_logs/`)
- Server startup logs
- Tool execution logs  
- Debug output from `@debug_tool` decorator

Example:
```bash
grep "MCP_ARANGO_TEST_20250718_073103" ~/.claude/mcp_logs/arango-tools_*.log
```

#### B. Posthook Reports (`~/.claude/mcp_debug_reports/`)
- Detailed execution reports
- Tool inputs and outputs
- Error messages
- Timing information

Example report structure:
```json
{
  "timestamp": "2025-07-18T07:31:03",
  "tool_name": "mcp__arango-tools__insert",
  "tool_input": {
    "collection": "test_logs",
    "test_marker": "INSERT_MCP_ARANGO_TEST_20250718_073103_M3"
  },
  "tool_output": {
    "_id": "test_logs/12345",
    "_key": "12345"
  }
}
```

#### C. Claude Transcripts (`~/.claude/projects/*/`)
- Complete record of all tool calls
- JSON entries for each interaction
- Searchable with ripgrep

Example:
```bash
rg "MCP_ARANGO_TEST_20250718_073103" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl
```

### 3. Testing Approach

#### Step 1: Generate Test Plan
```python
# Create unique markers for each tool
markers = {
    "get_schema": f"SCHEMA_{TEST_RUN_ID}_M1",
    "execute_aql": f"AQL_{TEST_RUN_ID}_M2",
    "insert": f"INSERT_{TEST_RUN_ID}_M3"
}
```

#### Step 2: Execute Tools with Markers
```python
# Call each tool with its unique marker
await mcp__arango-tools__execute_aql({
    "aql": f"RETURN '{markers['execute_aql']}'"
})
```

#### Step 3: Verify Execution
```bash
# Quick verification - should find matches in all three locations
rg "MCP_ARANGO_TEST_20250718_073103" ~/.claude/mcp_logs/ ~/.claude/mcp_debug_reports/ ~/.claude/projects/-*/*.jsonl
```

### 4. Proof of Non-Hallucination

If execution was hallucinated:
- ❌ No entries in MCP logs
- ❌ No posthook reports generated
- ❌ No tool results in transcript

If execution was real:
- ✅ MCP logs show tool execution with markers
- ✅ Posthook reports contain detailed results
- ✅ Transcript has toolUseResult entries

### 5. Example Test Sequence

```python
# 1. Generate unique test ID
TEST_RUN_ID = "MCP_ARANGO_TEST_20250718_073103_1752838263128"

# 2. Call tool with marker
result = await mcp__arango-tools__insert({
    "collection": "test_logs",
    "test_marker": f"INSERT_{TEST_RUN_ID}",
    "data": "test"
})

# 3. Verify in logs (done by human or script)
# ~/.claude/mcp_logs/arango-tools_debug.log will contain:
# [2025-07-18 07:31:03] Executing tool: insert
# Input: {"collection": "test_logs", "test_marker": "INSERT_MCP_ARANGO_TEST_..."}
# Output: {"_id": "test_logs/12345", "_key": "12345"}

# 4. Verify in posthook report
# ~/.claude/mcp_debug_reports/mcp_report_20250718_073103.json will contain full details

# 5. Verify in transcript
# rg output will show the complete tool call and result
```

### 6. Automated Verification Script

Use `verify_mcp_execution.py` to check all three sources:
```bash
python verify_mcp_execution.py MCP_ARANGO_TEST_20250718_073103_1752838263128
```

Output:
```
=== VERIFYING MCP EXECUTION ===
Test Run ID: MCP_ARANGO_TEST_20250718_073103_1752838263128

1. CHECKING MCP LOGS:
✓ FOUND in MCP logs:
  245: [2025-07-18 07:31:03] test_marker: INSERT_MCP_ARANGO_TEST_20250718_073103_M3

2. CHECKING POSTHOOK REPORTS:
✓ FOUND in posthook report:
  tool_name: mcp__arango-tools__insert
  tool_input: {"collection": "test_logs", "test_marker": "INSERT_MCP_ARANGO_TEST_..."}

3. CHECKING CLAUDE TRANSCRIPT:
✓ FOUND in transcript:
  Tool Result: {"_id": "test_logs/12345", "_key": "12345"}
```

### 7. Best Practices

1. **Always use unique markers**: Include timestamp and random component
2. **Test incrementally**: Start with simple tools like `get_schema`
3. **Save test plans**: Document what markers were used for each tool
4. **Verify immediately**: Check logs right after execution
5. **Use posthooks**: They capture the most detailed information

### 8. Common Issues and Solutions

**Issue**: MCP tool not available
- Check: Is the server in Claude's config?
- Check: Did the server start successfully?
- Solution: Check startup logs first

**Issue**: No logs appearing
- Check: Is MCPLogger initialized?
- Check: Are tools decorated with @debug_tool?
- Solution: Ensure mcp-logger-utils is installed

**Issue**: Can't find transcript
- Check: Correct project directory name
- Check: Recent transcript files
- Solution: Use exact project path in search

### 9. Summary

To prove MCP execution is not hallucinated:
1. Generate unique test markers
2. Execute tools with markers
3. Verify in three locations:
   - MCP logs (server-side execution)
   - Posthook reports (detailed capture)
   - Claude transcript (complete record)
4. All three must contain the test markers

This multi-layer verification ensures that tool execution is real and can be independently verified by both agents and humans.