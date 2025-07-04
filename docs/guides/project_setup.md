# Python Project Setup Guide

This guide provides a standardized approach for setting up new Python projects with proper structure, virtual environments, and configuration.

## How to Use This Guide

1. **Navigate to your project directory first**:
   ```bash
   cd /path/to/your/project
   ```

2. **Run the setup script** or follow the manual steps below

3. **The setup will**:
   - Use the current directory name as the project name
   - Create a Python 3.10.11 virtual environment
   - Set up proper src/ layout structure
   - Configure all necessary files (pyproject.toml, .env, .gitignore, etc.)
   - Install the project in editable mode

## Quick Setup Script

Save this as `setup_project.sh` in your project directory and run it:

```bash
#!/bin/bash
# Save as setup_project.sh and run with: bash setup_project.sh

# Get current directory name as project name
PROJECT_NAME=$(basename "$(pwd)")
echo "Setting up project: $PROJECT_NAME in $(pwd)"

# Initialize git (if not already initialized)
if [ ! -d .git ]; then
    git init
fi

# Create virtual environment with specific Python version
uv venv --python=3.10.11

# Activate virtual environment
source .venv/bin/activate

# Create project structure
mkdir -p src/$PROJECT_NAME/{core,cli,utils,prompts}
mkdir -p tests/{unit,integration}
mkdir -p docs examples scripts

# Create __init__.py files
touch src/$PROJECT_NAME/__init__.py
touch src/$PROJECT_NAME/{core,cli,utils,prompts}/__init__.py

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "PROJECT_NAME"
version = "0.1.0"
description = "Project description"
authors = [{ name = "Your Name", email = "your.email@example.com" }]
requires-python = ">=3.10.11"
readme = "README.md"
license = "MIT"
keywords = []

# Core dependencies
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0.0",
    "loguru>=0.7.2",
    "python-dotenv>=1.0.0",
    "aiofiles>=23.0.0",
    "asyncio>=3.4.3",
    "typer>=0.16.0",
    "rich>=14.0.0",
    "httpx>=0.28.1",
    "pytest>=8.4.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.4.1",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.scripts]
PROJECT_NAME = "PROJECT_NAME.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/PROJECT_NAME"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
EOF

# Replace PROJECT_NAME placeholder
sed -i "s/PROJECT_NAME/$PROJECT_NAME/g" pyproject.toml

# Create .env.example
cat > .env.example << 'EOF'
# Environment Configuration
PYTHONPATH=./src

# API Keys
ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# PERPLEXITY_API_KEY=your_key_here

# Redis Configuration (optional)
# REDIS_URL=redis://localhost:6379

# Application Settings
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
DEBUG=false

# Security - CHANGE THIS IN PRODUCTION!
SECRET_KEY=your-secret-key-here-change-in-production

# Process Configuration (optional)
PYTHONUNBUFFERED=1  # Ensures real-time output streaming

# Additional settings
# MAX_WORKERS=4
# TIMEOUT=300
EOF

# Create .env from example
cp .env.example .env

# Create .gitignore
cat > .gitignore << 'EOF'
# Local/private files
private.py
local.env
.DS_Store

# Development/testing
experiments/
test_data/
playground/
temp.md
temp/
benchmark_data/
debug_data/
coverage.xml

# Data/uploads
uploads/
/cache
repos/
archive/
*.dat
report.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
env.bak/
venv.bak/
*.egg-info/
dist/
build/
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/
.hypothesis/

# Environment
.env
.env.local
.env.*.local

# Project specific
/tmp/
/logs/
/data/
*.log
*.db
*.sqlite

# Node (if using MCP servers)
node_modules/
dist/

# UV
uv.lock

# Sensitive credentials
*_service_account.json
*.pem
*.key

# But keep these
!pyproject.toml
!package*.json
!examples/*.json
EOF

# Create .mcp.json (for MCP server integration)
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "perplexity-ask": {
      "command": "npx",
      "args": [
        "-y",
        "server-perplexity-ask"
      ],
      "env": {
        "PERPLEXITY_API_KEY": "your-perplexity-key-here"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search",
        "--api-key",
        "your-brave-key-here"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ]
    },
    "ripgrep": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-ripgrep@latest"
      ]
    }
  }
}
EOF

# Create README.md
cat > README.md << EOF
# $PROJECT_NAME

## Overview

Brief description of what this project does.

## Installation

\`\`\`bash
# Clone the repository
git clone https://github.com/username/$PROJECT_NAME.git
cd $PROJECT_NAME

# Create virtual environment
uv venv --python=3.10
source .venv/bin/activate

# Install dependencies
uv sync
uv pip install -e .
\`\`\`

## Usage

\`\`\`bash
# Run the CLI
$PROJECT_NAME --help

# Run tests
uv run pytest
\`\`\`

## Project Structure

\`\`\`
$PROJECT_NAME/
├── src/
│   └── $PROJECT_NAME/
│       ├── __init__.py
│       ├── core/          # Core business logic
│       ├── cli/           # Command-line interface
│       ├── utils/         # Utility functions
│       └── prompts/       # Prompt templates (if using LLMs)
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docs/                 # Documentation
├── examples/             # Example usage
├── scripts/              # Utility scripts
├── pyproject.toml        # Project configuration
├── .env.example          # Environment template
├── .env                  # Local environment (gitignored)
└── README.md            # This file
\`\`\`

## Development

\`\`\`bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests with coverage
uv run pytest --cov=$PROJECT_NAME

# Format code
uv run black src/ tests/
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/
\`\`\`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

[Choose appropriate license]
EOF

# Create a simple main.py for CLI
cat > src/$PROJECT_NAME/cli/main.py << EOF
"""Command-line interface for $PROJECT_NAME."""
import typer
from typing import Optional
from pathlib import Path
import sys

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from $PROJECT_NAME.core.config import Settings

app = typer.Typer(
    name="$PROJECT_NAME",
    help="$PROJECT_NAME CLI",
    add_completion=False,
)

@app.command()
def hello(name: str = "World"):
    """Say hello."""
    typer.echo(f"Hello, {name}!")

@app.command()
def version():
    """Show version."""
    from $PROJECT_NAME import __version__
    typer.echo(f"$PROJECT_NAME version: {__version__}")

if __name__ == "__main__":
    app()
EOF

# Create __init__.py with version
cat > src/$PROJECT_NAME/__init__.py << 'EOF'
"""PROJECT_NAME package."""
__version__ = "0.1.0"
EOF
sed -i "s/PROJECT_NAME/$PROJECT_NAME/g" src/$PROJECT_NAME/__init__.py

# Create basic config
cat > src/$PROJECT_NAME/core/config.py << EOF
"""Configuration management for $PROJECT_NAME."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings."""
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    DATA_DIR = PROJECT_ROOT / "data"
    
    # Environment
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # API Keys (examples)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    def validate(cls):
        """Validate required settings."""
        # Add validation logic here
        pass

# Create singleton
settings = Settings()
EOF

# Create a simple test
cat > tests/unit/test_basic.py << EOF
"""Basic tests for $PROJECT_NAME."""
import pytest
from $PROJECT_NAME import __version__

def test_version():
    """Test version is set."""
    assert __version__ == "0.1.0"

def test_import():
    """Test package can be imported."""
    import $PROJECT_NAME
    assert $PROJECT_NAME is not None
EOF

# Install the package in editable mode
uv pip install -e .

# Initialize uv.lock
uv sync

echo "Project $PROJECT_NAME set up successfully in $(pwd)!"
echo ""
echo "Environment activated. You can now:"
echo "1. uv run pytest  # Run tests"
echo "2. $PROJECT_NAME hello  # Test CLI"
echo "3. Edit .env to add your API keys"
echo "4. Update .mcp.json with your MCP server keys"
```

