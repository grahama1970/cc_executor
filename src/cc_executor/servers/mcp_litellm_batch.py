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
An MCP tool for running multiple, independent LiteLLM calls in parallel.

This tool is designed to be a fast, reliable, and cost-aware batch processor.
It is the best choice when you need to make several LLM calls that do not
depend on each other's results.

**When to Use:**
- Use this when you have a list of items to process independently.
- Ideal for tasks like:
  - Summarizing a list of articles.
  - Classifying a batch of user comments.
  - Generating variations of a piece of text for multiple inputs.

**Key Features:**
- **Fast & Controlled:** Processes requests concurrently, with a configurable limit to avoid rate-limiting.
- **Reliable:** Automatically retries failed requests due to network issues or temporary API rate limits.
- **Cost-Aware:** Calculates and returns the USD cost for each successful request.
- **Flexible:** Allows per-request configuration for caching, models, and other parameters.

**Example Input (`requests` parameter):**
[
    {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "What is the capital of Spain?"}],
        "request_id": "spain_capital_query"
    },
    {
        "model": "claude-3-haiku-20240307",
        "messages": [{"role": "user", "content": "Write a haiku about servers."}],
        "request_id": "haiku_request",
        "cache": {"no-cache": True}
    }
]

**Example Output (A list of LiteLLMResult objects):**
[
    {
        "request_id": "spain_capital_query",
        "status": "success",
        "response": { ... full litellm response ... },
        "cost": 0.00015,
        "error": null,
        "final_attempt": 1
    },
    {
        "request_id": "haiku_request",
        "status": "success",
        "response": { ... full litellm response ... },
        "cost": 0.0008,
        "error": null,
        "final_attempt": 1
    }
]
"""

import os
import sys
import json
import asyncio
import uuid
import traceback
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Literal, Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv
from loguru import logger
from tqdm import tqdm

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

import litellm
from litellm.exceptions import APIConnectionError, RateLimitError, ServiceUnavailableError, Timeout
from litellm import ModelResponse

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log, retry_if_exception_type



# --- Boilerplate and Initialization ---
load_dotenv(find_dotenv())

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Import from mcp-logger-utils package
from mcp_logger_utils import MCPLogger, debug_tool
mcp_logger = MCPLogger("litellm-batch-processor")

# Define models inline to avoid import issues
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
mcp = FastMCP("litellm-batch-processor")


# --- Core Logic with Tenacity Retry Decorator ---

RETRYABLE_EXCEPTIONS = (APIConnectionError, RateLimitError, ServiceUnavailableError, Timeout)

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, "INFO")
)
async def _execute_single_request_with_retry(request: LiteLLMRequest) -> ModelResponse:
    """Internal function that executes a single litellm call, wrapped by tenacity for resilience."""
    params = request.model_dump(exclude={"request_id"}, exclude_none=True)
    return await litellm.acompletion(**params)


# --- Core Batch Processing Logic ---

async def _process_batch_core(
    requests: List[LiteLLMRequest],
    concurrency: int = 25
) -> List[LiteLLMResult]:
    """Core logic for batch processing without MCP decoration."""
    # Ensure cache is initialized (lazy loading)
    _ensure_cache_initialized()
    
    logger.info(f"Received batch of {len(requests)} requests. Starting with concurrency of {concurrency}.")
    semaphore = asyncio.Semaphore(concurrency)
    
    async def _process_and_handle_request(req: LiteLLMRequest) -> LiteLLMResult:
        """Helper to wrap the retryable call, manage semaphore, and format the result."""
        async with semaphore:
            try:
                raw_response = await _execute_single_request_with_retry(req)
                attempt_number = _execute_single_request_with_retry.retry.statistics.get('attempt_number', 1)
                
                cost = litellm.completion_cost(completion_response=raw_response) if raw_response.usage else 0.0

                return LiteLLMResult(
                    request_id=req.request_id,
                    status="success",
                    response=raw_response.model_dump(),
                    cost=cost,
                    final_attempt=attempt_number
                )
            
            except Exception as e:
                logger.error(f"Failed request {req.request_id} after all retries: {type(e).__name__}: {e}")
                return LiteLLMResult(
                    request_id=req.request_id,
                    status="error",
                    error=f"{type(e).__name__}: {e}",
                    final_attempt=_execute_single_request_with_retry.retry.statistics.get('attempt_number', 1)
                )
    
    # Process all requests with tqdm progress bar
    tasks = [_process_and_handle_request(req) for req in requests]
    results = []
    
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing LiteLLM requests"):
        result = await coro
        results.append(result)
    
    # Sort results back to their original order to maintain request/response pairing
    results.sort(key=lambda r: next(i for i, req in enumerate(requests) if req.request_id == r.request_id))
    
    succeeded = sum(1 for r in results if r.status == "success")
    logger.info(f"Batch complete: {succeeded}/{len(results)} succeeded.")
    
    return results

# --- The Main MCP Tool ---

@mcp.tool()
@debug_tool(mcp_logger)
async def process_batch_requests(
    requests: str = Field(description="JSON string of request objects array. Each object should have: model, messages, and optional temperature, max_tokens, cache."),
    concurrency: int = Field(default=25, ge=1, le=100, description="Maximum number of parallel requests to run.")
) -> str:
    """
    Processes a batch of LiteLLM requests concurrently with retries, a progress bar, and concurrency control.

    This tool is highly resilient to transient network errors and API rate limits.
    It takes a list of requests and returns a list of corresponding results.
    Each result is guaranteed to have the 'request_id' from its original request.
    """
    start_time = time.time()
    
    try:
        # Parse JSON string and create LiteLLMRequest objects
        import json
        request_dicts = json.loads(requests)
        request_objects = [LiteLLMRequest(**req) for req in request_dicts]
        
        # Delegate to the core logic function
        results = await _process_batch_core(requests=request_objects, concurrency=concurrency)
        
        # Convert results to standardized response format
        return create_success_response(
            data={
                "results": [result.model_dump() for result in results],
                "summary": {
                    "total_requests": len(results),
                    "successful": sum(1 for r in results if r.status == "success"),
                    "failed": sum(1 for r in results if r.status == "error"),
                    "total_cost": sum(r.cost or 0 for r in results if r.status == "success")
                }
            },
            tool_name="process_batch_requests",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=f"{type(e).__name__}: {str(e)}",
            tool_name="process_batch_requests",
            start_time=start_time
        )


# --- Test Function ---
async def test_tool():
    """A simple function to test the tool's functionality."""
    print("--- Testing LiteLLM Batch Processor ---")
    
    sample_requests = [
        LiteLLMRequest(
            model="gpt-4o-mini", messages=[{"role": "user", "content": "Tell me a joke about Python."}]
        ),
        LiteLLMRequest(
            model="this-model-does-not-exist", messages=[{"role": "user", "content": "This will fail immediately."}]
        ),
        LiteLLMRequest(
            model="gpt-4o-mini", messages=[{"role": "user", "content": "What is the capital of France?"}], temperature=0.1
        ),
    ]
    
    results = await process_batch_requests(sample_requests, concurrency=5)
    
    print("\n--- Results ---")
    print(json.dumps([res.model_dump() for res in results], indent=2))
    print("--- Test Complete ---")


# --- Run Server or Test ---
if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(test_tool())
    else:
        try:
            logger.info("Starting LiteLLM Batch Processor MCP server...")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)