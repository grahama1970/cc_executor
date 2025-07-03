# Memory Optimization for Large Outputs

## Current Architecture

The cc_executor handles large outputs efficiently through:

1. **8MB Subprocess Buffer Limit**
   - Prevents unlimited memory growth
   - Forces streaming instead of buffering

2. **Async Streaming**
   - Reads output as produced
   - Doesn't accumulate in memory

3. **WebSocket Chunking**
   - 64KB chunks prevent frame size issues
   - Memory usage stays constant

## PYTHONUNBUFFERED=1 Impact

**What it does:**
- Forces immediate flush of print() statements
- Prevents Python's internal buffering (typically 4-8KB)
- Does NOT affect subprocess pipe buffers (8MB)
- Does NOT increase memory usage

**Memory flow:**
```
Python print() → [No buffer] → OS pipe buffer (8MB) → asyncio read → WebSocket chunks (64KB)
```

## Handling Extremely Large Outputs

For multi-gigabyte outputs, consider:

### 1. File-Based Streaming
```python
# Instead of memory pipes, use temporary files
process = await asyncio.create_subprocess_exec(
    zsh_path, "-c", command,
    stdout=open(f'/tmp/output_{session_id}.txt', 'w'),
    stderr=asyncio.subprocess.PIPE,
    ...
)
```

### 2. Output Pagination
```python
# Add pagination to WebSocket protocol
{
    "method": "execute",
    "params": {
        "command": "large_output_command",
        "output_options": {
            "max_lines": 1000,
            "pagination": true
        }
    }
}
```

### 3. Compression
```python
# Compress large outputs before sending
import gzip
compressed = gzip.compress(output.encode())
if len(compressed) < len(output) * 0.8:  # 20% savings
    send_compressed(compressed)
```

### 4. Selective Output
```python
# For Claude commands, use response filtering
command = 'claude -p "..." --max-tokens 1000'  # Limit response size
```

## Memory Monitoring

Add memory tracking for large operations:

```python
import psutil
import resource

# Before subprocess
process = psutil.Process()
mem_before = process.memory_info().rss / 1024 / 1024  # MB

# After streaming
mem_after = process.memory_info().rss / 1024 / 1024  # MB
logger.info(f"Memory delta: {mem_after - mem_before:.1f}MB")

# Set memory limits if needed
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))  # 2GB limit
```

## Recommendations

1. **Keep PYTHONUNBUFFERED=1** - It prevents hangs, doesn't increase memory
2. **Monitor large commands** - Add memory tracking for commands known to produce large output
3. **Use streaming** - Current architecture already streams efficiently
4. **Add limits where appropriate** - Token limits for Claude, row limits for data processing

## Testing Large Outputs

Test with this script to verify memory handling:

```python
# test_large_output.py
import sys
import time

# Generate 100MB of output
for i in range(1000000):
    print(f"Line {i}: " + "x" * 100)
    if i % 10000 == 0:
        print(f"Progress: {i/10000}%", file=sys.stderr)
        time.sleep(0.1)  # Simulate processing
```

Run through cc_executor and monitor memory usage - it should stay constant due to streaming.