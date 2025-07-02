# Load-Aware Timeout Implementation

## Summary

We've implemented automatic timeout adjustment based on system load to handle performance degradation under high CPU/GPU usage.

## Key Changes

### 1. Redis Timing Module (`redis_task_timing.py`)
- Added `get_system_load()` method to check CPU load and GPU memory usage
- Integrated load multiplier into `estimate_complexity()` method
- Store CPU/GPU load with each task execution for historical analysis

### 2. Redis Operations (`redis_ops.md`)
- Enhanced schema to include `cpu_load` and `gpu_memory_gb` fields
- Store load metrics when creating and updating tasks
- Added queries to analyze performance by load level

### 3. Timeout Calculation (`redis_timing.md`)
- Added `get_system_load()` bash function
- Modified `get_bm25_timeout()` to apply 3x multiplier when CPU load > 14
- Shows warning when high load is detected

## How It Works

1. **Load Detection**:
   - CPU load average (1-minute) via `os.getloadavg()[0]`
   - GPU memory usage via `nvidia-smi` (if available)

2. **Timeout Adjustment**:
   - Normal: CPU load < 14 → Use standard timeout
   - High: CPU load ≥ 14 → Apply 3x multiplier to all timeouts
   - Warning message displayed when multiplier is applied

3. **Historical Tracking**:
   - Each task execution records CPU/GPU load at start and end
   - Enables analysis of performance under different load conditions
   - Can query tasks by load level to understand impact

## Example Usage

```python
# Python
timer = RedisTaskTimer()
result = await timer.estimate_complexity("analyze python code")
# If load > 14: expected_time and max_time are multiplied by 3

# Bash
TIMEOUT=$(get_bm25_timeout "analyze code" 120)
# If load > 14: Shows warning and returns 3x timeout
```

## Benefits

1. **Automatic Adaptation**: No manual intervention needed during high load
2. **Prevents Timeouts**: 3x multiplier gives tasks enough time under stress
3. **Load Visibility**: Historical data shows performance vs load correlation
4. **Smart Defaults**: Only applies multiplier when truly needed (load > 14)

## Real-World Example

From our testing:
- System load: 14.99 (Ollama using 21GB GPU memory)
- Without adjustment: 38.5% pass rate (many timeouts)
- With 3x multiplier: Would give tasks sufficient time to complete

## Future Enhancements

1. **Graduated Multipliers**: 
   - Load 5-10: 1.5x
   - Load 10-14: 2x
   - Load >14: 3x

2. **GPU-Aware Adjustment**:
   - If GPU memory > 20GB: Additional multiplier
   - Track GPU-specific tasks separately

3. **Predictive Adjustment**:
   - Use historical data to predict optimal multiplier
   - Learn task-specific load sensitivity