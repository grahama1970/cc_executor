# MCP Debugging Guide: Finding and Fixing Issues

## The Problem

MCP tools fail silently by default. When something goes wrong, you often see:
- "Tool not available" 
- No error messages
- Tools disappear from Claude's tool list
- Cryptic initialization failures

This guide provides practical debugging strategies.

## Debugging Strategy Overview

```
1. Enable verbose logging everywhere
2. Test tool standalone first  
3. Check config syntax carefully
4. Use process monitoring
5. Add custom logging infrastructure
```

## Step 1: Enable All Logging

### Claude MCP Debug Mode
```bash
# Enable MCP debug logging
export MCP_DEBUG=true
export ANTHROPIC_DEBUG=true
claude

# Or on Windows
set MCP_DEBUG=true
set ANTHROPIC_DEBUG=true
claude

# RECOMMENDED: Add to ~/.zshrc or ~/.bashrc for persistent debugging
echo '# MCP debugging for claude code' >> ~/.zshrc
echo 'export MCP_DEBUG=true' >> ~/.zshrc
echo 'export ANTHROPIC_DEBUG=true' >> ~/.zshrc
```

### Find Claude's Log Files
```bash
# ACTUAL LOG LOCATIONS (discovered during testing):
# 1. Basic tool execution log (limited info)
~/.claude/tool_execution.log

# 2. MCP-specific logs (when MCP_DEBUG=true)
~/.claude/mcp_logs/    # Created by our centralized logger
~/.claude/mcp_logs/{tool_name}_startup.log
~/.claude/mcp_logs/{tool_name}_errors.log
~/.claude/mcp_logs/{tool_name}_calls.jsonl
~/.claude/mcp_logs/{tool_name}_debug.log

# 3. Project transcripts (not MCP-specific but useful)
~/.claude/projects/{project-path}/*.jsonl

# Watch logs in real-time
tail -f ~/.claude/mcp_logs/*.log
tail -f ~/.claude/tool_execution.log
```

### Add Logging to Your MCP Server

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "loguru"
# ]
# ///

import sys
from pathlib import Path
from loguru import logger
from fastmcp import FastMCP

# Configure comprehensive logging
log_file = Path.home() / ".claude" / "mcp_debug.log"
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="DEBUG")  # Console output
logger.add(log_file, level="DEBUG", rotation="10 MB")  # File output

logger.info(f"MCP Server starting - PID: {os.getpid()}")
logger.info(f"Python: {sys.executable}")
logger.info(f"Working dir: {os.getcwd()}")
logger.info(f"Sys path: {sys.path}")

mcp = FastMCP("your-tool")

@mcp.tool()
async def your_function(param: str) -> str:
    logger.debug(f"Function called with param: {param}")
    try:
        result = do_something(param)
        logger.info(f"Function succeeded: {result}")
        return result
    except Exception as e:
        logger.error(f"Function failed: {e}", exc_info=True)
        raise

logger.info("MCP Server initialized successfully")

if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as e:
        logger.critical(f"MCP Server crashed: {e}", exc_info=True)
        sys.exit(1)
```

## Step 2: Test Standalone First

Create a test harness:

```python
# test_mcp_standalone.py
import subprocess
import json
import time
import sys

def test_mcp_server():
    """Test if MCP server starts and responds to initialization"""
    
    cmd = [
        sys.executable,  # Use same Python
        "src/servers/mcp_your_tool.py"
    ]
    
    print(f"Starting MCP server: {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Check if process started
    time.sleep(0.5)
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print(f"Server died immediately!")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    # Send JSON-RPC initialization
    init_msg = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "capabilities": {}
        },
        "id": 1
    }
    
    print(f"Sending: {json.dumps(init_msg)}")
    proc.stdin.write(json.dumps(init_msg) + '\n')
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        print(f"Response: {response_line}")
        response = json.loads(response_line)
        if "result" in response:
            print("✓ Server initialized successfully")
            print(f"Tools available: {response.get('result', {}).get('tools', [])}")
            return True
    
    print("✗ No valid response received")
    proc.terminate()
    return False

if __name__ == "__main__":
    test_mcp_server()
```

## Step 3: Common Issues and Solutions

### Issue: Import Errors

**Symptom**: Server dies immediately with ModuleNotFoundError

**Debug Steps**:
```python
# Add to top of MCP server
import sys
print(f"Python path: {sys.path}", file=sys.stderr)
print(f"Current dir: {os.getcwd()}", file=sys.stderr)

