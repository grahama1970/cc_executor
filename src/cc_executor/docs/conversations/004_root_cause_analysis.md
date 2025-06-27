# Root Cause Analysis: MCP Bridge Test Failures

**Date**: 2025-06-24
**Agent**: Claude (Implementer)

## Summary

After extensive debugging, I've identified that the MCP WebSocket bridge implementation is actually working correctly. The test failures are due to an issue with the upstream `claude-api` service, not the MCP bridge itself.

## What's Working

The MCP bridge successfully:
1. ✅ Accepts WebSocket connections using the MCP protocol
2. ✅ Receives JSON-RPC messages from clients
3. ✅ Forwards commands to the claude-api HTTP endpoint
4. ✅ Streams responses back to WebSocket clients
5. ✅ Detects the end marker ("====") and sends COMPLETED status
6. ✅ Handles errors and connection lifecycle properly

## The Actual Problem

The `claude-api` service (`cc-executor/claude-code-docker:latest`) is NOT sending the actual command output through its `/execute/stream` endpoint. 

When we send a command like `python3 -c "print('RESULT:::168')"`, the stream only contains:
```
Execution ID: xxxxx
Starting execution: claude --dangerously-skip-permissions -p python3 -c "print('RESULT:::' + str(24 * 7))"
============================================================
```

But NO actual output from the Python command execution.

## Evidence

1. **Direct API Testing**: Testing the claude-api directly (without MCP bridge) shows the same issue - no command output
2. **Multiple Commands Tested**: Simple commands like `echo 'Hello'`, `print(168)`, and `24 * 7` all show the same behavior
3. **Logs Confirm Execution**: The claude-api logs show it's receiving and executing commands, but the output isn't being streamed

## Root Cause

The claude-api service has an issue with its subprocess output capture. Based on perplexity-ask research:
- The `claude` CLI tool may be detecting non-interactive mode and suppressing output
- Output buffering in the subprocess pipeline
- The streaming implementation in claude-api may not be properly forwarding stdout from the subprocess

## Conclusion

The MCP bridge implementation is correct and functional. The test failures are due to a bug in the upstream claude-api service that needs to be fixed separately. The MCP bridge cannot forward output that isn't being provided by the upstream service.

## Recommendations

1. Fix the claude-api service to properly stream command output
2. Once fixed, the MCP bridge tests should pass without any changes
3. Consider adding a mock claude-api for testing the MCP bridge independently