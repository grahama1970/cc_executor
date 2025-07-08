# Claude Code Workarounds Guide

This document outlines workarounds for various limitations when using Claude Code with MCP servers and other integrations.

## Table of Contents
1. [Real-Time Progress Monitoring](#real-time-progress-monitoring)
2. [Sequential Task Execution](#sequential-task-execution)
3. [Working Hooks](#working-hooks)
4. [MCP Streaming Limitations](#mcp-streaming-limitations)
5. [Tool Execution Patterns](#tool-execution-patterns)

---

## Real-Time Progress Monitoring

### Problem
Claude Code doesn't display MCP progress updates (`ctx.info()`, `ctx.report_progress()`) in real-time, even though FastMCP supports these features.

### Workarounds

#### 1. Log Monitoring Tools
We've added three tools to the ArXiv MCP server for monitoring progress:

```python
# Get recent log entries
await mcp__arxiv__get_recent_logs(
    lines=50,
    operation_filter="mcp_bulk_download",
    since_seconds=60
)

# Monitor a specific operation
await mcp__arxiv__monitor_operation(
    operation_id="mcp_bulk_download",
    poll_interval=2.0,
    max_polls=30
)

# Get operation summary
await mcp__arxiv__get_operation_summary(
    operation_type="mcp_search_papers"
)
```

#### 2. Enhanced Result Format
Include execution logs in the final result:

```python
return {
    "results": [...],
    "execution_log": [
        "[00:00] Starting bulk download of 5 papers",
        "[00:02] Downloaded paper 1/5: 2301.07041",
        "[00:05] Downloaded paper 2/5: 2303.08774",
        "[00:08] Analysis complete"
    ]
}
```

#### 3. Progress in Response
Always include progress information in tool responses:

```
📊 Execution Progress Log:
──────────────────────────────────────────────────
[00:00] Starting bulk download and analysis of 3 papers
[00:00] Analysis type: summary
[00:00] ✓ Processed 2301.04567
[00:00]   - Generated summary
[02:00] ✓ Processed 2304.08123
[02:00]   - Generated summary
[04:00] ✓ Processed 2401.02345
[04:00]   - Generated summary
[06:00] Completed: 3/3 successful
──────────────────────────────────────────────────
```

---

## Sequential Task Execution

### Problem
Need to ensure tasks execute in order and handle complex workflows.

### Workarounds

#### 1. CC Executor Pattern
Use the cc_executor project at `/home/graham/workspace/experiments/cc_executor`:

```python
# Create a task file
cat > task.md << 'EOF'
Task 1: Search for papers
Task 2: Download top 5
Task 3: Extract evidence
Task 4: Generate report
EOF

# Execute sequentially
python run_executor.py task.md
```

#### 2. Chained Tool Calls
Design tools to return IDs for chaining:

```python
# First call returns operation_id
result1 = await search_papers(query="quantum computing")
operation_id = result1["operation_id"]

# Use operation_id in next call
result2 = await download_papers(operation_id=operation_id)

# Chain continues
result3 = await extract_evidence(operation_id=operation_id)
```

#### 3. Batch Operations with Dependencies
Use bulk operations that handle sequencing internally:

```python
await bulk_operation(
    operations=[
        {"tool": "search", "arguments": {"query": "AI safety"}},
        {"tool": "download", "arguments": {"use_previous": True}},
        {"tool": "summarize", "arguments": {"use_previous": True}}
    ],
    parallel=False  # Force sequential execution
)
```

---

## Working Hooks

### Problem
Need to intercept and modify behavior at key points.

### Workarounds

#### 1. Middleware Pattern
Wrap handlers with middleware functions:

```python
def with_progress_logging(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        op_logger.info(f"Starting {handler.__name__}")
        try:
            result = await handler(*args, **kwargs)
            op_logger.info(f"Completed {handler.__name__}")
            return result
        except Exception as e:
            op_logger.error(f"Failed {handler.__name__}: {e}")
            raise
    return wrapper

# Apply to all handlers
handle_search = with_progress_logging(handle_search)
```

#### 2. Event Emission
Use logging as an event system:

```python
# Emit events via structured logging
logger.info("operation.started", extra={
    "operation": "bulk_download",
    "event_type": "start",
    "timestamp": datetime.now().isoformat(),
    "metadata": {"paper_count": 5}
})

# Monitor events
grep '"event_type":' /path/to/logs/*.log | jq '.'
```

#### 3. Context Propagation
Pass context through all operations:

```python
class OperationContext:
    def __init__(self):
        self.operation_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.events = []
    
    def add_event(self, event):
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "event": event
        })

# Use throughout operation
ctx = OperationContext()
ctx.add_event("search_started")
result = await search_with_context(query, ctx)
ctx.add_event("search_completed")
```

---

## MCP Streaming Limitations

### Problem
MCP protocol is request/response, not streaming. FastMCP features like SSE aren't visible in Claude Code.

### Workarounds

#### 1. Polling Pattern
Create status endpoints:

```python
# Start long operation
operation_id = await start_bulk_download(paper_ids)

# Poll for status
while True:
    status = await get_operation_status(operation_id)
    print(f"Progress: {status['current']}/{status['total']}")
    if status['completed']:
        break
    await asyncio.sleep(2)
```

#### 2. Chunked Results
Return results in manageable chunks:

```python
# First chunk with continuation token
result = await search_papers_chunked(
    query="machine learning",
    chunk_size=10
)

# Get next chunk
if result["has_more"]:
    next_result = await get_next_chunk(
        token=result["continuation_token"]
    )
```

#### 3. Log Tailing
Use log monitoring as pseudo-streaming:

```bash
# In one terminal
tail -f /path/to/arxiv_*.log | grep "operation_id:12345"

# In Claude Code
operation_id = await start_operation()
print(f"Monitor progress with: tail -f logs | grep {operation_id}")
```

---

## Tool Execution Patterns

### Problem
Need reliable patterns for complex tool interactions.

### Workarounds

#### 1. Transaction Pattern
Group related operations:

```python
async def research_transaction(topic):
    transaction_id = str(uuid.uuid4())
    
    try:
        # All operations share transaction_id
        papers = await search_papers(topic, transaction_id=transaction_id)
        downloads = await download_papers(papers, transaction_id=transaction_id)
        analysis = await analyze_papers(downloads, transaction_id=transaction_id)
        
        await commit_transaction(transaction_id)
        return analysis
    except Exception as e:
        await rollback_transaction(transaction_id)
        raise
```

#### 2. Result Caching
Cache intermediate results:

```python
# Use FastMCP's caching
@cached(ttl=300)  # 5 minute cache
async def expensive_operation(params):
    return await do_expensive_work(params)

# Or manual caching
cache = {}
cache_key = f"{operation}:{params}"
if cache_key in cache:
    return cache[cache_key]
```

#### 3. Error Recovery
Build in retry logic:

```python
async def with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
```

---

## Best Practices

### 1. Always Log Operations
```python
op_logger = get_operation_logger("my_operation")
op_logger.info("Starting", extra={"params": params})
```

### 2. Include Progress in Results
```python
return {
    "data": result,
    "progress_log": progress_events,
    "execution_time": elapsed_time
}
```

### 3. Design for Polling
```python
# Instead of: await long_operation()
# Use: 
op_id = await start_long_operation()
result = await wait_for_completion(op_id)
```

### 4. Use Structured Logging
```python
logger.info("event", extra={
    "operation": "download",
    "phase": "start",
    "paper_id": "2301.07041",
    "timestamp": datetime.now().isoformat()
})
```

### 5. Provide Escape Hatches
```python
# Allow users to check logs directly
print(f"Check progress: tail -f {log_file} | grep {operation_id}")
print(f"Or use: mcp__arxiv__monitor_operation('{operation_id}')")
```

---

## Future Improvements

When Claude Code adds streaming support:
1. All `ctx.info()` and `ctx.report_progress()` calls will work
2. Real-time updates will appear in the UI
3. No code changes needed - infrastructure is ready

Until then, these workarounds provide functional alternatives for progress monitoring and complex workflows.