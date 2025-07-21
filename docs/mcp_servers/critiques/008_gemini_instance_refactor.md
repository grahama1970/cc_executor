#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "tenacity",
#     "mcp-logger-utils>=0.1.5",
#     "pydantic>=2.0"
# ]
# ///
"""
MCP Server for LLM Instance Execution - Simple subprocess-based LLM execution.

This server provides a unified interface for executing LLM commands via their CLI tools,
avoiding direct SDK complexity in favor of simple, reliable subprocess execution.

Key Features:
- Direct subprocess execution (no WebSocket overhead)
- Support for multiple LLM CLIs (Claude, Gemini, OpenAI, etc.)
- Configuration-driven command building (no hardcoded logic)
- Robust streaming and JSON parsing with fallbacks
- Automatic retries for rate limits
- Fixed timeout categories
- Clean error handling
"""

import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging first
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server
mcp = FastMCP("llm-instance")

try:
    from mcp_logger_utils import MCPLogger
    mcp_logger = MCPLogger("llm-instance")
except ImportError:
    logger.warning("mcp-logger-utils not available, continuing without it")
    mcp_logger = None

# ========== CONFIGURATION ==========
class TimeoutCategory(str, Enum):
    """Fixed timeout categories for predictable behavior."""
    QUICK = "quick"      # 60 seconds
    NORMAL = "normal"    # 300 seconds
    LONG = "long"        # 600 seconds
    EXTENDED = "extended" # 1800 seconds

TIMEOUT_VALUES = {
    TimeoutCategory.QUICK: 60,
    TimeoutCategory.NORMAL: 300,
    TimeoutCategory.LONG: 600,
    TimeoutCategory.EXTENDED: 1800
}

@dataclass
class LLMConfig:
    """Configuration for an LLM CLI tool, acting as a command blueprint."""
    name: str
    command_template: List[str]
    env_vars: Dict[str, str] = field(default_factory=dict)
    env_vars_to_remove: List[str] = field(default_factory=list)
    supports_streaming: bool = True
    supports_json_mode: bool = False
    stream_args: List[str] = field(default_factory=list)
    json_mode_args: List[str] = field(default_factory=list)
    rate_limit_patterns: List[str] = field(default_factory=list)
    timeout_category: TimeoutCategory = TimeoutCategory.NORMAL
    max_retries: int = 3

# Default LLM configurations. Note that local models like ollama are handled by
# a separate, API-based server (e.g., using LiteLLM) for better parameter control.
LLM_CONFIGS = {
    "claude": LLMConfig(
        name="claude",
        command_template=["claude", "--dangerously-skip-permissions", "{stream_args}", "{json_args}", "-p", "{prompt}"],
        env_vars_to_remove=["ANTHROPIC_API_KEY"],  # Force use of browser auth
        supports_streaming=True,
        supports_json_mode=True,
        stream_args=["--output-format", "stream-json", "--verbose"],
        json_mode_args=["--output-format", "json"],
        rate_limit_patterns=["rate limit", "429", "too many requests", "usage limit"],
    ),
    "gemini": LLMConfig(
        name="gemini",
        command_template=["gemini", "-y", "-p", "{prompt}"],
        supports_streaming=True,
        supports_json_mode=False,
        rate_limit_patterns=["quota", "rate limit", "429"],
    ),
    "gpt4-cli": LLMConfig(
        name="gpt4-cli",
        command_template=["openai", "chat", "completions", "create", "-m", "gpt-4", "-g", "{prompt}"],
        env_vars={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")},
        supports_streaming=True,
        supports_json_mode=True,
        stream_args=["--stream"],
        json_mode_args=["--response-format", "json_object"],
        rate_limit_patterns=["rate limit", "429", "quota exceeded"],
    )
}

# ========== EXCEPTIONS & DATA MODELS ==========
class RateLimitError(Exception): pass
class LLMNotFoundError(Exception): pass
class LLMExecutionError(Exception): pass

class LLMResult(BaseModel):
    success: bool
    model: str
    output: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    session_id: Optional[str] = None

# ========== HELPER FUNCTIONS ==========
def get_llm_config(model: str) -> LLMConfig:
    if model not in LLM_CONFIGS:
        raise LLMNotFoundError(f"Unknown model: {model}. Available: {list(LLM_CONFIGS.keys())}")
    return LLM_CONFIGS[model]

def detect_rate_limit(output: str, config: LLMConfig) -> bool:
    output_lower = output.lower()
    return any(pattern in output_lower for pattern in config.rate_limit_patterns)

def _extract_json(text: str, question: str) -> Dict[str, Any]:
    """Robustly extracts JSON from LLM output, with a fallback schema."""
    # 1. Look for markdown code fences (e.g., ```json ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    json_str = match.group(1) if match else None

    # 2. If not found, look for the broadest possible JSON object
    if not json_str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0) if match else None

    # 3. Try to parse, with fallbacks
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extracted JSON: {e}. Wrapping in default schema.")
    else:
        logger.warning("No JSON object found in output. Wrapping in default schema.")

    # Fallback for both no-JSON-found and JSON-parse-error
    return {"question": question, "answer": text.strip()}

def build_command(config: LLMConfig, prompt: str, **kwargs) -> List[str]:
    """Builds the shell command from the LLMConfig template."""
    replacements = {
        "{prompt}": prompt,
        "{stream_args}": " ".join(config.stream_args) if kwargs.get("stream") else "",
        "{json_args}": " ".join(config.json_mode_args) if kwargs.get("json_mode") and config.supports_json_mode else "",
    }
    
    final_command = []
    for part in config.command_template:
        for key, value in replacements.items():
            part = part.replace(key, value)
        if part:
            final_command.extend(part.split())
            
    return final_command

