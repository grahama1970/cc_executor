# Anti-Hallucination Verification Report
Generated: 2025-07-10T14:09:45.286232

## Summary
- Status: **PASS**
- Is Hallucination: **NO - RESULTS ARE REAL**
- Files Checked: 1

## ✅ VERIFICATION PASSED

**Proof**: Physical files exist at: /home/graham/workspace/experiments/cc_executor/src/cc_executor/client/tmp/responses

## Verified Executions

### Execution #1 - VERIFIED REAL
- **File**: `cc_execute_4fd8d9d8_20250710_140859.json`
- **Full Path**: `/home/graham/workspace/experiments/cc_executor/src/cc_executor/client/tmp/responses/cc_execute_4fd8d9d8_20250710_140859.json`
- **File Size**: 1530 bytes
- **Modified**: 2025-07-10T14:09:39.634697
- **Task**: Write a Python function that calculates the factorial of a number. Include error handling for negati...
- **Output**: ```json
{
  "result": "def factorial(n):\n    \"\"\"\n    Calculate the factorial of a non-negative ...
- **UUID**: `503dfd38-1893-4146-8d08-2e7819688233`
- **Exit Code**: 0
- **Execution Time**: 39.83s
- **JSON Mode**: Yes

**Parsed JSON Response**:
```json
{
  "result": "def factorial(n):\n    \"\"\"\n    Calculate the factorial of a non-negative integer.\n    \n    Args:\n        n (int): The number to calculate factorial for\n        \n    Returns:\n        int: The factorial of n\n        \n    Raises:\n        ValueError: If n is negative\n        TypeError: If n is not an integer\n    \"\"\"\n    if not isinstance(n, int):\n        raise TypeError(f\"Expected an integer, got {type(n).__name__}\")\n    \n    if n < 0:\n        raise ValueError
... (truncated)
```

## Independent Verification Commands

Run these commands yourself to verify:

```bash
# List actual files on disk
ls -la src/cc_executor/client/tmp/responses/cc_execute_*.json | tail -10

# Check file contents directly
tail -5 src/cc_executor/client/tmp/responses/cc_execute_*.json | head -50

# Verify with jq
for f in src/cc_executor/client/tmp/responses/cc_execute_*.json; do
    echo "=== $f ==="
    jq -r '.execution_uuid + " | " + .task' "$f" 2>/dev/null | head -5
done
```

## Conclusion

✅ **VERIFIED**: These results are real and exist on disk.

Physical JSON files EXIST at the paths shown above.
