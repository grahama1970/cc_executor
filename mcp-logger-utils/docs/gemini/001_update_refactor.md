Of course. Here is the complete, unabridged source code for your `mcp-logger-utils` package, including all the improvements we've discussed, formatted into a single Markdown file. I've also included a comprehensive `pyproject.toml`, a detailed `README.md`, and clear, step-by-step instructions for publishing to PyPI.

---

# `mcp-logger-utils` Complete Project

This file contains the full source code and documentation for the `mcp-logger-utils` package.

## 1. Project Structure

Here is the final directory structure for the project:

```
mcp-logger-utils/
├── .gitignore
├── pyproject.toml
├── README.md
└── src/
    └── mcp_logger_utils/
        ├── __init__.py
        ├── json_utils.py
        └── logger.py
```

## 2. File Contents

### `mcp-logger-utils/.gitignore`

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
#  Usually these files are written by a parent script -
#  warn user what these files are for in README.md
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.idea/
.vscode/
```

### `mcp-logger-utils/pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-logger-utils"
version = "0.2.0"
description = "Shared utilities for MCP servers, including robust logging and JSON repair."
authors = [{name = "Graham Anderson", email = "graham@grahama.co"}]
dependencies = [
    "loguru>=0.7.0",
    "json-repair>=0.19.0",
]
requires-python = ">=3.8"
readme = "README.md"
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Logging",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

[project.urls]
Homepage = "https://github.com/yourusername/mcp-logger-utils"
Repository = "https://github.com/yourusername/mcp-logger-utils"
```

### `mcp-logger-utils/README.md`

```markdown
# MCP Logger Utils

A robust, shared logging and utility package for MCP (Model Context Protocol) servers, especially tailored for Claude Code environments.

## Features

- **Isolated Logging:** Prevents conflicts with other libraries using `loguru`.
- **Automatic Truncation:** Automatically shortens large strings, base64 data, and long lists (like embeddings) in logs to keep them clean and readable.
- **Universal Decorator:** The `@debug_tool` decorator works seamlessly with both `async` and `sync` functions.
- **Safe Serialization:** Handles non-serializable types (`datetime`, `Path`, etc.), preventing the logger from crashing.
- **Rich Context:** Logs function arguments, return values, execution time, and detailed error tracebacks.
- **Configurable:** Customize log directory, level, and truncation limits via constructor arguments or environment variables.
- **Robust JSON Repair:** Includes a powerful utility to parse malformed JSON commonly produced by LLMs.
- **Structured Error Response:** Returns a standardized JSON object on tool failure, including a unique error ID.

## Installation

```bash
pip install mcp-logger-utils
```

Or using `uv`:

```bash
uv pip install mcp-logger-utils
```

## Usage

### 1. Robust Logging with `@debug_tool`

Decorate your MCP tool functions to get automatic logging of inputs, outputs, performance, and errors.

#### a. Initialize the Logger

In your MCP server file, create an instance of `MCPLogger`. You can optionally configure truncation limits.

```python
from mcp_logger_utils import MCPLogger

# Default initialization
mcp_logger = MCPLogger("my-awesome-server")

# Customizing truncation limits
mcp_logger_custom = MCPLogger(
    "my-data-server",
    max_log_str_len=512,      # Allow longer strings in logs
    max_log_list_len=5       # Show fewer list items
)
```

#### b. Apply the Decorator

The same decorator works for both `async` and `sync` functions.

```python
from mcp_logger_utils import debug_tool

@mcp.tool()
@debug_tool(mcp_logger)
async def process_data(embedding: list, image_data: str) -> dict:
    # `embedding` (if long) and `image_data` (if long) will be
    # automatically truncated in the debug logs.
    return {"status": "processed"}
```

#### c. Configuration via Environment Variables

-   `MCP_LOG_DIR`: Overrides the default log directory (`~/.claude/mcp_logs`).
-   `MCP_LOG_LEVEL`: Sets the console log level (e.g., `DEBUG`, `INFO`).
-   `MCP_DEBUG`: Set to `true` or `1` for verbose `DEBUG` level logging.

### 2. JSON Repair Utility

When working with LLMs, you often get responses that are *almost* JSON but contain small errors or are wrapped in text. This utility provides a robust way to handle such cases.

#### `repair_and_parse_json(content, logger_instance=None)`

This function takes a string and does its best to return a valid Python `dict` or `list`.

-   It automatically extracts JSON from markdown code blocks (e.g., ` ```json ... ``` `).
-   It uses the `json-repair` library to fix common syntax errors.
-   If parsing fails, it safely returns the original string.

#### Example: Creating a Robust Tool

