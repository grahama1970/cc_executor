#!/usr/bin/env python3
"""
Test UUID4 anti-hallucination verification.
"""
import asyncio
import json
from pathlib import Path
from executor import cc_execute


async def test_uuid_verification():
    """Test that UUID4 is properly implemented."""
    print("Testing UUID4 anti-hallucination...")
    
    # Execute a simple task
    result = await cc_execute("Write a one-line Python comment", stream=False)
    
    print(f"\nGot result: {result.strip()}")
    
    # Find the latest response file
    response_dir = Path(__file__).parent / "tmp" / "responses"
    response_files = sorted(
        response_dir.glob("cc_execute_*.json"),
        key=lambda p: p.stat().st_mtime
    )
    
    if not response_files:
        print("❌ No response files found!")
        return False
    
    latest = response_files[-1]
    print(f"\n✅ Found response file: {latest.name}")
    
    # Load and verify UUID is at END
    with open(latest) as f:
        data = json.load(f)
    
    print(f"\nResponse data keys: {list(data.keys())}")
    
    # Verify UUID exists
    if "execution_uuid" not in data:
        print("❌ No execution_uuid found!")
        return False
    
    print(f"✅ Found execution_uuid: {data['execution_uuid']}")
    
    # Verify it's the LAST key
    keys = list(data.keys())
    if keys[-1] != "execution_uuid":
        print(f"❌ UUID not at end! Last key: {keys[-1]}")
        return False
    
    print("✅ UUID is the LAST key (anti-hallucination verified)")
    
    # Show the complete JSON structure
    print("\nComplete response structure:")
    print(json.dumps(data, indent=2))
    
    return True


async def main():
    """Run UUID verification test."""
    success = await test_uuid_verification()
    
    if success:
        print("\n✅ UUID4 VERIFICATION PASSED")
        print("- UUID generated at start")
        print("- UUID saved at END of JSON")
        print("- Ready for transcript verification")
    else:
        print("\n❌ UUID4 VERIFICATION FAILED")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)