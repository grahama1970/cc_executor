# CC Executor Comprehensive Assessment Report
Generated: 2025-07-09T13:58:53.189603

## Executive Summary

- **Total Tests Run:** 6
- **Overall Success Rate:** 83.3%
- **Average Response Time:** 3.68s
- **Deployment Categories Tested:** 3/4

## Deployment Category Results

### Python API (Local)

**Status:** ✅ OPERATIONAL

- Tests Run: 3
- Successful: 3
- Failed: 0
- Success Rate: 100.0%
- Avg Response Time: 7.25s

**Test Results:**

- Simple math ✅
  - Duration: 7.53s
  - Result: `42`
- List colors ✅
  - Duration: 6.63s
  - Result: `red, blue, yellow`
- Boolean logic ✅
  - Duration: 7.59s
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

**Status:** ✅ OPERATIONAL

- Tests Run: 2
- Successful: 2
- Failed: 0
- Success Rate: 100.0%
- Avg Response Time: 0.17s

**Test Results:**

- Math via Docker ✅
  - Duration: 0.17s
  - Result: `Process started`
- Word via Docker ✅
  - Duration: 0.17s
  - Result: `Process started`

## Raw Test Data

Complete test results are available in: `tests/stress_test_results/comprehensive_raw_20250709_135853.json`

### Sample Successful Response (Raw JSON)

```json
{
  "name": "Simple math",
  "success": true,
  "duration": 7.534050703048706,
  "result": "42"
}
```
