# Python Script Template Guide

## Overview

This template provides the standard structure for Python scripts in the CC Executor project. Following this template ensures consistency, testability, and maintainability across all scripts.

## Template Structure

```python
#!/usr/bin/env python3
"""
Brief one-line description of script purpose.

Detailed description explaining:
- What problem this script solves
- Key functionality provided
- Integration points with other components
- Any important constraints or assumptions

AGENT VERIFICATION INSTRUCTIONS:
- Run this script directly to execute working_usage()
- The working_usage() function MUST pass all assertions
- This verifies the script produces expected results
- DO NOT assume the script works without running it

Third-party Documentation:
- [Relevant API/Library Name]: https://docs.example.com/
- [Another Resource]: https://reference.example.com/

Example Input:
    {
        "task": "analyze data",
        "params": {"threshold": 0.8}
    }

Expected Output:
    {
        "status": "success",
        "results": {
            "analyzed_items": 150,
            "above_threshold": 42
        }
    }
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Third-party imports
from loguru import logger
import redis

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# CRITICAL: Environment and Path Setup
# DO NOT hardcode parent directory traversals like:
#   project_root = Path(__file__).parent.parent.parent.parent  # BAD!
# Instead use find_dotenv() which searches up the directory tree:
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # Automatically finds .env file

# Get project root from .env location if needed
env_path = find_dotenv()
if env_path:
    project_root = Path(env_path).parent
else:
    project_root = Path.cwd()

# Optional: Add file logging with rotation
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / f"{Path(__file__).stem}_{{time}}.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG"
)

# Logger Agent Integration (HIGHLY RECOMMENDED)
# This enables knowledge building and error pattern learning
try:
    # Adjust path as needed for your project structure
    sys.path.insert(0, str(Path(__file__).parent / "logger_agent" / "src"))
    from agent_log_manager import get_log_manager
    LOGGER_AGENT_AVAILABLE = True
    logger.info("✓ Logger agent available for knowledge building")
except ImportError:
    LOGGER_AGENT_AVAILABLE = False
    logger.debug("Logger agent not available - running in standalone mode")

# Redis connection (optional)
try:
    redis_client = redis.Redis(decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    logger.warning("Redis not available - some features will be limited")
    redis_client = None
    REDIS_AVAILABLE = False


# ============================================
# CORE FUNCTIONS (Outside __main__ block)
# ============================================

def validate_input(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate input data structure and content.
    
    Args:
        data: Input data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["task", "params"]
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if not isinstance(data["params"], dict):
        return False, "params must be a dictionary"
        
    return True, None


async def process_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single task asynchronously.
    
    Args:
        task_data: Task configuration and parameters
        
    Returns:
        Processing results with status and metadata
    """
    logger.info(f"Processing task: {task_data.get('task', 'unknown')}")
    
    # Simulate async processing
    await asyncio.sleep(0.1)
    
    # Store intermediate results in Redis if available
    if redis_client and REDIS_AVAILABLE:
        # BREAKPOINT: Complex Redis key generation - verify format
        key = f"task:{task_data['task']}:{datetime.now().timestamp()}"
        redis_client.setex(key, 3600, json.dumps(task_data))
        logger.debug(f"Cached task data in Redis: {key}")
    
    # BREAKPOINT: Critical business logic - results generation
    # Low confidence: Ensure all required fields are present
    results = {
        "status": "success",
        "task": task_data["task"],
        "processed_at": datetime.now().isoformat(),
        "results": {
            "analyzed_items": 150,
            "above_threshold": 42
        }
    }
    
    return results


def save_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """
    Save results to a prettified JSON file.
    
    Args:
        results: Results dictionary to save
        output_dir: Optional output directory (defaults to tmp/responses)
        
    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "tmp" / "responses"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(__file__).stem}_results_{timestamp}.json"
    output_path = output_dir / filename
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    logger.info(f"Results saved to: {output_path}")
    return output_path


# ============================================
# USAGE EXAMPLE (Inside __main__ block)
# ============================================

async def run_usage_example():
    """Run usage example demonstrating script functionality."""
    logger.info("=== Running Usage Example ===")
    
    # Example input
    example_input = {
        "task": "analyze_data",
        "params": {
            "threshold": 0.8,
            "include_outliers": True
        }
    }
    
    # Validate input
    is_valid, error = validate_input(example_input)
    if not is_valid:
        logger.error(f"Input validation failed: {error}")
        return False
    
    # Process task
    try:
        results = await process_task(example_input)
        
        # Save results
        output_path = save_results(results)
        
        # Display summary
        logger.success(f"Task completed successfully!")
        logger.info(f"Results summary: {results['results']}")
        
        # Verify output matches expected format
        assert results["status"] == "success", "Expected success status"
        assert "results" in results, "Missing results field"
        assert results["results"]["analyzed_items"] > 0, "No items analyzed"
        
        return True
        
    except Exception as e:
        logger.error(f"Task processing failed: {e}")
        logger.exception("Full traceback:")
        return False


async def working_usage():
    """
    Known working examples that demonstrate script functionality.
    This function contains stable, tested code that reliably works.
    
    CRITICAL FOR AGENTS:
    - This function MUST verify that the script produces expected results
    - Use assertions to validate outputs match expectations
    - Return True only if ALL tests pass
    - This is how agents verify the script actually works
    """
    logger.info("=== Running Working Usage Examples ===")
    
    # Initialize logger agent if available
    log_manager = None
    execution_id = f"test_{datetime.now().timestamp()}"
    
    if LOGGER_AGENT_AVAILABLE:
        try:
            log_manager = await get_log_manager()
            await log_manager.log_event(
                level="INFO",
                message="Starting working_usage tests",
                script_name=Path(__file__).name,
                execution_id=execution_id,
                tags=["test", "start"]
            )
        except Exception as e:
            logger.warning(f"Failed to initialize logger agent: {e}")
    
    # Example 1: Basic functionality test
    example_input = {
        "task": "analyze_data", 
        "params": {"threshold": 0.8}
    }
    
    try:
        results = await process_task(example_input)
        save_results(results)
        
        # VERIFY EXPECTED RESULTS - THIS IS CRITICAL!
        assert results["status"] == "success", "Expected success status"
        assert "results" in results, "Missing results field"
        assert results["results"]["analyzed_items"] == 150, "Expected 150 items"
        assert results["results"]["above_threshold"] == 42, "Expected 42 above threshold"
        
        # Log success if logger agent available
        if log_manager:
            await log_manager.log_event(
                level="SUCCESS",
                message="All tests passed",
                script_name=Path(__file__).name,
                execution_id=execution_id,
                extra_data={"test_results": results},
                tags=["test", "success"]
            )
        
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        
        # If using logger agent, assess the error
        if log_manager:
            # In real usage, you would call assess_complexity MCP tool
            await log_manager.log_event(
                level="ERROR",
                message=f"Test assertion failed: {e}",
                script_name=Path(__file__).name,
                execution_id=execution_id,
                extra_data={"error_type": "AssertionError", "error_message": str(e)},
                tags=["test", "failure", "assertion"]
            )
        
        return False
    
    # Example 2: Verify specific behavior
    logger.info(f"Results: {results['results']}")
    logger.success("✓ All working_usage tests passed!")
    
    return True


async def debug_function():
    """
    Debug function for testing new features or debugging issues.
    Update this frequently while developing/debugging.
    """
    logger.info("=== Running Debug Function ===")
    
    # Current debugging focus: Test edge cases
    test_data = {
        "task": "debug_test",
        "params": {"experimental": True}
    }
    
    # Add debug code here - this is your playground
    logger.debug(f"Testing with data: {test_data}")
    
    # Example: Test Redis connection
    if redis_client:
        redis_client.set("debug_test", "active")
        value = redis_client.get("debug_test")
        logger.debug(f"Redis test result: {value}")
    
    return True


async def stress_test():
    """
    Run comprehensive stress tests loaded from JSON files.
    Tests are defined in tests/stress/fixtures/ directory.
    Reports are saved to tests/stress/reports/ directory.
    """
    logger.info("=== Running Stress Tests ===")
    
    # Look for stress test files in the tests directory
    # Get project root from environment (set during initialization)
    project_root = Path(os.environ.get('PROJECT_ROOT', Path.cwd()))
    stress_test_dir = project_root / "tests" / "stress" / "fixtures"
    if not stress_test_dir.exists():
        logger.warning(f"No stress test directory found at {stress_test_dir}")
        logger.info("Creating example stress test file...")
        
        # Create example stress test
        stress_test_dir.mkdir(parents=True, exist_ok=True)
        example_test = {
            "name": "example_stress_test",
            "description": "Example stress test configuration",
            "iterations": 10,
            "concurrent": False,
            "tests": [
                {
                    "name": "heavy_load",
                    "task": "analyze_data",
                    "params": {"threshold": 0.9, "data_size": "large"},
                    "repeat": 5
                },
                {
                    "name": "concurrent_test",
                    "task": "process_batch",
                    "params": {"batch_size": 100},
                    "concurrent_instances": 3
                }
            ]
        }
        
        example_path = stress_test_dir / "example_stress_test.json"
        with open(example_path, 'w') as f:
            json.dump(example_test, f, indent=2)
        logger.info(f"Created example at: {example_path}")
        return True
    
    # Load and run stress tests
    test_files = list(stress_test_dir.glob("*.json"))
    logger.info(f"Found {len(test_files)} stress test files")
    
    total_passed = 0
    total_failed = 0
    
    for test_file in test_files:
        logger.info(f"\n📄 Loading: {test_file.name}")
        
        try:
            with open(test_file) as f:
                test_config = json.load(f)
            
            test_name = test_config.get('name', test_file.stem)
            logger.info(f"Running: {test_name}")
            
            # Run tests based on configuration
            tests = test_config.get('tests', [])
            for test in tests:
                repeat = test.get('repeat', 1)
                for i in range(repeat):
                    try:
                        result = await process_task({
                            "task": test['task'],
                            "params": test['params']
                        })
                        logger.success(f"  ✅ {test['name']} [{i+1}/{repeat}]")
                        total_passed += 1
                    except Exception as e:
                        logger.error(f"  ❌ {test['name']} [{i+1}/{repeat}]: {e}")
                        total_failed += 1
                        
        except Exception as e:
            logger.error(f"Failed to load {test_file}: {e}")
            total_failed += 1
    
    # Summary
    logger.info(f"\n📊 Stress Test Summary:")
    logger.info(f"  Total: {total_passed + total_failed}")
    logger.info(f"  Passed: {total_passed}")
    logger.info(f"  Failed: {total_failed}")
    logger.info(f"  Success Rate: {(total_passed/(total_passed+total_failed)*100) if (total_passed+total_failed) > 0 else 0:.1f}%")
    
    return total_failed == 0


if __name__ == "__main__":
    """
    Script entry point with triple-mode execution.
    
    Usage:
        python script.py              # Runs working_usage() - stable tests
        python script.py debug        # Runs debug_function() - experimental
        python script.py stress       # Runs stress_test() - load tests from JSON
        python script.py stress.json  # Runs specific stress test file
    
    This pattern provides:
    1. Stable working examples that always run
    2. Debug playground for testing without breaking working code
    3. Comprehensive stress testing from JSON configurations
    4. Easy switching between modes via command line
    """
    import sys
    
    # Parse command line arguments
    mode = "working"
    stress_file = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "debug":
            mode = "debug"
        elif arg == "stress":
            mode = "stress"
        elif arg.endswith(".json"):
            mode = "stress"
            stress_file = arg
        else:
            mode = "working"
    
    async def main():
        """Main async entry point."""
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            success = await debug_function()
        elif mode == "stress":
            logger.info("Running in STRESS TEST mode...")
            if stress_file:
                logger.info(f"Loading specific test: {stress_file}")
                # Modify stress_test() to accept optional filename
            success = await stress_test()
        else:
            logger.info("Running in WORKING mode...")
            success = await working_usage()
        
        return success
    
    # Single asyncio.run() call
    success = asyncio.run(main())
    exit(0 if success else 1)
```