## Step-by-Step Manual Setup

### 1. Navigate to Your Project Directory

```bash
cd /path/to/your/project
# The directory name will be used as the project name
```

### 2. Initialize Git (if needed)

```bash
# Only if not already a git repository
if [ ! -d .git ]; then
    git init
fi
```

### 3. Create Virtual Environment

Using `uv` with Python 3.10.11 (recommended for consistency):

```bash
# Create venv with specific Python version
uv venv --python=3.10.11

# Activate it
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

### 4. Create Project Structure

```bash
# Create source directory with package name
mkdir -p src/my_project/{core,cli,utils,prompts}

# Create test directories
mkdir -p tests/{unit,integration}

# Create other directories
mkdir -p docs examples scripts

# Create __init__.py files
touch src/my_project/__init__.py
touch src/my_project/{core,cli,utils,prompts}/__init__.py
```

### 5. Create pyproject.toml

Create a modern Python project configuration. Replace `your_project_name` with your actual project name:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "your_project_name"
version = "0.1.0"
description = "Your project description"
authors = [{ name = "Your Name", email = "your.email@example.com" }]
requires-python = ">=3.10.11"
readme = "README.md"
license = "MIT"
keywords = []

# Core dependencies
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0.0",
    "loguru>=0.7.2",
    "python-dotenv>=1.0.0",
    "aiofiles>=23.0.0",
    "asyncio>=3.4.3",
    "typer>=0.16.0",
    "rich>=14.0.0",
    "httpx>=0.28.1",
    "pytest>=8.4.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.4.1",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.scripts]
your-project = "your_project_name.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/your_project_name"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 6. Create .env.example and .env

`.env.example` (commit this):
```bash
# Environment Configuration
PYTHONPATH=./src

