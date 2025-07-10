# Medium Example - Concurrent Task Execution

This example demonstrates concurrent execution of multiple independent tasks using CC Executor.

## What This Example Does

Shows how to:
- Execute multiple tasks concurrently
- Use semaphores to limit parallelism
- Track progress with tqdm
- Handle results in order

## Features Demonstrated

- **Concurrent Execution**: Run multiple cc_execute calls in parallel
- **Rate Limiting**: Semaphore prevents overloading (max 3 concurrent)
- **Progress Tracking**: Visual progress bar with tqdm
- **Batch Processing**: Alternative pattern using asyncio.gather

## Run It

```bash
python concurrent_tasks.py
```

## Example Output

```
=== Concurrent Execution Example ===
Processing: 100%|████████████| 6/6 [00:20<00:00,  3.4s/it]

Results:
✅ README generated
✅ API docs created
✅ Tests written
✅ Docker compose ready
✅ CI/CD workflow done
✅ Contributing guide complete

Total time: 20.4s (vs ~40s sequential)
Speedup: ~2x
```

## Key Concepts

### Semaphore Pattern
```python
semaphore = Semaphore(3)  # Max 3 concurrent

async def execute_with_limit(task):
    async with semaphore:
        return await cc_execute(task)
```

### Progress Tracking
```python
from tqdm.asyncio import tqdm

async for future in tqdm(as_completed(tasks), total=len(tasks)):
    result = await future
```

## When To Use This Pattern

- Multiple independent tasks (no dependencies)
- Want faster overall execution
- Need to respect rate limits
- Visual progress tracking desired

## Next Steps

- See `../advanced/` for production patterns with mixed execution modes