## Triple-Mode Execution Pattern

The template now includes a **triple-mode execution pattern** with three functions:

### 1. `working_usage()` - Stable Examples
- Contains known working code that demonstrates functionality
- Used for reliable testing and verification
- Should NOT be modified frequently
- Run by default when executing the script
- **Alternative name ideas**: `stable()`, `production_ready()`, or `verified_examples()`

### 2. `debug_function()` - Development Playground
- For testing new features or debugging issues
- Update frequently during development
- Isolated from stable code to prevent breaking working examples
- Run with `python script.py debug`

### 3. `stress_test()` - Comprehensive Testing
- Loads test configurations from JSON files
- Supports repeated tests, concurrent execution, and parameterized scenarios
- Tests stored in `tests/stress/fixtures/` directory
- Reports saved to `tests/stress/reports/` directory
- Creates example test file if none exist
- Run with `python script.py stress`

### Benefits of This Pattern
- **Separation of Concerns**: Stable, debug, and stress test code are isolated
- **Quick Testing**: Easy to switch between modes via command line
- **No Test File Proliferation**: All test logic contained in the main script
- **JSON-Driven Tests**: Complex test scenarios defined declaratively
- **Built-in Documentation**: Working examples serve as live documentation
- **Progressive Testing**: From simple (working) to complex (stress)

