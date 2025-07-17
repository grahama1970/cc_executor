#!/usr/bin/env python3
"""
Core executor for complex Claude tasks.

Handles:
- Long-running complex tasks (hours)
- Streaming output for visibility
- Proper error handling
- Task list execution

IMPORTANT: Claude CLI instances do NOT have access to:
- Task/Todo tools (use direct questions instead)
- UI features (drag & drop, buttons, etc.)
- Rich formatting (markdown rendering, etc.)
- Built-in productivity tools

See docs/guides/CLAUDE_CLI_PROMPT_BEST_PRACTICES.md for details.
"""
import asyncio
import json
import os
import sys
import time
import uuid
import signal
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, AsyncIterator, Dict, Any, Union, Callable, Tuple
from dataclasses import dataclass
import subprocess
from loguru import logger
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import redis  # Always available in cc_executor environment


# Custom exception for rate limits
class RateLimitError(Exception):
    """Raised when Claude API rate limit is hit."""
    pass


class ThinkingIndicatorHandler:
    """Handles confirmation that Claude has started processing."""
    
    def __init__(self, 
                 thinking_threshold: float = 5.0,
                 update_interval: float = 30.0):
        """
        Initialize thinking indicator handler.
        
        Args:
            thinking_threshold: Seconds to wait before showing thinking indicator
            update_interval: Seconds between status updates (increased to 30s)
        """
        self.thinking_threshold = thinking_threshold
        self.update_interval = update_interval
        self.start_time = None
        self.first_content_time = None
        self.thinking_task = None
        self.initial_message_shown = False
        
    async def start_monitoring(self, progress_callback: Optional[Callable] = None):
        """Start monitoring for thinking indicators."""
        self.start_time = time.time()
        
        if progress_callback:
            self.thinking_task = asyncio.create_task(
                self._thinking_monitor(progress_callback)
            )
    
    async def _thinking_monitor(self, callback: Callable):
        """Monitor and provide simple status updates."""
        await asyncio.sleep(self.thinking_threshold)
        
        # If no content yet, show initial confirmation
        if self.first_content_time is None and not self.initial_message_shown:
            elapsed = time.time() - self.start_time
            # Handle both sync and async callbacks
            try:
                result = callback(f"✅ Claude is processing your request... ({elapsed:.0f}s)")
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.debug(f"Thinking callback error: {e}")
            self.initial_message_shown = True
            
            # Continue with periodic updates (less frequent)
            while self.first_content_time is None:
                await asyncio.sleep(self.update_interval)
                elapsed = time.time() - self.start_time
                
                # Simple elapsed time update
                try:
                    result = callback(f"⏱️  Still processing... ({elapsed:.0f}s elapsed)")
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.debug(f"Thinking callback error: {e}")
    
    def record_first_content(self):
        """Record when first actual content is received."""
        if self.first_content_time is None:
            self.first_content_time = time.time()
            if self.thinking_task and not self.thinking_task.done():
                self.thinking_task.cancel()
    
    async def cleanup(self):
        """Clean up any running tasks."""
        if self.thinking_task and not self.thinking_task.done():
            self.thinking_task.cancel()
            try:
                await self.thinking_task
            except asyncio.CancelledError:
                pass


# Import report generator for assessment reports
from cc_executor.client.report_generator import generate_assessment_report, save_assessment_report

# Import JSON utilities for robust parsing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from cc_executor.utils.json_utils import clean_json_string

# Import HookIntegration for consistent pre/post execution hooks
from cc_executor.hooks.hook_integration import HookIntegration






# Logger configuration handled by main cc_executor package

@dataclass
class CCExecutorConfig:
    """Configuration for CC Executor."""
    timeout: int = 300  # 5 minutes default (reasonable for most tasks)
    stream_output: bool = True
    save_transcript: bool = True
    # CRITICAL: Follow PROMPT_TEMPLATE.md - save to local tmp/responses
    response_dir: Path = Path(__file__).parent / "tmp" / "responses"
    transcript_dir: Path = Path("/tmp/cc_executor_transcripts")
    # api_key_env: str = "ANTHROPIC_API_KEY"  # NOT USED - browser auth
    
    def __post_init__(self):
        self.response_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(exist_ok=True)


async def estimate_timeout_async(task: str, default: int = 120) -> int:
    """
    Estimate timeout based on task complexity and Redis history.
    Uses the sophisticated RedisTaskTimer system for intelligent predictions.
    """
    try:
        # Use the sophisticated Redis timing system directly
        # Add the src directory to path for the import
        import sys
        if str(Path(__file__).parent.parent.parent) not in sys.path:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from cc_executor.prompts.redis_task_timing import RedisTaskTimer
        
        # Create timer instance
        timer = RedisTaskTimer()
        
        # Get complexity estimation which includes timeout prediction
        estimation = await timer.estimate_complexity(task)
        
        # Use the max_time as timeout (includes safety margin)
        suggested_timeout = int(estimation['max_time'])
        
        logger.info(f"RedisTaskTimer prediction: {suggested_timeout}s "
                   f"(category: {estimation['category']}, "
                   f"complexity: {estimation['complexity']}, "
                   f"confidence: {estimation['confidence']:.2f}, "
                   f"based on: {estimation['based_on']})")
        
        # Ensure minimum timeout
        return max(suggested_timeout, 60)
            
    except Exception as e:
        logger.warning(f"RedisTaskTimer failed: {e}, falling back to simple estimation")
        return await estimate_timeout_simple_async(task, default)


