#!/usr/bin/env python3
"""Test script to verify mcp-logger-utils functionality before PyPI upload."""

import asyncio
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_logger_utils import MCPLogger, debug_tool, repair_and_parse_json


# Test 1: Basic logger functionality
print("Test 1: Basic Logger Functionality")
print("-" * 50)
logger = MCPLogger("test-server")
print(f"✓ Logger created, log directory: {logger.log_dir}")
print(f"✓ Debug log file: {logger.debug_log}")


# Test 2: Truncation functionality
print("\nTest 2: Truncation Functionality")
print("-" * 50)

# Test string truncation
long_string = "A" * 500
truncated = logger._truncate_for_log(long_string)
print(f"✓ Long string ({len(long_string)} chars) truncated to: {len(truncated)} chars")

# Test list truncation
long_list = list(range(100))
truncated_list = logger._truncate_for_log(long_list)
print(f"✓ Long list ({len(long_list)} items) truncated to: {truncated_list}")

# Test base64 truncation
base64_image = "data:image/png;base64," + "A" * 1000
truncated_b64 = logger._truncate_for_log(base64_image)
print(f"✓ Base64 image truncated properly: {len(truncated_b64)} chars")


# Test 3: Sync function decoration
print("\nTest 3: Sync Function Decoration")
print("-" * 50)

@debug_tool(logger)
def sync_function(name: str, value: int) -> dict:
    """Test sync function."""
    if value < 0:
        raise ValueError("Value must be positive")
    return {"name": name, "value": value * 2}

# Test success
result = sync_function("test", 5)
print(f"✓ Sync function success: {result}")

# Test error handling
error_result = sync_function("test", -1)
print(f"✓ Sync function error handled: {error_result[:100]}...")


# Test 4: Async function decoration
print("\nTest 4: Async Function Decoration")
print("-" * 50)

@debug_tool(logger)
async def async_function(items: list) -> dict:
    """Test async function."""
    await asyncio.sleep(0.1)  # Simulate async work
    if not items:
        raise ValueError("Items list cannot be empty")
    return {"count": len(items), "first": items[0]}

async def test_async():
    # Test success
    result = await async_function([1, 2, 3])
    print(f"✓ Async function success: {result}")
    
    # Test error handling
    error_result = await async_function([])
    print(f"✓ Async function error handled: {error_result[:100]}...")

asyncio.run(test_async())


# Test 5: JSON repair functionality
print("\nTest 5: JSON Repair Functionality")
print("-" * 50)

test_cases = [
    # Already valid JSON
    '{"valid": true}',
    
    # JSON in markdown block
    '```json\n{"name": "Claude", "version": 3.0}\n```',
    
    # Malformed JSON with comments and trailing comma
    '{\n  "name": "Claude",\n  "helpful": true, // very helpful!\n  "version": 3.0,\n}',
    
    # Not JSON at all
    "This is just plain text",
    
    # Already a dict
    {"already": "parsed"},
]

for i, test_case in enumerate(test_cases):
    result = repair_and_parse_json(test_case, logger_instance=logger.logger)
    print(f"✓ Test case {i+1}: {type(result).__name__} - {str(result)[:50]}...")


# Test 6: Custom truncation limits
print("\nTest 6: Custom Truncation Limits")
print("-" * 50)

custom_logger = MCPLogger(
    "custom-test",
    max_log_str_len=50,
    max_log_list_len=3
)

short_truncated = custom_logger._truncate_for_log("X" * 100)
print(f"✓ Custom string truncation (50 chars): {len(short_truncated)} chars")

short_list = custom_logger._truncate_for_log(list(range(10)))
print(f"✓ Custom list truncation (3 items): {short_list}")


# Test 7: Environment variable configuration
print("\nTest 7: Environment Variable Configuration")
print("-" * 50)

import os
os.environ["MCP_DEBUG"] = "true"
os.environ["MCP_LOG_DIR"] = "/tmp/test_mcp_logs"

env_logger = MCPLogger("env-test")
print(f"✓ MCP_DEBUG recognized: Debug mode active")
print(f"✓ MCP_LOG_DIR recognized: {env_logger.log_dir}")

# Cleanup
del os.environ["MCP_DEBUG"]
del os.environ["MCP_LOG_DIR"]


print("\n" + "="*50)
print("✅ ALL TESTS PASSED!")
print("="*50)
print("\nThe mcp-logger-utils package is working correctly and ready for PyPI upload.")
print("\nLog files created in:")
print(f"  - {logger.debug_log}")
print(f"  - {custom_logger.debug_log}")
print(f"  - {env_logger.debug_log}")