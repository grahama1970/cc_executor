#!/usr/bin/env python3
"""
Manual test for the mcp_llm_instance server functions.

This bypasses the MCP decorators and tests the core functionality directly.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the module
import mcp_llm_instance


async def test_execute():
    """Test basic LLM execution."""
    print("Testing basic LLM execution...")
    
    # Test Claude
    print("\n1. Testing Claude:")
    try:
        config = mcp_llm_instance.get_llm_config("claude")
        command = await mcp_llm_instance.build_command(config, "What is 2+2? Just the number.", stream=False)
        print(f"   Command: {' '.join(command[:3])}...")
        
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=mcp_llm_instance.os.environ.copy(),
            timeout=30,
            stream_callback=None
        )
        
        print(f"   Success: {result['success']}")
        print(f"   Output: {result['output'][:100]}")
        print(f"   Time: {result['execution_time']:.2f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Gemini
    print("\n2. Testing Gemini:")
    try:
        config = mcp_llm_instance.get_llm_config("gemini")
        command = await mcp_llm_instance.build_command(config, "What is 3+3? Just the number.")
        print(f"   Command: {' '.join(command[:3])}...")
        
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=mcp_llm_instance.os.environ.copy(),
            timeout=30,
            stream_callback=None
        )
        
        print(f"   Success: {result['success']}")
        print(f"   Output: {result['output'][:100]}")
        print(f"   Error output: {result.get('error', 'None')[:200] if result.get('error') else 'None'}")
        print(f"   Time: {result['execution_time']:.2f}s")
    except Exception as e:
        print(f"   Error: {e}")


async def test_streaming():
    """Test streaming functionality."""
    print("\n\nTesting streaming functionality...")
    
    print("\n3. Testing Claude streaming:")
    try:
        config = mcp_llm_instance.get_llm_config("claude")
        command = await mcp_llm_instance.build_command(config, "Count from 1 to 3", stream=True)
        
        chunks = []
        async def collect_chunk(chunk):
            chunks.append(chunk)
            print(f".", end='', flush=True)
        
        result = await mcp_llm_instance.execute_llm_with_retry(
            config=config,
            command=command,
            env=mcp_llm_instance.os.environ.copy(),
            timeout=60,
            stream_callback=collect_chunk
        )
        
        print(f"\n   Received {len(chunks)} chunks")
        print(f"   Success: {result['success']}")
        print(f"   Total output length: {len(''.join(chunks))}")
    except Exception as e:
        print(f"\n   Error: {e}")


async def test_timeout_estimation():
    """Test timeout category estimation."""
    print("\n\nTesting timeout estimation...")
    
    test_prompts = [
        ("Hello", "Expected: QUICK"),
        ("Write a comprehensive analysis of quantum computing", "Expected: LONG"),
        ("What is the capital of France?", "Expected: QUICK"),
        ("Generate a detailed research report on climate change", "Expected: LONG"),
    ]
    
    for prompt, expected in test_prompts:
        category = mcp_llm_instance.estimate_timeout_category(prompt)
        timeout = mcp_llm_instance.TIMEOUT_VALUES[category]
        print(f"   '{prompt[:30]}...' -> {category} ({timeout}s) - {expected}")


async def main():
    """Run all tests."""
    print("MCP LLM Instance Manual Tests")
    print("=" * 50)
    
    await test_execute()
    await test_streaming()
    await test_timeout_estimation()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())