# API Keys
ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# PERPLEXITY_API_KEY=your_key_here

# Redis Configuration (optional)
# REDIS_URL=redis://localhost:6379

# Application Settings
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
DEBUG=false

# Security - CHANGE THIS IN PRODUCTION!
SECRET_KEY=your-secret-key-here-change-in-production

# Process Configuration (optional)
PYTHONUNBUFFERED=1  # Ensures real-time output streaming

# Additional settings
# MAX_WORKERS=4
# TIMEOUT=300
```

Then copy it:
```bash
cp .env.example .env
```

### 7. Create .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.coverage
.pytest_cache/
htmlcov/

# Environment
.env
.env.local

# Project specific
/tmp/
/logs/
/data/
*.log
*.db

# UV
uv.lock
```

### 8. Create .mcp.json (Optional - for MCP server integration)

```json
{
  "mcpServers": {
    "perplexity-ask": {
      "command": "npx",
      "args": [
        "-y",
        "server-perplexity-ask"
      ],
      "env": {
        "PERPLEXITY_API_KEY": "your-perplexity-key-here"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search",
        "--api-key",
        "your-brave-key-here"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ]
    },
    "ripgrep": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-ripgrep@latest"
      ]
    }
  }
}
```

### 9. Install Dependencies

```bash
# Install the package in editable mode
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"

# Sync dependencies
uv sync
```

## Key Components Explained

### Why `PYTHONPATH=./src` in .env?

This ensures Python can find your package when running scripts from the project root:
- Allows `from my_project.core import something` to work
- Prevents import errors during development
- Makes the project structure consistent

### Why the `src/` Layout?

The `src/` layout is **essential** for proper Python packaging:
- Prevents accidentally importing from the project root
- Ensures you're testing the installed package, not local files
- Makes packaging cleaner and more reliable
- Industry best practice for Python projects
- Required for proper editable installs with modern tools

### The `[tool.setuptools.packages.find]` Section

This tells setuptools where to find your packages:
- `where = ["src"]` - Look for packages in the src directory
- `include = ["my_project*"]` - Include packages starting with your project name
- `namespaces = false` - Don't use namespace packages

## Common Patterns

### Adding a CLI Command

In `src/my_project/cli/main.py`:

```python
import typer

app = typer.Typer()

@app.command()
def hello(name: str = "World"):
    """Say hello."""
    typer.echo(f"Hello, {name}!")

if __name__ == "__main__":
    app()
```

### Configuration Management

In `src/my_project/core/config.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    API_KEY = os.getenv("API_KEY")

settings = Settings()
```

### Testing Structure

```python
# tests/unit/test_example.py
import pytest
from my_project.core.example import my_function

def test_my_function():
    result = my_function("input")
    assert result == "expected"
```

## Best Practices

1. **Always use virtual environments** - Isolate dependencies per project
2. **Include .env.example** - Show required environment variables
3. **Use pyproject.toml** - Modern Python packaging
4. **Follow src/ layout** - Better testing and packaging
5. **Set PYTHONPATH** - Avoid import issues during development
6. **Pin Python version** - Use `uv venv --python=3.10` for consistency
7. **Use type hints** - Better IDE support and fewer bugs
8. **Configure tools** - Black, ruff, mypy in pyproject.toml

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`:
1. Check `PYTHONPATH=./src` is in your .env
2. Ensure you've activated the virtual environment
3. Install the package: `uv pip install -e .`

### UV Issues

If `uv` commands fail:
1. Ensure uv is installed: `pip install uv`
2. Check Python version: `python --version`
3. Try without version: `uv venv` (uses system Python)

### Package Not Found

If your CLI command isn't found:
1. Reinstall: `uv pip install -e .`
2. Check `[project.scripts]` in pyproject.toml
3. Ensure the entry point exists

## Next Steps

1. Customize the structure for your needs
2. Add your specific dependencies to pyproject.toml
3. Set up pre-commit hooks for code quality
4. Configure CI/CD (GitHub Actions, etc.)
5. Add comprehensive tests
6. Document your API in docs/

## Example Usage

After running the setup:

```bash
# Your project is ready!
source .venv/bin/activate

# Run tests
uv run pytest

# Run your CLI
your-project-name hello

# Start development
code .  # or your preferred editor
```

This setup provides a solid foundation for any Python project, whether it's a CLI tool, web service, or library. The structure mirrors successful projects like CC Executor and follows Python packaging best practices.

Last updated: 2025-01-04