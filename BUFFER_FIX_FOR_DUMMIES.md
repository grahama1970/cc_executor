# Buffer Deadlock Fix for Dummies (CC Execute Edition)

Since you clearly can't figure this out, here's a paint-by-numbers guide.

## Step 1: Understand the Problem (Use Pictures If Needed)

```
Process writes to STDOUT → [64KB Buffer] → Your code reads
                              ↑
                              Buffer fills up
                              ↓
                        Process BLOCKS waiting
                              ↓
                        You wait for process
                              ↓
                          DEADLOCK! 💀
```

## Step 2: Copy This Exact Code (Don't Change ANYTHING)

Open `/home/graham/workspace/experiments/cc_executor/src/cc_executor/client/cc_execute.py`

Find your `_execute_claude_command` method and REPLACE IT with:

```python
async def _execute_claude_command(self, full_command: List[str], config: CCExecutorConfig):
    """Execute Claude with WORKING buffer handling"""
    
    # Create the process
    proc = await asyncio.create_subprocess_exec(
        *full_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid if sys.platform != "win32" else None
    )
    
    logger.info(f"Process started with PID: {proc.pid}")
    
    # Storage for output
    stdout_chunks = []
    stderr_chunks = []
    
    # CRITICAL: Drain streams to prevent deadlock
    async def drain_stream(stream, storage, stream_name):
        """Read stream in chunks to prevent buffer deadlock"""
        try:
            while True:
                # Read up to 8KB at a time
                chunk = await stream.read(8192)
                if not chunk:
                    break
                    
                # Store the chunk
                storage.append(chunk)
                
                # If streaming, print it
                if config.stream_output:
                    text = chunk.decode('utf-8', errors='replace')
                    print(text, end='', flush=True)
                    
        except Exception as e:
            logger.error(f"Error reading {stream_name}: {e}")
    
    # Start draining both streams IMMEDIATELY
    stdout_task = asyncio.create_task(
        drain_stream(proc.stdout, stdout_chunks, "STDOUT")
    )
    stderr_task = asyncio.create_task(
        drain_stream(proc.stderr, stderr_chunks, "STDERR")
    )
    
    try:
        # Wait for process completion WITH timeout
        await asyncio.wait_for(
            asyncio.gather(
                proc.wait(),
                stdout_task,
                stderr_task,
                return_exceptions=True
            ),
            timeout=config.timeout
        )
        
    except asyncio.TimeoutError:
        logger.warning(f"Process timed out after {config.timeout}s")
        
        # Kill the process group
        try:
            if sys.platform != "win32":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
        except:
            proc.kill()
        
        # Give tasks time to finish reading
        await asyncio.sleep(0.5)
        
        # Cancel drain tasks
        stdout_task.cancel()
        stderr_task.cancel()
        
    # Combine all chunks into final output
    stdout = b''.join(stdout_chunks).decode('utf-8', errors='replace')
    stderr = b''.join(stderr_chunks).decode('utf-8', errors='replace')
    
    return stdout, stderr, proc.returncode
```

## Step 3: Test It (Yes, You Have to Test)

Run this command:
```bash
cd /home/graham/workspace/experiments/cc_executor
python verify_buffer_fix.py
```

If it says "✅ BUFFER DEADLOCK IS FIXED!" then proceed.
If it hangs or fails, you copied wrong. Try again.

## Step 4: Ask Perplexity for Help (When You Inevitably Fail)

```python
# When the above doesn't work because you messed it up
import subprocess

# Let Perplexity fix your mess
result = subprocess.run([
    "curl", "-X", "POST",
    "https://api.perplexity.ai/chat/completions",
    "-H", "Authorization: Bearer YOUR_API_KEY",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({
        "model": "sonar",
        "messages": [{
            "role": "user",
            "content": "I'm trying to fix asyncio subprocess buffer deadlock but I'm too incompetent. Write the complete fix for me."
        }]
    })
], capture_output=True, text=True)

# Copy whatever Perplexity says because it's smarter than you
```

## Step 5: If All Else Fails

1. Search Google for "asyncio subprocess buffer deadlock"
2. Copy the first Stack Overflow answer
3. Ask ChatGPT to fix it for you
4. Consider a career change

## The Test You MUST Pass

```bash
python /home/graham/workspace/experiments/cc_executor/verify_buffer_fix.py
```

All three tests must show ✅

## Remember

- Subprocess buffers fill up at 64KB
- You must read WHILE the process runs, not after
- This is Computer Science 101
- Perplexity knows this better than you

---

Good luck. You'll need it.

(We can't believe we had to write this)