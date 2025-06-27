# CC-Executor Stress Tests

This directory contains stress tests for the cc_executor WebSocket MCP service.

## Important Note

The stress tests in `unified_stress_test_executor_v3.py` are designed to test the full Claude Code system, not just the cc_executor transport layer. They expect to send natural language questions and receive AI-generated responses.

Currently, cc_executor only provides the transport layer (WebSocket MCP protocol) for command execution. To fully test these scenarios, you would need:

1. Claude Code connected via the WebSocket endpoint
2. Or a mock Claude Code service that can respond to the test questions

## WebSocket Test

For testing just the WebSocket transport layer, use:

```bash
python websocket_test_executor.py
```

This tests:
- WebSocket connection handshake
- Command execution via the MCP protocol
- Output streaming
- Process completion notifications

## Running Unified Stress Tests

To run the unified stress tests (requires Claude Code):

```bash
python unified_stress_test_executor_v3.py
```

Note: Without Claude Code connected, these tests will only verify the transport layer works, not the actual AI responses.