# Try importing your modules
try:
    from cc_executor.tools import something
    print("✓ Imports successful", file=sys.stderr)
except ImportError as e:
    print(f"✗ Import failed: {e}", file=sys.stderr)
    sys.exit(1)
```

**Fix**: Ensure PYTHONPATH in config:
```json
{
  "mcpServers": {
    "tool": {
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/project",
        "UV_PROJECT_ROOT": "/absolute/path/to/project"
      }
    }
  }
}
```

### Issue: JSON Config Errors

**Symptom**: Tool doesn't appear, no error message

**Debug Steps**:
```bash
# Validate JSON syntax
python -m json.tool < ~/.claude/claude_code/.mcp.json

# Or use jq
jq . ~/.claude/claude_code/.mcp.json
```

**Common JSON mistakes**:
- Trailing commas
- Missing quotes around keys
- Wrong path separators on Windows
- Comments (JSON doesn't support them)

### Issue: Process Crashes Silently

**Debug Steps**:
```bash
# Monitor process lifecycle
# Linux/macOS
ps aux | grep mcp_
strace -f claude 2>&1 | grep mcp_

# See what files are accessed
lsof -p $(pgrep -f mcp_your_tool)
```

**Add wrapper script**:
```bash
#!/bin/bash
# mcp_wrapper.sh
echo "[$(date)] Starting MCP server" >> /tmp/mcp_debug.log
echo "Environment:" >> /tmp/mcp_debug.log
env >> /tmp/mcp_debug.log

python /path/to/mcp_server.py 2>&1 | tee -a /tmp/mcp_debug.log
echo "[$(date)] MCP server exited with code $?" >> /tmp/mcp_debug.log
```

### Issue: FastMCP kwargs Error

**Symptom**: "Functions with **kwargs are not supported as tools"

**Debug**:
```python
# Find the offending function
import inspect

for name, func in inspect.getmembers(your_module, inspect.isfunction):
    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        if param.kind == param.VAR_KEYWORD:
            print(f"Function {name} uses **kwargs!")
```

**Fix**: Replace with explicit parameters or use a dict:
```python
# Bad
async def query(aql: str, **kwargs):
    bind_vars = kwargs.get('bind_vars', {})

# Good
async def query(aql: str, bind_vars: dict = None):
    bind_vars = bind_vars or {}
```

## Step 4: Enhanced Error Reporting

### Add Error Context to All Tools

```python
from functools import wraps
import traceback

