# Orchestration Agent Control Patterns

## Overview

This document explains how orchestration agents use the WebSocket MCP control commands (PAUSE, RESUME, CANCEL) to manage long-running Claude Code executions.

## Why Orchestration Agents Need Control Commands

### 1. **Resource Management**
When running multiple Claude instances, agents need to:
- Pause lower-priority tasks when high-priority work arrives
- Resume paused tasks when resources become available
- Cancel tasks that exceed time/cost budgets

### 2. **Error Recovery**
Agents must handle:
- Runaway processes consuming excessive resources
- Stuck processes showing no output for extended periods
- Incorrect executions that need to be stopped early

### 3. **User Intervention**
Enable users to:
- Pause expensive operations for review
- Cancel mistaken requests
- Resume after providing additional context

## Control Command Use Cases

### PAUSE - Temporary Suspension

**When to use PAUSE:**
1. **Resource Contention**
   ```python
   # Orchestrator detects high memory usage
   if system_memory_usage() > 90:
       await websocket.send(json.dumps({
           "jsonrpc": "2.0",
           "id": 2,
           "method": "control",
           "params": {"type": "PAUSE"}
       }))
       await wait_for_resources()
   ```

2. **Rate Limiting**
   ```python
   # Pause when approaching API limits
   if api_calls_this_minute >= 50:
       await pause_all_low_priority_tasks()
       await sleep(60)  # Wait for rate limit reset
       await resume_tasks()
   ```

3. **Human Review Required**
   ```python
   # Pause for verification on sensitive operations
   if task.requires_approval and not task.approved:
       await pause_task(task.id)
       await notify_human_for_approval()
   ```

**What happens during PAUSE:**
- Process receives SIGSTOP signal
- All CPU activity stops immediately
- Memory remains allocated
- Network connections may timeout
- File handles remain open
- Can be resumed later with exact state

### RESUME - Continuing Execution

**When to use RESUME:**
1. **Resources Available**
   ```python
   # Resume when system load decreases
   async def resource_monitor():
       paused_tasks = await get_paused_tasks()
       
       for task in paused_tasks:
           if system_resources_available():
               await websocket.send(json.dumps({
                   "jsonrpc": "2.0",
                   "id": 3,
                   "method": "control",
                   "params": {"type": "RESUME"}
               }))
               await log_task_resumed(task.id)
   ```

2. **Approval Received**
   ```python
   # Resume after human approval
   async def handle_approval(task_id, approved):
       if approved:
           await resume_task(task_id)
       else:
           await cancel_task(task_id)
   ```

3. **Scheduled Resume**
   ```python
   # Resume during off-peak hours
   async def scheduled_resume():
       if datetime.now().hour in OFF_PEAK_HOURS:
           await resume_all_paused_background_tasks()
   ```

**Considerations for RESUME:**
- Process continues exactly where it left off
- May need to handle stale connections
- Check if context has changed during pause

### CANCEL - Terminating Execution

**When to use CANCEL:**
1. **Timeout Exceeded**
   ```python
   # Cancel long-running tasks
   async def timeout_monitor(task_id, max_duration):
       start_time = time.time()
       
       while task_running(task_id):
           if time.time() - start_time > max_duration:
               await websocket.send(json.dumps({
                   "jsonrpc": "2.0",
                   "id": 4,
                   "method": "control",
                   "params": {"type": "CANCEL"}
               }))
               await log_timeout_cancellation(task_id)
               break
           await asyncio.sleep(10)
   ```

2. **No Output Detection**
   ```python
   # Cancel if no output for extended period
   async def stall_detector(websocket):
       last_output_time = time.time()
       
       while True:
           msg = await websocket.recv()
           data = json.loads(msg)
           
           if data.get('method') == 'process.output':
               last_output_time = time.time()
           
           # Check for stall
           if time.time() - last_output_time > STALL_TIMEOUT:
               await send_cancel_command(websocket)
               break
   ```

