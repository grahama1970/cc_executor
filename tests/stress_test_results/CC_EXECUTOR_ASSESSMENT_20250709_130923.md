# CC Executor Comprehensive Assessment Report
Generated: 2025-07-09T13:09:23.792177

## Executive Summary

- **Total Tests Run:** 5
- **Success Rate:** 60.0%
- **Average Response Time:** 4.17s
- **Deployment Modes Tested:** 3/3

## Deployment Mode Results

### Python Api

**Status:** ✅ OPERATIONAL

- Tests Run: 3
- Successful: 3
- Failed: 0
- Success Rate: 100.0%
- Avg Response Time: 6.94s

**Test Results:**

- Simple arithmetic ✅
  - Duration: 5.97s
  - Result: `12`
- Prime numbers ✅
  - Duration: 8.16s
  - Result: `2, 3, 5, 7, 11, 13, 17`
- Complex question ✅
  - Duration: 6.70s
  - Result: `Paris`

### Mcp Local Websocket

**Status:** ❌ FAILING

- Tests Run: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Avg Response Time: 0.00s

**Test Results:**

- Connection test ❌
  - Duration: 0.00s
  - Error: 'WebSocketClient' object has no attribute 'connect'

### Docker Websocket

**Status:** ❌ FAILING

- Tests Run: 1
- Successful: 0
- Failed: 1
- Success Rate: 0.0%
- Avg Response Time: 0.00s

**Test Results:**

- Connection test ❌
  - Duration: 0.00s
  - Error: 'WebSocketClient' object has no attribute 'connect'

## Recommendations

### Mcp Local Websocket
- Fix: Connection test - 'WebSocketClient' object has no attribute 'connect'

### Docker Websocket
- Fix: Connection test - 'WebSocketClient' object has no attribute 'connect'

## Raw Test Data

Complete test results with all details are available in:
`tests/stress_test_results/comprehensive_test_raw_20250709_130923.json`

### Sample Raw JSON Response

```json
{
  "name": "Simple arithmetic",
  "success": true,
  "duration": 5.967441082000732,
  "result": "12"
}
```
