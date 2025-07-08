# Setup Template Pattern

## Overview

The `setup_template.py` provides a reusable base for initializing task list environments. Each task list customizes this template by replacing placeholders.

## How It Works

1. **Template Location**: `src/cc_executor/prompts/setup_template.py`
2. **Customization**: Task lists read and modify the template
3. **Execution**: Modified script runs in the task list context

## Template Placeholders

- `PLACEHOLDER_PROJECT_ROOT` - Actual project root path (determined dynamically)
- `PLACEHOLDER_TASK_LIST_NAME` - Human-readable name
- `PLACEHOLDER_TASK_LIST_PATH` - Path relative to project root

## Directory Structure Created

```
task_list_dir/
├── tmp/
│   ├── responses/    # JSON execution results
│   └── scripts/      # Generated Python scripts
└── reports/          # Markdown reports
```

## Usage in Task Lists

```python
# Task 0: Setup (always first)
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Determine project root dynamically
import os
from pathlib import Path

current_dir = Path(os.getcwd())
project_root = current_dir

# Find project root by looking for markers
while project_root.parent != project_root:
    if (project_root / "pyproject.toml").exists() or (project_root / ".git").exists():
        break
    project_root = project_root.parent

# 3. Read and customize template
template_path = project_root / 'src/cc_executor/prompts/setup_template.py'
with open(template_path, 'r') as f:
    setup_code = f.read()

setup_code = setup_code.replace('PLACEHOLDER_PROJECT_ROOT', str(project_root))
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_NAME', 'Your Task List')
setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_PATH', 'path/to/task/list')

# 4. Save and run
setup_path = project_root / 'path/to/task/list/tmp/setup_custom.py'
setup_path.parent.mkdir(parents=True, exist_ok=True)
with open(setup_path, 'w') as f:
    f.write(setup_code)

exec(open(setup_path).read())
```

## Why This Pattern?

1. **Consistency**: All task lists follow same structure
2. **Flexibility**: Each can customize paths as needed
3. **Isolation**: Each task list has its own tmp/reports
4. **No Pollution**: Generated files stay organized