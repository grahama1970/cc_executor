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


# Import report generator for assessment reports
try:
    from cc_executor.client.report_generator import generate_assessment_report, save_assessment_report
except ImportError:
    logger.warning("Could not import report_generator, report generation will be disabled")
    generate_assessment_report = None
    save_assessment_report = None

# Import JSON utilities for robust parsing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
try:
    from cc_executor.utils.json_utils import clean_json_string
except ImportError:
    # Fallback if not in proper cc_executor environment
    logger.warning("Could not import json_utils, using basic JSON parsing")
    clean_json_string = None

# Import HookIntegration for consistent pre/post execution hooks
try:
    from cc_executor.hooks.hook_integration import HookIntegration
except ImportError:
    logger.warning("Could not import HookIntegration, hooks will be disabled")
    HookIntegration = None


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


def estimate_timeout(task: str, default: int = 120) -> int:
    """
    Estimate timeout based on task complexity and Redis history.
    Mirrors websocket_handler.py logic.
    """
    # Basic heuristics - increase for MCP operations
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
    
    # Try Redis for historical data
    try:
        r = redis.Redis(decode_responses=True)
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        timing_key = f"task:timing:{task_hash}"
        
        if r.exists(timing_key):
            avg_time = float(r.get(timing_key))
            # Add 20% buffer
            estimated = int(avg_time * 1.2)
            logger.info(f"Redis timing history: {avg_time:.1f}s avg, using {estimated}s")
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
    
    # Check for vague references without clear antecedents
    vague_patterns = ['that', 'this', 'it', 'those', 'these']
    words = task.lower().split()
    if len(words) > 0 and words[0] in vague_patterns:
        issues.append("Starts with vague reference - specify what you're referring to")
    
    # Check for missing specifications
    if any(phrase in task.lower() for phrase in ['generate a report', 'create a function', 'make a script'] 
           ) and len(task.split()) < 10:
        issues.append("Missing specifications - provide more details about requirements")
    
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
    stream: bool,
    hooks: Any,
    progress_callback: Optional[Callable[[str], Any]] = None
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
        if stream and config.stream_output:
            # Stream output in real-time with timeout
            # Create tasks for reading stdout and stderr
            async def read_stream(stream, target_list, prefix=""):
                """Read from stream line by line."""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    target_list.append(decoded)
                    # Stream to console with session ID
                    print(f"[{session_id}] {decoded}", end='')
                    
                    # Report progress
                    if progress_callback and any(indicator in decoded.lower() for indicator in 
                                               ['complete', 'done', 'finish', 'success']):
                        await progress_callback(f"Progress: {decoded.strip()[:100]}")
                    
                    # Smart logging - truncate large data
                    log_line = decoded.strip()
                    if len(log_line) > 200:
                        # Check for base64/embeddings
                        if any(marker in log_line for marker in ['data:image/', 'base64,', 'embedding:', 'vector:']):
                            log_line = f"[BINARY/EMBEDDING DATA - {len(log_line)} chars]"
                        else:
                            log_line = log_line[:200] + f"... [{len(log_line)-200} chars truncated]"
                    
                    # Log progress indicators and truncated content
                    if any(indicator in decoded.lower() for indicator in 
                           ['complete', 'done', 'finish', 'success', 'fail', 'error']):
                        logger.info(f"[{session_id}] Progress: {log_line}")
                    elif log_line != decoded.strip():  # Was truncated
                        logger.debug(f"[{session_id}] Output: {log_line}")
            
            # Create concurrent tasks for stdout/stderr
            logger.debug(f"[{session_id}] Starting stream readers")
            stdout_task = asyncio.create_task(
                read_stream(proc.stdout, output_lines)
            )
            stderr_task = asyncio.create_task(
                read_stream(proc.stderr, error_lines, "[STDERR] ")
            )
            
            # Wait for process completion with timeout
            try:
                logger.debug(f"[{session_id}] Waiting for process with timeout={config.timeout}s")
                await asyncio.wait_for(
                    proc.wait(),
                    timeout=config.timeout
                )
                # Ensure we've read all output
                await stdout_task
                await stderr_task
                logger.info(f"[{session_id}] Process completed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"[{session_id}] Process timed out after {config.timeout}s")
                # Cancel read tasks
                stdout_task.cancel()
                stderr_task.cancel()
                raise
                
        else:
            # Non-streaming mode - wait for completion
            if progress_callback:
                await progress_callback("Waiting for Claude to complete (non-streaming mode)...")
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=config.timeout
            )
            
            if stdout:
                output_lines = stdout.decode().splitlines(keepends=True)
            if stderr:
                error_lines = stderr.decode().splitlines(keepends=True)
            
            if progress_callback:
                await progress_callback("Claude execution completed")
    
    except asyncio.TimeoutError:
        logger.error(f"[{session_id}] TIMEOUT after {config.timeout}s!")
        # Kill process group on timeout (matching websocket_handler.py)
        if proc.returncode is None:
            try:
                # Kill the entire process group
                pgid = os.getpgid(proc.pid)
                logger.warning(f"[{session_id}] Killing process group {pgid}")
                os.killpg(pgid, signal.SIGTERM)
                await asyncio.sleep(0.5)
                if proc.returncode is None:
                    os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        
        logger.error(f"[{session_id}] === CC_EXECUTE LIFECYCLE FAILED (TIMEOUT) ===")
        raise TimeoutError(
            f"Task exceeded {config.timeout}s timeout. "
            f"Partial output:\n{''.join(output_lines[-50:])}"
        )
    
    # Check return code
    if proc.returncode != 0:
        error_msg = ''.join(error_lines) or "Unknown error"
        logger.error(f"[{session_id}] Process failed with code {proc.returncode}")
        logger.error(f"[{session_id}] Error: {error_msg[:500]}...")
        logger.error(f"[{session_id}] === CC_EXECUTE LIFECYCLE FAILED (EXIT {proc.returncode}) ===")
        
        # Check if it's a rate limit error
        if any(pattern in error_msg.lower() for pattern in ['rate limit', '429', 'too many requests']):
            raise RateLimitError(f"Claude rate limit hit: {error_msg}")
        else:
            raise RuntimeError(f"Claude failed with code {proc.returncode}: {error_msg}")
    
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
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,
    return_json: Optional[bool] = None,  # Deprecated - use json_mode
    generate_report: bool = False,
    amend_prompt: bool = False,
    validation_prompt: Optional[str] = None,  # If provided, validates response with fresh instance
    progress_callback: Optional[Callable[[str], Any]] = None  # Progress reporting callback
) -> Union[str, Dict[str, Any]]:
    """
    Execute a complex Claude task with streaming output.
    
    Args:
        task: Task description (can be very complex)
        config: Executor configuration
        stream: Whether to stream output line by line
        agent_predict_timeout: If True, use Claude to predict timeout based on task complexity
        json_mode: If True, parse output as JSON and return dict (industry standard naming)
        return_json: Deprecated - use json_mode instead
        generate_report: If True, generate an assessment report following CORE_ASSESSMENT_REPORT_TEMPLATE.md
        amend_prompt: If True, use Claude to amend the prompt for better reliability
        validation_prompt: If provided, spawns fresh Claude instance to validate response.
                          Only works with json_mode=True. Use {response} placeholder for the response.
        progress_callback: Optional callback for progress updates
        
    Returns:
        Complete output from Claude (str if json_mode=False, dict if json_mode=True)
        If validation_prompt provided, returns dict with 'result', 'validation', and 'is_valid'
        
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
    
    # Handle backward compatibility for return_json parameter
    if return_json is not None:
        logger.warning("return_json is deprecated. Use json_mode instead.")
        json_mode = return_json
    
    # No API key needed - using Claude Max Plan with CLI
    # Authentication is handled by claude login
    
    # Amend prompt if requested
    original_task = task
    if amend_prompt:
        logger.info(f"Amending prompt for better reliability...")
        
        # Import amendment module
        try:
            from prompt_amender import apply_basic_rules, amend_prompt as amend_with_claude
            
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
        except ImportError:
            logger.warning("Could not import prompt_amender, using original prompt")
    
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
                    config.timeout = max(estimate_timeout(task), 300)
                    logger.warning(f"Could not parse Redis timing result: {e}, using local estimate: {config.timeout}s")
            else:
                # Fallback to local estimation
                config.timeout = max(estimate_timeout(task), 300)
                logger.warning(f"Redis timing failed, using local estimate: {config.timeout}s")
        except Exception as e:
            logger.warning(f"Redis timing analysis failed: {e}, using local estimation")
            config.timeout = max(estimate_timeout(task), 300)
    
    elif config.timeout == 300:  # Using default value
        # Use Redis-based estimation
        estimated_timeout = estimate_timeout(task)
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
    logger.info(f"[{session_id}] Stream: {stream}")
    
    # Print UUID for transcript verification
    print(f"🔐 Starting execution with UUID: {execution_uuid}")
    
    # Initialize hooks
    hooks = None
    if HookIntegration:
        try:
            hooks = HookIntegration()
            if hooks.enabled:
                logger.info(f"Hook integration enabled with {len(hooks.config.get('hooks', {}))} hooks configured")
        except Exception as e:
            logger.warning(f"Could not initialize hook integration: {e}")
            hooks = None
    
    # Build command string to match websocket_handler.py
    # Use shell string format, not exec array
    
    if json_mode:
        # Add JSON output format for structured responses
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
    else:
        # Regular text mode - no JSON requirements
        escaped_task = task.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
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
            await progress_callback(f"⚠️  Warning: {ambiguity_warning}")
    
    # Log the command for debugging
    logger.info(f"Executing command: {command}")
    
    # Report progress
    if progress_callback:
        await progress_callback("Starting Claude execution...")
    
    # Execute command with automatic rate limit retry via tenacity
    try:
        output_lines, error_lines, proc = await _execute_claude_command(
            command=command,
            env=env,
            session_id=session_id,
            config=config,
            stream=stream,
            hooks=hooks,
            progress_callback=progress_callback
        )
    except RateLimitError as e:
        # Tenacity exhausted all retries
        logger.error(f"[{session_id}] Rate limit persists after all retries: {e}")
        raise
    except Exception as e:
        # Other errors bubble up
        logger.error(f"[{session_id}] Execution failed: {e}")
        raise
    
    # Combine output
    full_output = ''.join(output_lines)
    
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
    
    # Save execution time to Redis for future estimation
    if proc.returncode == 0:
        try:
            r = redis.Redis(decode_responses=True)
            task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
            timing_key = f"task:timing:{task_hash}"
            
            # Store or update average execution time
            execution_time = time.time() - start_time
            if r.exists(timing_key):
                # Rolling average
                old_avg = float(r.get(timing_key))
                new_avg = (old_avg + execution_time) / 2
                r.set(timing_key, new_avg, ex=86400 * 7)  # 7 day expiry
            else:
                r.set(timing_key, execution_time, ex=86400 * 7)
            
            # Also update last run time
            r.set(f"task:last_run:{task_hash}", datetime.now().isoformat(), ex=86400 * 7)
            
            logger.info(f"Saved execution time {execution_time:.1f}s for future estimation")
        except Exception as e:
            logger.debug(f"Failed to save timing to Redis: {e}")
    
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
    if generate_report and generate_assessment_report:
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
            stream=stream,
            json_mode=json_mode,
            amend_prompt=amend_prompt,
            estimate_timeout_func=estimate_timeout
        )
        
        save_assessment_report(report_file, report_content)
        logger.info(f"[{session_id}] Assessment report saved: {report_file}")
        print(f"\n📋 Assessment report generated: {report_file}")
    elif generate_report and not generate_assessment_report:
        logger.warning("Report generation requested but report_generator module not available")
    
    # Parse JSON if requested
    if json_mode:
        try:
            # Use clean_json_string for robust parsing
            if clean_json_string:
                # This handles markdown blocks, malformed JSON, etc.
                result_dict = clean_json_string(full_output, return_dict=True)
                
                if isinstance(result_dict, dict):
                    # Verify execution UUID
                    if result_dict.get('execution_uuid') != execution_uuid:
                        logger.warning(f"[{session_id}] UUID mismatch! Expected: {execution_uuid}, Got: {result_dict.get('execution_uuid')}")
                    
                    # Validation with fresh instance if requested
                    if validation_prompt:
                        await _perform_validation(result_dict, validation_prompt, session_id, config)
                    
                    return result_dict
                else:
                    raise ValueError(f"Expected dict, got {type(result_dict)}")
            else:
                # Basic JSON parsing
                return json.loads(full_output)
                
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
                    
                    return fallback_json
                except:
                    pass
            
            # Final fallback - return basic structure
            logger.warning(f"[{session_id}] Returning fallback JSON structure")
            return {
                "result": full_output,
                "error": f"Failed to parse JSON: {e}",
                "execution_uuid": execution_uuid
            }
    
    # Return raw output for non-JSON mode
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
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True
) -> List[Dict[str, Any]]:
    """
    Execute a list of tasks sequentially.
    
    Args:
        tasks: List of task descriptions
        config: Executor configuration
        stream: Whether to stream output
        
    Returns:
        List of results for each task
    """
    results = []
    
    for i, task in enumerate(tasks):
        logger.info(f"\n{'='*60}")
        logger.info(f"Executing Task {i+1}/{len(tasks)}")
        logger.info(f"{'='*60}\n")
        
        try:
            output = await cc_execute(task, config, stream)
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


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Test basic execution
        result = await cc_execute(
            "Create a Python function to calculate fibonacci numbers",
            stream=True
        )
        print(f"\nResult: {result[:200]}...")
        
        # Test JSON mode
        result_json = await cc_execute(
            "Create a Python function to calculate prime numbers. Return as JSON with 'code' and 'explanation' keys.",
            json_mode=True
        )
        print(f"\nJSON Result: {json.dumps(result_json, indent=2)[:500]}...")
        
        # Test with validation
        result_validated = await cc_execute(
            "Create a Python function to sort a list",
            json_mode=True,
            validation_prompt="Check if this code is correct: {response}. Return {'is_valid': true/false, 'issues': []}"
        )
        print(f"\nValidated Result: {json.dumps(result_validated, indent=2)[:500]}...")
    
    asyncio.run(main())