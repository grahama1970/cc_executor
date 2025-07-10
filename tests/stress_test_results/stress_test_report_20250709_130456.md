# CC Executor Stress Test Report
Generated: 2025-07-09T13:04:56.478540

## Summary

### Python Api
- Total Tests: 3
- Successful: 3
- Failed: 0
- Success Rate: 100.0%
- Average Duration: 6.50s

### Mcp Local
- Total Tests: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Average Duration: 0.00s

### Docker
- Total Tests: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Average Duration: 0.00s

## Detailed Results

### Python Api

**Simple calculation** ✅
- Duration: 6.08s
- Result: `4
`

**List generation** ✅
- Duration: 6.79s
- Result: `2, 3, 5, 7, 11
`

**Error case** ✅
- Duration: 6.61s
- Result: `The square root of -1 does not exist in real numbers. In the real number system, you cannot take the...`

### Mcp Local

**MCP WebSocket test** ❌
- Duration: 0.00s
- Error: asyncio.run() cannot be called from a running event loop

### Docker

**Docker WebSocket** ❌
- Duration: 0.00s
- Error: asyncio.run() cannot be called from a running event loop

