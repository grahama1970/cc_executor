# CC Executor Examples

Clean, organized examples demonstrating cc_executor capabilities.

## Quick Start

Each example is self-contained with its own README:

1. **[01_basic_usage](01_basic_usage/)** - Simplest example showing sequential task execution
2. **[02_with_error_recovery](02_with_error_recovery/)** - Error handling and retry logic
3. **[03_with_hooks](03_with_hooks/)** - Pre-flight checks and post-execution reports

## Running Examples

```bash
# Basic usage
cd examples/01_basic_usage
python run_example.py

# With error recovery
cd examples/02_with_error_recovery
python run_example.py

# With hooks
cd examples/03_with_hooks
python run_example.py
```

## What Each Example Teaches

### 01_basic_usage
- Writing task lists that reference cc_execute.md
- Sequential execution with dependencies
- Fresh context per task (200K tokens)
- File creation and modification

### 02_with_error_recovery
- Documenting common errors upfront
- Automatic retry with exponential backoff
- Building a knowledge base of errors
- Self-healing task lists

### 03_with_hooks
- Pre-flight complexity assessment
- Risk identification before execution
- Post-execution quality reports
- Automated verification

## Key Concepts

1. **Sequential Execution**: Tasks run one after another, not in parallel
2. **Fresh Context**: Each task gets a clean 200K token window
3. **No Pollution**: Tasks don't see each other's generation process
4. **Tool Integration**: Full MCP tool access per task

## Directory Structure

```
examples/
├── README.md                    # This file
├── 01_basic_usage/             # Simplest example
│   ├── README.md               # Example documentation
│   ├── task_list.md            # Task definitions
│   └── run_example.py          # Execution script
├── 02_with_error_recovery/     # Error handling
│   ├── README.md
│   ├── task_list.md
│   └── run_example.py
└── 03_with_hooks/              # Quality assurance
    ├── README.md
    ├── task_list.md
    ├── .claude-hooks.json      # Hook configuration
    └── run_example.py
```

## Output Organization

Each example creates its own output directories:
- `tmp/responses/` - JSON execution results
- Generated code in appropriate directories
- Reports (for examples with hooks)

All outputs are gitignored by default.

## Best Practices

1. **Start Simple**: Begin with 01_basic_usage
2. **Add Complexity Gradually**: Move to error recovery, then hooks
3. **Learn from Outputs**: Check JSON files to understand execution
4. **Customize**: Modify examples for your use cases

## Troubleshooting

If examples fail:
1. Check you're in the virtual environment: `source .venv/bin/activate`
2. Ensure dependencies installed: `uv pip install fastapi pytest httpx`
3. Review JSON outputs in `tmp/responses/`
4. For hook examples, check reports in `reports/`

## Next Steps

After running these examples:
1. Create your own task lists
2. Experiment with different tools
3. Add custom hooks for your workflow
4. Build complex multi-step automations