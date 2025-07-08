#!/usr/bin/env python3
"""Test report generation with a simple task."""
import asyncio
from executor import cc_execute, CCExecutorConfig

async def test_simple_with_report():
    """Test report generation with a simple task."""
    print("Testing Report Generation Feature")
    print("="*60)
    
    # Simple task with report generation
    task = "Write a one-line Python lambda to square a number"
    
    print(f"Task: {task}")
    print("Executing with report generation enabled...")
    
    result = await cc_execute(
        task,
        config=CCExecutorConfig(timeout=120),  # 2 minute timeout
        stream=True,
        return_json=True,
        generate_report=True  # Enable report generation
    )
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    if isinstance(result, dict):
        print(f"✅ Result: {result.get('result', 'No result')}")
        print(f"✅ Summary: {result.get('summary', 'No summary')}")
        print(f"✅ Execution UUID: {result.get('execution_uuid', 'No UUID')}")
        print(f"\n📋 Report generated in: tmp/responses/")
        print("Look for: CC_EXECUTE_ASSESSMENT_REPORT_*.md")
    else:
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
    
    # List generated files
    print("\n" + "="*60)
    print("GENERATED FILES:")
    print("="*60)
    
    import os
    from pathlib import Path
    
    response_dir = Path("tmp/responses")
    if response_dir.exists():
        files = sorted(response_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
        for f in files[:5]:  # Show last 5 files
            print(f"  {f.name} ({f.stat().st_size} bytes)")

async def test_complex_with_report():
    """Test report generation with a more complex task."""
    print("\n\n" + "="*60)
    print("Testing Complex Task with Report")
    print("="*60)
    
    task = """Create a Python function that:
1. Calculates the nth Fibonacci number
2. Includes error handling for negative inputs
3. Has a docstring explaining the algorithm
4. Include usage examples in if __name__ == "__main__"
"""
    
    print(f"Task: {task[:100]}...")
    print("Executing with report generation...")
    
    result = await cc_execute(
        task,
        config=CCExecutorConfig(timeout=180),  # 3 minute timeout
        stream=True,
        return_json=True,
        generate_report=True
    )
    
    if isinstance(result, dict):
        print(f"\n✅ Files created: {result.get('files_created', [])}")
        print(f"✅ Summary: {result.get('summary', 'No summary')}")
        print(f"✅ Execution UUID: {result.get('execution_uuid', 'No UUID')}")
        print(f"\n📋 Report generated - check tmp/responses/")

if __name__ == "__main__":
    print("CC_EXECUTE REPORT GENERATION TEST")
    print("="*80)
    print("This test demonstrates the assessment report generation feature")
    print("Reports follow the CORE_ASSESSMENT_REPORT_TEMPLATE.md format")
    print("="*80)
    
    asyncio.run(test_simple_with_report())
    asyncio.run(test_complex_with_report())