### Usage Examples
```bash
# Run stable working examples (default)
python my_script.py

# Run debug/experimental code
python my_script.py debug

# Run all stress tests from JSON files
python my_script.py stress

# Run specific stress test file
python my_script.py specific_test.json
```

### Stress Test JSON Format
```json
{
  "name": "example_stress_test",
  "description": "Example stress test configuration",
  "iterations": 10,
  "concurrent": false,
  "tests": [
    {
      "name": "heavy_load",
      "task": "analyze_data",
      "params": {"threshold": 0.9, "data_size": "large"},
      "repeat": 5
    },
    {
      "name": "concurrent_test", 
      "task": "process_batch",
      "params": {"batch_size": 100},
      "concurrent_instances": 3
    }
  ]
}

## Key Requirements Checklist

### Structure Requirements
- [ ] Shebang line: `#!/usr/bin/env python3`
- [ ] Comprehensive docstring with purpose, examples, and links
- [ ] **AGENT VERIFICATION INSTRUCTIONS in docstring**
- [ ] All imports at the top, organized by type
- [ ] Logger configuration immediately after imports
- [ ] Optional service connections (Redis, ArangoDB) with availability checks
- [ ] All core functions OUTSIDE the `if __name__ == "__main__"` block
- [ ] `working_usage()` function with stable examples (or alternative name: `stable()`)
- [ ] **working_usage() MUST include assertions to verify expected results**
- [ ] `debug_function()` for experimental code
- [ ] `stress_test()` for JSON-driven comprehensive testing
- [ ] Mode selection logic supporting all three modes
- [ ] Only ONE `asyncio.run()` call in the entire script

