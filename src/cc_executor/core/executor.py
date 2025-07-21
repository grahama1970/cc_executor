"""
Core executor for complex Claude tasks.

Handles:
- Long-running complex tasks (hours)
- Streaming output for visibility
- Proper error handling
- Task list execution
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
from typing import Optional, List, AsyncIterator, Dict, Any, Union
from dataclasses import dataclass
import subprocess
from loguru import logger

import redis  # Always available in cc_executor environment

# Import JSON utilities for robust parsing
from cc_executor.utils.json_utils import clean_json_string

# FIX 3: Helper function for parsing partial JSON
def try_parse_partial_json(text: str) -> Optional[dict]:
    """
    Attempt to parse incomplete JSON by fixing common issues.
    Used when tasks timeout but we want to salvage partial results.
    """
    if not text or not text.strip():
        return None
    
    # Method 1: Try clean_json_string first
    try:
        result = clean_json_string(text, return_dict=True)
        if isinstance(result, dict):
            return result
    except:
        pass
    
    # Method 2: Find JSON boundaries and fix unclosed structures
    if '"sections"' in text or '{' in text:
        # Track opening/closing brackets
        brackets = []
        json_start = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if json_start == -1:
                    json_start = i
                brackets.append('{')
            elif char == '[':
                brackets.append('[')
            elif char == '}':
                if brackets and brackets[-1] == '{':
                    brackets.pop()
            elif char == ']':
                if brackets and brackets[-1] == '[':
                    brackets.pop()
        
        # Extract from first { to end
        if json_start >= 0:
            partial = text[json_start:]
            
            # Add missing closing brackets
            for bracket in reversed(brackets):
                if bracket == '{':
                    partial += '}'
                elif bracket == '[':
                    partial += ']'
            
            # Try to parse the fixed JSON
            try:
                return json.loads(partial)
            except json.JSONDecodeError:
                # Try with clean_json_string as last resort
                try:
                    result = clean_json_string(partial, return_dict=True)
                    if isinstance(result, dict):
                        return result
                except:
                    pass
    
    return None

# FIX 4: Enhanced JSON extraction function
def extract_json_from_response(text: str) -> dict:
    """
    Extract JSON from Claude's response, handling various formats.
    More robust than the original implementation.
    """
    if not text:
        raise ValueError("Empty response text")
    
    # Method 1: Try clean_json_string first (handles most cases)
    try:
        result = clean_json_string(text, return_dict=True)
        if isinstance(result, dict):
            logger.debug("Successfully extracted JSON using clean_json_string")
            return result
    except Exception as e:
        logger.debug(f"clean_json_string failed: {e}")
    
    # Method 2: Look for ```json blocks specifically
    json_blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_blocks:
        for block in json_blocks:
            try:
                result = json.loads(block.strip())
                logger.debug("Successfully extracted JSON from markdown code block")
                return result
            except json.JSONDecodeError:
                continue
    
    # Method 3: Find JSON by looking for { } boundaries
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace >= 0 and last_brace > first_brace:
        json_candidate = text[first_brace:last_brace + 1]
        try:
            result = json.loads(json_candidate)
            logger.debug("Successfully extracted JSON by finding braces")
            return result
        except json.JSONDecodeError:
            # Try fixing common issues
            json_candidate = fix_common_json_issues(json_candidate)
            try:
                result = json.loads(json_candidate)
                logger.debug("Successfully extracted JSON after fixing common issues")
                return result
            except:
                pass
    
    # Method 4: Look for array responses
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')
    
    if first_bracket >= 0 and last_bracket > first_bracket:
        json_candidate = text[first_bracket:last_bracket + 1]
        try:
            result = json.loads(json_candidate)
            if isinstance(result, list):
                # Convert to dict format
                return {"result": result, "summary": "Array response"}
            return result
        except:
            pass
    
    # Method 5: Try to extract any valid JSON-like structure
    # Look for common patterns in Claude responses
    patterns = [
        r'"result"\s*:\s*"([^"]+)"',
        r'"summary"\s*:\s*"([^"]+)"',
        r'"output"\s*:\s*"([^"]+)"'
    ]
    
    extracted_data = {}
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            key = pattern.split('"')[1]
            extracted_data[key] = match.group(1)
    
    if extracted_data:
        logger.debug("Extracted partial JSON data from patterns")
        return extracted_data
    
    # Last resort: Return text as result
    logger.warning("Could not extract valid JSON, returning text as result")
    return {
        "result": text.strip(),
        "summary": "Raw text response (JSON parsing failed)",
        "parse_error": "Could not extract valid JSON structure"
    }

def fix_common_json_issues(json_str: str) -> str:
    """Fix common JSON formatting issues."""
    
    # Fix trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unescaped newlines in strings
    # This is tricky - we need to find strings and escape newlines in them
    def fix_newlines_in_match(match):
        content = match.group(0)
        # Replace actual newlines with \n
        return content.replace('\n', '\\n').replace('\r', '\\r')
    
    # Match string values (basic pattern)
    json_str = re.sub(r'"[^"]*":\s*"[^"]*"', fix_newlines_in_match, json_str)
    
    # Fix missing commas between objects in arrays
    json_str = re.sub(r'}\s*{', '},{', json_str)
    
    # Remove comments (sometimes Claude adds them)
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    return json_str


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
    
    # FIX 2: Add connection pooling configuration
    use_connection_pool: bool = False  # Experimental feature
    pool_size: int = 3
    
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
    
    # IMPORTANT: Add significant buffer for MCP operations
    # MCP server startup and tool loading adds overhead
    mcp_overhead = 30  # 30 seconds for MCP initialization
    base_timeout += mcp_overhead
    
    # Use Redis-based estimation
    try:
        r = redis.Redis(decode_responses=True)
        # Check for similar tasks
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        
        # Look for exact match
        exact_key = f"task:timing:{task_hash}"
        if r.exists(exact_key):
            avg_time = float(r.get(exact_key))
            # Add 50% buffer and ensure minimum of base_timeout
            redis_timeout = int(avg_time * 1.5)
            # Don't trust Redis if it's unreasonably low
            if redis_timeout < 30:
                logger.warning(f"Redis returned suspiciously low timeout: {redis_timeout}s, using base: {base_timeout}s")
                return max(base_timeout, 60)  # At least 60s for any MCP call
            return max(redis_timeout, base_timeout)
        
        # Look for similar tasks (simplified BM25)
        pattern = f"task:timing:*"
        similar_times = []
        for key in r.scan_iter(match=pattern, count=100):
            try:
                time_val = float(r.get(key))
                # Skip suspiciously low values
                if time_val >= 10:
                    similar_times.append(time_val)
            except:
                continue
        
        if similar_times:
            avg = sum(similar_times) / len(similar_times)
            redis_timeout = int(avg * 1.5)
            return max(redis_timeout, base_timeout)
            
    except Exception as e:
        logger.debug(f"Redis timeout estimation failed: {e}")
    
    # Default to 5 minutes if no Redis data available
    # This is reasonable for most Claude tasks with MCP
    return max(base_timeout, 300)  # At least 5 minutes for any Claude call with MCP


async def cc_execute(
    task: str,
    config: Optional[CCExecutorConfig] = None,
    stream: bool = True,
    agent_predict_timeout: bool = False,
    json_mode: bool = False,
    return_json: Optional[bool] = None,  # Deprecated - use json_mode
    generate_report: bool = False,
    amend_prompt: bool = False
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
        
    Returns:
        Complete output from Claude (str if json_mode=False, dict if json_mode=True)
        
    Example:
        # Get string output
        result = await cc_execute(
            "Create a complete REST API with SQLAlchemy models"
        )
        
        # Get structured JSON output
        result = await cc_execute(
            "Create a function to calculate fibonacci",
            json_mode=True
        )
        print(result['result'])  # The actual code
        print(result['summary'])  # What was done
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
    
    # Log the command for debugging
    logger.info(f"Executing command: {command}")
    
    # Create process using best practices from ProcessManager
    logger.info(f"[{session_id}] Creating subprocess...")
    
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
            
            # FIX 1: Output Buffer Deadlock - Wait for BOTH process completion AND stream reading
            try:
                logger.debug(f"[{session_id}] Waiting for process with timeout={config.timeout}s")
                # Wait for all three: process exit, stdout reading, stderr reading
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
                # Don't cancel tasks yet - we want partial output!
                # stdout_task.cancel() # REMOVED - keep partial output
                # stderr_task.cancel() # REMOVED - keep partial output
                # FIX 3: Don't raise immediately - collect partial results first
                pass  # Continue to handle timeout gracefully
                
        else:
            # Non-streaming mode - wait for completion
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=config.timeout
            )
            
            if stdout:
                output_lines = stdout.decode().splitlines(keepends=True)
            if stderr:
                error_lines = stderr.decode().splitlines(keepends=True)
    
    except asyncio.TimeoutError:
        logger.warning(f"[{session_id}] TIMEOUT after {config.timeout}s - collecting partial results")
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
        
        # FIX 3: Return partial results instead of raising
        logger.info(f"[{session_id}] Returning partial results after timeout")
        full_output = ''.join(output_lines)
        
        # Save partial results
        execution_time = time.time() - start_time
        response_file = config.response_dir / f"cc_execute_{session_id}_{timestamp}_PARTIAL.json"
        response_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "output": full_output,
            "error": f"Task timed out after {config.timeout}s",
            "partial": True,
            "timeout_after": config.timeout,
            "execution_time": execution_time,
            "execution_uuid": execution_uuid
        }
        
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        
        logger.info(f"[{session_id}] Partial response saved: {response_file}")
        
        # Return partial results based on mode
        if json_mode:
            # Try to parse partial JSON
            partial_json = try_parse_partial_json(full_output)
            if partial_json:
                partial_json['partial'] = True
                partial_json['timeout_after'] = config.timeout
                partial_json['execution_uuid'] = execution_uuid
                return partial_json
            else:
                return {
                    "result": full_output,
                    "partial": True,
                    "timeout_after": config.timeout,
                    "error": "Task timed out but partial results available",
                    "summary": f"Partial completion of: {task[:100]}...",
                    "execution_uuid": execution_uuid
                }
        else:
            # For text mode, return what we have with a timeout marker
            return full_output + f"\n\n[TIMEOUT: Task exceeded {config.timeout}s limit]\n[Partial results returned]"
    
    # Check return code
    if proc.returncode != 0:
        error_msg = ''.join(error_lines) or "Unknown error"
        logger.error(f"[{session_id}] Process failed with code {proc.returncode}")
        logger.error(f"[{session_id}] Error: {error_msg[:500]}...")
        logger.error(f"[{session_id}] === CC_EXECUTE LIFECYCLE FAILED (EXIT {proc.returncode}) ===")
        raise RuntimeError(f"Claude failed with code {proc.returncode}: {error_msg}")
    
    # Combine output
    full_output = ''.join(output_lines)
    
    # Log success and execution time
    execution_time = time.time() - start_time
    logger.info(f"[{session_id}] Process completed successfully in {execution_time:.2f}s")
    logger.info(f"[{session_id}] Output size: {len(full_output)} chars")
    
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
    if generate_report:
        report_uuid = str(uuid.uuid4())
        report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_file = config.response_dir / f"CC_EXECUTE_ASSESSMENT_REPORT_{timestamp}.md"
        
        # Build report following CORE_ASSESSMENT_REPORT_TEMPLATE.md
        report_content = f"""# CC_EXECUTE Assessment Report