def estimate_timeout(task: str, default: int = 120) -> int:
    """
    Synchronous wrapper for estimate_timeout_async.
    For backward compatibility when called from sync context.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, can't use run_until_complete
            # Fall back to simple estimation
            logger.debug("Already in async context, using simple estimation")
            return estimate_timeout_simple(task, default)
        else:
            # We can run the async version
            return loop.run_until_complete(estimate_timeout_async(task, default))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(estimate_timeout_async(task, default))


async def estimate_timeout_simple_async(task: str, default: int = 120) -> int:
    """Simple async timeout estimation as fallback."""
    return estimate_timeout_simple(task, default)


def estimate_timeout_simple(task: str, default: int = 120) -> int:
    """Simple synchronous timeout estimation."""
    # Fallback to simple heuristics
    if len(task) < 50:
        base_timeout = 30  # Very simple tasks
    elif len(task) < 200:
        base_timeout = 60  # Medium tasks  
    else:
        base_timeout = 120  # Complex tasks
        
        # Check for keywords indicating complexity
        complex_keywords = [
            'create', 'build', 'implement', 'design', 'develop',
            'full', 'complete', 'comprehensive', 'test', 'suite'
        ]
        
        keyword_count = sum(1 for kw in complex_keywords if kw in task.lower())
        base_timeout += keyword_count * 30
        
        # MCP operations need more time
        if 'mcp' in task.lower() or 'perplexity' in task.lower():
            base_timeout += 60
        
        # Try simple Redis lookup as last resort
        try:
            r = redis.Redis(decode_responses=True)
            task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
            timing_key = f"task:timing:{task_hash}"
            
            if r.exists(timing_key):
                avg_time = float(r.get(timing_key))
                # Add 20% buffer
                estimated = int(avg_time * 1.2)
                logger.info(f"Simple Redis history: {avg_time:.1f}s avg, using {estimated}s")
                return max(estimated, 60)  # At least 60s
                
        except Exception as e:
            logger.debug(f"Redis timing lookup failed: {e}")
        
        return max(base_timeout, default)


def check_token_limit(task: str, max_tokens: int = 190000) -> str:
    """
    Pre-check task length and truncate if needed to avoid token limit errors.
    
    Args:
        task: The task/prompt to check
        max_tokens: Maximum token limit (default 190k for Claude)
        
    Returns:
        Original or truncated task
    """
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = len(task) // 4
    
    if estimated_tokens > max_tokens:
        logger.warning(f"Task exceeds token limit ({estimated_tokens} > {max_tokens}), truncating...")
        # Leave room for response
        safe_chars = (max_tokens - 10000) * 4  # Reserve 10k tokens for response
        truncated = task[:safe_chars] + "\n\n[TRUNCATED due to token limit]"
        return truncated
    
    return task


def detect_ambiguous_prompt(task: str) -> Optional[str]:
    """
    Detect potentially problematic prompts and return warning.
    Complements amend_prompt by providing quick heuristic checks.
    
    Args:
        task: The task/prompt to check
        
    Returns:
        Warning message if issues detected, None otherwise
    """
    issues = []
    
    # Check for command-style prompts that often timeout
    command_verbs = ['Write', 'Create', 'Build', 'Make', 'Generate', 'Implement']
    first_word = task.strip().split()[0] if task.strip() else ""
    if first_word in command_verbs:
        issues.append(f"Starts with '{first_word}' - consider question format: 'What is...'")
    
    # Check for overly brief prompts
    if len(task.split()) < 5:
        issues.append("Very brief prompt - may be too vague")
    
    # Check for complex multi-step without structure
    if len(task) > 200 and "step by step" not in task.lower() and "\n" not in task:
        issues.append("Long prompt without structure - consider adding 'step by step' or line breaks")
    
    # Check for interactive patterns that won't work
    interactive_patterns = ['guide me', 'help me', 'walk me through', 'ask me']
    if any(pattern in task.lower() for pattern in interactive_patterns):
        issues.append("Interactive language detected - Claude CLI can't interact")
    
    return "; ".join(issues) if issues else None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),  # Includes jitter by default
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=lambda retry_state: logger.warning(f"Rate limit hit, retrying in {retry_state.next_action.sleep} seconds...")
)
async def _execute_claude_command(
    command: str,
    env: Dict[str, str],
    session_id: str,
    config: CCExecutorConfig,
    hooks: Any,
    progress_callback: Optional[Callable[[str], Any]] = None,
    thinking_handler: Optional[ThinkingIndicatorHandler] = None
) -> Tuple[List[str], List[str], Any]:
    """
    Execute Claude command with proper subprocess handling.
    
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
    
    # Create subprocess with best practices from ProcessManager
    proc = await asyncio.create_subprocess_shell(
        command,
        stdin=asyncio.subprocess.DEVNULL,  # CRITICAL: Prevent stdin deadlock
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,  # Use our enhanced environment (NO API KEY - browser auth)
        # Match websocket_handler.py process group handling
        preexec_fn=os.setsid if os.name != 'nt' else None,
        limit=8 * 1024 * 1024  # 8MB buffer limit for large outputs
    )
    logger.info(f"[{session_id}] Subprocess created with PID: {proc.pid}")
    
    # Collect output
    output_lines = []
    error_lines = []
    
    try:
        if config.stream_output:
            # Stream output in real-time with timeout
            # Create tasks for reading stdout and stderr
            async def read_stream(stream, target_list, prefix=""):
                """Read from stream in CHUNKS, not lines - fixes buffer deadlock!"""
                buffer = b""
                try:
                    while True:
                        # CRITICAL FIX: Read chunks, not lines!
                        chunk = await stream.read(8192)  # 8KB chunks
                        if not chunk:
                            # Process any remaining buffer
                            if buffer:
                                decoded = buffer.decode('utf-8', errors='replace')
                                target_list.append(decoded)
                                if config.stream_output:
                                    print(f"[{session_id}] {prefix}{decoded}", end='', flush=True)
                            break
                        
                        # Add chunk to buffer
                        buffer += chunk
                        
                        # Process complete lines from buffer
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            decoded = line.decode('utf-8', errors='replace') + '\n'
                            target_list.append(decoded)
                            
                            # Stream to console if requested
                            if config.stream_output:
                                print(f"[{session_id}] {prefix}{decoded}", end='', flush=True)
                            
                            # Report progress
                            if progress_callback and any(indicator in decoded.lower() for indicator in 
                                                       ['complete', 'done', 'finish', 'success']):
                                await progress_callback(f"Progress: {decoded.strip()[:100]}")
                            
                            # Detect first real content and stop thinking indicator
                            if thinking_handler and prefix != "[STDERR] ":
                                # Try to parse as JSON to see if it's assistant content
                                try:
                                    json_data = json.loads(decoded.strip())
                                    if json_data.get('type') == 'assistant' and json_data.get('message'):
                                        # Real content is starting
                                        thinking_handler.record_first_content()
                                        if progress_callback:
                                            try:
                                                result = progress_callback("✅ Claude is now generating the response...")
                                                if asyncio.iscoroutine(result):
                                                    await result
                                            except Exception as e:
                                                logger.debug(f"Progress callback error: {e}")
                                except:
                                    # Not JSON, but if it's substantial text, consider it content
                                    if len(decoded.strip()) > 20 and not decoded.startswith('['):
                                        thinking_handler.record_first_content()
                        
                        # If buffer is getting too large (no newlines), flush it
                        if len(buffer) > 65536:  # 64KB
                            decoded = buffer.decode('utf-8', errors='replace')
                            target_list.append(decoded)
                            if config.stream_output:
                                print(f"[{session_id}] {prefix}{decoded}", end='', flush=True)
                            buffer = b""
                                
                except Exception as e:
                    logger.error(f"Error reading {prefix}: {e}")
            
            # Create concurrent tasks for stdout/stderr
            logger.debug(f"[{session_id}] Starting stream readers")
            stdout_task = asyncio.create_task(
                read_stream(proc.stdout, output_lines)
            )
            stderr_task = asyncio.create_task(
                read_stream(proc.stderr, error_lines, "[STDERR] ")
            )
            
            # Wait for process completion with timeout
            # CRITICAL FIX: We must wait for BOTH process completion AND stream reading
            # to prevent output buffer deadlock. The process can hang if output fills
            # the OS pipe buffer and we're not actively reading it.
            try:
                logger.debug(f"[{session_id}] Waiting for process with timeout={config.timeout}s")
                # Use gather to ensure streams are being read while waiting for process
                await asyncio.wait_for(
                    asyncio.gather(
                        proc.wait(),
                        stdout_task,
                        stderr_task,
                        return_exceptions=True  # Don't fail if one task fails
                    ),
                    timeout=config.timeout
                )
                logger.info(f"[{session_id}] Process completed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"[{session_id}] Process timed out after {config.timeout}s")
                # Don't cancel tasks immediately - let them finish reading available data
                # Give tasks a moment to read any remaining output
                try:
                    await asyncio.wait_for(
                        asyncio.gather(stdout_task, stderr_task, return_exceptions=True),
                        timeout=1.0  # Brief grace period
                    )
                except asyncio.TimeoutError:
                    # Now cancel if they're still running
                    stdout_task.cancel()
                    stderr_task.cancel()
                
                # Don't raise - we have output to return!
                logger.info(f"[{session_id}] Returning partial output after timeout")
                
        else:
            # Non-streaming mode - still need to read chunks to avoid deadlock!
            if progress_callback:
                await progress_callback("Waiting for Claude to complete (non-streaming mode)...")
            
            # Create simple chunk readers for non-streaming mode
            async def collect_stream(stream):
                chunks = []
                try:
                    while True:
                        chunk = await stream.read(8192)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except Exception as e:
                    logger.error(f"Error collecting stream: {e}")
                return b''.join(chunks)
            
            # Read both streams concurrently
            try:
                stdout_data, stderr_data, _ = await asyncio.wait_for(
                    asyncio.gather(
                        collect_stream(proc.stdout),
                        collect_stream(proc.stderr),
                        proc.wait()
                    ),
                    timeout=config.timeout
                )
                
                if stdout_data:
                    output_lines = stdout_data.decode('utf-8', errors='replace').splitlines(keepends=True)
                    if not output_lines and stdout_data:  # No newlines
                        output_lines = [stdout_data.decode('utf-8', errors='replace')]
                if stderr_data:
                    error_lines = stderr_data.decode('utf-8', errors='replace').splitlines(keepends=True)
                    if not error_lines and stderr_data:  # No newlines
                        error_lines = [stderr_data.decode('utf-8', errors='replace')]
                
                if progress_callback:
                    await progress_callback("Claude execution completed")
            except asyncio.TimeoutError:
                # Handle timeout in non-streaming mode
                logger.warning(f"[{session_id}] Non-streaming mode timed out after {config.timeout}s")
                # Kill the process
                if proc.returncode is None:
                    try:
                        proc.terminate()
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except:
                        proc.kill()
                # Re-raise to be handled below
                raise
    
    except asyncio.TimeoutError:
        # This should not happen anymore as we handle timeout in the streaming section
        # But if it does (non-streaming mode), handle gracefully
        logger.error(f"[{session_id}] TIMEOUT after {config.timeout}s!")
        
        # Kill process if still running
        if proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        
        # Return what we have instead of raising
        logger.info(f"[{session_id}] Returning partial results after timeout")
        return output_lines, error_lines, proc
    
    # Check return code
    if proc.returncode is not None and proc.returncode != 0:
        error_msg = ''.join(error_lines) or "Unknown error"
        logger.error(f"[{session_id}] Process failed with code {proc.returncode}")
        logger.error(f"[{session_id}] Error: {error_msg[:500]}...")
        logger.error(f"[{session_id}] === CC_EXECUTE LIFECYCLE FAILED (EXIT {proc.returncode}) ===")
        
        # Check if it's a rate limit error
        if any(pattern in error_msg.lower() for pattern in ['rate limit', '429', 'too many requests']):
            raise RateLimitError(f"Claude rate limit hit: {error_msg}")
        else:
            raise RuntimeError(f"Claude failed with code {proc.returncode}: {error_msg}")
    elif proc.returncode is None:
        # Process was killed due to timeout
        logger.warning(f"[{session_id}] Process killed due to timeout after {config.timeout}s")
        logger.info(f"[{session_id}] Returning partial output (if any)")
    
    return output_lines, error_lines, proc


async def export_execution_history(
    redis_client: Optional[Any] = None,
    format: str = "json",
    limit: int = 100
) -> str:
    """
    Export execution history from Redis for analysis.
    
    Args:
        redis_client: Optional Redis client (will create if None)
        format: Output format ('json' or 'csv')
        limit: Maximum number of records to export
        
    Returns:
        Formatted execution history
    """
    if redis_client is None:
        try:
            import redis
            redis_client = redis.Redis(decode_responses=True)
        except:
            return json.dumps({"error": "Redis not available"}, indent=2)
    
    history = []
    
    try:
        # Scan for all task timing keys
        for key in redis_client.scan_iter("task:timing:*", count=limit):
            task_hash = key.split(":")[-1]
            
            # Get timing data
            avg_time = redis_client.get(key)
            if avg_time:
                # Try to get additional metadata
                last_run_key = f"task:last_run:{task_hash}"
                success_key = f"task:success_rate:{task_hash}"
                
                record = {
                    "task_hash": task_hash,
                    "avg_time_seconds": float(avg_time),
                    "last_run": redis_client.get(last_run_key) or "unknown",
                    "success_rate": float(redis_client.get(success_key) or 1.0)
                }
                
                history.append(record)
        
        # Sort by average time (longest first)
        history.sort(key=lambda x: x['avg_time_seconds'], reverse=True)
        
        if format == "csv":
            # Simple CSV format
            lines = ["task_hash,avg_time_seconds,last_run,success_rate"]
            for record in history:
                lines.append(f"{record['task_hash']},{record['avg_time_seconds']},{record['last_run']},{record['success_rate']}")
            return "\n".join(lines)
        else:
            # JSON format
            return json.dumps({
                "execution_history": history,
                "total_records": len(history),
                "export_time": datetime.now().isoformat()
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to export history: {e}")
        return json.dumps({"error": str(e)}, indent=2)


async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    agent_predict_timeout: bool = False,
    generate_report: bool = False,
    amend_prompt: bool = False,
    validation_prompt: Optional[str] = None,  # If provided, validates response with fresh instance
    progress_callback: Optional[Callable[[str], Any]] = None,  # Progress reporting callback
    json_schema: Optional[Dict[str, Any]] = None,  # Custom JSON schema to use instead of default
    return_dict: bool = True  # If False, return just the 'result' field as string
) -> Union[str, Dict[str, Any]]:
    """
    Execute a complex Claude task. Always uses streaming JSON format internally.
    
    Args:
        task: Task description (can be very complex)
        config: Executor configuration
        agent_predict_timeout: If True, use Claude to predict timeout based on task complexity
        generate_report: If True, generate an assessment report following CORE_ASSESSMENT_REPORT_TEMPLATE.md
        amend_prompt: If True, use Claude to amend the prompt for better reliability
        validation_prompt: If provided, spawns fresh Claude instance to validate response.
                          Use {response} placeholder for the response.
        progress_callback: Optional callback for progress updates
        json_schema: Custom JSON schema dict to use instead of the default schema
        return_dict: If True, return full dict. If False, return just the 'result' field as string
        
    Returns:
        Dict with Claude's response if return_dict=True, or just the 'result' string if return_dict=False
        If validation_prompt provided, always returns dict with 'result', 'validation', and 'is_valid'
        
    Example:
        # Get string output
        result = await cc_execute(
            "Create a complete REST API with SQLAlchemy models"
        )
        
        # Get structured JSON output with validation
        result = await cc_execute(
            "Create a function to calculate fibonacci",
            json_mode=True,
            validation_prompt="Validate this code: {response}. Return {{'is_valid': bool, 'issues': []}}"
        )
        print(result['result'])     # The actual code
        print(result['is_valid'])   # Whether validation passed
        print(result['validation']) # Validation details
    """
    if config is None:
        config = CCExecutorConfig()
    
    # No API key needed - using Claude Max Plan with CLI
    # Authentication is handled by claude login
    
    # Amend prompt if requested
    original_task = task
    if amend_prompt:
        logger.info(f"Amending prompt for better reliability...")
        
        # Import amendment module
        from cc_executor.utils.prompt_amender import apply_basic_rules, amend_prompt as amend_with_claude
        
        # For speed, use basic rules for short prompts
        if len(task) < 100:
            task = apply_basic_rules(task)
            if task != original_task:
                logger.info(f"Applied basic amendment: {original_task[:50]}... → {task[:50]}...")
        else:
            # For complex prompts, use Claude (recursive cc_execute call)
            try:
                # Avoid infinite recursion - don't amend amendment requests
                if "amend it for Claude CLI reliability" not in task:
                    amended_task, explanation = await amend_with_claude(original_task, cc_execute)
                    if amended_task != original_task:
                        logger.info(f"Claude amended prompt: {explanation}")
                        task = amended_task
            except Exception as e:
                logger.warning(f"Claude amendment failed: {e}, using basic rules")
                task = apply_basic_rules(task)
    
    # Smart timeout estimation
    if agent_predict_timeout:
        # Use the Redis task timing system via cc_execute
        logger.info(f"Using Redis timing analysis for task: {task[:50]}...")
        
        # Have Claude run the Redis timing script to get intelligent timeout
        timing_prompt = f"""Run the Redis task timing analysis for this task:

{task}

Use the RedisTaskTimer from /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/redis_task_timing.py to:
1. Classify the task (category, complexity, type)
2. Check Redis for historical execution times
3. Find similar tasks if no exact match
4. Return the recommended timeout in seconds

Execute the analysis and return ONLY the timeout number."""
        
        try:
            # Use cc_execute to run the Redis timing analysis
            timeout_result = await cc_execute(
                timing_prompt,
                config=CCExecutorConfig(timeout=60),  # Quick timeout for analysis
                stream=False,
                agent_predict_timeout=False,  # Don't recurse!
                json_mode=True  # Get structured response
            )
            
            if isinstance(timeout_result, dict):
                try:
                    # Extract the timeout from the result
                    predicted_timeout = int(timeout_result['result'].strip())
                    config.timeout = max(60, min(3600, predicted_timeout))
                    logger.info(f"Redis timing predicted: {config.timeout}s (summary: {timeout_result.get('summary', 'N/A')})")
                except (ValueError, KeyError, AttributeError) as e:
                    # Couldn't parse - use local estimation
                    config.timeout = max(await estimate_timeout_async(task), 300)
                    logger.warning(f"Could not parse Redis timing result: {e}, using local estimate: {config.timeout}s")
            else:
                # Fallback to local estimation
                config.timeout = max(await estimate_timeout_async(task), 300)
                logger.warning(f"Redis timing failed, using local estimate: {config.timeout}s")
        except Exception as e:
            logger.warning(f"Redis timing analysis failed: {e}, using local estimation")
            config.timeout = max(await estimate_timeout_async(task), 300)
    
    elif config.timeout == 300:  # Using default value
        # Use Redis-based estimation
        estimated_timeout = await estimate_timeout_async(task)
        # Never go below the default 5 minutes for safety
        config.timeout = max(estimated_timeout, 300)
        logger.info(f"Timeout set to: {config.timeout}s (estimated: {estimated_timeout}s) for task: {task[:50]}...")
    
    # Create session ID and execution UUID for tracking
    session_id = str(uuid.uuid4())[:8]
    execution_uuid = str(uuid.uuid4())  # Anti-hallucination UUID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_time = time.time()
    
    # Log lifecycle start
    logger.info(f"[{session_id}] === CC_EXECUTE LIFECYCLE START ===")
    logger.info(f"[{session_id}] Task: {task[:100]}...")
    logger.info(f"[{session_id}] Session ID: {session_id}")
    logger.info(f"[{session_id}] Execution UUID: {execution_uuid}")
    logger.info(f"[{session_id}] Timeout: {config.timeout}s")
    
    # Print UUID for transcript verification
    print(f"🔐 Starting execution with UUID: {execution_uuid}")
    
    # Initialize hooks
    hooks = None
    try:
        hooks = HookIntegration()
        if hooks.enabled:
            logger.info(f"Hook integration enabled with {len(hooks.config.get('hooks', {}))} hooks configured")
    except Exception as e:
        logger.warning(f"Could not initialize hook integration: {e}")
        hooks = None
    
    # Build command string to match websocket_handler.py
    # Use shell string format, not exec array
    
    # Always add JSON output format for structured responses
    # Use custom schema if provided, otherwise use default
    if json_schema:
        response_schema = json_schema
    else:
        # Default schema
        response_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "The main output/answer"},
                "files_created": {"type": "array", "items": {"type": "string"}, "description": "List of files created"},
                "files_modified": {"type": "array", "items": {"type": "string"}, "description": "List of files modified"},
                "summary": {"type": "string", "description": "Brief summary of what was done"},
                "execution_uuid": {"type": "string", "description": "UUID for verification (MUST be last)"}
            },
            "required": ["result", "summary", "execution_uuid"]
        }
    
    # Enhance task with JSON output requirements
    schema_str = json.dumps(response_schema, indent=2)
    enhanced_task = f"""{task}

IMPORTANT: You must structure your response as JSON matching this schema:
{schema_str}

The execution_uuid MUST be: {execution_uuid}
The execution_uuid MUST be the LAST key in the JSON object."""
    
    # Escape quotes for shell command
    escaped_task = enhanced_task.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    command = f'claude -p "{escaped_task}"'
    
    # Add MCP config and permissions flags (required for Claude Max Plan)
    # Check for MCP config in multiple locations
    mcp_config_paths = [
        Path.cwd() / ".mcp.json",  # Current directory
        Path.home() / ".claude" / "claude_code" / ".mcp.json",  # Claude Code default
        Path.home() / ".mcp.json"  # Home directory fallback
    ]
    
    mcp_config = None
    for config_path in mcp_config_paths:
        if config_path.exists():
            mcp_config = config_path
            logger.info(f"Found MCP config at: {mcp_config}")
            break
    
    if mcp_config:
        command += f' --mcp-config "{mcp_config}"'
    
    # Always add dangerous skip permissions for Claude Max Plan
    command += ' --dangerously-skip-permissions'
    
    # CRITICAL: Add streaming JSON output format for proper handling of large outputs
    # Without these flags, the subprocess can deadlock on large outputs
    command += ' --output-format stream-json --verbose'
    
    # Add model if specified
    if os.environ.get("ANTHROPIC_MODEL"):
        command += f' --model {os.environ["ANTHROPIC_MODEL"]}'
    
    # Add environment variables for Claude Code
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "ENABLE_BACKGROUND_TASKS": "1"
    }
    
    # Remove ANTHROPIC_API_KEY - cc_executor uses browser auth, not API keys
    if 'ANTHROPIC_API_KEY' in env:
        logger.info("Removing ANTHROPIC_API_KEY (using browser auth)")
        del env['ANTHROPIC_API_KEY']
    
    # Apply token limit check
    task = check_token_limit(task)
    
    # Check for ambiguous prompts (warning only)
    ambiguity_warning = detect_ambiguous_prompt(task)
    if ambiguity_warning and not amend_prompt:
        logger.warning(f"[{session_id}] Ambiguous prompt detected: {ambiguity_warning}")
        if progress_callback:
            # Handle both sync and async callbacks
            try:
                result = progress_callback(f"⚠️  Warning: {ambiguity_warning}")
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.debug(f"Progress callback error: {e}")
    
    # Log the command for debugging
    logger.info(f"Executing command: {command}")
    
    # Report progress
    if progress_callback:
        await progress_callback("Starting Claude execution...")
    
    # Create thinking indicator handler for complex prompts
    # Use simple heuristic: prompts over 500 chars are likely complex
    thinking_handler = None
    if len(task) > 500:
        thinking_handler = ThinkingIndicatorHandler(
            thinking_threshold=5.0,  # Wait 5 seconds before showing indicator
            update_interval=30.0     # Update every 30 seconds
        )
        await thinking_handler.start_monitoring(progress_callback)
    
    # Execute command with automatic rate limit retry via tenacity
    try:
        output_lines, error_lines, proc = await _execute_claude_command(
            command=command,
            env=env,
            session_id=session_id,
            config=config,
            hooks=hooks,
            progress_callback=progress_callback,
            thinking_handler=thinking_handler
        )
    except RateLimitError as e:
        # Tenacity exhausted all retries
        logger.error(f"[{session_id}] Rate limit persists after all retries: {e}")
        raise
    except Exception as e:
        # Other errors bubble up
        logger.error(f"[{session_id}] Execution failed: {e}")
        raise
    
    # Clean up thinking handler
    if thinking_handler:
        await thinking_handler.cleanup()
    
    # Combine output
    full_output = ''.join(output_lines)
    
    # Parse streaming JSON format if we used --output-format stream-json
    # The output contains multiple JSON objects, one per line
    parsed_output = None
    if '--output-format stream-json' in command:
        try:
            # Parse each line as JSON and extract the final result
            json_lines = []
            for line in output_lines:
                line = line.strip()
                if line:
                    try:
                        json_obj = json.loads(line)
                        json_lines.append(json_obj)
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        pass
            
            # Find the result message in the JSON lines
            for obj in json_lines:
                if obj.get('type') == 'result' and obj.get('subtype') == 'success':
                    # Extract the actual result text
                    parsed_output = obj.get('result', '')
                    break
                elif obj.get('type') == 'assistant' and 'message' in obj:
                    # Fallback to assistant message content
                    message = obj.get('message', {})
                    content = message.get('content', [])
                    if content and isinstance(content, list):
                        text_parts = [c.get('text', '') for c in content if c.get('type') == 'text']
                        if text_parts:
                            parsed_output = ''.join(text_parts)
            
            if parsed_output is not None:
                logger.debug(f"[{session_id}] Parsed streaming JSON output: {parsed_output[:100]}...")
                full_output = parsed_output
            else:
                logger.warning(f"[{session_id}] Could not parse streaming JSON format, using raw output")
                
        except Exception as e:
            logger.warning(f"[{session_id}] Failed to parse streaming JSON: {e}, using raw output")
    
    # Log success and execution time
    execution_time = time.time() - start_time
    logger.info(f"[{session_id}] Process completed successfully in {execution_time:.2f}s")
    logger.info(f"[{session_id}] Output size: {len(full_output)} chars")
    
    # Run post-execution hooks if available
    if hooks and hooks.enabled:
        try:
            logger.info("[HOOKS] Running post-execution hooks")
            await hooks.post_execution_hook(
                command=command,
                exit_code=proc.returncode,
                duration=execution_time,
                output=full_output[:1000]  # First 1000 chars for hook
            )
        except Exception as e:
            logger.warning(f"[HOOKS] Post-execution hook failed: {e}")
            # Continue even if hooks fail
    
    # CRITICAL: Always save to tmp/responses with UUID4 at END
    response_file = config.response_dir / f"cc_execute_{session_id}_{timestamp}.json"
    response_data = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "output": full_output,
        "error": ''.join(error_lines) if error_lines else None,
        "return_code": proc.returncode,
        "execution_time": time.time() - start_time if 'start_time' in locals() else None,
        "execution_uuid": execution_uuid  # MUST BE LAST KEY for anti-hallucination
    }
    
    with open(response_file, 'w') as f:
        json.dump(response_data, f, indent=2)
    
    logger.info(f"[{session_id}] Response saved: {response_file}")
    print(f"\n[{session_id}] Response saved: {response_file}")
    
    # Always generate an execution receipt for anti-hallucination verification
    try:
        from cc_executor.reporting.execution_receipt import generate_execution_receipt
        receipt_file = generate_execution_receipt(
            session_id=session_id,
            task=task,
            execution_uuid=execution_uuid,
            response_file=response_file,
            output=full_output,
            execution_time=execution_time,
            exit_code=proc.returncode
        )
        logger.info(f"[{session_id}] Execution receipt: {receipt_file.name}")
    except Exception as e:
        logger.debug(f"Failed to generate receipt: {e}")
    
    # Save execution time to Redis using sophisticated RedisTaskTimer
    if proc.returncode == 0:
        try:
            # Add the src directory to path for the import
            import sys
            if str(Path(__file__).parent.parent.parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from cc_executor.prompts.redis_task_timing import RedisTaskTimer
            
            # Create timer instance
            timer = RedisTaskTimer()
            
            # Classify the task
            task_type = timer.classify_command(task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Update history with all the sophisticated metadata
            # Since we're already in an async function, we can await directly
            await timer.update_history(
                task_type=task_type,
                elapsed=execution_time,
                success=True,
                expected=config.timeout  # Use configured timeout as expected
            )
            
            logger.info(f"Saved execution time {execution_time:.1f}s to RedisTaskTimer "
                       f"(category: {task_type['category']}, "
                       f"complexity: {task_type['complexity']})")
        except Exception as e:
            logger.debug(f"Failed to save timing to RedisTaskTimer: {e}")
    
    # Also save transcript if configured
    if config.save_transcript:
        transcript_file = config.transcript_dir / f"claude_{session_id}_{timestamp}.md"
        transcript_file.write_text(
            f"# Claude Execution Transcript\n\n"
            f"**Session ID**: {session_id}\n"
            f"**Timestamp**: {datetime.now()}\n"
            f"**Task**: {task}\n\n"
            f"## Output\n\n{full_output}\n"
        )
    
    logger.info(f"[{session_id}] === CC_EXECUTE LIFECYCLE COMPLETE ===")
    
    # Generate assessment report if requested
    if generate_report:
        report_file, report_content = generate_assessment_report(
            session_id=session_id,
            task=task,
            execution_uuid=execution_uuid,
            proc_returncode=proc.returncode,
            execution_time=execution_time,
            full_output=full_output,
            output_lines=output_lines,
            error_lines=error_lines,
            response_file=response_file,
            response_data=response_data,
            config_timeout=config.timeout,
            amend_prompt=amend_prompt,
            estimate_timeout_func=estimate_timeout
        )
        
        save_assessment_report(report_file, report_content)
        logger.info(f"[{session_id}] Assessment report saved: {report_file}")
        print(f"\n📋 Assessment report generated: {report_file}")
    
    # Always parse JSON output since we always use JSON mode
        try:
            # Use clean_json_string for robust parsing
            # This handles markdown blocks, malformed JSON, etc.
            result_dict = clean_json_string(full_output, return_dict=True)
            
            if isinstance(result_dict, dict):
                # Verify execution UUID
                if result_dict.get('execution_uuid') != execution_uuid:
                    logger.warning(f"[{session_id}] UUID mismatch! Expected: {execution_uuid}, Got: {result_dict.get('execution_uuid')}")
                
                # Validation with fresh instance if requested
                if validation_prompt:
                    await _perform_validation(result_dict, validation_prompt, session_id, config)
                
                # Check if we should return just the result field (backward compatibility)
                if not return_dict and 'result' in result_dict:
                    return result_dict['result']
                
                return result_dict
            else:
                raise ValueError(f"Expected dict, got {type(result_dict)}")
                
        except Exception as e:
            logger.error(f"[{session_id}] Failed to parse JSON: {e}")
            logger.debug(f"Raw output:\n{full_output[:1000]}...")
            
            # Attempt recovery by extracting JSON from markdown
            import re
            json_match = re.search(r'```(?:json)?\s*\n({.*?})\s*\n```', full_output, re.DOTALL)
            if json_match:
                try:
                    fallback_json = json.loads(json_match.group(1))
                    logger.info(f"[{session_id}] Recovered JSON from markdown block")
                    
                    # Validation if requested
                    if validation_prompt:
                        await _perform_validation(fallback_json, validation_prompt, session_id, config)
                    
                    if not return_dict and 'result' in fallback_json:
                        return fallback_json['result']
                    
                    return fallback_json
                except:
                    pass
            
            # Final fallback - return basic structure
            logger.warning(f"[{session_id}] Returning fallback JSON structure")
            fallback_result = {
                "result": full_output,
                "error": f"Failed to parse JSON: {e}",
                "execution_uuid": execution_uuid
            }
            
            if not return_dict:
                return full_output  # Fallback to raw output
            
            return fallback_result
    
    # This point should not be reached with JSON mode always enabled
    # But if it does, return the raw output as fallback
    return full_output


async def _perform_validation(
    result_dict: Dict[str, Any],
    validation_prompt: str,
    session_id: str,
    config: CCExecutorConfig
) -> None:
    """
    Perform validation with fresh Claude instance.
    Updates result_dict in-place with validation results.
    """
    try:
        logger.info(f"[{session_id}] Running validation with fresh Claude instance...")
        
        # Replace placeholder with the response
        actual_validation_prompt = validation_prompt.replace(
            "{response}",
            json.dumps(result_dict, indent=2)
        )
        
        # Run validation with fresh instance (no amend_prompt to avoid loops)
        validation_result = await cc_execute(
            actual_validation_prompt,
            config=CCExecutorConfig(timeout=120),  # 2 min for validation
            stream=False,
            json_mode=True,
            amend_prompt=False  # Don't amend validation prompts
        )
        
        # Add validation results to the dict
        if isinstance(validation_result, dict):
            result_dict['validation'] = validation_result
            result_dict['is_valid'] = validation_result.get('is_valid', True)
            logger.info(f"[{session_id}] Validation complete: is_valid={result_dict['is_valid']}")
        else:
            result_dict['validation'] = {"error": "Invalid validation response"}
            result_dict['is_valid'] = True  # Default to true on validation errors
            
    except Exception as e:
        logger.error(f"[{session_id}] Validation failed: {e}")
        result_dict['validation'] = {"error": str(e)}
        result_dict['is_valid'] = True  # Default to true on validation errors


# Convenience functions for backward compatibility
async def cc_execute_task_list(
    tasks: List[str],
    config: Optional[CCExecutorConfig] = None
) -> List[Dict[str, Any]]:
    """
    Execute a list of tasks sequentially.
    
    Args:
        tasks: List of task descriptions
        config: Executor configuration
        
    Returns:
        List of results for each task
    """
    results = []
    
    for i, task in enumerate(tasks):
        logger.info(f"\n{'='*60}")
        logger.info(f"Executing Task {i+1}/{len(tasks)}")
        logger.info(f"{'='*60}\n")
        
        try:
            output = await cc_execute(task, config)
            results.append({
                "task_num": i + 1,
                "task": task,
                "output": output,
                "success": True,
                "error": None
            })
        except Exception as e:
            logger.error(f"Task {i+1} failed: {e}")
            results.append({
                "task_num": i + 1,
                "task": task,
                "output": None,
                "success": False,
                "error": str(e)
            })
            # Continue with next task
    
    return results


# Synchronous wrapper for simple use cases
def cc_execute_sync(task: str, **kwargs) -> str:
    """Synchronous wrapper for cc_execute."""
    import asyncio
    return asyncio.run(cc_execute(task, **kwargs))


# Export the history function for direct use
def export_history_sync(format: str = "json", limit: int = 100) -> str:
    """Export execution history synchronously."""
    import asyncio
    return asyncio.run(export_execution_history(format=format, limit=limit))


async def working_usage():
    """Known working examples that demonstrate cc_execute functionality."""
    print("\n=== CC_EXECUTE WORKING USAGE EXAMPLES ===\n")
    
    # 1. Simple math test - always works
    print("1. Testing simple math...")
    result = await cc_execute(
        "What is 17 + 25? Just the number.",
        return_dict=False  # Get just the result string
    )
    print(f"   Result: {result}")
    
    # 2. List test - clear output
    print("\n2. Testing list output...")
    result = await cc_execute(
        "Name 3 primary colors, comma separated.",
        return_dict=False  # Get just the result string
    )
    print(f"   Result: {result}")
    
    # 3. JSON mode with simple structure
    print("\n3. Testing JSON mode...")
    result_json = await cc_execute(
        "What is 10 * 10? Return JSON with 'answer' key only."
    )
    print(f"   JSON Result: {json.dumps(result_json, indent=2)}")
    
    print("\n=== ALL TESTS COMPLETED ===")


async def debug_function():
    """Debug function for testing new features or debugging issues."""
    print("\n=== DEBUG MODE ===\n")
    
    # Quick verification of stress test functionality
    print("Running quick stress test verification...")
    
    test_results = []
    
    # Test 1: Simple math
    try:
        result = await cc_execute(
            "What is 7 + 3? Just the number.",
            config=CCExecutorConfig(timeout=20),
            return_dict=False  # Get just the result string
        )
        test_results.append(("Math test", result == "10", result))
    except Exception as e:
        test_results.append(("Math test", False, str(e)))
    
    # Test 2: JSON mode
    try:
        result = await cc_execute(
            "What is 5 * 5? Return JSON with 'answer' key only.",
            config=CCExecutorConfig(timeout=20)
        )
        success = isinstance(result, dict) and "result" in result
        test_results.append(("JSON test", success, result.get("result", "No result")))
    except Exception as e:
        test_results.append(("JSON test", False, str(e)))
    
    # Test 3: List output
    try:
        result = await cc_execute(
            "Name 3 fruits, comma separated.",
            config=CCExecutorConfig(timeout=20),
            return_dict=False  # Get just the result string
        )
        success = "," in result  # Should have commas
        test_results.append(("List test", success, result[:50]))
    except Exception as e:
        test_results.append(("List test", False, str(e)))
    
    # Summary
    print("\n📊 Debug Test Summary:")
    passed = sum(1 for _, success, _ in test_results if success)
    total = len(test_results)
    
    for name, success, output in test_results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}: {output}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    return passed == total


async def stress_test(test_file=None):
    """Run comprehensive stress tests from JSON files."""
    logger.info("=== STRESS TEST MODE ===\n")
    
    # Look for stress test files in the tests directory
    project_root = Path(__file__).parent.parent.parent.parent  # Navigate to project root
    stress_test_dir = project_root / "tests" / "stress" / "fixtures"
    if not stress_test_dir.exists():
        logger.warning(f"No stress test directory found at {stress_test_dir}")
        logger.info("Creating example stress test file...")
        
        # Create example stress test for cc_execute
        stress_test_dir.mkdir(parents=True, exist_ok=True)
        example_test = {
            "name": "cc_execute_stress_test",
            "description": "Stress test for cc_execute functionality",
            "tests": [
                {
                    "name": "rapid_math",
                    "prompt": "What is {n} + {n}? Just the number.",
                    "params": {"n": [5, 10, 15, 20, 25]},
                    "repeat": 3,
                    "return_dict": False  # Get just result string
                },
                {
                    "name": "json_mode_test",
                    "prompt": "Calculate {a} * {b}. Return JSON with 'result' key only.",
                    "params": {"a": [2, 3, 4], "b": [5, 6, 7]},
                    "repeat": 2
                },
                {
                    "name": "long_response",
                    "prompt": "Write a haiku about {topic}",
                    "params": {"topic": ["coding", "testing", "debugging"]},
                    "timeout": 60
                }
            ]
        }
        
        example_path = stress_test_dir / "cc_execute_example_stress.json"
        with open(example_path, 'w') as f:
            json.dump(example_test, f, indent=2)
        logger.info(f"Created example at: {example_path}")
        return True
    
    # Load and run stress tests
    if test_file:
        # Run specific test file
        test_path = stress_test_dir / test_file
        if not test_path.exists():
            logger.error(f"Test file not found: {test_path}")
            return False
        test_files = [test_path]
    else:
        # Run all test files
        test_files = list(stress_test_dir.glob("*.json"))
    
    logger.info(f"Found {len(test_files)} stress test files")
    
    total_passed = 0
    total_failed = 0
    
    for test_file in test_files:
        logger.info(f"\n📄 Loading: {test_file.name}")
        
        try:
            with open(test_file) as f:
                test_config = json.load(f)
            
            test_name = test_config.get('name', test_file.stem)
            logger.info(f"Running: {test_name}")
            
            # Run tests based on configuration
            tests = test_config.get('tests', [])
            for test in tests:
                # Handle parameterized tests
                params_config = test.get('params', {})
                param_combinations = []
                
                # Generate all parameter combinations
                if params_config:
                    # Simple parameter expansion for the example
                    first_param = list(params_config.keys())[0]
                    for value in params_config[first_param]:
                        param_combinations.append({first_param: value})
                else:
                    param_combinations = [{}]
                
                repeat = test.get('repeat', 1)
                
                for params in param_combinations:
                    for i in range(repeat):
                        try:
                            # Format prompt with parameters
                            prompt = test['prompt'].format(**params)
                            
                            # Execute with test configuration
                            result = await cc_execute(
                                prompt,
                                config=CCExecutorConfig(
                                    timeout=test.get('timeout', 30)
                                ),
                                return_dict=test.get('return_dict', True)
                            )
                            
                            logger.success(f"  ✅ {test['name']} {params} [{i+1}/{repeat}]")
                            total_passed += 1
                            
                        except Exception as e:
                            logger.error(f"  ❌ {test['name']} {params} [{i+1}/{repeat}]: {e}")
                            total_failed += 1
                            
        except Exception as e:
            logger.error(f"Failed to load {test_file}: {e}")
            total_failed += 1
    
    # Summary
    logger.info(f"\n📊 Stress Test Summary:")
    logger.info(f"  Total: {total_passed + total_failed}")
    logger.info(f"  Passed: {total_passed}")
    logger.info(f"  Failed: {total_failed}")
    logger.info(f"  Success Rate: {(total_passed/(total_passed+total_failed)*100) if (total_passed+total_failed) > 0 else 0:.1f}%")
    
    # Save report
    report_dir = project_root / "tests" / "stress" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"cc_execute_stress_report_{timestamp}.json"
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_passed + total_failed,
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": (total_passed/(total_passed+total_failed)*100) if (total_passed+total_failed) > 0 else 0,
        "test_files": [str(f.name) for f in test_files]
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    logger.info(f"\n📄 Report saved to: {report_file}")
    
    return total_failed == 0


if __name__ == "__main__":
    import asyncio
    import sys
    
    # Parse command line arguments
    mode = "working"
    stress_file = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "debug":
            mode = "debug"
        elif arg == "stress":
            mode = "stress"
        elif arg.endswith(".json"):
            mode = "stress"
            stress_file = arg
        else:
            mode = "working"
    
    # Run the selected mode
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    elif mode == "stress":
        print("Running stress test mode...")
        if stress_file:
            # Extract just the filename from the path
            filename = Path(stress_file).name
            asyncio.run(stress_test(filename))
        else:
            asyncio.run(stress_test())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())