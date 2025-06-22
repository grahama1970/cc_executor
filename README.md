# CC-Executor

Docker container for executing Claude Code tasks with gamification prompt system.

## Overview

CC-Executor provides a containerized environment for running Claude Code with:
- 🎮 Gamification system for prompt development (10:1 success ratio)
- 🐳 Docker container with FastAPI for code execution
- 📊 Metrics tracking and anti-hallucination verification
- 🔧 Modular prompt-based architecture

## Setup

### Prerequisites
- Python 3.10.11
- uv package manager
- Docker and docker-compose
- Active virtual environment

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cc_executor
```

2. Create and activate virtual environment:
```bash
uv venv --python=3.10.11 .venv
source .venv/bin/activate  # On Unix/macOS
```

3. Install dependencies:
```bash
uv pip install -e .
```

## Project Structure
```
cc_executor/
├── src/
│   └── cc_executor/
│       ├── setup/           # Setup system
│       │   ├── prompts/     # Gamified prompts (10:1 ratio required)
│       │   ├── generated/   # Files created by prompts
│       │   └── graduated/   # Prompts that reached 10:1
│       ├── core/           # Core functionality
│       ├── docs/           # Documentation
│       ├── scripts/        # Utility scripts
│       └── tasks/          # Task definitions
├── .env                    # Environment variables
├── .gitignore             # Git ignore rules
├── .mcp.json              # MCP configuration
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## Gamification System

All code starts as markdown prompts in `setup/prompts/`. Each prompt must:
- Track Success/Failure/Total metrics
- Achieve 10:1 success ratio to graduate
- Extract with: `sed -n '/^```python$/,/^```$/p' [file] | sed '1d;$d'`
- Graduate to Python files when 10:1 reached

## Quick Start

```bash
# Navigate to setup directory
cd src/cc_executor/setup

# Find available port
export PORT=$(docker ps --format '{.Ports}' 2>/dev/null | grep -oE ':[0-9]+->' | cut -d: -f2 | cut -d- -f1 | sort -n | tail -1 | awk '{print $1 + 1}')
[ -z "$PORT" ] && export PORT=8000

# Run orchestrator (once it's created)
sed -n '/^```python$/,/^```$/p' prompts/orchestrator/orchestrator.md | sed '1d;$d' > temp.py && python temp.py --port $PORT --force; rm -f temp.py
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
ruff check src/
```

## Anti-Hallucination Verification

Verify all executions with transcript checking:
```bash
rg "CC_EXECUTOR_SETUP" ~/.claude/projects/*/*.jsonl
```

## License
MIT License

## Author
Graham Anderson <graham@grahama.co>