Generated: {report_timestamp}
Session ID: {session_id}
Execution UUID: {execution_uuid}
Report UUID: {report_uuid}
Template: docs/templates/CORE_ASSESSMENT_REPORT_TEMPLATE.md v1.3

## Summary
- Task: {task}
- Exit Code: {proc.returncode}
- Execution Time: {execution_time:.2f}s
- Output Size: {len(full_output)} characters
- Timeout Used: {config.timeout}s
- Stream Mode: {stream}
- JSON Mode: {json_mode}
- Prompt Amended: {amend_prompt}

## Task Execution Assessment

### Automated Results
- **Exit Code**: {proc.returncode}
- **Execution Time**: {execution_time:.2f}s
- **Output Lines**: {len(output_lines)}
- **Error Output**: {"Yes" if error_lines else "No"}
- **Response Saved**: {response_file}

### Complete JSON Response File
```json
{json.dumps(response_data, indent=2)}
```

### Output Analysis
"""
        
        if json_mode and isinstance(full_output, str) and 'json' in full_output.lower():
            report_content += f"""#### JSON Structure Detected
- JSON parsing was requested and output appears to contain JSON
- Clean JSON extraction was successful
"""
        
        if error_lines:
            report_content += f"""#### Error Output
```
{''.join(error_lines[:20])}{"..." if len(error_lines) > 20 else ""}
```
"""
        
        report_content += f"""### Performance Metrics
