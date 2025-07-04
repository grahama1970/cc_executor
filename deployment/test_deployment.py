#!/usr/bin/env python3
"""Test script for CC Executor Docker deployment."""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_executor import WebSocketClient


async def test_deployment():
    """Test the Docker deployment of CC Executor."""
    client = WebSocketClient(url="ws://localhost:8003/ws/mcp")
    
    try:
        print("🔌 Connecting to WebSocket...")
        await client.connect()
        print("✅ Connected successfully!")
        
        # Test simple command
        print("\n📝 Testing simple echo command...")
        result = await client.execute_command('echo "CC Executor Docker deployment test"')
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Test Claude command (if API key is set)
        print("\n🤖 Testing Claude command...")
        result = await client.execute_command('claude -p "Say hello from Docker"')
        print(f"Result: {json.dumps(result, indent=2)}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
    finally:
        await client.disconnect()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_deployment())
    sys.exit(0 if success else 1)