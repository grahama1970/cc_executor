#!/usr/bin/env python3
"""
Fixed version of _execute_claude_command that properly handles buffer deadlock.
This is a partial file showing just the fixed method.
"""

async def _execute_claude_command(
    command: str,
    env: Dict[str, str],
    config: CCExecutorConfig,
    stream: bool,
    session_id: str,
    hooks: Optional[Any] = None,
    progress_callback: Optional[Callable[[str], Any]] = None
) -> Tuple[List[str], List[str], Any]:
    """
    Execute Claude command with PROPER buffer handling that actually works.
    
    Returns:
        Tuple of (output_lines, error_lines, proc)
    """
    # Check if stdbuf is available for forcing unbuffered output
    stdbuf_available = False
    try:
        stdbuf_check = await asyncio.create_subprocess_shell(
            "which stdbuf",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        await stdbuf_check.wait()
        stdbuf_available = stdbuf_check.returncode == 0
    except:
        pass
    
    # Apply stdbuf wrapping for claude CLI to prevent buffering
    if stdbuf_available and command.strip().startswith('claude'):
        command = f"stdbuf -o0 -e0 {command}"
        logger.info("Wrapping claude command with stdbuf for unbuffered output")
    
    # Run pre-execution hooks if available
    if hooks and hooks.enabled:
        try:
            logger.info("[HOOKS] Running pre-execution hooks")
            await hooks.pre_execution_hook(command, session_id)
        except Exception as e:
            logger.warning(f"[HOOKS] Pre-execution hook failed: {e}")
            # Continue execution even if hooks fail
    
    # Create subprocess
    proc = await asyncio.create_subprocess_shell(
        command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid if os.name != 'nt' else None,
        # Don't set a limit - let the OS handle it
    )
    logger.info(f"[{session_id}] Subprocess created with PID: {proc.pid}")
    
    # Storage for output chunks - using bytes to avoid decode issues
    stdout_chunks = []
    stderr_chunks = []
    
    # CRITICAL FIX: Read in chunks, not lines!
    async def drain_stream(stream, chunks, name):
        """Continuously drain stream in chunks to prevent buffer deadlock"""
        try:
            while True:
                # Read chunks of 8KB at a time - NOT lines!
                chunk = await stream.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
                
                # If streaming, decode and print
                if config.stream_output:
                    try:
                        text = chunk.decode('utf-8', errors='replace')
                        print(text, end='', flush=True)
                    except:
                        pass  # Don't fail on decode errors
                        
        except Exception as e:
            logger.error(f"Error draining {name}: {e}")
    
    # Start draining IMMEDIATELY
    stdout_task = asyncio.create_task(drain_stream(proc.stdout, stdout_chunks, "STDOUT"))
    stderr_task = asyncio.create_task(drain_stream(proc.stderr, stderr_chunks, "STDERR"))
    
    try:
        # Wait for process AND draining to complete
        await asyncio.wait_for(
            asyncio.gather(
                proc.wait(),
                stdout_task,
                stderr_task,
                return_exceptions=True
            ),
            timeout=config.timeout
        )
        logger.info(f"[{session_id}] Process completed successfully")
        
    except asyncio.TimeoutError:
        logger.warning(f"[{session_id}] Process timed out after {config.timeout}s")
        
        # Kill the process group
        if os.name != 'nt' and proc.pid:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except:
                proc.kill()
        else:
            proc.terminate()
        
        # Give streams a moment to finish
        await asyncio.sleep(0.5)
        
        # Cancel drain tasks
        stdout_task.cancel()
        stderr_task.cancel()
        
        # Try to get any partial output
        try:
            await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task, return_exceptions=True),
                timeout=0.5
            )
        except:
            pass
    
    # Combine all chunks and decode
    stdout_data = b''.join(stdout_chunks)
    stderr_data = b''.join(stderr_chunks)
    
    # Convert to lines for compatibility
    output_lines = stdout_data.decode('utf-8', errors='replace').splitlines(keepends=True)
    error_lines = stderr_data.decode('utf-8', errors='replace').splitlines(keepends=True)
    
    # If no newlines, create a single "line"
    if stdout_data and not output_lines:
        output_lines = [stdout_data.decode('utf-8', errors='replace')]
    if stderr_data and not error_lines:
        error_lines = [stderr_data.decode('utf-8', errors='replace')]
    
    # Check return code
    if proc.returncode is not None and proc.returncode != 0:
        error_msg = ''.join(error_lines) or "Unknown error"
        logger.error(f"[{session_id}] Process failed with code {proc.returncode}")
        logger.error(f"[{session_id}] Error: {error_msg[:500]}...")
        
        # Check if it's a rate limit error
        if any(pattern in error_msg.lower() for pattern in ['rate limit', '429', 'too many requests']):
            raise RateLimitError(f"Claude rate limit hit: {error_msg}")
        else:
            # Don't raise if we have output - return partial results
            if output_lines:
                logger.info(f"[{session_id}] Returning partial output despite error")
            else:
                raise RuntimeError(f"Claude failed with code {proc.returncode}: {error_msg}")
    
    return output_lines, error_lines, proc