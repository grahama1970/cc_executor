# Core Prompts Directory Structure

This directory contains the self-improving assessment system for core components.

## Directory Structure

```
prompts/
├── ASSESS_ALL_CORE_USAGE.md    # Self-improving prompt documentation
├── scripts/                     # Python implementation scripts
│   └── assess_all_core_usage.py # Runs usage functions and generates reports
├── reports/                     # Generated assessment reports
│   └── CORE_USAGE_REPORT_*.md  # Timestamped reports
└── tmp/                        # Temporary files during assessment
```

## Why This Structure?

1. **Self-contained**: Everything related to core assessment in one place
2. **No code extraction issues**: Python scripts separate from markdown
3. **Clean reports location**: All reports go to `prompts/reports/`
4. **Temporary isolation**: `tmp/` for any transient files

## Usage

```bash
# Run the assessment
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/core/prompts/scripts/assess_all_core_usage.py

# View latest report
ls -lt prompts/reports/ | head -2
```

## Important Notes

- Reports are generated in `prompts/reports/`, NOT in `core/reports/`
- The assessment script automatically creates directories if needed
- All paths are relative to maintain portability