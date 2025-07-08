# Redis Timing Integration for Stress Tests

## Overview

The stress test runner now integrates with Redis to provide adaptive timeouts based on historical execution data. This system learns from each test execution to provide more accurate timeout predictions, reducing both test failures from timeouts and wasted time from overly conservative timeouts.

## Key Features

### 1. Dynamic Timeout Calculation
- **Complex/Extreme prompts**: Get 10-minute (600s) minimum timeouts
- **Unknown prompts**: Get 90s minimum timeout with acknowledgment
- **Historical data**: Uses past execution times to predict future needs
- **System load awareness**: Multiplies timeouts by 3x when CPU load > 14

### 2. Redis Data Storage
After each test execution, the system stores:
- Actual execution time
- Expected vs actual variance
- Success/failure status
- System load at time of execution
- Task classification metadata

### 3. Intelligent Classification
The enhanced prompt classifier categorizes prompts by:
- **Category**: code, claude, system, redis, testing, etc.
- **Complexity**: trivial, low, simple, medium, high, complex, extreme
- **Task type**: Specific task within category (e.g., haiku_5, refactor, analyze)
- **Question type**: creative_writing, code_generation, debugging, etc.

### 4. Fallback Mechanism
When Redis is unavailable:
- Uses static timeouts with 3x baseline multiplier
- Continues to function with conservative defaults
- No test failures due to missing Redis

## Usage

### Running Tests with Redis Timing

```bash
# Basic usage - runs all tests with adaptive timeouts
./stress_tests/run_unified_stress_tests_with_redis.py

# Test the Redis integration
./test_redis_timing_integration.py

# Demo the adaptive timeout system
./demo_adaptive_timeout_stress_test.py
```

### How It Works

1. **Before Test Execution**:
   ```python
   # Get timeout prediction from Redis
   estimation = await timer.estimate_complexity(prompt)
   timeout = int(estimation['max_time'])
   stall_timeout = estimation['stall_timeout']
   ```

2. **After Test Execution**:
   ```python
   # Update Redis with actual timing
   await timer.update_history(
       task_type,
       elapsed=actual_time,
       success=True,
       expected=estimation['expected_time']
   )
   ```

3. **Learning Process**:
   - First execution: Uses category/complexity defaults
   - After 3+ executions: Uses historical average with confidence
   - Continuous improvement: Each execution refines predictions

## Timeout Guidelines

### Default Timeouts (with 3x baseline multiplier)

| Complexity | Expected Time | Max Timeout |
|------------|---------------|-------------|
| trivial    | 15s          | 45s         |
| low        | 60s          | 180s        |
| simple     | 30s          | 90s         |
| medium     | 180s         | 540s        |
| high       | 360s         | 1080s       |
| complex    | 540s         | 1800s (30m) |
| extreme    | 900s         | 2700s (45m) |

### Special Cases

1. **Unknown Prompts**: Minimum 90s timeout
2. **High System Load**: 3x multiplier when CPU load > 14
3. **Complex Tasks**: Minimum 600s (10 minutes)
4. **Stall Detection**: Separate timeout for no output (typically 50% of main timeout)

## Redis Data Structure

### Keys
- `cc_executor:times:{category}:{task}:history` - Execution history
- `cc_executor:times:{category}:{task}:stats` - Aggregate statistics
- `cc_executor:times:{category}:{task}:{complexity}:{type}:history` - Detailed history
- `cc_executor:times:{category}:{task}:{complexity}:{type}:stats` - Detailed stats

### History Entry Format
```json
{
    "timestamp": 1234567890,
    "expected": 60.0,
    "actual": 58.5,
    "success": true,
    "variance": -0.025,
    "complexity": "medium",
    "question_type": "code_generation",
    "cpu_load": 2.5,
    "gpu_memory_gb": 0.0
}
```

## Benefits

1. **Reduced Failures**: Fewer timeout-related test failures
2. **Time Efficiency**: No more waiting for overly conservative timeouts
3. **Learning System**: Improves with each execution
4. **Load Awareness**: Adapts to system conditions
5. **Transparency**: Clear reporting of timeout sources and confidence

## Monitoring

The test reports now include:
- Timing accuracy analysis
- Prediction confidence levels
- Variance statistics
- Worst predictions for improvement

## Future Enhancements

1. **Token-based estimation**: Consider prompt length in predictions
2. **Model-specific timing**: Different timeouts for different AI models
3. **Pattern learning**: Identify common prompt patterns
4. **Cross-category learning**: Use similar complexity tasks across categories