### Documentation Requirements
- [ ] Clear one-line purpose description
- [ ] Detailed explanation of functionality
- [ ] Links to third-party documentation
- [ ] Real-world input example (not abstract)
- [ ] Expected output example with actual values
- [ ] Function docstrings with Args/Returns sections
- [ ] Breakpoint comments where debugging may be needed (high complexity/low confidence)

### Code Quality Requirements
- [ ] Type hints on all function parameters and returns
- [ ] Input validation with clear error messages
- [ ] Proper error handling with logger.error/exception
- [ ] Results saved to `tmp/responses/` with timestamp
- [ ] JSON output prettified with `indent=2`
- [ ] Assertions to validate expected behavior
- [ ] Exit codes: 0 for success, 1 for failure
- [ ] **NO hardcoded parent directory traversals** - use `find_dotenv()`

### Logging Requirements
- [ ] Use loguru instead of print statements
- [ ] Remove default handler and configure custom format
- [ ] Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Include function context in log format
- [ ] Optional file logging with rotation

### Data Storage Requirements
- [ ] Redis for quick/simple key-value storage
- [ ] Check Redis availability before use
- [ ] Use expiring keys (setex) for temporary data
- [ ] ArangoDB for complex graph/document storage
- [ ] Always handle connection failures gracefully

## Breakpoint Comments Pattern

### When to Add Breakpoint Comments

Add `# BREAKPOINT:` comments where debugging might be needed:

1. **High Complexity Code**
   ```python
   # BREAKPOINT: Complex calculation - verify algorithm correctness
   weighted_score = sum(
       item['value'] * item['weight'] / total_weight
       for item in items
       if item['active']
   ) * normalization_factor
   ```

2. **Low Confidence Areas**
   ```python
   # BREAKPOINT: Uncertain about edge case handling
   # TODO: What happens if all items are inactive?
   if not active_items:
       return default_score
   ```

3. **Critical Business Logic**
   ```python
   # BREAKPOINT: Payment calculation - must be exact
   final_amount = base_price * (1 + tax_rate) - discount
   ```

4. **External Service Integration**
   ```python
   # BREAKPOINT: API response parsing - structure may vary
   try:
       data = response.json()['data']['attributes']
   except KeyError:
       logger.error("Unexpected API response structure")
   ```

