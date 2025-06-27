# Review Request: Dynamic Timeout System

## Sequence: 009
## Focus Area: dynamic_timeout_system
## Type: review_request
## Priority: critical

## Overview

After experiencing 40% failure rate (6/15 tests) in stress tests due to hardcoded stall timeouts, we implemented a dynamic timeout system. Need review of the architecture and implementation to achieve 90%+ success rate.

## Core Challenge

Previous implementation had hardcoded values:
- Stall timeout: 60 seconds (too aggressive for long content generation)
- Max timeout: 300 seconds (insufficient for complex tasks)

All failures showed pattern: "[STALLED for 60.3s]" while generating legitimate content.

## Current Solution

Implemented fully dynamic timeout system with:
1. Environment variable configuration
2. Redis historical learning
3. Task complexity classification
4. No hardcoded values

## Files to Review

### Core Implementation
```
src/cc_executor/prompts/unified_stress_test_executor.py
src/cc_executor/prompts/websocket_orchestrator.py
src/cc_executor/prompts/redis_task_timing.py
src/cc_executor/utils/task_loader.py
```

### Documentation
```
src/cc_executor/CONFIG_ENVIRONMENT.md
src/cc_executor/DYNAMIC_TIMEOUTS.md
```

## Specific Issues to Investigate

### 1. Async Context Issue
**File**: `redis_task_timing.py`
**Line**: 169
**Issue**: Using `asyncio.run()` inside sync method `_calculate_stall_timeout()`
**Impact**: Potential event loop conflicts

### 2. Redis Key Growth
**Pattern**: `cc_executor:times:{category}:{task}:{complexity}:{type}:history`
**Issue**: Unbounded growth without TTL
**Impact**: Redis memory exhaustion

### 3. Timeout Calculation Logic
**Method**: `_calculate_stall_timeout()`
**Issue**: Uses mean instead of percentile
**Impact**: Outliers skew timeout estimates

### 4. Environment Variable Proliferation
**Count**: 15+ environment variables
**Issue**: Complex configuration management
**Impact**: Deployment complexity

### 5. Task Classification Accuracy
**Method**: `classify_command()` using regex
**Issue**: May misclassify edge cases
**Impact**: Wrong timeout selection

## Expected Bugs to Find

1. **Race Conditions**
   - WebSocket message buffering during high load
   - Concurrent Redis updates

2. **Edge Cases**
   - Redis unavailable fallback
   - Malformed environment variables
   - Extreme task durations

3. **Performance Issues**
   - Redis lookup on every execution
   - Environment variable parsing overhead

4. **Security Concerns**
   - Environment variable injection
   - Redis key manipulation

## Success Metrics

Current: 60% success rate (9/15 tests)
Target: 90%+ success rate

## Verification Methods

```bash
# Run stress tests with dynamic timeouts
cd /home/graham/workspace/experiments/cc_executor
python src/cc_executor/prompts/unified_stress_test_executor.py

# Check timeout calculations
python src/cc_executor/utils/task_loader.py

# Verify Redis learning
redis-cli keys "cc_executor:times:*" | wc -l
```

## Questions for Review

1. Is the timeout fallback chain too complex?
2. Should we use median/p95 instead of mean for historical data?
3. Are we solving the right problem (timeouts vs. task design)?
4. How to prevent Redis key explosion?
5. Better ML approach for timeout prediction?

## Related Context

- Must maintain WebSocket MCP protocol
- Docker deployment required
- No hardcoded values allowed
- System must self-improve over time

Please analyze for architectural flaws, performance bottlenecks, and reliability issues.