def debug_tool(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        import time
        start = time.time()
        
        logger.debug(f"Tool {func.__name__} called")
        logger.debug(f"Args: {args}")
        logger.debug(f"Kwargs: {kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"Tool {func.__name__} succeeded in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"Tool {func.__name__} failed after {duration:.2f}s: {e}",
                exc_info=True
            )
            
            # Return error details instead of raising
            return json.dumps({
                "error": str(e),
                "type": type(e).__name__,
                "tool": func.__name__,
                "duration": duration,
                "traceback": traceback.format_exc()
            }, indent=2)
    
    return wrapper

# Use it
@mcp.tool()
@debug_tool
async def your_function(param: str) -> str:
    # Your code here
```

### Process Monitoring Script

```python
# monitor_mcp.py
import psutil
import time
import sys

def monitor_mcp_processes():
    """Monitor all MCP-related processes"""
    
    while True:
        print("\n" + "="*60)
        print(f"MCP Process Monitor - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        mcp_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'mcp_' in cmdline or 'fastmcp' in cmdline:
                    mcp_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not mcp_processes:
            print("No MCP processes found")
        else:
            for proc in mcp_processes:
                try:
                    print(f"\nPID: {proc.pid}")
                    print(f"Status: {proc.status()}")
                    print(f"CPU: {proc.cpu_percent()}%")
                    print(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
                    print(f"Command: {' '.join(proc.cmdline())}")
                    
                    # Check for hanging
                    if proc.status() == 'zombie':
                        print("⚠️  ZOMBIE PROCESS DETECTED")
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    monitor_mcp_processes()
```

## Step 5: Better Logging Infrastructure

### Centralized MCP Logger

```python
# mcp_logger.py
from pathlib import Path
from datetime import datetime
import json

class MCPLogger:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.log_dir = Path.home() / ".claude" / "mcp_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Different log files for different purposes
        self.startup_log = self.log_dir / f"{tool_name}_startup.log"
        self.error_log = self.log_dir / f"{tool_name}_errors.log"
        self.calls_log = self.log_dir / f"{tool_name}_calls.jsonl"
    
    def log_startup(self, message: str):
        with open(self.startup_log, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
    
    def log_error(self, error: Exception, context: dict = None):
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {}
        }
        with open(self.error_log, 'a') as f:
            f.write(json.dumps(error_entry) + '\n')
    
    def log_call(self, function: str, args: dict, result: any, duration: float):
        call_entry = {
            "timestamp": datetime.now().isoformat(),
            "function": function,
            "args": args,
            "success": not isinstance(result, Exception),
            "duration": duration
        }
        if isinstance(result, Exception):
            call_entry["error"] = str(result)
        
        with open(self.calls_log, 'a') as f:
            f.write(json.dumps(call_entry) + '\n')

# Use in your MCP server
logger = MCPLogger("arango-tools")
logger.log_startup("Server starting")
```

### Quick Debug Checklist

```bash
#!/bin/bash
# debug_mcp.sh

echo "MCP Debug Checklist"
echo "=================="

# 1. Check config syntax
echo -n "1. JSON config valid: "
if python -m json.tool < ~/.claude/claude_code/.mcp.json > /dev/null 2>&1; then
    echo "✓"
else
    echo "✗ - Fix JSON syntax"
    python -m json.tool < ~/.claude/claude_code/.mcp.json
fi

# 2. Check if server runs standalone
echo -n "2. Server runs standalone: "
if timeout 5 python src/servers/mcp_*.py > /dev/null 2>&1; then
    echo "✓"
else
    echo "✗ - Check imports and dependencies"
fi

# 3. Check log files
echo -n "3. Log files exist: "
if ls ~/.claude/logs/mcp*.log > /dev/null 2>&1; then
    echo "✓"
    echo "   Recent errors:"
    grep -i error ~/.claude/logs/mcp*.log | tail -5
else
    echo "✗ - No log files found"
fi

# 4. Check running processes
echo -n "4. MCP processes running: "
if pgrep -f mcp_ > /dev/null; then
    echo "✓"
    ps aux | grep mcp_ | grep -v grep
else
    echo "✗ - No MCP processes found"
fi
```

## Lessons Learned from Production Testing

### 1. MCP Log Locations Are Not What You Expect
- Claude Code's default logs are minimal: `~/.claude/tool_execution.log` only shows basic execution info
- Without `MCP_DEBUG=true`, you get almost no visibility into MCP operations
- You must create your own logging infrastructure for proper debugging

### 2. Common Issues Found During Testing
- **Syntax Errors**: Unclosed docstrings can crash the entire server silently
- **Method Name Mismatches**: Calling non-existent methods (e.g., `tools.upsert()` vs `tools.upsert_document()`)
- **Input Validation**: Tools may expect specific formats (e.g., error messages with quotes)
- **Import Path Issues**: MCP servers run in different contexts, absolute imports are safer

### 3. Essential Debugging Workflow
```bash
# 1. Always test standalone first
python src/servers/mcp_tool.py test

# 2. Check for syntax errors
python -m py_compile src/servers/mcp_tool.py

# 3. Test with timeout to catch hangs
timeout 5s uv run --script src/servers/mcp_tool.py

# 4. Monitor logs in real-time
tail -f ~/.claude/mcp_logs/*_debug.log
```

### 4. Centralized Logger Pattern (Recommended)
Create a reusable logger utility (`src/utils/mcp_logger.py`) that:
- Logs to multiple destinations (console, files)
- Captures startup info (PID, Python version, environment)
- Records all tool calls with timing
- Gracefully handles errors without crashing
- Provides decorators for automatic logging

### 5. Testing MCP Tools Effectively
- Use the actual MCP interface, not direct function calls
- Test each tool with valid and invalid inputs
- Document expected responses for reference
- Create a comprehensive test report

## Summary: Debugging Best Practices

1. **Always add verbose logging** - You can't debug what you can't see
2. **Test standalone first** - Ensure server works before integrating
3. **Use wrapper scripts** - Capture all output and errors
4. **Monitor processes** - Detect hangs and crashes
5. **Return errors gracefully** - Don't let exceptions kill the server
6. **Create debug utilities** - Scripts to quickly check common issues
7. **Log strategically** - Separate startup, errors, and calls
8. **Add to ~/.zshrc** - Make MCP_DEBUG persistent across sessions
9. **Use centralized logging** - Consistent logging across all MCP servers
10. **Test systematically** - Create test reports for all tools

Remember: The hardest part of debugging MCP tools is that failures are often silent. Build visibility into every step of the process.