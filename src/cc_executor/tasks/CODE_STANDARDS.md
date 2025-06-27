# Shared Code Standards

## Overview
These standards apply to ALL Python code in cc_executor. Orchestrators check for these, executors implement them.

## File Structure Requirements

### 1. File Size Limit
- **Maximum 500 lines per file**
- If approaching limit, split into logical modules
- Each module should have a single, clear purpose

### 2. Required File Header
Every Python file MUST start with:

```python
#!/usr/bin/env python3
"""
Brief description of what this module does.

Longer explanation if needed, describing the module's purpose,
main components, and how it fits into the larger system.

Third-party Documentation:
- Relevant Library: https://docs.library.com/
- Protocol Spec: https://example.com/spec
- API Reference: https://api.example.com/docs

Example Input:
    Description of typical input this module processes
    ```
    {"command": "echo hello", "timeout": 30}
    ```

Expected Output:
    Description of what output to expect
    ```
    {"status": "completed", "output": "hello\n", "exit_code": 0}
    ```
"""
```

### 3. Standard Imports
```python
# Standard library
import asyncio
import json
from typing import Dict, Any, Optional

# Third-party
from loguru import logger  # ALWAYS use loguru for logging

# Local imports
from .models import ProcessResult
```

### 4. Usage Function (MANDATORY)
Every module MUST have a runnable usage example:

```python
if __name__ == "__main__":
    """
    Usage example with real-world data that demonstrates the module works.
    This serves as both documentation and a quick test.
    """
    # Example with real data
    async def test_usage():
        manager = ProcessManager()
        result = await manager.execute("echo 'Hello, World!'", timeout=5)
        print(f"Output: {result.output}")
        print(f"Exit code: {result.exit_code}")
        
        # Verify expected behavior
        assert result.exit_code == 0, f"Expected 0, got {result.exit_code}"
        assert "Hello, World!" in result.output, "Output missing expected text"
        print("✓ All checks passed")
    
    asyncio.run(test_usage())
```

## Code Style Rules

### 1. Type Hints
- All function parameters and returns MUST have type hints
- Use `Optional[T]` instead of `T | None` for clarity

```python
# Good
async def execute_command(
    command: str,
    timeout: Optional[float] = None
) -> ProcessResult:
    ...

# Bad
async def execute_command(command, timeout=None):
    ...
```

### 2. Error Handling
- Use specific exceptions, not bare `except:`
- Always log errors with context
- Clean up resources in finally blocks

```python
# Good
try:
    result = await process.communicate(timeout=timeout)
except asyncio.TimeoutError:
    logger.error(f"Command timed out after {timeout}s: {command}")
    raise
finally:
    if process.returncode is None:
        process.terminate()
        await process.wait()
```

### 3. Logging Standards
- Import: `from loguru import logger`
- Use appropriate levels:
  - `logger.debug()` - Detailed diagnostic info
  - `logger.info()` - Normal flow
  - `logger.warning()` - Recoverable issues
  - `logger.error()` - Errors that need attention

### 4. Constants
- Define at module level in UPPER_CASE
- Include units in name when applicable

```python
MAX_BUFFER_SIZE_BYTES = 1024 * 1024  # 1MB
DEFAULT_TIMEOUT_SECONDS = 30
MAX_CONCURRENT_SESSIONS = 100
```

## Verification Commands

### For Executors (Before Committing)
```bash
# Check file meets standards
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/check_file_rules.py path/to/file.py

# Run usage function
python path/to/file.py

# Verify no hallucination
MARKER="CODE_STANDARDS_$(date +%Y%m%d_%H%M%S)"
echo "$MARKER: Verified file meets standards"
```

### For Orchestrators (When Reviewing)
Add these to your fix verification:

```json
{
  "id": 8,
  "severity": "major",
  "file": "core/new_module.py",
  "issue": "Module lacks required documentation and usage function",
  "fix": "Add header with third-party links, example input/output, and runnable usage function",
  "verification": "python new_module.py should run successfully and show example usage"
}
```

