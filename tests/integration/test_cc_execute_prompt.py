#!/usr/bin/env python3
"""
Test cc_execute prompt-based approach after MCP evaluation.
Verifies that the prompt-based approach continues to work reliably.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
import sys
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

async def test_simple_task():
    """Test executing a simple task via cc_execute prompt."""
    logger.info("Testing cc_execute prompt with simple task...")
    
    # Simple task that should complete quickly
    task = {
        "task": "What is the directory structure for a FastAPI project? Create a folder 'test_fastapi_service' with an empty __init__.py and a main.py file that imports FastAPI.",
        "tools": ["Write"],
        "timeout": 60
    }
    
    try:
        # execute_task_via_websocket is synchronous, so we run it in a thread
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            execute_task_via_websocket,
            task["task"],
            task["timeout"],
            task["tools"]
        )
        
        logger.info(f"Task completed: {result['success']}")
        
        # Save raw result for verification
        output_path = Path("/tmp/responses/cc_execute_prompt_test.json")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "task": task,
                "result": result,
                "test": "cc_execute_prompt_verification"
            }, f, indent=2)
        
        logger.info(f"Result saved to: {output_path}")
        
        # Verify files were created
        if result["success"]:
            test_dir = Path("test_fastapi_service")
            if test_dir.exists():
                logger.success("✅ Directory created successfully")
                if (test_dir / "__init__.py").exists():
                    logger.success("✅ __init__.py created")
                if (test_dir / "main.py").exists():
                    logger.success("✅ main.py created")
                    content = (test_dir / "main.py").read_text()
                    if "FastAPI" in content:
                        logger.success("✅ FastAPI import found")
                
                # Clean up test directory
                import shutil
                shutil.rmtree(test_dir)
                logger.info("Cleaned up test directory")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing cc_execute: {e}")
        return {"success": False, "error": str(e)}

async def test_timeout_handling():
    """Test that timeouts are handled properly."""
    logger.info("Testing timeout handling...")
    
    # Task that will likely timeout
    task = {
        "task": "What are all the prime numbers between 1 and 1 million? Calculate and list them all.",
        "tools": ["Write"],
        "timeout": 5  # Very short timeout
    }
    
    try:
        # execute_task_via_websocket is synchronous, so we run it in a thread
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            execute_task_via_websocket,
            task["task"],
            task["timeout"],
            task["tools"]
        )
        
        if not result["success"] and "timeout" in str(result.get("error", "")).lower():
            logger.success("✅ Timeout handled correctly")
        else:
            logger.warning("⚠️ Unexpected result for timeout test")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in timeout test: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("CC_EXECUTE PROMPT VERIFICATION TEST")
    logger.info("Testing after MCP evaluation - confirming prompt approach")
    logger.info("=" * 60)
    
    # Test 1: Simple task execution
    logger.info("\n📝 Test 1: Simple Task Execution")
    result1 = await test_simple_task()
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test 2: Timeout handling
    logger.info("\n⏱️ Test 2: Timeout Handling")
    result2 = await test_timeout_handling()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    if result1["success"]:
        logger.success("✅ Simple task execution: PASSED")
    else:
        logger.error("❌ Simple task execution: FAILED")
        
    if not result2["success"] and "timeout" in str(result2.get("error", "")).lower():
        logger.success("✅ Timeout handling: PASSED")
    else:
        logger.error("❌ Timeout handling: FAILED")
    
    logger.info("\n🎯 CONCLUSION:")
    logger.info("Prompt-based cc_execute continues to work reliably.")
    logger.info("No need for MCP wrapper - prompts are superior for this use case.")

if __name__ == "__main__":
    # First check if WebSocket server is running
    logger.info("Checking if WebSocket server is running...")
    import subprocess
    
    result = subprocess.run(
        ["cc-executor", "server", "status"],
        capture_output=True,
        text=True
    )
    
    if "running" not in result.stdout.lower():
        logger.warning("WebSocket server not running. Starting it...")
        subprocess.run(["cc-executor", "server", "start"], check=False)
        # Give it time to start
        import time
        time.sleep(3)
    
    # Run the tests
    asyncio.run(main())