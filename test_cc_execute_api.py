#!/usr/bin/env python3
"""
Test CC Executor Python API to verify it's working before MCP deployment.
"""

import asyncio
from src.cc_executor.client.cc_execute import cc_execute, CCExecutorConfig


async def test_basic_execution():
    """Test basic command execution."""
    print("🧪 Testing basic cc_execute...")
    
    try:
        result = await cc_execute("What is 2+2?")
        print(f"✅ Basic test passed: {result.strip()}")
        return True
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False


async def test_json_mode():
    """Test JSON mode execution."""
    print("\n🧪 Testing JSON mode...")
    
    try:
        result = await cc_execute(
            "Create a JSON object with name='test' and value=123",
            json_mode=True
        )
        print(f"✅ JSON mode passed: {result}")
        return True
    except Exception as e:
        print(f"❌ JSON mode failed: {e}")
        return False


async def test_with_config():
    """Test with custom config."""
    print("\n🧪 Testing with custom config...")
    
    try:
        config = CCExecutorConfig(timeout=30)
        result = await cc_execute(
            "List 3 benefits of Python programming",
            config=config
        )
        print(f"✅ Config test passed (output length: {len(result)} chars)")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("CC Executor API Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_execution(),
        test_json_mode(),
        test_with_config()
    ]
    
    results = await asyncio.gather(*tests)
    
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n✅ All tests passed! CC Executor is ready.")
        return 0
    else:
        print(f"\n❌ {total - passed} tests failed. Please check the logs.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)