- Redis Timeout Estimation: {estimate_timeout(task)}s
- Actual Execution Time: {execution_time:.2f}s
- Efficiency: {(execution_time / config.timeout * 100):.1f}% of allocated timeout

### Anti-Hallucination Verification
**Report UUID**: `{report_uuid}`
**Execution UUID**: `{execution_uuid}`

These UUIDs can be verified against:
- JSON response file: {response_file}
- Transcript logs for session: {session_id}

## Verification Commands
```bash
# Verify response file exists
ls -la {response_file}

# Check execution UUID in response
jq -r '.execution_uuid' {response_file}

# Search transcripts for this execution
rg "{execution_uuid}" ~/.claude/projects/*/$(date +%Y%m%d)*.jsonl
```

## Task Completion Status
{"✅ COMPLETED" if proc.returncode == 0 else "❌ FAILED"}

Generated by cc_execute() with report generation enabled.
"""
        
        # Write report
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        logger.info(f"[{session_id}] Assessment report saved: {report_file}")
        print(f"\n📋 Assessment report generated: {report_file}")
    
    # Parse JSON if requested
    if json_mode:
        try:
            # FIX 4: Enhanced JSON extraction with multiple methods
            result_dict = extract_json_from_response(full_output)
            
            # Verify execution UUID if present
            if isinstance(result_dict, dict) and result_dict.get('execution_uuid') != execution_uuid:
                logger.warning(f"[{session_id}] UUID mismatch! Expected: {execution_uuid}, Got: {result_dict.get('execution_uuid')}")
                # Add the correct UUID if missing
                if 'execution_uuid' not in result_dict:
                    result_dict['execution_uuid'] = execution_uuid
            
            return result_dict
            
        except Exception as e:
            logger.warning(f"[{session_id}] Failed to parse JSON output: {e}")
            logger.info(f"[{session_id}] Converting text response to JSON structure")
            
            # Convert text response to JSON structure
            # This is a fallback when Claude returns plain text instead of JSON
            try:
                # Basic structure for text responses
                fallback_json = {
                    "result": full_output.strip(),
                    "summary": f"Response to: {task[:100]}...",
                    "files_created": [],
                    "files_modified": [],
                    "execution_uuid": execution_uuid
                }
                
                # Try to detect files from the output
                import re
                
                # Look for file creation patterns
                created_pattern = r"(?:created?|wrote|saved?|generated?)\s+(?:file\s+)?['\"`]?([^\s'\"`,]+\.[a-zA-Z]+)"
                created_files = re.findall(created_pattern, full_output, re.IGNORECASE)
                if created_files:
                    fallback_json["files_created"] = list(set(created_files))
                
                # Look for file modification patterns  
                modified_pattern = r"(?:modified?|updated?|edited?|changed?)\s+(?:file\s+)?['\"`]?([^\s'\"`,]+\.[a-zA-Z]+)"
                modified_files = re.findall(modified_pattern, full_output, re.IGNORECASE)
                if modified_files:
                    fallback_json["files_modified"] = list(set(modified_files))
                
                # Extract a better summary if possible
                lines = full_output.strip().split('\n')
                if lines:
                    # Use first non-empty line as summary
                    for line in lines:
                        if line.strip() and not line.strip().startswith('```'):
                            fallback_json["summary"] = line.strip()[:200]
                            break
                
                logger.info(f"[{session_id}] Successfully converted text to JSON structure")
                return fallback_json
                
            except Exception as conv_error:
                logger.error(f"[{session_id}] Failed to convert to JSON structure: {conv_error}")
                # Last resort - return as string
                return full_output
    
    return full_output


async def cc_execute_list(
    tasks: List[str],
    config: Optional[CCExecutorConfig] = None,
    sequential: bool = True,
    json_mode: bool = False,
    return_json: Optional[bool] = None,  # Deprecated
    amend_prompt: bool = True  # Default to True for lists
) -> List[Union[str, Dict[str, Any]]]:
    """
    Execute a list of complex tasks.
    
    Args:
        tasks: List of task descriptions
        config: Executor configuration
        sequential: If True, run tasks one after another
        
    Returns:
        List of outputs for each task
        
    Example:
        results = await cc_execute_list([
            "1. Create FastAPI project structure",
            "2. Add SQLAlchemy models for users and posts",
            "3. Implement JWT authentication",
            "4. Add comprehensive test suite"
        ])
    """
    if sequential:
        # Run tasks one by one (safer for dependent tasks)
        results = []
        for i, task in enumerate(tasks):
            print(f"\n{'='*60}")
            print(f"Executing task {i+1}/{len(tasks)}: {task[:100]}...")
            print(f"{'='*60}\n")
            
            result = await cc_execute(task, config, json_mode=json_mode, amend_prompt=amend_prompt)
            results.append(result)
            
            # Brief pause between tasks
            if i < len(tasks) - 1:
                await asyncio.sleep(1)
        
        return results
    else:
        # Run tasks concurrently (faster but use with caution)
        tasks_coroutines = [
            cc_execute(task, config, json_mode=json_mode, amend_prompt=amend_prompt) for task in tasks
        ]
        return await asyncio.gather(*tasks_coroutines)


async def _stream_output(proc: asyncio.subprocess.Process) -> AsyncIterator[str]:
    """Stream output from subprocess line by line."""
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        
        decoded_line = line.decode('utf-8', errors='replace')
        yield decoded_line
    
    # Also check for any stderr
    if proc.stderr:
        stderr = await proc.stderr.read()
        if stderr:
            yield f"\n[STDERR]: {stderr.decode('utf-8', errors='replace')}\n"


# Convenience function for testing
async def test_simple():
    """Test basic execution."""
    # Test with amendment to convert command to question
    result = await cc_execute(
        "Write a Python function that calculates fibonacci numbers",
        amend_prompt=True  # This will convert to "What is a Python function..."
    )
    print(f"Result length: {len(result)} characters")
    return result


async def test_complex():
    """Test complex multi-step execution."""
    # Original imperative commands - will be amended automatically
    tasks = [
        "Create a Python class for managing a todo list with add, remove, and list methods",
        "Add persistence to the todo list using JSON file storage",
        "Add unit tests for the todo list class using pytest"
    ]
    
    results = await cc_execute_list(tasks)
    
    for i, (task, result) in enumerate(zip(tasks, results)):
        print(f"\n{'='*60}")
        print(f"Task {i+1}: {task}")
        print(f"Result preview: {result[:200]}...")
        print(f"{'='*60}")
    
    return results


async def test_game_engine_algorithm_competition():
    """Test complex orchestration with multiple Claude instances competing on algorithms."""
    print("\n🎮 GAME ENGINE ALGORITHM COMPETITION TEST")
    print("="*80)
    print("Spawning 4 Claude instances to create algorithms better than fast inverse square root...")
    print("Each with different parameters: --max-turns and temperature/creativity")
    print("="*80)
    
    # Complex orchestration task using Task tool and MCP
    competition_task = """Use your Task tool to spawn 4 concurrent Claude instances to create game engine algorithms more efficient than the fast inverse square root algorithm.

