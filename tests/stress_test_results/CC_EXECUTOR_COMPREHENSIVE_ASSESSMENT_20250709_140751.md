# CC Executor Comprehensive Assessment Report
Generated: 2025-07-09T14:07:51.570575

## Executive Summary

- **Total Tests Run:** 5
- **Overall Success Rate:** 60.0%
- **Average Response Time:** 4.46s
- **Deployment Categories Tested:** 3/4

## Deployment Category Results

### Python API (Local)

**Status:** ✅ OPERATIONAL

- Tests Run: 3
- Successful: 3
- Failed: 0
- Success Rate: 100.0%
- Avg Response Time: 7.44s

**Test Results:**

- Simple math ✅
  - Duration: 7.34s
  - Result: `42`
- List colors ✅
  - Duration: 6.26s
  - Result: `red, green, blue`
- Boolean logic ✅
  - Duration: 8.72s
  - Result: `Yes`

### MCP Local WebSocket

**Status:** ❌ FAILING

- Tests Run: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Avg Response Time: 0.00s

**Test Results:**

- Connection test ❌
  - Duration: 0.00s
  - Error: [Errno 111] Connect call failed ('127.0.0.1', 8003)

### Docker API

**Status:** ❌ NOT TESTED

### MCP Docker WebSocket

**Status:** ❌ FAILING

- Tests Run: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Avg Response Time: 0.00s

**Test Results:**

- Connection test ❌
  - Duration: 0.00s
  - Error: server rejected WebSocket connection: HTTP 403

## Raw Test Data

Complete test results are available in: `tests/stress_test_results/comprehensive_raw_20250709_140751.json`

### Sample Successful Response (Raw JSON)

```json
{
  "name": "Simple math",
  "success": true,
  "duration": 7.335897922515869,
  "result": "42"
}
```