3. **Error Detection**
   ```python
   # Cancel on error patterns
   async def error_monitor(websocket):
       while True:
           msg = await websocket.recv()
           data = json.loads(msg)
           
           if data.get('method') == 'process.output':
               output = data['params']['data']
               
               # Check for error patterns
               if any(error in output for error in FATAL_ERRORS):
                   await send_cancel_command(websocket)
                   await log_error_cancellation(output)
                   break
   ```

4. **User Request**
   ```python
   # Handle user cancellation
   async def handle_user_cancel(task_id):
       websocket = get_task_websocket(task_id)
       await send_cancel_command(websocket)
       await notify_user_cancelled(task_id)
   ```

**CANCEL Process Flow:**
1. First sends SIGTERM (graceful shutdown)
2. Waits 10 seconds for process to clean up
3. If still running, sends SIGKILL (force kill)
4. Ensures all child processes are terminated

## Orchestration Patterns

### Pattern 1: Priority-Based Resource Management

```python
class PriorityOrchestrator:
    def __init__(self):
        self.active_tasks = {}
        self.paused_tasks = {}
        self.max_concurrent = 5
    
    async def submit_task(self, task):
        if len(self.active_tasks) < self.max_concurrent:
            await self.start_task(task)
        else:
            # Pause lowest priority task
            lowest = min(self.active_tasks.values(), 
                        key=lambda t: t.priority)
            
            if task.priority > lowest.priority:
                await self.pause_task(lowest.id)
                await self.start_task(task)
            else:
                self.queue_task(task)
    
    async def pause_task(self, task_id):
        task = self.active_tasks[task_id]
        await task.websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "id": task.next_msg_id(),
            "method": "control",
            "params": {"type": "PAUSE"}
        }))
        
        self.paused_tasks[task_id] = task
        del self.active_tasks[task_id]
```

### Pattern 2: Cost-Aware Execution

```python
class CostAwareOrchestrator:
    def __init__(self, budget_per_hour=10.0):
        self.budget_per_hour = budget_per_hour
        self.current_cost = 0
        self.hour_start = time.time()
    
    async def execute_with_budget(self, task):
        # Start execution
        websocket = await self.connect_and_execute(task)
        
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            
            # Track token usage from Claude output
            if data.get('method') == 'process.output':
                self.current_cost += self.estimate_cost(data)
                
                # Pause if approaching budget
                if self.current_cost > self.budget_per_hour * 0.9:
                    await self.pause_all_tasks()
                    await self.wait_for_budget_reset()
                    await self.resume_all_tasks()
            
            elif data.get('method') == 'process.completed':
                break
```

### Pattern 3: Intelligent Failure Recovery

```python
class ResilientOrchestrator:
    async def execute_with_recovery(self, task):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await self.execute_task(task)
                return result
                
            except StallDetected:
                # Cancel and retry with different parameters
                await self.cancel_task(task)
                task.adjust_parameters()  # Simplify request
                retry_count += 1
                
            except HighMemoryUsage:
                # Pause, wait, resume
                await self.pause_task(task)
                await self.wait_for_memory()
                await self.resume_task(task)
                
            except NetworkError:
                # Cancel and retry with backoff
                await self.cancel_task(task)
                await asyncio.sleep(2 ** retry_count)
                retry_count += 1
```

### Pattern 4: Multi-Stage Pipeline Control

```python
class PipelineOrchestrator:
    async def run_pipeline(self, stages):
        results = []
        
        for i, stage in enumerate(stages):
            # Execute stage
            websocket = await self.connect_and_execute(stage)
            result = await self.collect_output(websocket)
            
            # Validate stage output
            if not self.validate_stage(result):
                # Cancel remaining stages
                await self.cancel_task(stage)
                
                # Retry or adjust
                if stage.can_retry:
                    continue
                else:
                    raise PipelineError(f"Stage {i} failed")
            
            # Check if we should pause before next stage
            if self.should_pause_for_review(stage, result):
                await self.pause_pipeline()
                await self.wait_for_review()
                await self.resume_pipeline()
            
            results.append(result)
        
        return results
```