REQUIREMENTS:
1. First, run 'which gcc' and 'gcc --version' to check the C compiler environment

2. Each instance should create a DIFFERENT algorithm approach
3. Each instance uses different parameters:
   - Instance 1: Conservative (--max-turns 1, low creativity)
   - Instance 2: Balanced (--max-turns 2, medium creativity)  
   - Instance 3: Creative (--max-turns 3, high creativity)
   - Instance 4: Experimental (--max-turns 3, maximum creativity)

4. Each algorithm must include:
   - The algorithm implementation in C/C++
   - COMPILE and RUN the code to verify it works
   - Performance benchmarks vs original (with actual timing measurements)
   - Use case in game engines
   - Mathematical explanation
   - Include any compilation errors/warnings and fix them

5. After all 4 complete, use the perplexity-ask MCP tool to evaluate all algorithms and pick the best one with detailed rationale.

6. Return a JSON response with this exact schema:
{
  "algorithms": [
    {
      "instance": 1,
      "name": "Algorithm name",
      "code": "C/C++ implementation",
      "compilation_output": "gcc output or errors",
      "test_results": "Execution results showing it works",
      "performance_gain": "X% faster (with actual measurements)",
      "benchmark_data": "Timing comparisons with original",
      "use_case": "Description",
      "explanation": "Mathematical basis"
    },
    // ... for all 4 instances
  ],
  "perplexity_evaluation": {
    "winner": 1,  // instance number
    "rationale": "Detailed explanation of why this algorithm won",
    "comparison": "How algorithms compare to each other"
  },
  "summary": "Overall summary of the competition",
  "execution_uuid": "Will be provided"
}

