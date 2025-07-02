# Environment Setup - ALWAYS DO THIS FIRST

## 🚨 Critical Setup Steps

```bash
# 1. ALWAYS activate virtual environment
source .venv/bin/activate

# 2. Set PYTHONPATH (check .env for other variables)
export PYTHONPATH=./src

# 3. Load all environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
```

## 📋 Quick Checklist

| Step | Command | Expected Result |
|------|---------|----------------|
| Activate venv | `source .venv/bin/activate` | Prompt shows `(.venv)` |
| Check Python | `which python` | Should be `.venv/bin/python` |
| Check PYTHONPATH | `echo $PYTHONPATH` | Should show `./src` |
| Check Redis | `redis-cli ping` | Should return `PONG` |
| Check Claude | `claude --version` | Should show version |

## 🔍 Common Issues

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3` or activate venv |
| `ModuleNotFoundError` | Set `PYTHONPATH=./src` |
| Redis connection failed | Check Docker: `docker ps` |
| Claude hangs | Unset `ANTHROPIC_API_KEY` for Claude Max |

## 📁 Project Structure Reference

```
cc_executor/
├── .env                  # Environment variables
├── .venv/               # Virtual environment
├── src/cc_executor/     # Main code (PYTHONPATH points here)
├── logs/                # Check for errors
└── test_outputs/        # Test results
```

## 🎯 Complete Example

```python
#!/usr/bin/env python3
"""Example with proper setup"""

import os
import sys

# Ensure PYTHONPATH is set
if 'PYTHONPATH' not in os.environ:
    os.environ['PYTHONPATH'] = './src'
    
# Add to path if needed
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

# Now imports will work
from cc_executor.core.websocket_handler import WebSocketHandler
```

## 🚀 One-Liner Setup

```bash
# Copy-paste this to set up everything
source .venv/bin/activate && export PYTHONPATH=./src && [ -f .env ] && export $(grep -v '^#' .env | xargs) || true
```