#!/usr/bin/env python3
"""
Enhanced cc_execute with better progress monitoring based on arxiv-mcp-server critique.

Improvements:
1. Progress callback called on every line (let callback filter)
2. Heartbeat every 30 seconds
3. Structured progress data (elapsed time, line count, etc.)
4. Progress pattern detection (percentages, steps, etc.)
"""

import asyncio
import json
import os
import sys
import time
import uuid
import signal
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, AsyncIterator, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass, asdict
import subprocess
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import the original cc_execute module
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from cc_executor.client.cc_execute import (
    CCExecutorConfig,
    RateLimitError,
    check_token_limit,
    detect_ambiguous_prompt,
    export_execution_history,
    estimate_timeout,
    clean_json_string,
    HookIntegration,
    _execute_claude_command as _original_execute_claude_command
)


@dataclass
class ProgressData:
    """Structured progress data for callbacks."""
    elapsed_seconds: float
    line_count: int
    current_line: str
    is_heartbeat: bool = False
    detected_progress: Optional[Dict[str, Any]] = None  # For patterns like "Step 2/5" or "50%"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def detect_progress_patterns(line: str) -> Optional[Dict[str, Any]]:
    """
    Detect common progress patterns in output.
    
    Returns dict with detected pattern info or None.
    """
    patterns = {
        # Percentage: "50%", "Progress: 75%", etc.
        'percentage': r'(\d+(?:\.\d+)?)\s*%',
        
        # Step format: "Step 2/5", "Task 3 of 10", etc.
        'steps': r'(?:step|task|phase)\s*(\d+)\s*(?:of|\/)\s*(\d+)',
        
        # Iteration: "Iteration 5", "Epoch 10/20"
        'iteration': r'(?:iteration|epoch|round)\s*(\d+)(?:\s*(?:of|\/)\s*(\d+))?',
        
        # Status markers
        'status': r'(?:starting|processing|completing|finished|done|complete)',
        
        # File operations: "Processing file.txt", "Writing to output.json"
        'file_op': r'(?:reading|writing|processing|creating|modifying)\s+(?:file\s+)?(\S+)',
    }
    
    line_lower = line.lower()
    detected = {}
    
    for pattern_name, pattern in patterns.items():
        match = re.search(pattern, line_lower)
        if match:
            if pattern_name == 'percentage':
                detected['type'] = 'percentage'
                detected['value'] = float(match.group(1))
            elif pattern_name == 'steps':
                detected['type'] = 'steps'
                detected['current'] = int(match.group(1))
                detected['total'] = int(match.group(2))
                detected['percentage'] = (int(match.group(1)) / int(match.group(2))) * 100
            elif pattern_name == 'iteration':
                detected['type'] = 'iteration'
                detected['current'] = int(match.group(1))
                if match.group(2):
                    detected['total'] = int(match.group(2))
                    detected['percentage'] = (int(match.group(1)) / int(match.group(2))) * 100
            elif pattern_name == 'status':
                detected['type'] = 'status'
                detected['status'] = match.group(0)
            elif pattern_name == 'file_op':
                detected['type'] = 'file_operation'
                detected['operation'] = match.group(0).split()[0]
                detected['file'] = match.group(1)
    
    return detected if detected else None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=lambda retry_state: logger.warning(f"Rate limit hit, retrying in {retry_state.next_action.sleep} seconds...")
)
async def _execute_claude_command_enhanced(
    cmd: str,
    config: CCExecutorConfig,
    session_id: str,
    execution_uuid: str,
    hooks: Optional[Any],
    stream: bool,
    progress_callback: Optional[Callable[[ProgressData], Any]] = None
) -> Tuple[List[str], List[str], Any]:
    """
    Enhanced version with better progress monitoring.
    """
    start_time = time.time()
    line_count = 0
    last_heartbeat = start_time
    HEARTBEAT_INTERVAL = 30  # seconds
    
    # Create enhanced progress callback that wraps the user's callback
    async def enhanced_progress_handler(line: str):
        nonlocal line_count, last_heartbeat
        line_count += 1
        
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Detect progress patterns
        detected = detect_progress_patterns(line)
        
        # Create progress data
        progress = ProgressData(
            elapsed_seconds=elapsed,
            line_count=line_count,
            current_line=line.strip()[:200],  # Truncate long lines
            is_heartbeat=False,
            detected_progress=detected
        )
        
        # Call user's progress callback on every line
        if progress_callback:
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(progress)
                else:
                    progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        # Send heartbeat if needed
        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
            last_heartbeat = current_time
            heartbeat = ProgressData(
                elapsed_seconds=elapsed,
                line_count=line_count,
                current_line="[HEARTBEAT] Still running...",
                is_heartbeat=True
            )
            if progress_callback:
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(heartbeat)
                    else:
                        progress_callback(heartbeat)
                except Exception as e:
                    logger.warning(f"Heartbeat callback error: {e}")
    
    # Wrap command with stdbuf for unbuffered output
    wrapped_cmd = f"stdbuf -o0 -e0 {cmd}"
    logger.info(f"Executing enhanced command with progress monitoring")
    
    # Pre-execution hooks
    if hooks and hooks.enabled:
        logger.info(f"[HOOKS] Running pre-execution hooks")
        success = await hooks.async_pre_execute_hook(wrapped_cmd, execution_uuid)
        if not success:
            raise RuntimeError("Pre-execution hook failed")
    
    # Create subprocess
    proc = await asyncio.create_subprocess_shell(
        wrapped_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
        limit=8 * 1024 * 1024  # 8MB buffer limit
    )
    logger.info(f"[{session_id}] Enhanced subprocess created with PID: {proc.pid}")
    
    # Collect output
    output_lines = []
    error_lines = []
    
    try:
        if stream and config.stream_output:
            # Enhanced streaming with progress on every line
            async def read_stream(stream, target_list, prefix=""):
                """Read from stream line by line with enhanced progress."""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    target_list.append(decoded)
                    
                    # Stream to console with session ID
                    print(f"[{session_id}] {decoded}", end='')
                    
                    # Call progress handler on EVERY line
                    await enhanced_progress_handler(decoded)
            
            # Create concurrent tasks for stdout/stderr
            stdout_task = asyncio.create_task(read_stream(proc.stdout, output_lines))
            stderr_task = asyncio.create_task(read_stream(proc.stderr, error_lines))
            
            # Wait for process with timeout and heartbeats
            try:
                while True:
                    # Check if process is done
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=1.0)
                        break  # Process completed
                    except asyncio.TimeoutError:
                        # Process still running, check for heartbeat
                        current_time = time.time()
                        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
                            # Send heartbeat
                            elapsed = current_time - start_time
                            heartbeat = ProgressData(
                                elapsed_seconds=elapsed,
                                line_count=line_count,
                                current_line=f"[HEARTBEAT] Process running for {elapsed:.1f}s",
                                is_heartbeat=True
                            )
                            if progress_callback:
                                try:
                                    if asyncio.iscoroutinefunction(progress_callback):
                                        await progress_callback(heartbeat)
                                    else:
                                        progress_callback(heartbeat)
                                except Exception as e:
                                    logger.warning(f"Heartbeat callback error: {e}")
                            last_heartbeat = current_time
                
                # Process completed, wait for streams to finish
                await stdout_task
                await stderr_task
                
            except asyncio.TimeoutError:
                logger.error(f"[{session_id}] Process timed out after {config.timeout}s")
                await terminate_process_group(proc, session_id)
                raise
        else:
            # Non-streaming mode - still send heartbeats
            async def heartbeat_monitor():
                """Send heartbeats during non-streaming execution."""
                nonlocal last_heartbeat
                while True:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    current_time = time.time()
                    elapsed = current_time - start_time
                    heartbeat = ProgressData(
                        elapsed_seconds=elapsed,
                        line_count=0,  # Unknown in non-streaming
                        current_line=f"[HEARTBEAT] Process running for {elapsed:.1f}s (non-streaming mode)",
                        is_heartbeat=True
                    )
                    if progress_callback:
                        try:
                            if asyncio.iscoroutinefunction(progress_callback):
                                await progress_callback(heartbeat)
                            else:
                                progress_callback(heartbeat)
                        except Exception as e:
                            logger.warning(f"Heartbeat callback error: {e}")
                    last_heartbeat = current_time
            
            # Start heartbeat monitor
            heartbeat_task = asyncio.create_task(heartbeat_monitor())
            
            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=config.timeout
                )
                output_lines = stdout.decode('utf-8', errors='replace').splitlines(keepends=True)
                error_lines = stderr.decode('utf-8', errors='replace').splitlines(keepends=True)
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
        
        # Check for rate limit errors
        full_output = ''.join(output_lines)
        full_error = ''.join(error_lines)
        
        if any(pattern in full_output.lower() or pattern in full_error.lower() 
               for pattern in ['rate limit', '429', 'too many requests']):
            logger.warning(f"Rate limit detected in output")
            raise RateLimitError("Claude API rate limit hit")
        
        logger.info(f"[{session_id}] Process completed successfully")
        return output_lines, error_lines, proc
        
    except Exception as e:
        logger.error(f"[{session_id}] Process error: {e}")
        await terminate_process_group(proc, session_id)
        raise


