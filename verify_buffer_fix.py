#!/usr/bin/env python3
"""
Simple test to verify buffer deadlock is fixed.
If this hangs, the buffer deadlock is NOT fixed.
If this completes, you've made progress.
"""

import asyncio
import sys
import time

# Add CC Execute to path
sys.path.insert(0, '/home/graham/workspace/experiments/cc_executor/src')

try:
    from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig
    print("✅ CC Execute imported successfully")
except ImportError as e:
    print(f"❌ Failed to import CC Execute: {e}")
    sys.exit(1)

async def test_small_output():
    """Test 1: Small output (should always work)"""
    print("\n" + "="*60)
    print("TEST 1: Small Output (<1KB)")
    print("="*60)
    
    task = "What is 2+2? Answer in one word."
    config = CCExecutorConfig(timeout=10, stream_output=False)
    
    start = time.time()
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        elapsed = time.time() - start
        print(f"✅ Completed in {elapsed:.1f}s")
        print(f"   Result: {result.strip()}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def test_medium_output():
    """Test 2: Medium output (~10KB)"""
    print("\n" + "="*60)
    print("TEST 2: Medium Output (~10KB)")
    print("="*60)
    
    task = "Generate a list of exactly 1000 random words, one per line."
    config = CCExecutorConfig(timeout=30, stream_output=True)
    
    start = time.time()
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        elapsed = time.time() - start
        print(f"✅ Completed in {elapsed:.1f}s")
        print(f"   Output size: {len(result)} bytes")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def test_large_output():
    """Test 3: Large output (>64KB) - THE CRITICAL TEST"""
    print("\n" + "="*60)
    print("TEST 3: Large Output (>64KB) - BUFFER DEADLOCK TEST")
    print("="*60)
    
    task = """Generate exactly 100,000 'A' characters. 
    Just the letter A repeated 100,000 times.
    No spaces, no newlines, just AAAAAAA... 100,000 times."""
    
    config = CCExecutorConfig(timeout=30, stream_output=True)
    
    print("🔄 Starting buffer deadlock test...")
    print("   If this hangs, buffer deadlock is NOT fixed")
    
    start = time.time()
    try:
        result = await cc_execute(task, config=config, json_mode=False)
        elapsed = time.time() - start
        
        # Count the A's
        a_count = result.count('A')
        
        if a_count >= 90000:  # Allow some tolerance
            print(f"✅ SUCCESS! Buffer deadlock appears fixed!")
            print(f"   Completed in {elapsed:.1f}s")
            print(f"   Generated {a_count:,} A's")
            print(f"   Total output size: {len(result):,} bytes")
            return True
        else:
            print(f"❌ Output too small: {a_count} A's (expected ~100,000)")
            return False
            
    except asyncio.TimeoutError:
        print(f"❌ TIMEOUT after 30s - buffer deadlock NOT fixed!")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔍 CC Execute Buffer Deadlock Verification")
    print("="*80)
    
    results = []
    
    # Run tests in order
    results.append(await test_small_output())
    results.append(await test_medium_output())
    results.append(await test_large_output())
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if results[2]:  # The critical test
        print("\n✅ BUFFER DEADLOCK IS FIXED! You can notify ArXiv MCP.")
        print("\nNext steps:")
        print("1. Commit your changes")
        print("2. Push to repository")
        print("3. Notify ArXiv with commit SHA")
        return True
    else:
        print("\n❌ BUFFER DEADLOCK STILL EXISTS!")
        print("\nYou need to:")
        print("1. Implement proper stream draining")
        print("2. Handle subprocess output concurrently")
        print("3. Test again with this script")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)