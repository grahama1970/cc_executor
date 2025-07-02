# Resource Monitoring and Dynamic Timeout Adjustment

## Overview

The CC Executor now includes automatic resource monitoring that dynamically adjusts timeouts based on system load. When CPU or GPU usage exceeds 14%, timeouts are automatically multiplied by 3x to prevent false timeout failures during high system load.

## Rationale

As documented in [LESSONS_LEARNED.md](./LESSONS_LEARNED.md#lesson-2-system-load-dramatically-affects-timeout-requirements), high system load can cause perfectly good operations to fail due to timeouts. This feature prevents those failures by automatically adjusting timeouts when the system is under stress.

## How It Works

1. **Monitoring**: The system continuously monitors CPU usage (via `psutil`) and GPU usage (via `nvidia-smi`)
2. **Threshold**: When either CPU or GPU usage exceeds 14%, the system enters "high load" mode
3. **Adjustment**: All timeouts are multiplied by 3x during high load conditions
4. **Recovery**: When load drops below 14%, timeouts return to normal

## Configuration

### Enable Dynamic Timeout Adjustment

By default, the WebSocket handler runs with no timeout (processes complete naturally). To enable timeout-based stream handling with dynamic adjustment:

```bash
export ENABLE_STREAM_TIMEOUT=true
```

### Customize the Base Timeout

```bash
export STREAM_TIMEOUT=300  # Base timeout in seconds (default: 600)
```

### Adjust the Load Threshold

The 14% threshold is based on empirical observations but can be modified in code:

```python
from cc_executor.core.resource_monitor import adjust_timeout

# Use custom threshold
adjusted = adjust_timeout(base_timeout=60, threshold=20.0)  # 20% threshold
```

## Implementation Details

### Resource Monitor Module

The `resource_monitor.py` module provides:

- `get_cpu_usage()`: Returns current CPU usage percentage
- `get_gpu_usage()`: Returns GPU usage via nvidia-smi (or None if unavailable)
- `calculate_timeout_multiplier(threshold)`: Returns 1.0 or 3.0 based on load
- `adjust_timeout(base_timeout, threshold)`: Returns adjusted timeout value

### WebSocket Handler Integration

When `ENABLE_STREAM_TIMEOUT=true`, the WebSocket handler:

1. Checks system load before streaming output
2. Applies the multiplier to the base timeout
3. Logs the adjustment for debugging

Example log output:
```
[2025-06-28 10:15:23] | INFO | resource_monitor:65 - CPU usage 18.5% exceeds 14%, applying 3x timeout multiplier
[2025-06-28 10:15:23] | INFO | websocket_handler:519 - Streaming output with 1800s timeout (base: 600s)
```

## Testing

### Unit Test
```bash
python tests/test_resource_monitor_integration.py
```

### Live Demo
```bash
python examples/demo_resource_monitor.py
```

This demo:
1. Shows current system load
2. Simulates high CPU load
3. Demonstrates automatic timeout adjustment
4. Provides usage examples

## Use Cases

### 1. Development Environments
When running resource-intensive tasks (compiling, model training, etc.) alongside CC Executor:
- Prevents WebSocket timeouts during builds
- Maintains reliability during system stress

### 2. CI/CD Pipelines
When tests run on shared infrastructure:
- Adapts to varying system loads
- Reduces flaky test failures

### 3. Production Services
When running alongside other services:
- Handles load spikes gracefully
- Provides better user experience

## Performance Impact

The resource monitoring has minimal overhead:
- CPU usage check: ~1ms
- GPU usage check: ~5-10ms (subprocess call)
- Only performed once per command execution

## Troubleshooting

### GPU Monitoring Not Working

If GPU usage always shows as None:
1. Verify nvidia-smi is installed: `which nvidia-smi`
2. Check GPU drivers: `nvidia-smi -q`
3. The system will still work using CPU-only monitoring

### Timeouts Still Occurring

If timeouts occur even with adjustment:
1. Check if load exceeds 14%: `python -c "from cc_executor.core.resource_monitor import get_system_load; print(get_system_load())"`
2. Verify ENABLE_STREAM_TIMEOUT is set
3. Consider increasing base timeout or threshold

### Logs for Debugging

Enable debug logging to see all timeout adjustments:
```bash
export LOGURU_LEVEL=DEBUG
```

## Future Enhancements

1. **Configurable Multiplier**: Allow customizing the 3x multiplier
2. **Gradual Scaling**: Progressive timeout increases (1.5x, 2x, 3x) based on load levels
3. **Historical Tracking**: Record timeout adjustments for analysis
4. **Memory Monitoring**: Include RAM usage in load calculations
5. **Per-Operation Timeouts**: Different multipliers for different operation types

## API Reference

```python
from cc_executor.core.resource_monitor import (
    get_cpu_usage,      # () -> float
    get_gpu_usage,      # () -> Optional[float]
    get_system_load,    # () -> Tuple[float, Optional[float]]
    calculate_timeout_multiplier,  # (threshold: float = 14.0) -> float
    adjust_timeout      # (base_timeout: float, threshold: float = 14.0) -> float
)
```

## Related Documentation

- [LESSONS_LEARNED.md](./LESSONS_LEARNED.md) - Background on why this feature exists
- [WebSocket Handler](../src/cc_executor/core/websocket_handler.py) - Integration point
- [Configuration](../src/cc_executor/core/config.py) - Timeout settings