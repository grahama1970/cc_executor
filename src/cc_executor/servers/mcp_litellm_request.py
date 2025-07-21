#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "litellm",
#     "loguru",
#     "pydantic",
#     "tenacity",
#     "tqdm",
#     "redis",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
An MCP tool for making a single, resilient LiteLLM call.

This is the best tool to use for simple, one-off LLM queries. It provides a
straightforward interface and returns a single, structured result.

**When to Use:**
- When you need to ask a single question or perform one task.
- Example: "What is the capital of France?"
- Example: "Summarize this one specific article."

**This tool is a simplified front-end to the more powerful batch processor.**
It automatically handles retries on network errors and tracks the cost
of the call.

**Example Input (Direct Arguments):**
- model: "gpt-4o-mini"
- messages: [{"role": "user", "content": "What is the capital of Germany?"}]

**Example Output (A single LiteLLMResult object):**
{
    "request_id": "some-unique-id",
    "status": "success",
    "response": { ... full litellm response ... },
    "cost": 0.00018,
    "error": null,
    "final_attempt": 1
}
"""

import os
import sys
import json
import asyncio
import time
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# --- Boilerplate and Initialization ---
# This setup assumes the batch processor and this file are in the same directory.
load_dotenv(find_dotenv())

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Import from mcp-logger-utils package
from mcp_logger_utils import MCPLogger, debug_tool
mcp_logger = MCPLogger("litellm-request")

# Define models inline to avoid import issues
import uuid
from typing import Literal
import litellm

class LiteLLMRequest(BaseModel):
    """Represents a single LiteLLM API request."""
    model: str
    messages: List[Dict[str, str]]
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    cache: Optional[Dict[str, Any]] = None

class LiteLLMResult(BaseModel):
    """Represents the result of a single LiteLLM API request."""
    request_id: str
    status: Literal["success", "error"]
    response: Optional[Any] = None
    cost: Optional[float] = None
    error: Optional[str] = None
    final_attempt: int = 1

# Lazy load cache initialization
_cache_initialized = False

def _ensure_cache_initialized():
    """Lazy initialize litellm cache on first use."""
    global _cache_initialized
    if not _cache_initialized:
        try:
            import redis
            # Basic cache setup if redis is available
            redis_client = redis.Redis(host='localhost', port=6379)
            redis_client.ping()
            litellm.cache = "redis"
            litellm.cache_params = {"redis_client": redis_client}
        except Exception:
            # Fallback to in-memory cache
            litellm.cache = "simple"
        _cache_initialized = True
# --- End Boilerplate ---


# --- Initialize FastMCP Server ---
mcp = FastMCP("litellm-request")


# --- Core Logic Function ---

async def _process_single_request_core(
    model: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    cache: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None
) -> LiteLLMResult:
    """Core logic for processing a single request without MCP decoration."""
    # Ensure cache is initialized (lazy loading)
    _ensure_cache_initialized()
    
    logger.info(f"Received single request for model: {model}")

    # 1. Create a single LiteLLMRequest object from the direct arguments.
    single_request = LiteLLMRequest(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        cache=cache
    )

    # 2. Process the request directly with retry logic
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    from litellm.exceptions import APIConnectionError, RateLimitError, ServiceUnavailableError, Timeout
    
    RETRYABLE_EXCEPTIONS = (APIConnectionError, RateLimitError, ServiceUnavailableError, Timeout)
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS)
    )
    async def _execute_with_retry():
        params = single_request.model_dump(exclude={"request_id"}, exclude_none=True)
        # Handle optional API configuration
        if api_key:
            params["api_key"] = api_key
        if api_base:
            params["api_base"] = api_base
        return await litellm.acompletion(**params)
    
    # 3. Execute with error handling
    try:
        response = await _execute_with_retry()
        
        # Calculate cost if possible
        cost = None
        try:
            from litellm import completion_cost
            if hasattr(response, 'usage'):
                cost = completion_cost(completion_response=response, model=model)
        except Exception:
            pass
        
        logger.info(f"Successfully processed single request {single_request.request_id}")
        return LiteLLMResult(
            request_id=single_request.request_id,
            status="success",
            response=response.model_dump() if hasattr(response, 'model_dump') else response,
            cost=cost,
            error=None,
            final_attempt=1
        )
    except Exception as e:
        logger.error(f"Failed to process request {single_request.request_id}: {str(e)}")
        return LiteLLMResult(
            request_id=single_request.request_id,
            status="error",
            response=None,
            cost=None,
            error=str(e),
            final_attempt=5
        )

# --- The Main MCP Tool ---

@mcp.tool()
@debug_tool(mcp_logger)
async def process_single_request(
    model: str = Field(description="The model name to use (e.g., 'gpt-4o')."),
    messages: str = Field(description="JSON string of messages list for the chat completion."),
    temperature: Optional[float] = Field(default=None, description="Sampling temperature."),
    max_tokens: Optional[int] = Field(default=None, description="Maximum number of tokens to generate."),
    cache: Optional[str] = Field(default=None, description="JSON string of cache control options (e.g., '{\"no-cache\": true}')."),
    api_key: Optional[str] = Field(default=None, description="API key. SECURITY NOTE: Using environment variables is preferred.")
) -> str:
    """
    Processes a single, resilient LiteLLM request and returns a single result object.

    This is the ideal tool for simple, individual queries. It wraps the powerful
    batch processor to provide retries, cost tracking, and caching.
    """
    start_time = time.time()
    # Parse JSON strings
    import json
    messages_list = json.loads(messages)
    cache_dict = json.loads(cache) if cache else None
    
    # Delegate to the core logic function
    result = await _process_single_request_core(
        model=model,
        messages=messages_list,
        temperature=temperature,
        max_tokens=max_tokens,
        cache=cache_dict,
        api_key=api_key
    )
    return create_success_response(
        data=result.model_dump(),
        tool_name="process_single_request",
        start_time=start_time
    )


# --- Test Function ---
async def test_tool():
    """A simple function to test the single request tool."""
    print("--- Testing LiteLLM Single Request Tool ---")

    print("\n1. Testing a successful call...")
    success_result = await process_single_request(
        model="gpt-4o-mini",
        messages=json.dumps([{"role": "user", "content": "Tell me a short story about a robot who discovers music."}])
    )
    print(success_result)

    print("\n2. Testing a call that will fail (invalid model)...")
    fail_result = await process_single_request(
        model="invalid-model-name-12345",
        messages=json.dumps([{"role": "user", "content": "This will not work."}])
    )
    print(fail_result)
    print("\n--- Test Complete ---")


# --- Run Server or Test ---
if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(test_tool())
    else:
        try:
            logger.info("Starting LiteLLM Single Request MCP server...")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)