## Best Practices for Orchestration Agents

### 1. **State Tracking**
Always maintain state about controlled processes:
```python
class TaskState:
    def __init__(self, task_id):
        self.task_id = task_id
        self.status = "running"  # running, paused, cancelled
        self.start_time = time.time()
        self.last_output_time = time.time()
        self.pause_count = 0
        self.total_pause_duration = 0
        self.output_buffer = []
```

### 2. **Graceful Degradation**
Handle control command failures:
```python
async def safe_cancel(websocket, task_id):
    try:
        # Try graceful cancel
        await send_cancel_command(websocket)
    except WebSocketError:
        # If websocket fails, ensure cleanup
        await force_cleanup(task_id)
    finally:
        await mark_task_cancelled(task_id)
```

### 3. **Resource Monitoring**
Track resource usage for intelligent control:
```python
async def resource_aware_execution():
    monitor = ResourceMonitor()
    
    async def check_resources():
        while True:
            stats = monitor.get_stats()
            
            if stats.memory_percent > 80:
                await pause_low_priority_tasks()
            elif stats.memory_percent < 50:
                await resume_paused_tasks()
            
            await asyncio.sleep(5)
    
    # Run monitor in background
    asyncio.create_task(check_resources())
```

### 4. **Audit Logging**
Log all control actions for debugging:
```python
async def log_control_action(task_id, action, reason):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "action": action,  # PAUSE, RESUME, CANCEL
        "reason": reason,
        "system_state": get_system_metrics()
    }
    await audit_log.write(log_entry)
```

## Integration Example: Complete Orchestrator

```python
class ClaudeOrchestrator:
    def __init__(self):
        self.tasks = {}
        self.websockets = {}
    
    async def execute_claude_task(self, prompt, max_time=300):
        task_id = str(uuid.uuid4())
        
        # Connect to MCP server
        ws = await websockets.connect("ws://localhost:8003/ws/mcp")
        self.websockets[task_id] = ws
        
        # Wait for connection
        await ws.recv()
        
        # Execute Claude
        command = f'claude --print "{prompt}"'
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {"command": command}
        }))
        
        # Monitor execution
        task = {
            "id": task_id,
            "start_time": time.time(),
            "last_output": time.time(),
            "output": "",
            "status": "running"
        }
        self.tasks[task_id] = task
        
        # Start monitors
        asyncio.create_task(self.timeout_monitor(task_id, max_time))
        asyncio.create_task(self.stall_monitor(task_id))
        
        # Collect output
        return await self.collect_output(task_id)
    
    async def timeout_monitor(self, task_id, max_time):
        await asyncio.sleep(max_time)
        
        if self.tasks[task_id]["status"] == "running":
            await self.cancel_task(task_id, "Timeout exceeded")
    
    async def stall_monitor(self, task_id, stall_timeout=120):
        while self.tasks[task_id]["status"] == "running":
            last_output = self.tasks[task_id]["last_output"]
            
            if time.time() - last_output > stall_timeout:
                await self.cancel_task(task_id, "No output for 2 minutes")
                break
            
            await asyncio.sleep(10)
    
    async def cancel_task(self, task_id, reason):
        ws = self.websockets.get(task_id)
        if not ws:
            return
        
        # Send cancel command
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "control",
            "params": {"type": "CANCEL"}
        }))
        
        self.tasks[task_id]["status"] = "cancelled"
        await self.log_action(task_id, "CANCEL", reason)
```

## Conclusion

The WebSocket MCP control commands (PAUSE, RESUME, CANCEL) provide orchestration agents with fine-grained control over long-running processes. These commands enable:

1. **Resource optimization** through priority-based scheduling
2. **Cost management** via usage-based pausing
3. **Reliability** through timeout and stall detection
4. **Flexibility** with pause/resume for human review

By leveraging these controls, orchestration agents can build sophisticated execution strategies that maximize efficiency while maintaining reliability and cost-effectiveness.