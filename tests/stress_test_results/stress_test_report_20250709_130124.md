# CC Executor Stress Test Report
Generated: 2025-07-09T13:01:24.385519

## Summary

### Python Api
- Total Tests: 3
- Successful: 3
- Failed: 0
- Success Rate: 100.0%
- Average Duration: 6.36s

### Mcp Local
- Total Tests: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Average Duration: 8.26s

### Docker
- Total Tests: 1
- Successful: 1
- Failed: 0
- Success Rate: 100.0%
- Average Duration: 0.01s

## Detailed Results

### Python Api

**Simple calculation** ✅
- Duration: 5.74s
- Result: `4
`

**List generation** ✅
- Duration: 5.79s
- Result: `2, 3, 5, 7, 11
`

**Error case** ✅
- Duration: 7.55s
- Result: `The square root of -1 does not exist in real numbers. It's undefined in the real number system becau...`

### Mcp Local

**Simple MCP call** ❌
- Duration: 8.26s
- Error: Both --config and --server must be provided together. If you specify one, you must specify the other.


### Docker

**Docker WebSocket** ✅
- Duration: 0.01s
- Result: `{"detail":"Not Found"}`

