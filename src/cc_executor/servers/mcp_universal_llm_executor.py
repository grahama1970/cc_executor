#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "tenacity",
#     "redis",
#     "tiktoken",
#     "chardet",
#     "mcp-logger-utils>=0.1.5",
#     "json-repair"
# ]
# ///
"""
MCP Server for Universal LLM Execution - Execute any LLM CLI with smart file handling.

=== MCP DEBUGGING NOTES (2025-07-19) ===

COMMON MCP USAGE PITFALLS:
1. File paths must be absolute paths, not relative
2. Concatenated files are saved to /tmp/ for safety
3. Large files are automatically chunked based on token limits
4. Output is captured to timestamped files in output_dir
5. Process groups ensure clean subprocess termination

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start
   python src/cc_executor/servers/mcp_universal_llm_executor.py test
   
   # Check imports work
   python -c "from cc_executor.servers.mcp_universal_llm_executor import UniversalLLMExecutor"
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/universal-llm-executor_startup.log
   - Debug log: ~/.claude/mcp_logs/universal-llm-executor_debug.log
   - Calls log: ~/.claude/mcp_logs/universal-llm-executor_calls.jsonl

3. COMMON ISSUES & FIXES:
   
   a) LLM CLI not found:
      - Error: "Command 'claude' not found"
      - Fix: Ensure LLM CLI is installed and in PATH
      - Check: which claude, which gemini
   
   b) Token limit exceeded:
      - Error: "Content exceeds token limit"
      - Fix: Use chunk_size parameter or smaller files
      - Default: 100k tokens per chunk
   
   c) Process timeout:
      - Error: "Process timed out after X seconds"
      - Fix: Increase timeout or use streaming
      - Redis learns optimal timeouts over time
   
   d) Permission denied:
      - Error: "Permission denied: /output/path"
      - Fix: Ensure output_dir is writable
      - Default: /tmp/llm_outputs/

4. ENVIRONMENT VARIABLES:
   - PYTHONPATH=/home/graham/workspace/experiments/cc_executor/src
   - LLM_OUTPUT_DIR=/tmp/llm_outputs (default)
   - REDIS_HOST=localhost (for timeout learning)
   - REDIS_PORT=6379 (for timeout learning)
   - MCP_DEBUG=true (enable debug logging)

5. CURRENT FEATURES:
   - ✅ Auto-detects installed LLM CLIs
   - ✅ Smart file concatenation with chunking
   - ✅ Token counting and estimation
   - ✅ Process group management
   - ✅ Redis-based timeout learning
   - ✅ Progress tracking via file monitoring
   - ✅ Gemini debug log filtering

=== END DEBUGGING NOTES ===

This MCP server provides universal LLM execution with intelligent file handling.
"""

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
import uuid

# Environment setup before imports

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False

try:
    from json_repair import repair_json
    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response
from tenacity import retry, stop_after_attempt, wait_exponential

# Import from our shared PyPI package
from mcp_logger_utils import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))

# Load environment
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("universal-llm-executor", dependencies=["redis", "tiktoken", "chardet"])
mcp_logger = MCPLogger("universal-llm-executor")

# Global configuration
DEFAULT_OUTPUT_DIR = Path(os.getenv("LLM_OUTPUT_DIR", "/tmp/llm_outputs"))
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Redis configuration for timeout learning
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "decode_responses": True
}

# Token limits for different models
TOKEN_LIMITS = {
    "claude": 100000,
    "gemini": 100000,
    "gpt": 100000,
    "llama": 32000,
    "mistral": 32000,
    "default": 50000
}

# LLM CLI patterns
LLM_CLI_PATTERNS = {
    "claude": {
        "command": "claude",
        "prompt_flag": "-p",
        "stream_flag": "--stream",
        "output_format": "--output-format",
        "use_stdin": True
    },
    "gemini": {
        "command": "gemini",
        "prompt_flag": "-p",
        "stream_flag": None,
        "output_format": None,
        "use_stdin": False
    },
    "llama": {
        "command": "llama",
        "prompt_flag": "-p",
        "stream_flag": "--stream",
        "output_format": None,
        "use_stdin": False
    },
    "gpt": {
        "command": "gpt",
        "prompt_flag": "-p",
        "stream_flag": "--stream",
        "output_format": None,
        "use_stdin": False
    }
}