# ========== CORE EXECUTION LOGIC ==========
async def _stream_subprocess(proc: asyncio.subprocess.Process) -> AsyncIterator[Dict[str, str]]:
    """A generic async generator to stream lines from a process's stdout and stderr."""
    async def stream_reader(stream, stream_name):
        while True:
            line = await stream.readline()
            if not line:
                break
            yield {stream_name: line.decode('utf-8', errors='replace')}

    # Concurrently read from both stdout and stderr
    tasks = [
        asyncio.create_task(stream_reader(proc.stdout, 'stdout')),
        asyncio.create_task(stream_reader(proc.stderr, 'stderr'))
    ]
    
    while tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for future in done:
            try:
                async for item in future.result(): # This will not happen, as generator is consumed in loop
                    yield item
            except StopAsyncIteration:
                pass # Generator finished
        tasks = list(pending)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=lambda rs: logger.warning(f"Rate limit hit, retrying in {rs.next_action.sleep}s...")
)
async def execute_llm_with_retry(config: LLMConfig, command: List[str], env: Dict[str, str], timeout: int) -> LLMResult:
    """Executes an LLM command, capturing all output and handling errors."""
    session_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"[{session_id}] Executing {config.name}: {' '.join(command)}")
    
    proc = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
    )
    
    output_lines, error_lines = [], []
    try:
        async for chunk in asyncio.wait_for(_stream_subprocess(proc), timeout=timeout):
            if 'stdout' in chunk:
                output_lines.append(chunk['stdout'])
            elif 'stderr' in chunk:
                error_lines.append(chunk['stderr'])
                if detect_rate_limit(chunk['stderr'], config):
                    raise RateLimitError(f"Rate limit in stderr: {chunk['stderr']}")
        await proc.wait()
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise LLMExecutionError(f"Process timed out after {timeout} seconds.")
    
    execution_time = time.time() - start_time
    full_output = "".join(output_lines)
    full_error = "".join(error_lines)

    if proc.returncode != 0:
        error_msg = full_error or full_output or "Unknown error"
        if detect_rate_limit(error_msg, config):
            raise RateLimitError(error_msg)
        raise LLMExecutionError(f"LLM failed with code {proc.returncode}: {error_msg}")
    
    logger.success(f"[{session_id}] Completed in {execution_time:.2f}s")
    
    return LLMResult(
        success=True, model=config.name, output=full_output, error=full_error, 
        execution_time=execution_time, session_id=session_id
    )

# ========== MCP TOOLS ==========
@mcp.tool()
async def execute_llm(model: str, prompt: str, timeout: Optional[int] = None, json_mode: bool = False) -> Dict[str, Any]:
    """Executes an LLM command and returns the complete, parsed result."""
    try:
        config = get_llm_config(model)
        command = build_command(config, prompt, json_mode=json_mode, stream=False)
        
        if timeout is None:
            timeout = TIMEOUT_VALUES[config.timeout_category]
        
        env = os.environ.copy()
        env.update(config.env_vars)
        for key in config.env_vars_to_remove:
            env.pop(key, None)
        
        result = await execute_llm_with_retry(config, command, env, timeout)
        
        if (json_mode and config.supports_json_mode) or model in ["claude", "gemini"]:
             result.parsed_json = _extract_json(result.output, question=prompt)
        
        return result.model_dump(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Execution failed for model {model}: {e}")
        return LLMResult(success=False, model=model, error=str(e)).model_dump()

@mcp.tool()
async def stream_llm(model: str, prompt: str, timeout: Optional[int] = None) -> AsyncIterator[str]:
    """Streams output from an LLM in real-time."""
    try:
        config = get_llm_config(model)
        if not config.supports_streaming:
            yield f"\nError: Model '{model}' does not support streaming.\n"
            return
            
        command = build_command(config, prompt, stream=True)
        if timeout is None:
            timeout = TIMEOUT_VALUES[config.timeout_category]
            
        env = os.environ.copy()
        env.update(config.env_vars)
        for key in config.env_vars_to_remove:
            env.pop(key, None)
            
        proc = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )

        try:
            async for chunk in asyncio.wait_for(_stream_subprocess(proc), timeout=timeout):
                if 'stdout' in chunk:
                    yield chunk['stdout']
                elif 'stderr' in chunk:
                    logger.warning(f"[{model} stderr] {chunk['stderr'].strip()}")
            
            await proc.wait()
            if proc.returncode != 0:
                yield f"\nError: Process exited with code {proc.returncode}\n"
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            yield f"\nError: Stream timed out after {timeout} seconds.\n"

    except Exception as e:
        yield f"\nError: {str(e)}\n"

@mcp.tool()
async def get_llm_status() -> Dict[str, Any]:
    """Checks which configured LLM CLIs are available and working."""
    status = {}
    for model_name, config in LLM_CONFIGS.items():
        try:
            result = await execute_llm(
                model=model_name, prompt="Say 'OK'", timeout=30
            )
            is_available = result.get("success", False)
            message = "OK" if is_available else result.get("error", "Unknown error")
        except Exception as e:
            is_available = False
            message = str(e)
        
        status[model_name] = {
            "available": is_available,
            "message": message,
            "supports_json": config.supports_json_mode,
            "supports_streaming": config.supports_streaming
        }
    return {"success": True, "models": status, "timestamp": datetime.now().isoformat()}

# ========== MAIN ENTRY POINT ==========
if __name__ == "__main__":
    logger.info("Starting LLM Instance MCP Server...")
    logger.info(f"Available CLI models: {list(LLM_CONFIGS.keys())}")
    mcp.run()