async def terminate_process_group(proc, session_id):
    """Terminate process group."""
    try:
        if proc.returncode is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            await asyncio.sleep(0.5)
            if proc.returncode is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception as e:
        logger.error(f"[{session_id}] Error terminating process group: {e}")


async def cc_execute_enhanced(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,
    generate_report: bool = False,
    amend_prompt: bool = False,
    validation_prompt: Optional[str] = None,
    progress_callback: Optional[Callable[[ProgressData], Any]] = None,
    legacy_progress_callback: Optional[Callable[[str], Any]] = None  # For backward compatibility
) -> Union[str, Dict[str, Any]]:
    """
    Enhanced cc_execute with better progress monitoring.
    
    The progress_callback now receives ProgressData objects with:
    - elapsed_seconds: Time since start
    - line_count: Number of lines processed
    - current_line: The current line (truncated)
    - is_heartbeat: True if this is a heartbeat update
    - detected_progress: Any detected progress patterns (percentages, steps, etc.)
    
    For backward compatibility, you can still use legacy_progress_callback which
    receives simple string messages.
    """
    if config is None:
        config = CCExecutorConfig()
    
    # Convert legacy callback to new format if needed
    if legacy_progress_callback and not progress_callback:
        def wrapped_callback(progress: ProgressData):
            # Convert to simple string for legacy callback
            if progress.is_heartbeat:
                msg = f"[HEARTBEAT] {progress.elapsed_seconds:.1f}s elapsed"
            elif progress.detected_progress:
                detected = progress.detected_progress
                if detected['type'] == 'percentage':
                    msg = f"Progress: {detected['value']:.1f}%"
                elif detected['type'] == 'steps':
                    msg = f"Step {detected['current']}/{detected['total']}"
                else:
                    msg = progress.current_line
            else:
                msg = progress.current_line
            legacy_progress_callback(msg)
        progress_callback = wrapped_callback
    
    # Apply token limit check
    task = check_token_limit(task)
    
    # Detect ambiguous prompts
    warning = detect_ambiguous_prompt(task)
    if warning:
        logger.warning(f"Ambiguous prompt detected: {warning}")
    
    # Set up the rest similar to original cc_execute
    session_id = str(uuid.uuid4())[:8]
    execution_uuid = str(uuid.uuid4())
    
    logger.info(f"[{session_id}] Starting enhanced execution")
    
    # Initialize hooks
    hooks = None
    if HookIntegration:
        try:
            hooks = HookIntegration()
        except Exception as e:
            logger.warning(f"Could not initialize hooks: {e}")
    
    # Build command
    mcp_config_path = Path.cwd() / ".mcp.json"
    mcp_flags = f' --mcp-config "{mcp_config_path}"' if mcp_config_path.exists() else ""
    
    if json_mode:
        # Add JSON schema requirement
        response_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "files_created": {"type": "array", "items": {"type": "string"}},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
                "execution_uuid": {"type": "string"}
            },
            "required": ["result", "summary", "execution_uuid"]
        }
        task = f"""{task}

IMPORTANT: Structure your response as JSON matching this schema:
{json.dumps(response_schema, indent=2)}

The execution_uuid MUST be: {execution_uuid}"""
    
    cmd = f'claude -p "{task}"{mcp_flags} --dangerously-skip-permissions --model claude-opus-4-20250514'
    
    # Execute with enhanced progress monitoring
    try:
        output_lines, error_lines, proc = await _execute_claude_command_enhanced(
            cmd, config, session_id, execution_uuid, hooks, stream, progress_callback
        )
        
        # Process results
        full_output = ''.join(output_lines).strip()
        full_error = ''.join(error_lines).strip()
        
        if json_mode and full_output:
            try:
                if clean_json_string:
                    cleaned = clean_json_string(full_output)
                    result = json.loads(cleaned)
                else:
                    result = json.loads(full_output)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                return {"error": "JSON parsing failed", "raw_output": full_output}
        
        return full_output
        
    except Exception as e:
        logger.error(f"[{session_id}] Execution failed: {e}")
        raise


# Example usage
async def example_progress_handler(progress: ProgressData):
    """Example of handling structured progress data."""
    if progress.is_heartbeat:
        print(f"\n💓 Heartbeat: {progress.elapsed_seconds:.1f}s elapsed, {progress.line_count} lines processed")
    elif progress.detected_progress:
        detected = progress.detected_progress
        if detected['type'] == 'percentage':
            print(f"\n📊 Progress: {detected['value']:.1f}%")
        elif detected['type'] == 'steps':
            print(f"\n📋 Step {detected['current']}/{detected['total']} ({detected['percentage']:.1f}%)")
        elif detected['type'] == 'file_operation':
            print(f"\n📁 {detected['operation'].title()} {detected['file']}")
    else:
        # Regular line - could filter for specific patterns
        if any(keyword in progress.current_line.lower() for keyword in ['error', 'warning', 'failed']):
            print(f"\n⚠️  {progress.current_line}")


if __name__ == "__main__":
    # Test the enhanced version
    async def test():
        result = await cc_execute_enhanced(
            "Create a Python script that counts from 1 to 10 slowly, printing progress",
            progress_callback=example_progress_handler
        )
        print(f"\nFinal result:\n{result}")
    
    asyncio.run(test())