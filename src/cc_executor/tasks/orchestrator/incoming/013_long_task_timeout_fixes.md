# Long Task Timeout Fixes - Implementation Plan

## Sequence: 013
## Focus Area: long_task_timeouts
## Type: implementation_plan
## Date: 2025-01-26

## Problem Summary

Stress tests show:
- **Simple tasks**: 100% success rate ✅
- **Long/complex tasks**: Failing with stall timeouts ❌

Pattern: Claude says "I'll write a 5000-word story..." then produces NO output for 90+ seconds, causing stall timeout.

## Root Cause (from Perplexity Analysis)

1. Claude doesn't stream output during heavy computation
2. Long content generation can take 90+ seconds before first output
3. Our stall timeout (90s) is too aggressive for these tasks

## Immediate Fixes Required

### 1. Increase Stall Timeouts for Content Generation
**File**: `src/cc_executor/prompts/redis_task_timing.py`
```python
# Add content generation detection
if task_type.get('question_type') == 'content_generation':
    # Much longer stall timeout for content generation
    stall_multiplier = float(os.environ.get('CONTENT_GEN_STALL_MULT', '3.0'))
    stall_timeout = int(stall_timeout * stall_multiplier)
```

### 2. Update Environment Configuration
**File**: `src/cc_executor/CONFIG_ENVIRONMENT.md`
Add:
- `CONTENT_GEN_STALL_MULT` - Multiplier for content generation stall timeouts (default: 3.0)
- `LONG_TASK_STALL_TIMEOUT` - Override for long tasks (default: 300)

### 3. Enhance Task Classification
**File**: `src/cc_executor/prompts/redis_task_timing.py`
Add patterns to detect long content generation:
- "write.*story.*words"
- "comprehensive guide"
- "detailed.*explanation"

### 4. Prompt Engineering for Progress Updates
**File**: `src/cc_executor/tasks/unified_stress_test_tasks.json`
Update long task prompts to include:
```json
"natural_language_request": "Write a 5000 word science fiction story... Output 'Progress: Writing section X of 10' every 500 words to show progress."
```

## Comprehensive Solution Plan

### Phase 1: Quick Fixes (Today)
1. **Triple stall timeouts for long tasks**
   - Detect content generation tasks
   - Apply 3x multiplier to stall timeout
   - Special handling for "extreme" complexity

2. **Update test definitions**
   - Increase timeouts for long_1, long_2
   - Add progress prompting to requests

### Phase 2: Infrastructure Improvements (This Week)
1. **Heartbeat System**
   - WebSocket handler sends keepalive during long waits
   - Client acknowledges to prevent disconnect

2. **Progress Detection**
   - Monitor for "thinking" patterns
   - Show user "Claude is working..." status

3. **Smart Timeout Scaling**
   - Calculate timeout based on requested word count
   - Use historical data for similar tasks

## Specific Task Fixes

### long_1 (5000-word story)
- Current stall timeout: 90s
- New stall timeout: 270s (3x multiplier)
- Add prompt: "Show progress every 1000 words"

### long_2 (comprehensive guide)
- Current stall timeout: 30s (misclassified as simple!)
- New stall timeout: 180s
- Fix classification to detect "comprehensive guide"

### extreme_1 (research paper)
- Current timeout: likely too short
- New approach: Scale with complexity
- Add chunked output prompting

## Test Strategy

1. **Incremental Testing**
   ```bash
   # Test single long task with new timeouts
   export CONTENT_GEN_STALL_MULT=3.0
   python unified_stress_test_executor.py --test long_1 --verbose
   ```

2. **Monitor Output Patterns**
   - Log time to first output
   - Track stall periods
   - Build historical data

3. **Validate All Categories**
   ```bash
   # After fixes, run all tests
   python unified_stress_test_executor.py --all
   ```

## Expected Results

With these fixes:
- Simple tasks: Remain at 100% ✅
- Long tasks: Should achieve 90%+ success ✅
- Extreme tasks: Should achieve 80%+ success ✅

Overall target: 90%+ success rate across all categories.

## Why This Will Work

Perplexity's analysis confirms:
1. Claude's long computation periods are expected behavior
2. Timeout adjustment is the primary solution
3. Progress prompting can maintain stream activity
4. Infrastructure heartbeats prevent connection drops

Our dynamic timeout system is working correctly - we just need to tune it for Claude's actual behavior on long tasks.