## Common Violations to Check

### 1. Missing Usage Function
```bash
# Check for __main__ block
grep -L 'if __name__ == "__main__"' *.py
```

### 2. File Too Long
```bash
# Find files over 500 lines
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 500 {print $2, $1}'
```

### 3. Missing Type Hints
```bash
# Find functions without return type hints
grep -E "^def |^async def " *.py | grep -v "\->"
```

### 4. Not Using Loguru
```bash
# Find files using print() or logging instead of loguru
grep -E "(^import logging|print\()" *.py
```

## Example Compliant Module

```python
#!/usr/bin/env python3
"""
Buffer management for streaming process output.

Handles buffering of process output with size limits and line count
restrictions to prevent memory exhaustion during long-running processes.

Third-party Documentation:
- Python asyncio streams: https://docs.python.org/3/library/asyncio-stream.html
- Memory profiling: https://pypi.org/project/memory-profiler/

Example Input:
    Stream of lines from a process that outputs continuously:
    ```
    Line 1: Processing item A
    Line 2: Processing item B
    ... (continues indefinitely)
    ```

Expected Output:
    Buffered output with limits enforced:
    ```
    {
        "lines": ["Line 1: Processing item A", ...],
        "total_lines": 1000,
        "dropped_lines": 0,
        "buffer_full": false
    }
    ```
"""

from typing import List, Optional
from loguru import logger

MAX_BUFFER_LINES = 1000
MAX_BUFFER_SIZE_BYTES = 1024 * 1024  # 1MB


class OutputBuffer:
    """Manages buffered output with size limits."""
    
    def __init__(
        self,
        max_lines: int = MAX_BUFFER_LINES,
        max_size: int = MAX_BUFFER_SIZE_BYTES
    ) -> None:
        self.lines: List[str] = []
        self.total_size: int = 0
        self.dropped_lines: int = 0
        self.max_lines = max_lines
        self.max_size = max_size
        
    def add_line(self, line: str) -> bool:
        """Add a line to the buffer if within limits."""
        line_size = len(line.encode('utf-8'))
        
        if (len(self.lines) < self.max_lines and 
            self.total_size + line_size < self.max_size):
            self.lines.append(line)
            self.total_size += line_size
            return True
        else:
            self.dropped_lines += 1
            if self.dropped_lines == 1:
                logger.warning(f"Buffer full, dropping lines (max_lines={self.max_lines}, max_size={self.max_size})")
            return False


if __name__ == "__main__":
    """Test buffer with simulated output."""
    buffer = OutputBuffer(max_lines=10, max_size=500)
    
    # Simulate process output
    for i in range(20):
        line = f"Line {i}: " + "x" * 40
        added = buffer.add_line(line)
        if not added and buffer.dropped_lines == 1:
            print(f"Buffer became full at line {i}")
    
    print(f"Buffered lines: {len(buffer.lines)}")
    print(f"Dropped lines: {buffer.dropped_lines}")
    print(f"Total size: {buffer.total_size} bytes")
    
    # Verify behavior
    assert len(buffer.lines) == 10, f"Expected 10 lines, got {len(buffer.lines)}"
    assert buffer.dropped_lines == 10, f"Expected 10 dropped, got {buffer.dropped_lines}"
    print("✓ Buffer limits working correctly")
```

## Enforcement

1. **Executors**: Must follow these standards when implementing fixes
2. **Orchestrators**: Must create fix tasks for any violations found
3. **CI/CD**: Can run check_file_rules.py on all Python files

## Quick Reference Checklist

- [ ] File under 500 lines
- [ ] Documentation header with third-party links
- [ ] Example input/output in header
- [ ] Usage function that runs with real data
- [ ] Type hints on all functions
- [ ] Using loguru for logging
- [ ] Error handling with cleanup
- [ ] Constants defined properly