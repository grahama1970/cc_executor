# Quickstart Example - Your First CC Executor Task

This is the simplest possible example to get you started with CC Executor in under 2 minutes.

## What This Example Does

Executes a single task using `cc_execute` to generate a Python function.

## Run It

```bash
python quickstart.py
```

## What You'll See

1. Task execution with progress output
2. Generated Python code
3. Automatic verification (no hallucination)
4. Execution receipt for audit trail

## The Code

```python
import asyncio
from cc_executor.client.cc_execute import cc_execute

async def main():
    # Execute a single task
    result = await cc_execute("Write a Python function to calculate fibonacci numbers")
    print(result)

asyncio.run(main())
```

## Key Points

- ✅ No configuration needed
- ✅ Automatic timeout prediction
- ✅ Built-in anti-hallucination
- ✅ Redis optional (falls back gracefully)

## Next Steps

Ready for more? Check out:
- `../basic/` - Multiple tasks in sequence
- `../medium/` - Concurrent execution
- `../advanced/` - Production patterns