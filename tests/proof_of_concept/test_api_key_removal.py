#!/usr/bin/env python3
import os
import asyncio
from executor import cc_execute

# Set a fake API key to test removal
os.environ['ANTHROPIC_API_KEY'] = 'test-key-should-be-removed'

async def test():
    result = await cc_execute(
        "What is 1+1?",
        stream=True,
        return_json=False
    )
    print(f"Result: {result[:100]}..." if len(result) > 100 else f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())
