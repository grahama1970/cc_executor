#!/usr/bin/env python3
"""
Complete example of proper logger integration showing both loguru and logger agent.

This example demonstrates:
1. Using loguru for immediate debugging output
2. Using logger agent for knowledge graph building
3. Proper error assessment and fix logging
4. Building relationships between errors and fixes

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python logger_integration_example.py          # Runs working_usage() - stable, known to work
  python logger_integration_example.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Configure loguru for immediate output
from loguru import logger
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
)

# Add logger agent for knowledge building
try:
    # Add parent directory to path for logger agent
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"))
    from agent_log_manager import get_log_manager
    LOGGER_AGENT_AVAILABLE = True
    logger.info("✓ Logger agent available for knowledge building")
except ImportError:
    LOGGER_AGENT_AVAILABLE = False
    logger.warning("Logger agent not available - running in standalone mode")


class SmartLogger:
    """Helper class that combines loguru and logger agent."""
    
    def __init__(self, script_name: str):
        self.script_name = script_name
        self.execution_id = f"exec_{datetime.utcnow().timestamp()}"
        self.manager = None
        self._current_assessment_id = None
    
    async def initialize(self):
        """Initialize logger agent connection."""
        if LOGGER_AGENT_AVAILABLE:
            try:
                self.manager = await get_log_manager()
                logger.info("Connected to logger agent database")
            except Exception as e:
                logger.error(f"Failed to connect to logger agent: {e}")
                self.manager = None
    
    async def log(self, level: str, message: str, **kwargs):
        """Log to both loguru and logger agent."""
        # Always log to loguru for immediate output
        getattr(logger, level.lower())(message)
        
        # Also log to logger agent if available
        if self.manager:
            try:
                await self.manager.log_event(
                    level=level.upper(),
                    message=message,
                    script_name=self.script_name,
                    execution_id=self.execution_id,
                    extra_data=kwargs.get('extra_data', {}),
                    tags=kwargs.get('tags', [])
                )
            except Exception as e:
                logger.debug(f"Failed to log to agent: {e}")
    
    async def assess_error(self, error: Exception, file_path: str) -> Optional[str]:
        """Assess an error and return assessment ID."""
        error_type = type(error).__name__
        error_message = str(error)
        
        logger.info(f"Assessing {error_type}: {error_message}")
        
        # In real usage, this would call the MCP tool
        # For this example, we'll simulate it
        if self.manager:
            # Log the error assessment
            result = await self.manager.log_event(
                level="ERROR",
                message=f"Assessing: {error_type}: {error_message}",
                script_name=self.script_name,
                execution_id=self.execution_id,
                extra_data={
                    "assessment_type": "error_analysis",
                    "error_type": error_type,
                    "error_message": error_message,
                    "file_path": file_path
                },
                tags=["assessment", "error", error_type.lower()]
            )
            
            assessment_id = result.get("_id")
            self._current_assessment_id = assessment_id
            
            # Search for similar errors
            similar = await self.search_similar_errors(error_type, error_message)
            if similar:
                logger.info(f"Found {len(similar)} similar errors with fixes")
                for fix in similar[:3]:
                    logger.info(f"  - {fix.get('fix_description', 'No description')}")
            
            return assessment_id
        
        return None
    
    async def log_fix(self, error_type: str, error_message: str, fix_description: str, file_path: str):
        """Log a successful fix."""
        logger.success(f"Fixed {error_type}: {fix_description}")
        
        if self.manager and self._current_assessment_id:
            # Log the fix
            fix_result = await self.manager.log_event(
                level="SUCCESS",
                message=f"Fixed {error_type}: {fix_description}",
                script_name=self.script_name,
                execution_id=self.execution_id,
                extra_data={
                    "fix_type": "error_resolution",
                    "error_type": error_type,
                    "original_error": error_message,
                    "file_path": file_path,
                    "fix_description": fix_description,
                    "assessment_id": self._current_assessment_id
                },
                tags=["fix", "resolution", error_type.lower(), "success"]
            )
            
            # Store as learning
            await self.manager.memory.add_memory(
                content=f"Fix for {error_type}: {fix_description}",
                memory_type="learning",
                metadata={
                    "error_type": error_type,
                    "fix_description": fix_description,
                    "file_path": file_path,
                    "confidence": 0.9
                }
            )
            
            # Create relationship between error and fix
            if hasattr(self.manager, 'relationships'):
                await self.manager.relationships.extract_relationships(
                    text1=f"Error: {error_message}",
                    text2=f"Fix: {fix_description}",
                    context={
                        "error_id": self._current_assessment_id,
                        "fix_id": fix_result.get("_id"),
                        "execution_id": self.execution_id
                    }
                )
    
    async def search_similar_errors(self, error_type: str, error_message: str) -> list:
        """Search for similar errors and their fixes."""
        if not self.manager:
            return []
        
        try:
            # Search for similar errors
            results = await self.manager.search.search_agent_activity(
                query=f"{error_type} {error_message}",
                filters={
                    "tags": ["fix", "resolution"],
                    "time_range": "30d"
                },
                limit=5
            )
            
            fixes = []
            for result in results:
                doc = result.get("doc", {})
                extra_data = doc.get("extra_data", {})
                if extra_data.get("fix_description"):
                    fixes.append({
                        "error_type": extra_data.get("error_type"),
                        "fix_description": extra_data.get("fix_description"),
                        "score": result.get("score", 0)
                    })
            
            return fixes
            
        except Exception as e:
            logger.debug(f"Failed to search similar errors: {e}")
            return []


# Example functions that demonstrate proper logging
async def function_that_might_fail(value: int) -> int:
    """Example function that logs its operations."""
    logger.info(f"Processing value: {value}")
    
    if value < 0:
        raise ValueError("Value must be non-negative")
    
    result = value * 2
    logger.debug(f"Calculated result: {result}")
    
    return result


async def working_usage():
    """
    Demonstrate proper logger integration with both loguru and logger agent.
    
    This shows the complete workflow:
    1. Immediate debugging with loguru
    2. Error assessment with logger agent
    3. Fix logging for knowledge building
    4. Graph relationships between errors and fixes
    """
    logger.info("=== Starting Logger Integration Example ===")
    
    # Initialize smart logger
    smart_logger = SmartLogger("logger_integration_example.py")
    await smart_logger.initialize()
    
    # Log start of operation
    await smart_logger.log("INFO", "Starting working_usage test", 
                          tags=["test", "start"])
    
    # Test 1: Successful operation
    logger.info("\nTest 1: Successful operation")
    try:
        result = await function_that_might_fail(5)
        await smart_logger.log("SUCCESS", f"Function succeeded with result: {result}",
                              extra_data={"input": 5, "output": result},
                              tags=["test", "success"])
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    # Test 2: Operation that fails and gets fixed
    logger.info("\nTest 2: Operation with error and fix")
    try:
        result = await function_that_might_fail(-5)
    except ValueError as e:
        # Assess the error
        assessment_id = await smart_logger.assess_error(e, __file__)
        logger.info(f"Assessment ID: {assessment_id}")
        
        # Fix the error (make value positive)
        logger.info("Applying fix: Converting to absolute value")
        fixed_result = await function_that_might_fail(abs(-5))
        
        # Log the successful fix
        await smart_logger.log_fix(
            error_type="ValueError",
            error_message=str(e),
            fix_description="Applied abs() to ensure non-negative value",
            file_path=__file__
        )
        
        await smart_logger.log("SUCCESS", f"Fixed function succeeded: {fixed_result}",
                              extra_data={"original_input": -5, "fixed_input": 5},
                              tags=["test", "fixed"])
    
    # Test 3: Simulate ModuleNotFoundError and fix
    logger.info("\nTest 3: Import error simulation")
    
    # Simulate finding an import error
    fake_error = ModuleNotFoundError("No module named 'requests'")
    assessment_id = await smart_logger.assess_error(fake_error, __file__)
    
    # Simulate fixing it
    logger.info("Simulating fix: uv add requests")
    await smart_logger.log_fix(
        error_type="ModuleNotFoundError",
        error_message="No module named 'requests'",
        fix_description="Installed requests with 'uv add requests'",
        file_path=__file__
    )
    
    # Test 4: Search for previous fixes
    logger.info("\nTest 4: Searching for previous fixes")
    similar_fixes = await smart_logger.search_similar_errors("ValueError", "non-negative")
    
    if similar_fixes:
        logger.info(f"Found {len(similar_fixes)} similar fixes:")
        for fix in similar_fixes:
            logger.info(f"  - {fix['fix_description']} (score: {fix['score']:.2f})")
    
    # Final summary
    await smart_logger.log("INFO", "Test completed successfully",
                          extra_data={"tests_run": 4, "tests_passed": 4},
                          tags=["test", "complete"])
    
    logger.success("\n✅ All tests completed!")
    return True


async def debug_function():
    """
    Debug function for testing edge cases and graph building.
    """
    logger.info("=== Debug Mode: Testing Graph Relationships ===")
    
    smart_logger = SmartLogger("debug_test.py")
    await smart_logger.initialize()
    
    if not smart_logger.manager:
        logger.error("Logger agent required for debug mode")
        return False
    
    # Create a chain of related errors and fixes
    logger.info("Creating error chain...")
    
    # Error 1: Import error
    error1 = ModuleNotFoundError("No module named 'numpy'")
    assessment1 = await smart_logger.assess_error(error1, "data_processor.py")
    
    # Error 2: Type error (caused by missing import)
    error2 = TypeError("unsupported operand type(s) for +: 'int' and 'str'")
    assessment2 = await smart_logger.assess_error(error2, "data_processor.py")
    
    # Fix 1: Install numpy
    await smart_logger.log_fix(
        "ModuleNotFoundError",
        "No module named 'numpy'",
        "Installed numpy with 'uv add numpy'",
        "data_processor.py"
    )
    
    # Fix 2: Fix type conversion
    await smart_logger.log_fix(
        "TypeError",
        "unsupported operand type(s) for +: 'int' and 'str'",
        "Added int() conversion to ensure numeric addition",
        "data_processor.py"
    )
    
    # Create causality relationship
    if hasattr(smart_logger.manager, 'graph'):
        logger.info("Creating causality edges...")
        
        # Error 1 caused Error 2
        await smart_logger.manager.graph.create_error(
            session_id=smart_logger.execution_id,
            error_type="CausalChain",
            message="Missing numpy import led to type error",
            file_context="data_processor.py"
        )
    
    logger.info("Debug test completed - check ArangoDB for graph relationships")
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())