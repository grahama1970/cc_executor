# Example 04: With UUID4 Verification

This example demonstrates the UUID4 anti-hallucination pattern with proper hook integration.

## Overview

Build a simple key-value store API while ensuring all executions are verifiable through UUID4 tracking.

## Features

- UUID4 generation for each task execution
- Pre-execution hook that sets UUID in environment
- Post-execution hook that verifies UUID presence
- JSON outputs with UUID at the END
- Full audit trail for verification

## Running the Example

```bash
cd examples/04_with_uuid_verification
python run_example.py
```

## What This Demonstrates

1. **Anti-Hallucination**: Every execution has a unique, verifiable UUID
2. **Hook Integration**: Pre/post hooks work together for verification
3. **Proper JSON Structure**: UUID always appears as the last key
4. **Audit Trail**: UUIDs can be traced through logs and outputs

## Expected Output Structure

Each task execution will produce JSON like:

```json
{
  "task_number": 1,
  "description": "Create KV Store API",
  "status": "success",
  "files_created": ["kv_store/main.py"],
  "timestamp": "2025-07-04T12:00:00",
  "execution_uuid": "a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c"
}
```

Note how `execution_uuid` is the LAST key.

## Verification

After execution, you can verify UUIDs:

```bash
# Check in output files
grep -A2 "execution_uuid" tmp/responses/*.json

# Verify it's the last key
tail -3 tmp/responses/*.json

# Check in reports
grep "UUID" reports/*.md
```

## Directory Structure

```
04_with_uuid_verification/
├── README.md                    # This file
├── task_list.md                # Task definitions with UUID requirements
├── run_example.py              # Execution script with UUID tracking
├── .claude-hooks.json          # Hook configuration
├── hooks/                      # Custom hooks for this example
│   ├── generate_uuid_hook.py   # Pre-execution UUID generation
│   └── verify_uuid_hook.py     # Post-execution UUID verification
└── tmp/                        # Generated outputs
    └── responses/              # JSON files with UUIDs
```

## Learning Points

1. **Generate Early**: UUID created at task start
2. **Position Matters**: Always place at END of JSON
3. **Verify Always**: Post-hook checks UUID presence
4. **Trace Everything**: UUIDs in logs, files, and reports