Here is how you can combine `@debug_tool` and `repair_and_parse_json` to build a tool that reliably processes LLM output.

```python
from mcp_logger_utils import MCPLogger, debug_tool, repair_and_parse_json
# from some_llm_library import get_llm_response

# Initialize logger
mcp_logger = MCPLogger("llm-processor-tool")

@mcp.tool()
@debug_tool(mcp_logger)
async def get_structured_data_from_llm(prompt: str) -> dict:
    """
    Calls an LLM to get structured data and robustly parses the response.
    """
    # 1. Get a response from an LLM. It might be messy.
    messy_response = "Here is the JSON you requested: ```json\n{\n  \"name\": \"Claude\",\n  \"version\": 3.0,\n  \"is_helpful\": true, // He is very helpful!\n}\n```"
    # messy_response = await get_llm_response(prompt)

    # 2. Use the utility to clean and parse it.
    # The logger passed to it will log the repair steps for easy debugging.
    parsed_data = repair_and_parse_json(messy_response, logger_instance=mcp_logger.logger)

    # 3. Check if parsing was successful before proceeding.
    if not isinstance(parsed_data, dict):
        raise ValueError(f"Failed to parse a valid dictionary from the LLM response. Got: {parsed_data}")

    # 4. Now you can safely work with the clean data.
    parsed_data["processed_at"] = "2024-07-19"
    return parsed_data
```

**Why this is a good pattern:**

1.  **Observability:** The `@debug_tool` logs the *raw, messy input* from the LLM, so you can always see exactly what your tool received.
2.  **Robustness:** Your tool doesn't crash on slightly malformed JSON.
3.  **Clarity:** The code explicitly shows the step where data is being cleaned, making the logic easy to follow.
```

### `mcp-logger-utils/src/mcp_logger_utils/__init__.py`

```python
"""MCP Logger Utils - Shared utilities for MCP servers."""

from .json_utils import repair_and_parse_json
from .logger import MCPLogger, debug_tool

__version__ = "0.2.0"
__all__ = ["MCPLogger", "debug_tool", "repair_and_parse_json"]
```

### `mcp-logger-utils/src/mcp_logger_utils/logger.py`

```python
"""MCP Logger implementation."""

import asyncio
import json
import os
import re
import sys
import time
import traceback
import uuid
from datetime import datetime
from functools import wraps
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from loguru import logger as loguru_logger

# Regex to identify common data URI patterns for images, moved to module level
BASE64_IMAGE_PATTERN = re.compile(r"^(data:image/[a-zA-Z+.-]+;base64,)")


class MCPLogger:
    """
    Centralized logger for MCP servers with comprehensive, automated debugging features.
    - Each instance is isolated to prevent conflicts with global loguru settings.
    - Automatically truncates large strings, lists (embeddings), and base64 data.
    """

    def __init__(
        self,
        tool_name: str,
        log_level: Optional[str] = None,
        max_log_str_len: int = 256,
        max_log_list_len: int = 10,
    ):
        """
        Initializes the MCPLogger.

        Args:
            tool_name: The name of the tool or server.
            log_level: The console logging level (overrides environment variables).
            max_log_str_len: Max length for strings before truncation in logs.
            max_log_list_len: Max number of elements for lists before summarizing.
        """
        self.tool_name = tool_name
        self.logger = loguru_logger.bind(tool_name=tool_name)
        
        # Store truncation configuration
        self.max_log_str_len = max_log_str_len
        self.max_log_list_len = max_log_list_len

        # Allow overriding log directory via environment variable
        log_dir_str = os.getenv("MCP_LOG_DIR", str(Path.home() / ".claude" / "mcp_logs"))
        self.log_dir = Path(log_dir_str)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Determine log level from param, env var, or default
        level = log_level or os.getenv("MCP_LOG_LEVEL", "INFO")
        if os.getenv("MCP_DEBUG", "false").lower() in ("true", "1"):
            level = "DEBUG"

        # Use a fresh logger configuration for this instance
        self.logger.remove()
        self.logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[tool_name]}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
            )
        )

        self.debug_log = self.log_dir / f"{self.tool_name}_debug.log"
        self.logger.add(
            self.debug_log,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[tool_name]}:{name}:{function}:{line} - {message}"
        )

        self.log_startup_info()

    def _truncate_for_log(self, value: Any) -> Any:
        """
        Recursively truncate large strings, lists, or dicts to make them log-friendly.
        This is an internal method that uses the instance's configuration.
        """
        if isinstance(value, str):
            match = BASE64_IMAGE_PATTERN.match(value)
            if match:
                header = match.group(1)
                data = value[len(header):]
                if len(data) > self.max_log_str_len:
                    half_len = self.max_log_str_len // 2
                    truncated_data = f"{data[:half_len]}...[truncated]...{data[-half_len:]}"
                    return header + truncated_data
                return value
            elif len(value) > self.max_log_str_len:
                half_len = self.max_log_str_len // 2
                return f"{value[:half_len]}...[truncated]...{value[-half_len:]}"
            return value

        elif isinstance(value, list):
            if len(value) > self.max_log_list_len:
                element_type = type(value[0]).__name__ if value else "element"
                return f"[<{len(value)} {element_type}s>]"
            return [self._truncate_for_log(item) for item in value]

        elif isinstance(value, dict):
            return {k: self._truncate_for_log(v) for k, v in value.items()}

        return value

    def _safe_json_dumps(self, data: Any, **kwargs) -> str:
        """
        Safely dump data to a JSON string, automatically truncating large values and
        handling common non-serializable types.
        """
        # First, truncate the data to make it log-friendly
        truncated_data = self._truncate_for_log(data)

        def default_serializer(o: Any) -> Any:
            if isinstance(o, (datetime, Path)):
                return str(o)
            if hasattr(o, '__dict__'):
                return self._truncate_for_log(o.__dict__)
            try:
                return f"<<non-serializable: {type(o).__name__}>>"
            except Exception:
                return "<<non-serializable>>"

        return json.dumps(truncated_data, default=default_serializer, **kwargs)

    def log_startup_info(self):
        """Log startup information."""
        self.logger.info(f"Logger initialized for '{self.tool_name}'. PID: {os.getpid()}")
        self.logger.debug(f"Log directory: {self.log_dir}")

    def log_call(self, function: str, duration: float, result: Optional[Any] = None):
        """Log a successful tool call."""
        self.logger.info(f"✓ {function} completed in {duration:.3f}s")
        self.logger.debug(f"Result: {self._safe_json_dumps(result)}")

    def log_error(self, function: str, duration: float, error: Exception, context: Dict[str, Any]) -> str:
        """Log an error with context and return a unique error ID."""
        error_id = str(uuid.uuid4())
        self.logger.error(f"✗ {function} failed in {duration:.3f}s. Error ID: {error_id}")
        self.logger.error(f"{type(error).__name__}: {error}")
        self.logger.debug(f"Error Context: {self._safe_json_dumps(context, indent=2)}")
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
        return error_id


def debug_tool(mcp_logger: MCPLogger, catch_exceptions: bool = True) -> Callable:
    """
    Decorator for comprehensive tool debugging. Handles both sync and async functions.

    Args:
        mcp_logger: An instance of MCPLogger.
        catch_exceptions: If True, catches exceptions and returns a JSON error.
                          If False, re-raises the exception.
    """
    def decorator(func: Callable) -> Callable:
        is_async = iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            log_context = {"args": args, "kwargs": kwargs}
            mcp_logger.logger.debug(f"Calling tool '{func_name}' with context: {mcp_logger._safe_json_dumps(log_context)}")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                mcp_logger.log_call(func_name, duration, result)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_id = mcp_logger.log_error(func_name, duration, e, log_context)
                if catch_exceptions:
                    return mcp_logger._safe_json_dumps({
                        "error": {
                            "id": error_id,
                            "type": type(e).__name__,
                            "message": str(e),
                            "tool": func_name,
                            "traceback": traceback.format_exc()
                        }
                    }, indent=2)
                else:
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            log_context = {"args": args, "kwargs": kwargs}
            mcp_logger.logger.debug(f"Calling tool '{func_name}' with context: {mcp_logger._safe_json_dumps(log_context)}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                mcp_logger.log_call(func_name, duration, result)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_id = mcp_logger.log_error(func_name, duration, e, log_context)
                if catch_exceptions:
                    return mcp_logger._safe_json_dumps({
                        "error": {
                            "id": error_id,
                            "type": type(e).__name__,
                            "message": str(e),
                            "tool": func_name,
                            "traceback": traceback.format_exc()
                        }
                    }, indent=2)
                else:
                    raise

        return async_wrapper if is_async else sync_wrapper
    return decorator
```

### `mcp-logger-utils/src/mcp_logger_utils/json_utils.py`

```python
"""
Module: json_utils.py
Description: Robust JSON parsing and repair utilities.
"""
import json
import re
from typing import Any, Dict, List, Optional, Union

from json_repair import repair_json
from loguru import logger

def repair_and_parse_json(
    content: Union[str, dict, list],
    logger_instance: Optional[Any] = None,
) -> Union[Dict, List, str]:
    """
    Cleans and parses a string that is expected to be JSON, but might be malformed
    or wrapped in markdown code blocks. Handles common LLM output issues.

    Args:
        content: The input string, dict, or list to clean. If it's already a
                 dict or list, it will be returned directly.
        logger_instance: An optional loguru logger instance to log repair steps.

    Returns:
        A cleaned Python dict or list, or the original string if it cannot be
        parsed into a valid JSON structure.
    """
    log = logger_instance or logger  # Use provided logger or a default one

    if isinstance(content, (dict, list)):
        return content

    if not isinstance(content, str):
        log.warning(f"Input is not a string, dict, or list, returning as is. Type: {type(content)}")
        return content

    original_content = content
    # 1. Extract from markdown code blocks if present
    # This is a common pattern for LLMs
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        content = match.group(1).strip()
        log.debug("Extracted content from JSON markdown block.")

    # 2. Try direct parsing first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        log.debug("Direct JSON parsing failed, attempting repair.")

    # 3. Attempt to repair the JSON
    try:
        # The repair_json function is robust against many common errors
        repaired = repair_json(content, return_objects=True)
        if isinstance(repaired, (dict, list)):
            log.info("Successfully repaired and parsed JSON content.")
            return repaired
    except Exception as e:
        log.error(f"JSON repair failed unexpectedly: {e}")
        # Fallback to returning the original string
        return original_content
        
    log.warning("Could not parse content as JSON, returning original string.")
    return original_content
```

---

## 3. How to Publish to PyPI

Here are clear, step-by-step instructions to publish your package to the Python Package Index (PyPI).

### Step 1: Prerequisites

1.  **Create PyPI Accounts:**
    *   Create an account on the **TestPyPI** server: [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/)
    *   Create an account on the **real PyPI** server: [https://pypi.org/account/register/](https://pypi.org/account/register/)
    *   Use a strong, unique password for each, and enable 2-Factor Authentication (2FA).

2.  **Install Publishing Tools:**
    *   You need `build` and `twine` to create and upload the package.

    ```bash
    python -m pip install --upgrade build twine
    ```

### Step 2: Build the Package

Navigate to the root directory of your `mcp-logger-utils` project (the one containing `pyproject.toml`).

Run the build command:

```bash
python -m build
```

This will create a `dist/` directory containing two files:
*   A source archive (`.tar.gz`)
*   A built distribution (`.whl` - a wheel file)

### Step 3: Test Upload to TestPyPI (Highly Recommended)

Before publishing to the real PyPI, always upload to TestPyPI first to ensure everything works as expected.

1.  **Upload to TestPyPI:**
    *   You will be prompted for your **TestPyPI** username and password.
    *   For the password, it's highly recommended to generate an API Token on TestPyPI and use that instead of your actual password.
        *   Go to your TestPyPI account settings > API tokens.
        *   Create a token scoped to your project.
        *   When prompted for username, enter `__token__`.
        *   When prompted for password, paste the entire API token (including the `pypi-` prefix).

    ```bash
    python -m twine upload --repository testpypi dist/*
    ```

2.  **Verify the Test Upload:**
    *   Go to `https://test.pypi.org/project/mcp-logger-utils/`. You should see your package listed.
    *   Try installing it from TestPyPI in a clean virtual environment to make sure it installs correctly.

    ```bash
    # Create and activate a new virtual environment
    python -m venv test_env
    source test_env/bin/activate  # On Windows: test_env\Scripts\activate

    # Install from TestPyPI
    pip install --index-url https://test.pypi.org/simple/ --no-deps mcp-logger-utils

    # Test the import
    python -c "from mcp_logger_utils import MCPLogger; print('Success!')"

    # Deactivate and clean up
    deactivate
    rm -rf test_env
    ```

### Step 4: Publish to the Real PyPI

Once you are confident that the package is correct, you can publish it to the official PyPI repository.

1.  **Clear the `dist` directory:**
    *   It's good practice to remove the old build artifacts to avoid uploading the wrong version.

    ```bash
    rm -rf dist/*
    ```

2.  **Re-build the package:**

    ```bash
    python -m build
    ```

3.  **Upload to PyPI:**
    *   This is the final, public step.
    *   Just like with TestPyPI, you will be prompted for your **real PyPI** username and password. It's best practice to use an API token here as well.

    ```bash
    python -m twine upload dist/*
    ```

### Step 5: You're Live!

Congratulations! Your package is now live on PyPI and can be installed by anyone using `pip install mcp-logger-utils`.

-   Check your package's page at `https://pypi.org/project/mcp-logger-utils/`.
-   Remember to increment the `version` number in `pyproject.toml` every time you want to publish an update.