class LLMExecutor:
    """Handles LLM execution with intelligent subprocess management."""
    
    def __init__(self):
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(**REDIS_CONFIG)
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis not available for timeout learning: {e}")
                self.redis_client = None
    
    def parse_json_output(self, content: str) -> Union[dict, list, str]:
        """Parse JSON from LLM output, handling common formatting issues."""
        if not content:
            return content
        
        # Try direct JSON parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_blocks:
            for block in json_blocks:
                try:
                    return json.loads(block.strip())
                except json.JSONDecodeError:
                    continue
        
        # Try to find JSON object or array in content
        json_match = re.search(r'(\{[^{}]*\}|\[[^\[\]]*\])', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try JSON repair if available
        if JSON_REPAIR_AVAILABLE:
            try:
                repaired = repair_json(content, return_objects=True)
                if isinstance(repaired, (dict, list)):
                    return repaired
            except Exception:
                pass
        
        # Return original content if all parsing fails
        return content
    
    def extract_streaming_json(self, output: str) -> List[Dict[str, Any]]:
        """Extract JSON objects from streaming output (newline-delimited JSON)."""
        results = []
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                results.append(obj)
            except json.JSONDecodeError:
                # Try to parse with JSON repair
                if JSON_REPAIR_AVAILABLE:
                    try:
                        obj = repair_json(line, return_objects=True)
                        if isinstance(obj, dict):
                            results.append(obj)
                    except:
                        pass
        return results
    
    def detect_available_llms(self) -> Dict[str, str]:
        """Detect which LLM CLIs are available in PATH."""
        available = {}
        for name, config in LLM_CLI_PATTERNS.items():
            cmd = config["command"]
            if shutil.which(cmd):
                available[name] = cmd
        return available
    
    def estimate_tokens(self, text: str, model: str = "default") -> int:
        """Estimate token count for text."""
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (GPT-4)
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except Exception:
                pass
        
        # Fallback: rough estimation (1 token ≈ 4 chars)
        return len(text) // 4
    
    def detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        if CHARDET_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    result = chardet.detect(f.read(10000))
                    return result['encoding'] or 'utf-8'
            except Exception:
                pass
        return 'utf-8'
    
    def clean_gemini_output(self, output: str) -> str:
        """Clean Gemini debug output to extract actual response."""
        lines = output.split('\n')
        cleaned_lines = []
        
        # Skip all [DEBUG] lines and related output
        skip_next = False
        for line in lines:
            if line.startswith('[DEBUG]') or 'Flushing log events' in line or 'Loaded cached credentials' in line:
                continue
            if skip_next:
                skip_next = False
                continue
            # Only keep non-debug lines
            if line.strip() and not line.startswith('['):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    async def concatenate_files(
        self,
        file_paths: List[str],
        output_path: Optional[str] = None,
        chunk_size: Optional[int] = None,
        model: str = "default"
    ) -> Dict[str, Any]:
        """Concatenate multiple files with smart chunking."""
        files = [Path(p) for p in file_paths]
        
        # Validate files exist
        missing = [f for f in files if not f.exists()]
        if missing:
            return {"error": f"Files not found: {[str(f) for f in missing]}"}
        
        # Determine output path
        if output_path:
            output = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = DEFAULT_OUTPUT_DIR / f"concatenated_{timestamp}.txt"
        
        # Get token limit
        if chunk_size is None:
            chunk_size = TOKEN_LIMITS.get(model, TOKEN_LIMITS["default"])
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for file_path in files:
            try:
                # Detect encoding
                encoding = self.detect_encoding(file_path)
                
                # Read file
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                # Add file header
                header = f"\n\n{'='*60}\n# File: {file_path}\n{'='*60}\n\n"
                header_tokens = self.estimate_tokens(header, model)
                content_tokens = self.estimate_tokens(content, model)
                
                # Check if adding this file would exceed chunk size
                if current_tokens + header_tokens + content_tokens > chunk_size:
                    # Save current chunk
                    if current_chunk:
                        chunks.append(''.join(current_chunk))
                    current_chunk = [header, content]
                    current_tokens = header_tokens + content_tokens
                else:
                    current_chunk.extend([header, content])
                    current_tokens += header_tokens + content_tokens
                    
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return {"error": f"Failed to read {file_path}: {str(e)}"}
        
        # Add final chunk
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        # Write output
        if len(chunks) == 1:
            # Single chunk - write directly
            output.write_text(chunks[0])
            return {
                "output_path": str(output),
                "total_files": len(files),
                "chunks": 1,
                "estimated_tokens": self.estimate_tokens(chunks[0], model)
            }
        else:
            # Multiple chunks - create separate files
            chunk_paths = []
            for i, chunk in enumerate(chunks):
                chunk_path = output.parent / f"{output.stem}_chunk{i+1}{output.suffix}"
                chunk_path.write_text(chunk)
                chunk_paths.append(str(chunk_path))
            
            return {
                "output_paths": chunk_paths,
                "total_files": len(files),
                "chunks": len(chunks),
                "chunk_size": chunk_size,
                "message": f"Content split into {len(chunks)} chunks due to token limit"
            }
    
    def get_learned_timeout(self, llm: str, prompt_size: int) -> int:
        """Get learned timeout from Redis based on past executions."""
        if not self.redis_client:
            return 300  # Default 5 minutes
        
        try:
            # Create key based on LLM and prompt size bucket
            size_bucket = (prompt_size // 10000) * 10000  # 10k token buckets
            key = f"llm_timeout:{llm}:{size_bucket}"
            
            # Get average from Redis
            avg_time = self.redis_client.get(key)
            if avg_time:
                # Add 50% buffer
                return int(float(avg_time) * 1.5)
        except Exception as e:
            logger.debug(f"Could not get learned timeout: {e}")
        
        # Default timeouts by model
        defaults = {
            "claude": 300,
            "gemini": 180,
            "gpt": 240,
            "llama": 120
        }
        return defaults.get(llm, 300)
    
    def update_learned_timeout(self, llm: str, prompt_size: int, actual_time: float):
        """Update learned timeout in Redis."""
        if not self.redis_client:
            return
        
        try:
            size_bucket = (prompt_size // 10000) * 10000
            key = f"llm_timeout:{llm}:{size_bucket}"
            
            # Use exponential moving average
            current = self.redis_client.get(key)
            if current:
                new_avg = 0.7 * float(current) + 0.3 * actual_time
            else:
                new_avg = actual_time
            
            self.redis_client.setex(key, 86400 * 7, str(new_avg))  # 7 day TTL
        except Exception as e:
            logger.debug(f"Could not update learned timeout: {e}")
    
    async def execute_llm(
        self,
        llm: str,
        prompt: str,
        timeout: Optional[int] = None,
        stream: bool = False,
        output_dir: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute LLM with intelligent subprocess management."""
        # Validate LLM
        if llm not in LLM_CLI_PATTERNS:
            available = self.detect_available_llms()
            return {"error": f"Unknown LLM: {llm}. Available: {list(available.keys())}"}
        
        config = LLM_CLI_PATTERNS[llm]
        
        # Check if LLM is available
        if not shutil.which(config["command"]):
            return {"error": f"LLM '{llm}' not found in PATH. Install with appropriate package manager."}
        
        # Prepare output directory
        output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"{llm}_output_{timestamp}.txt"
        
        # Build command
        cmd = [config["command"]]
        
        # Add JSON schema to prompt if provided
        final_prompt = prompt
        if json_schema:
            schema_instruction = f"\n\nRespond only in well-formatted JSON with the following schema: {json.dumps(json_schema)}"
            final_prompt = prompt + schema_instruction
        elif not json_schema and "?" in prompt:
            # Auto-detect question format and add default schema
            default_schema = {"question": "the question", "answer": "the answer"}
            schema_instruction = f"\n\nRespond only in well-formatted JSON with the following schema: {json.dumps(default_schema)}"
            final_prompt = prompt + schema_instruction
        
        # Add prompt handling
        if config["use_stdin"]:
            # Claude uses -p flag but expects prompt via stdin
            cmd.append(config["prompt_flag"])
            # Don't add the prompt to the command for stdin mode
        else:
            # Add prompt to command
            cmd.extend([config["prompt_flag"], final_prompt])
        
        # Add streaming if supported
        if stream and config["stream_flag"]:
            cmd.append(config["stream_flag"])
        
        # Add output format if supported
        if config["output_format"]:
            format_type = "stream-json" if stream else "text"
            cmd.extend([config["output_format"], format_type])
            # Claude requires --verbose with stream-json
            if llm == "claude" and format_type == "stream-json":
                cmd.append("--verbose")
        
        # Add Claude-specific flags
        if llm == "claude":
            # Add auth skip flag if not already in extra_args
            if not extra_args or "--dangerously-skip-permissions" not in extra_args:
                cmd.append("--dangerously-skip-permissions")
        
        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)
        
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Get timeout
        if timeout is None:
            prompt_tokens = self.estimate_tokens(prompt)
            timeout = self.get_learned_timeout(llm, prompt_tokens)
        
        # Log execution
        logger.info(f"Executing {llm} with timeout={timeout}s, output={output_file}")
        
        start_time = time.time()
        
        try:
            # Create process with process group
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if config["use_stdin"] else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
            
            # Send prompt via stdin if needed
            if config["use_stdin"]:
                stdin_data = final_prompt.encode()
            else:
                stdin_data = None
            
            # Monitor output file growth for progress
            async def monitor_progress():
                while True:
                    try:
                        if output_file.exists():
                            size = output_file.stat().st_size
                            if progress_callback:
                                progress_callback(f"Output size: {size:,} bytes")
                    except:
                        pass
                    await asyncio.sleep(1)
            
            # Start progress monitoring
            monitor_task = None
            if progress_callback:
                monitor_task = asyncio.create_task(monitor_progress())
            
            try:
                # Execute with timeout
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_data),
                    timeout=timeout
                )
                
                # Stop monitoring
                if monitor_task:
                    monitor_task.cancel()
                
                execution_time = time.time() - start_time
                
                # Update learned timeout
                prompt_tokens = self.estimate_tokens(prompt)
                self.update_learned_timeout(llm, prompt_tokens, execution_time)
                
                # Clean output for Gemini
                stdout_text = stdout.decode() if stdout else ""
                if llm == "gemini":
                    cleaned_output = self.clean_gemini_output(stdout_text)
                    # Save both raw and cleaned outputs
                    output_file.write_text(stdout_text)
                    clean_file = output_file.with_stem(f"{output_file.stem}_clean")
                    clean_file.write_text(cleaned_output)
                else:
                    cleaned_output = stdout_text
                    output_file.write_text(stdout_text)
                
                if proc.returncode == 0:
                    return {
                        "output_file": str(output_file),
                        "execution_time": execution_time,
                        "exit_code": proc.returncode,
                        "stdout": cleaned_output,
                        "raw_stdout": stdout_text,
                        "stderr": stderr.decode() if stderr else ""
                    }
                else:
                    return {
                        "error": f"Process exited with code {proc.returncode}",
                        "output_file": str(output_file),
                        "stderr": stderr.decode() if stderr else ""
                    }
                    
            except asyncio.TimeoutError:
                # Kill process group
                if sys.platform != 'win32':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                
                # Wait a bit then force kill if needed
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    if sys.platform != 'win32':
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                
                return {
                    "error": f"Process timed out after {timeout} seconds",
                    "output_file": str(output_file),
                    "partial_output": output_file.read_text() if output_file.exists() else ""
                }
                
        except Exception as e:
            return {
                "error": f"Execution failed: {str(e)}",
                "output_file": str(output_file) if output_file.exists() else None
            }


# Create global executor instance
executor = LLMExecutor()


@mcp.tool()
@debug_tool(mcp_logger)
async def execute_llm(
    llm: str,
    prompt: str,
    timeout: Optional[int] = None,
    stream: bool = False,
    output_dir: Optional[str] = None,
    extra_args: Optional[str] = None,
    env_vars: Optional[str] = None,
    json_schema: Optional[str] = None
) -> str:
    """Execute any LLM CLI with a prompt.

    Automatically detects installed LLMs (claude, gemini, gpt, llama, etc.) and 
    executes with intelligent timeout management based on Redis learning.
    
    If prompt contains a question (?) and no json_schema is provided, automatically
    adds a JSON schema instruction with {question, answer} format.

    Args:
        llm: LLM name (claude, gemini, gpt, llama, etc.)
        prompt: The prompt to send to the LLM
        timeout: Optional timeout in seconds (auto-calculated if not provided)
        stream: Enable streaming output if supported
        output_dir: Directory for output files (default: /tmp/llm_outputs)
        extra_args: Additional CLI arguments as JSON array
        env_vars: Additional environment variables as JSON object
        json_schema: Optional JSON schema to enforce response format

    Returns:
        JSON string with execution result including output, timing, and file paths

    Example:
        execute_llm("gemini", "What is 2+2?")  # Auto-adds JSON schema
        execute_llm("claude", "Explain quantum computing", json_schema='{"topic": "string", "explanation": "string"}')
    """
    start_time = time.time()
    
    # Parse JSON arguments
    extra_args_list = json.loads(extra_args) if extra_args else None
    env_vars_dict = json.loads(env_vars) if env_vars else None
    json_schema_dict = json.loads(json_schema) if json_schema else None
    
    result = await executor.execute_llm(
        llm=llm,
        prompt=prompt,
        timeout=timeout,
        stream=stream,
        output_dir=output_dir,
        extra_args=extra_args_list,
        env_vars=env_vars_dict,
        json_schema=json_schema_dict
    )
    
    # Check if result has an error
    if "error" in result:
        return create_error_response(
            error=result["error"],
            tool_name="execute_llm",
            start_time=start_time
        )
    else:
        return create_success_response(
            data=result,
            tool_name="execute_llm",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def concatenate_files(
    file_paths: str,
    output_path: Optional[str] = None,
    chunk_size: Optional[int] = None,
    model: str = "default"
) -> str:
    """Concatenate multiple files with intelligent chunking.

    Automatically handles large files by splitting into token-limited chunks.
    Detects file encoding and adds clear file separators.

    Args:
        file_paths: JSON array of file paths to concatenate
        output_path: Optional output file path (default: /tmp/llm_outputs/concatenated_*.txt)
        chunk_size: Maximum tokens per chunk (default: model-specific limit)
        model: Model name for token estimation (default: uses general estimation)

    Returns:
        JSON string with output path(s) and token statistics

    Example:
        concatenate_files('["file1.py", "file2.py", "README.md"]', chunk_size=50000)
    """
    start_time = time.time()
    
    # Parse file paths
    paths = json.loads(file_paths)
    
    result = await executor.concatenate_files(
        file_paths=paths,
        output_path=output_path,
        chunk_size=chunk_size,
        model=model
    )
    
    # Check if result has an error
    if "error" in result:
        return create_error_response(
            error=result["error"],
            tool_name="concatenate_files",
            start_time=start_time
        )
    else:
        return create_success_response(
            data=result,
            tool_name="concatenate_files",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def detect_llms() -> str:
    """Detect which LLM CLIs are available on the system.

    Checks PATH for known LLM commands and returns available options.

    Returns:
        JSON string with dictionary of available LLMs and their commands

    Example:
        detect_llms()
    """
    start_time = time.time()
    
    result = executor.detect_available_llms()
    return create_success_response(
        data=result,
        tool_name="detect_llms",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def estimate_tokens(
    text: Optional[str] = None,
    file_path: Optional[str] = None,
    model: str = "default"
) -> str:
    """Estimate token count for text or file.

    Uses tiktoken if available, otherwise falls back to character-based estimation.

    Args:
        text: Text content to analyze (use this OR file_path)
        file_path: Path to file to analyze (use this OR text)
        model: Model name for specific tokenizer (default: general estimation)

    Returns:
        JSON string with estimated token count

    Example:
        estimate_tokens(text="Hello world", model="claude")
    """
    start_time = time.time()
    
    if text:
        count = executor.estimate_tokens(text, model)
    elif file_path:
        path = Path(file_path)
        if not path.exists():
            return create_error_response(
                error=f"File not found: {file_path}",
                tool_name="estimate_tokens",
                start_time=start_time
            )
        text = path.read_text()
        count = executor.estimate_tokens(text, model)
    else:
        return create_error_response(
            error="Provide either text or file_path",
            tool_name="estimate_tokens",
            start_time=start_time
        )
    
    result = {
        "success": True,
        "estimated_tokens": count,
        "model": model,
        "method": "tiktoken" if TIKTOKEN_AVAILABLE else "character-based"
    }
    
    return create_success_response(
        data=result,
        tool_name="estimate_tokens",
        start_time=start_time
    )


@mcp.tool()
@debug_tool(mcp_logger)
async def parse_llm_output(
    output_file: Optional[str] = None,
    content: Optional[str] = None,
    extract_streaming: bool = False
) -> str:
    """Parse JSON from LLM output.

    Handles common LLM output formats including markdown code blocks,
    mixed content, and malformed JSON. Uses json_repair if available.

    Args:
        output_file: Path to LLM output file
        content: Direct content to parse (use this OR output_file)
        extract_streaming: If true, extract newline-delimited JSON objects

    Returns:
        JSON string with parsed content

    Example:
        parse_llm_output(output_file="/tmp/llm_outputs/claude_output_20250119_123456.txt")
    """
    start_time = time.time()
    
    # Get content
    if output_file:
        path = Path(output_file)
        if not path.exists():
            return create_error_response(
                error=f"File not found: {output_file}",
                tool_name="parse_llm_output",
                start_time=start_time
            )
        content = path.read_text()
    elif not content:
        return create_error_response(
            error="Provide either output_file or content",
            tool_name="parse_llm_output",
            start_time=start_time
        )
    
    # Parse based on mode
    if extract_streaming:
        results = executor.extract_streaming_json(content)
        result = {
            "success": True,
            "parsed": results,
            "count": len(results),
            "type": "streaming_json"
        }
    else:
        parsed = executor.parse_json_output(content)
        result = {
            "success": True,
            "parsed": parsed,
            "type": type(parsed).__name__,
            "json_repair_available": JSON_REPAIR_AVAILABLE
        }
    
    return create_success_response(
        data=result,
        tool_name="parse_llm_output",
        start_time=start_time
    )


async def working_usage():
    """Demonstrate proper usage of the universal LLM executor.
    
    AGENT: Run this for stable, production-ready example.
    """
    logger.info("=== Universal LLM Executor Usage ===")
    
    # Test 1: Detect available LLMs
    logger.info("\n1. Detecting available LLMs...")
    available = executor.detect_available_llms()
    logger.info(f"Available LLMs: {available}")
    
    # Test 2: Concatenate files
    logger.info("\n2. Testing file concatenation...")
    test_files = [
        "/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_llm_instance.py",
        "/home/graham/workspace/experiments/cc_executor/README.md"
    ]
    
    # Only test if files exist
    existing_files = [f for f in test_files if Path(f).exists()]
    if existing_files:
        result = await executor.concatenate_files(
            file_paths=existing_files[:2],  # Just 2 files
            chunk_size=10000  # Small chunks for demo
        )
        logger.info(f"Concatenation result: {result}")
    
    # Test 3: Execute a simple LLM command
    if "claude" in available:
        logger.info("\n3. Testing Claude execution...")
        result = await executor.execute_llm(
            llm="claude",
            prompt="Say 'Hello from Universal LLM Executor'",
            timeout=30
        )
        logger.info(f"Claude result: {result}")
    
    logger.success("✓ Usage demonstration complete!")


async def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    """
    logger.info("=== Debug Mode ===")
    
    # Test Gemini with clean output and JSON schema
    available = executor.detect_available_llms()
    if "gemini" in available:
        logger.info("Testing Gemini with 2+2 and auto JSON schema...")
        result = await executor.execute_llm(
            llm="gemini",
            prompt="What is 2+2?",
            timeout=30
        )
        logger.info(f"Raw result: {json.dumps(result, indent=2)}")
        
        # Show cleaned output
        if result.get("success"):
            logger.info(f"\nCleaned output: {result.get('stdout')}")
            
            # Try to parse as JSON
            try:
                json_response = json.loads(result.get('stdout', ''))
                logger.info(f"\nParsed JSON response: {json.dumps(json_response, indent=2)}")
            except json.JSONDecodeError:
                logger.warning("Could not parse response as JSON")
        
        # Test with custom schema
        logger.info("\n\nTesting with custom schema...")
        custom_schema = {
            "calculation": "string", 
            "result": "number",
            "explanation": "string"
        }
        
        result2 = await executor.execute_llm(
            llm="gemini",
            prompt="Calculate 5 * 7",
            timeout=30,
            json_schema=custom_schema
        )
        
        if result2.get("success"):
            logger.info(f"\nCustom schema output: {result2.get('stdout')}")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - TEST: Run with 'test' argument for quick MCP server test
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "test":
        # Quick test mode for MCP validation
        print(f"✓ {Path(__file__).name} can start successfully!")
        print(f"✓ Available LLMs: {executor.detect_available_llms()}")
        print(f"✓ Redis available: {executor.redis_client is not None}")
        print(f"✓ Tiktoken available: {TIKTOKEN_AVAILABLE}")
        sys.exit(0)
    elif mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())
        
        # Also run MCP server
        print("\nStarting MCP server...")
        mcp.run()