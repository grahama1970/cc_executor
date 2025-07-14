"""
Usage examples for cc_execute with WebSocket handler.

This file demonstrates how cc_execute.py calls work with proper streaming JSON format.
Each example shows the exact subprocess command that gets executed.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python usage_cc_execute.py          # Runs all examples
  python usage_cc_execute.py simple   # Run simple test only
  python usage_cc_execute.py medium   # Run medium test only
  python usage_cc_execute.py hard     # Run difficult test only
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.client.cc_execute import cc_execute, CCExecutorConfig
from loguru import logger

# Configure minimal logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


async def test_simple():
    """
    Simple test - basic math question that should complete quickly.
    
    Subprocess command:
    claude -p "What is 2+2? Just give me the number, nothing else." --dangerously-skip-permissions --output-format stream-json --verbose
    """
    logger.info("\n=== SIMPLE TEST ===")
    logger.info("Command: claude -p \"What is 2+2? Just give me the number, nothing else.\" --dangerously-skip-permissions --output-format stream-json --verbose")
    
    try:
        result = await cc_execute(
            "What is 2+2? Just give me the number, nothing else.",
            config=CCExecutorConfig(timeout=30),
            stream=True,
            json_mode=False
        )
        logger.success(f" Simple test passed. Result: {result.strip()}")
        return True
    except Exception as e:
        logger.error(f"L Simple test failed: {e}")
        return False


async def test_medium():
    """
    Medium test - generate creative content with structured output.
    
    Subprocess command:
    claude -p "Write 3 haikus about Python programming. Make them funny." --dangerously-skip-permissions --output-format stream-json --verbose
    """
    logger.info("\n=== MEDIUM TEST ===")
    logger.info("Command: claude -p \"Write 3 haikus about Python programming. Make them funny.\" --dangerously-skip-permissions --output-format stream-json --verbose")
    
    try:
        result = await cc_execute(
            "Write 3 haikus about Python programming. Make them funny.",
            config=CCExecutorConfig(timeout=60),
            stream=True,
            json_mode=False
        )
        # Verify we got haikus
        lines = result.strip().split('\n')
        haiku_count = sum(1 for line in lines if line.strip() == '')  # Count blank lines between haikus
        logger.success(f" Medium test passed. Generated {haiku_count + 1} haikus")
        logger.info(f"First few lines: {lines[:3]}")
        return True
    except Exception as e:
        logger.error(f"L Medium test failed: {e}")
        return False


async def test_difficult():
    """
    Difficult test - complex task with JSON output and file operations.
    
    Subprocess command (with JSON mode):
    claude -p "{enhanced_task_with_json_schema}" --dangerously-skip-permissions --output-format stream-json --verbose
    """
    logger.info("\n=== DIFFICULT TEST ===")
    logger.info("Command: claude -p \"{task + JSON schema}\" --dangerously-skip-permissions --output-format stream-json --verbose")
    
    try:
        result = await cc_execute(
            """Create a Python function that:
1. Calculates the Fibonacci sequence up to n terms
2. Includes proper error handling for invalid inputs
3. Has comprehensive docstring with examples
4. Returns a list of fibonacci numbers

The function should be production-ready with type hints.""",
            config=CCExecutorConfig(timeout=120),
            stream=True,
            json_mode=True  # This will add JSON schema to the prompt
        )
        
        # Verify JSON response
        if isinstance(result, dict):
            logger.success(f" Difficult test passed. Got JSON response with keys: {list(result.keys())}")
            if 'result' in result:
                logger.info(f"Code preview: {result['result'][:100]}...")
            if 'execution_uuid' in result:
                logger.info(f"Execution UUID verified: {result['execution_uuid']}")
            return True
        else:
            logger.error(f"L Expected JSON response, got: {type(result)}")
            return False
            
    except Exception as e:
        logger.error(f"L Difficult test failed: {e}")
        return False


async def test_websocket_integration():
    """
    Test WebSocket integration by calling the handler directly.
    This verifies the complete flow from cc_execute -> websocket_handler.
    """
    logger.info("\n=== WEBSOCKET INTEGRATION TEST ===")
    
    # Import WebSocket components
    try:
        from cc_executor.core.websocket_handler import execute_claude_command
        
        # Test direct WebSocket execution
        logger.info("Testing direct WebSocket command execution...")
        
        command = 'claude -p "What is the capital of France? One word answer." --dangerously-skip-permissions --output-format stream-json --verbose'
        result = await execute_claude_command(
            command=command,
            description="WebSocket integration test",
            timeout=30.0
        )
        
        if result['exit_code'] == 0:
            logger.success(f" WebSocket test passed. Got {len(result['output_lines'])} output lines")
            logger.info(f"Duration: {result['duration']:.1f}s")
            return True
        else:
            logger.error(f"L WebSocket test failed with exit code: {result['exit_code']}")
            return False
            
    except Exception as e:
        logger.error(f"L WebSocket integration test failed: {e}")
        return False


async def main():
    """Run all tests or specific test based on command line argument."""
    
    # Parse command line
    test_to_run = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    tests = {
        "simple": test_simple,
        "medium": test_medium,
        "hard": test_difficult,
        "difficult": test_difficult,  # Alias
        "websocket": test_websocket_integration
    }
    
    if test_to_run in tests:
        # Run specific test
        logger.info(f"Running {test_to_run} test only...")
        success = await tests[test_to_run]()
        return 0 if success else 1
    else:
        # Run all tests
        logger.info("Running all cc_execute usage tests...")
        
        results = []
        
        # Test 1: Simple
        results.append(await test_simple())
        await asyncio.sleep(1)  # Brief pause between tests
        
        # Test 2: Medium
        results.append(await test_medium())
        await asyncio.sleep(1)
        
        # Test 3: Difficult
        results.append(await test_difficult())
        await asyncio.sleep(1)
        
        # Test 4: WebSocket Integration
        results.append(await test_websocket_integration())
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        logger.info(f"\n=== SUMMARY ===")
        logger.info(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            logger.success(" All tests passed!")
            return 0
        else:
            logger.error(f"L {total - passed} tests failed")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)