5. **Concurrent Operations**
   ```python
   # BREAKPOINT: Race condition possible - verify thread safety
   async with self.lock:
       self.counter += 1
   ```

### When NOT to Add Breakpoints

- Simple variable assignments
- Standard library calls with clear behavior
- Well-tested utility functions
- Straightforward data structure access

### Breakpoint Format

```python
# BREAKPOINT: [Context] - [What to verify]
# Optional: Additional notes about concerns
```

## Common Patterns

### Pattern 1: WebSocket Handler Script
```python
async def handle_websocket_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Process WebSocket messages with proper error handling."""
    # Implementation here
    pass

# In __main__:
if __name__ == "__main__":
    # For WebSocket testing, create a simple test client
    async def test_websocket():
        # Test implementation
        pass
    
    asyncio.run(test_websocket())
```

### Pattern 2: Data Processing Script
```python
def process_csv_data(filepath: Path) -> pd.DataFrame:
    """Process CSV data with validation and cleaning."""
    # Implementation here
    pass

def generate_report(data: pd.DataFrame) -> Dict[str, Any]:
    """Generate analysis report from processed data."""
    # Implementation here
    pass

# In __main__:
if __name__ == "__main__":
    # Process sample data and verify results
    sample_file = Path("sample_data.csv")
    processed = process_csv_data(sample_file)
    report = generate_report(processed)
    save_results(report)
```

### Pattern 3: CLI Tool Script
```python
import typer

app = typer.Typer()

@app.command()
def process(input_file: str, output_dir: str = "./output"):
    """Process input file and save results."""
    # Implementation here
    pass

# In __main__:
if __name__ == "__main__":
    # Run CLI tests without actually calling app()
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["process", "test.txt"])
    assert result.exit_code == 0
```

## Anti-Patterns to Avoid

### ❌ DON'T: Mix logic with tests
```python
if __name__ == "__main__":
    def process_data(data):  # Don't define functions here!
        return data * 2
    
    result = process_data(5)
```

### ✅ DO: Separate concerns
```python
def process_data(data: int) -> int:
    """Process data by doubling it."""
    return data * 2

if __name__ == "__main__":
    # Only testing/usage here
    result = process_data(5)
    assert result == 10
```

### ❌ DON'T: Multiple asyncio.run() calls
```python
if __name__ == "__main__":
    asyncio.run(task1())  # First call
    asyncio.run(task2())  # Second call - BAD!
```

### ✅ DO: Single entry point
```python
async def main():
    """Main entry point for all async operations."""
    await task1()
    await task2()

if __name__ == "__main__":
    asyncio.run(main())  # Single call
```

### ❌ DON'T: Print statements for output
```python
print("Processing complete")
print(f"Results: {results}")
```

### ✅ DO: Use logger with appropriate levels
```python
logger.info("Processing complete")
logger.success(f"Results: {results}")
```

## Code Review Checklist

When reviewing scripts, verify:

1. **Structure Compliance**
   - Functions outside `__main__` block?
   - Single `asyncio.run()` call?
   - Proper import organization?

2. **Documentation Quality**
   - Clear purpose stated?
   - Real examples provided?
   - Third-party links included?

3. **Error Handling**
   - All exceptions caught and logged?
   - Graceful degradation for missing services?
   - Meaningful error messages?

4. **Testing Coverage**
   - Usage examples actually run?
   - Assertions validate behavior?
   - Results saved for verification?

5. **Performance Considerations**
   - Async operations where beneficial?
   - Redis caching for repeated operations?
   - Proper resource cleanup?

## Example Review Comment

```markdown
## Code Review: websocket_handler.py

✅ **Strengths:**
- Clear docstring with purpose and examples
- Functions properly separated from __main__ block
- Single asyncio.run() call
- Comprehensive error handling

🔧 **Improvements Needed:**
- [ ] Add Redis caching for timeout calculations
- [ ] Save raw WebSocket messages to tmp/responses/
- [ ] Add assertions to validate message format
- [ ] Include third-party WebSocket documentation link

📝 **Specific Changes:**
Line 145: Replace `print()` with `logger.info()`
Line 203: Add type hint for return value
Line 567: Extract this function outside __main__ block
```

## Summary

This template ensures that all Python scripts in the project follow consistent patterns for:
- Structure and organization
- Documentation and examples
- Error handling and logging
- Testing and validation
- Code review standards

Following this template makes scripts more maintainable, testable, and easier to review.