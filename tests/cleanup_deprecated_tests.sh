#!/bin/bash
# Clean up deprecated and redundant test files
# This script moves deprecated tests to an archive directory

set -e

echo "=== Cleaning Up Deprecated Test Files ==="
echo "This script will move deprecated and redundant test files to an archive"
echo

# Create deprecated tests archive
DEPRECATED_DIR="test_results/archive/deprecated_tests_$(date +%Y%m%d)"
echo "Creating archive directory: $DEPRECATED_DIR"
mkdir -p "$DEPRECATED_DIR"
mkdir -p "$DEPRECATED_DIR/integration"
mkdir -p "$DEPRECATED_DIR/proof_of_concept"
mkdir -p "$DEPRECATED_DIR/stress_runners"

# Function to move file with explanation
move_with_reason() {
    local file=$1
    local reason=$2
    local dest_dir=$3
    
    if [ -f "$file" ]; then
        echo "Moving $file - Reason: $reason"
        mv "$file" "$dest_dir/"
    else
        echo "⏭️  $file not found"
    fi
}

echo
echo "=== Archiving Redundant Hook Tests ==="
# Keep test_hook_integration.py as the main hook test
move_with_reason "integration/test_all_three_hooks.py" "Redundant - functionality covered by test_hook_integration.py" "$DEPRECATED_DIR/integration"
move_with_reason "integration/test_hook_demo.py" "Demo file - not a comprehensive test" "$DEPRECATED_DIR/integration"
move_with_reason "integration/test_hooks_really_work.py" "Redundant verification test" "$DEPRECATED_DIR/integration"

echo
echo "=== Archiving Deprecated Timeout Tests ==="
move_with_reason "proof_of_concept/test_timeout_debug.py" "Superseded by test_timeout_debug_fixed.py" "$DEPRECATED_DIR/proof_of_concept"

echo
echo "=== Archiving Redundant Stress Test Runners ==="
# Keep run_all_stress_tests.py as the main runner
move_with_reason "stress/runners/final_stress_test_report.py" "Redundant - use run_all_stress_tests.py" "$DEPRECATED_DIR/stress_runners"
move_with_reason "stress/runners/test_final_integration.py" "Test file in runners directory" "$DEPRECATED_DIR/stress_runners"

echo
echo "=== Cleaning Up Temporary Directories ==="
if [ -d "integration/tmp" ]; then
    echo "Moving integration/tmp to archive..."
    mv integration/tmp "$DEPRECATED_DIR/integration_tmp"
    echo "✅ Archived integration/tmp"
fi

# Create deprecation notes
cat > "$DEPRECATED_DIR/DEPRECATION_NOTES.md" << 'EOF'
# Deprecated Tests Archive

This directory contains test files that were deprecated or made redundant as of $(date).

## Archived Files

### Integration Tests
- **test_all_three_hooks.py**: Redundant hook test - functionality covered by test_hook_integration.py
- **test_hook_demo.py**: Demo file, not a comprehensive test
- **test_hooks_really_work.py**: Redundant verification test
- **integration/tmp/**: Temporary response files from old test runs

### Proof of Concept Tests
- **test_timeout_debug.py**: Original timeout debug test, superseded by test_timeout_debug_fixed.py

### Stress Test Runners
- **final_stress_test_report.py**: Redundant runner, use run_all_stress_tests.py
- **test_final_integration.py**: Test file incorrectly placed in runners directory

## Recommendations

1. Use `test_hook_integration.py` for comprehensive hook testing
2. Use `test_timeout_debug_fixed.py` for timeout debugging
3. Use `run_all_stress_tests.py` as the main stress test runner

## Files That Need Import Updates

The following files have imports that may need updating:
- stress/runners/adaptive.py - imports redis_task_timing
- stress/runners/redis.py - imports redis_task_timing  
- integration/test_cc_execute_full_flow.py - imports cc_execute_utils

Please verify these imports point to existing modules.
EOF

# Count archived files
if [ -d "$DEPRECATED_DIR" ]; then
    FILE_COUNT=$(find "$DEPRECATED_DIR" -type f | wc -l)
    echo
    echo "=== Cleanup Summary ==="
    echo "Archived $FILE_COUNT deprecated test files"
    echo "Location: $DEPRECATED_DIR"
fi

echo
echo "=== Files That Need Manual Review ==="
echo "The following files import modules that may not exist:"
echo "- stress/runners/adaptive.py (imports redis_task_timing)"
echo "- stress/runners/redis.py (imports redis_task_timing)"
echo "- integration/test_cc_execute_full_flow.py (imports cc_execute_utils)"
echo
echo "Please review these imports and update if necessary."

echo
echo "✅ Cleanup complete!"
echo
echo "Next steps:"
echo "1. Review the archived files in: $DEPRECATED_DIR"
echo "2. Check and fix the import issues mentioned above"
echo "3. Commit the changes with: git add -A && git commit -m 'Clean up deprecated test files'"