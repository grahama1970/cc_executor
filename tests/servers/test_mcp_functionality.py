#!/usr/bin/env python3
"""
Test MCP server functionality by directly calling the tool functions.
This verifies the underlying implementation works correctly.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_cc_execute_tool():
    """Test the cc_execute MCP tool functionality."""
    print("🔧 Testing cc_execute MCP tool...")
    print("-" * 50)
    
    # Import the actual tool implementation
    from cc_executor.servers.mcp_cc_execute import cc_execute as mcp_cc_execute
    
    # Test 1: Simple calculation
    print("\n1️⃣ Test: Simple calculation with JSON")
    task = "Calculate 10 * 5 and return JSON: {\"calculation\": \"10 * 5\", \"result\": 50}"
    
    try:
        result = await mcp_cc_execute(
            task=task,
            json_mode=True,
            timeout=30
        )
        print(f"✅ Success: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Code generation
    print("\n2️⃣ Test: Code generation with JSON schema")
    task = """Write a function to reverse a string.
    Return JSON: {
        "function_name": "reverse_string",
        "code": "def reverse_string(s): return s[::-1]",
        "example": "reverse_string('hello') # Returns 'olleh'"
    }"""
    
    try:
        result = await mcp_cc_execute(
            task=task,
            json_mode=True,
            timeout=30
        )
        print(f"✅ Success: Generated function")
        if "result" in result:
            print(f"   Code preview: {result['result'][:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


async def test_verify_execution_tool():
    """Test the verify_execution MCP tool functionality."""
    print("\n🔍 Testing verify_execution MCP tool...")
    print("-" * 50)
    
    # Import the actual tool implementation
    from cc_executor.servers.mcp_cc_execute import verify_execution
    
    # Test 1: Verify last execution
    print("\n1️⃣ Test: Verify last execution")
    
    try:
        result = await verify_execution(
            last_n=1,
            generate_report=False
        )
        print(f"✅ Verification result:")
        print(f"   Status: {result.get('status')}")
        print(f"   Files checked: {result.get('checked_files', 0)}")
        
        # Check verifications
        if "verifications" in result and result["verifications"]:
            v = result["verifications"][0]
            print(f"   Last execution:")
            print(f"     - File: {v.get('file', 'N/A')}")
            print(f"     - JSON valid: {v.get('json_valid', False)}")
            print(f"     - UUID verified: {v.get('uuid_verified', False)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Generate report
    print("\n2️⃣ Test: Generate anti-hallucination report")
    
    try:
        result = await verify_execution(
            last_n=2,
            generate_report=True
        )
        print(f"✅ Report generation result:")
        print(f"   Status: {result.get('status')}")
        if "report_path" in result:
            print(f"   Report saved to: {result['report_path']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


async def test_mcp_integration():
    """Test complete MCP integration flow."""
    print("\n🔄 Testing complete MCP integration flow...")
    print("-" * 50)
    
    # Execute a task and verify it
    from cc_executor.servers.mcp_cc_execute import cc_execute as mcp_cc_execute
    from cc_executor.servers.mcp_cc_execute import verify_execution
    
    # Step 1: Execute task
    print("\n1️⃣ Executing task with unique marker...")
    unique_marker = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    task = f"""Create a simple test.
    Return JSON: {{
        "test_id": "{unique_marker}",
        "status": "success",
        "timestamp": "{datetime.now().isoformat()}"
    }}"""
    
    try:
        exec_result = await mcp_cc_execute(task=task, json_mode=True)
        print(f"✅ Execution complete")
        print(f"   UUID: {exec_result.get('execution_uuid', 'N/A')}")
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return False
    
    # Step 2: Verify execution
    print("\n2️⃣ Verifying execution...")
    
    try:
        verify_result = await verify_execution(
            execution_uuid=exec_result.get('execution_uuid'),
            generate_report=False
        )
        print(f"✅ Verification complete")
        print(f"   Status: {verify_result.get('status')}")
        print(f"   Anti-hallucination check: {'PASSED' if verify_result.get('status') == 'success' else 'FAILED'}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    return True


async def main():
    """Run all MCP functionality tests."""
    print("🧪 CC Executor MCP Functionality Tests")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    results = []
    
    # Test 1: cc_execute tool
    results.append(("cc_execute tool", await test_cc_execute_tool()))
    
    # Test 2: verify_execution tool
    results.append(("verify_execution tool", await test_verify_execution_tool()))
    
    # Test 3: Integration flow
    results.append(("Integration flow", await test_mcp_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("-" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All MCP functionality tests PASSED!")
        print("\n✅ MCP server is ready for use with Claude Desktop")
        print("   Add the configuration from test_mcp_direct.py")
        return 0
    else:
        print("❌ Some tests FAILED - MCP server needs fixes")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)