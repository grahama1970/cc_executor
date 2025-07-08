#!/bin/bash
# Archive old test results from June 2025
# This script moves old test outputs to the archive directory

set -e

echo "=== Archiving Old Test Results ==="
echo "This script will move old test outputs from June 2025 to the archive directory"
echo

# Create archive directory structure
ARCHIVE_DIR="test_results/archive/stress_tests_june_2025"
echo "Creating archive directory: $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR"

# Archive test_results/stress/ directory
if [ -d "test_results/stress" ]; then
    echo "Moving test_results/stress/ to archive..."
    mv test_results/stress/* "$ARCHIVE_DIR/" 2>/dev/null || true
    rmdir test_results/stress 2>/dev/null || true
    echo "✅ Archived test_results/stress/"
else
    echo "⏭️  test_results/stress/ not found or already archived"
fi

# Archive stress/test_outputs/ directory
if [ -d "stress/test_outputs" ]; then
    echo "Moving stress/test_outputs/ to archive..."
    mkdir -p "$ARCHIVE_DIR/test_outputs"
    mv stress/test_outputs/* "$ARCHIVE_DIR/test_outputs/" 2>/dev/null || true
    rmdir stress/test_outputs 2>/dev/null || true
    echo "✅ Archived stress/test_outputs/"
else
    echo "⏭️  stress/test_outputs/ not found or already archived"
fi

# Count archived files
if [ -d "$ARCHIVE_DIR" ]; then
    FILE_COUNT=$(find "$ARCHIVE_DIR" -type f | wc -l)
    DIR_SIZE=$(du -sh "$ARCHIVE_DIR" | cut -f1)
    echo
    echo "=== Archive Summary ==="
    echo "Archived $FILE_COUNT files"
    echo "Total size: $DIR_SIZE"
    echo "Location: $ARCHIVE_DIR"
fi

# Create/update .gitignore for node_modules
GITIGNORE_FILE=".gitignore"
if ! grep -q "node_modules/" "$GITIGNORE_FILE" 2>/dev/null; then
    echo
    echo "Adding node_modules/ to .gitignore..."
    echo "" >> "$GITIGNORE_FILE"
    echo "# Node modules (auto-added by archive script)" >> "$GITIGNORE_FILE"
    echo "node_modules/" >> "$GITIGNORE_FILE"
    echo "✅ Updated .gitignore"
fi

# Create archive README
README_FILE="$ARCHIVE_DIR/README.md"
cat > "$README_FILE" << 'EOF'
# Archived Stress Test Results - June 2025

This directory contains archived stress test results from June 26-30, 2025.

## Contents

- **logs/** - Stress test execution logs (83 files)
- **metrics/** - Test metrics in JSON format (6 files)
- **reports/** - Comprehensive test reports in Markdown (7 files)
- **smart_test/** - Smart test execution logs (2 files)
- **test_outputs/** - Various test output files

## Purpose

These files are kept for historical reference and analysis but are not needed for current development. They document the stress testing phase of the cc_executor project in June 2025.

## Archival Date

Archived on: $(date)
Archived by: archive_old_tests.sh script
EOF

echo
echo "✅ Archive complete!"
echo
echo "Next steps:"
echo "1. Review the archived files in: $ARCHIVE_DIR"
echo "2. Commit the changes with: git add -A && git commit -m 'Archive June 2025 stress test results'"
echo "3. Consider adding more patterns to .gitignore if needed"