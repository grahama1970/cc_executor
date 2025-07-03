# Core Assessment System

This documents the self-improving assessment system for core components.

## Overview

The core module uses a self-assessment system that:
1. Runs usage functions from each Python file
2. Saves raw outputs to prevent hallucination
3. Generates comprehensive markdown reports
4. Uses behavioral testing, not regex matching

## Directory Structure

```
core/prompts/
├── ASSESS_ALL_CORE_USAGE.md    # Self-improving prompt documentation
├── scripts/                     # Python implementation scripts
│   └── assess_all_core_usage.py # Runs usage functions and generates reports
├── reports/                     # Generated assessment reports
│   └── CORE_USAGE_REPORT_*.md  # Timestamped reports
└── tmp/                        # Temporary files during assessment
```

## Usage

```bash
# Run the assessment
python src/cc_executor/core/prompts/scripts/assess_all_core_usage.py

# Or use the CLI
cc-executor test assess core

# View latest report
ls -lt src/cc_executor/core/prompts/reports/ | head -2
```

## How It Works

1. **Discovery**: Finds all Python files in the core directory
2. **Execution**: Runs each file's `if __name__ == "__main__"` block
3. **Capture**: Saves raw output to `tmp/responses/`
4. **Analysis**: Behavioral assessment of outputs
5. **Reporting**: Generates markdown report with findings

## Key Principles

- **Self-contained**: Everything related to core assessment in one place
- **No code extraction**: Python scripts separate from markdown prompts
- **Raw output saving**: Prevents AI hallucination
- **Behavioral testing**: Tests what code does, not how it's written

## Files

### Main Prompt
- `ASSESS_ALL_CORE_USAGE.md` - The self-improving prompt that guides assessment

### Implementation
- `scripts/assess_all_core_usage.py` - Python script that executes assessments

### Reports
- `reports/CORE_USAGE_REPORT_*.md` - Timestamped assessment reports

## Integration with CLI

The assessment is integrated into the CLI:

```bash
cc-executor test assess core
```

This runs the assessment and displays the results.