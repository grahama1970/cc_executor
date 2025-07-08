#!/usr/bin/env python3
"""
Quick test to verify responses are saved to /tmp/responses
"""
import asyncio
import json
from pathlib import Path
from executor import cc_execute

async def test_saves_to_responses():
    """Test that output is saved to /tmp/responses."""
    print("Testing cc_execute saves to /tmp/responses...")
    
    # Execute a simple task with explicit config
    from executor import CCExecutorConfig
    
    config = CCExecutorConfig(timeout=60)  # 60 second timeout
    result = await cc_execute(
        "Write a one-line Python function to add two numbers",
        config=config,
        stream=False  # Don't stream for quick test
    )
    
    print(f"\nResult: {result[:100]}...")
    
    # Check /tmp/responses
    response_files = list(Path("/tmp/responses").glob("cc_execute_*.json"))
    
    if response_files:
        latest = max(response_files, key=lambda p: p.stat().st_mtime)
        print(f"\n✅ Response saved to: {latest}")
        
        # Load and verify
        with open(latest, 'r') as f:
            data = json.load(f)
        
        print(f"\nResponse data:")
        print(f"  - Session ID: {data['session_id']}")
        print(f"  - Task: {data['task'][:50]}...")
        print(f"  - Output length: {len(data['output'])} chars")
        print(f"  - Return code: {data['return_code']}")
        
        return True
    else:
        print("\n❌ No response files found in /tmp/responses")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_saves_to_responses())
    exit(0 if success else 1)