Execute this complex orchestration task now."""
    
    try:
        start_time = time.time()
        
        # Execute with extended timeout for complex orchestration
        result = await cc_execute(
            competition_task,
            config=CCExecutorConfig(timeout=900),  # 15 minutes for complex orchestration
            stream=True,
            json_mode=True,
            generate_report=True  # Generate assessment report
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"✅ COMPETITION COMPLETE in {elapsed:.1f}s")
        print(f"{'='*80}")
        
        if isinstance(result, dict):
            # Display results
            algorithms = result.get('algorithms', [])
            print(f"\n📊 ALGORITHMS CREATED: {len(algorithms)}")
            for algo in algorithms:
                print(f"\n  Instance {algo.get('instance')}: {algo.get('name')}")
                print(f"  Performance: {algo.get('performance_gain')}")
                print(f"  Use case: {algo.get('use_case')[:100]}...")
            
            # Show winner
            eval_data = result.get('perplexity_evaluation', {})
            winner = eval_data.get('winner')
            print(f"\n🏆 WINNER: Instance {winner}")
            print(f"Rationale: {eval_data.get('rationale', 'N/A')[:200]}...")
            
            print(f"\nSummary: {result.get('summary', 'N/A')}")
            
            # Verify UUID
            if result.get('execution_uuid'):
                print(f"\n✅ UUID verified: {result['execution_uuid']}")
            else:
                print("\n⚠️  No execution UUID found!")
            
            # Report info
            print(f"\n📋 Assessment report generated in: tmp/responses/")
            print("Look for: CC_EXECUTE_ASSESSMENT_REPORT_*.md")
                
        else:
            print(f"\n⚠️  Unexpected result type: {type(result)}")
            print(f"Result: {str(result)[:500]}...")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Competition failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# For module testing only
if __name__ == "__main__" and False:  # Disabled in production
    # Test the executor
    print("Testing CC Executor...")
    print("="*60)
    
    async def run_all_tests():
        """Run all tests and report results."""
        results = []
        
        try:
            print("\n1. Running simple test...")
            await test_simple()
            results.append(("Simple Test", "PASSED"))
        except Exception as e:
            results.append(("Simple Test", f"FAILED: {e}"))
            import traceback
            traceback.print_exc()
        
        try:
            print("\n2. Running complex test...")
            await test_complex()
            results.append(("Complex Test", "PASSED"))
        except Exception as e:
            results.append(("Complex Test", f"FAILED: {e}"))
            import traceback
            traceback.print_exc()
        
        try:
            print("\n3. Running game engine algorithm competition test...")
            await test_game_engine_algorithm_competition()
            results.append(("Game Engine Competition", "PASSED"))
        except Exception as e:
            results.append(("Game Engine Competition", f"FAILED: {e}"))
            import traceback
            traceback.print_exc()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        for test_name, result in results:
            status = "✅" if "PASSED" in result else "❌"
            print(f"{status} {test_name}: {result}")
        
        # Check if all passed
        all_passed = all("PASSED" in r for _, r in results)
        return all_passed
    
    # Run all tests
    success = asyncio.run(run_all_tests())
    
    if not success:
        print("\n⚠️  Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")