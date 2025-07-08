#!/bin/bash
# Archive deprecated and unreferenced files
# This script moves deprecated files to organized archive locations

set -e

echo "=== Archiving Deprecated Files ==="
echo "This script will move deprecated and unreferenced files to the archive directory"
echo

# Create archive structure
ARCHIVE_BASE="/home/graham/workspace/experiments/cc_executor/archive"
ARCHIVE_DATE=$(date +%Y%m%d)
ARCHIVE_DIR="$ARCHIVE_BASE/cleanup_$ARCHIVE_DATE"

echo "Creating archive directory structure..."
mkdir -p "$ARCHIVE_DIR/src/prompts/commands"
mkdir -p "$ARCHIVE_DIR/src/prompts/utilities"
mkdir -p "$ARCHIVE_DIR/src/cli/prompts/scripts"
mkdir -p "$ARCHIVE_DIR/src/cli"
mkdir -p "$ARCHIVE_DIR/src/servers"
mkdir -p "$ARCHIVE_DIR/src/utils"
mkdir -p "$ARCHIVE_DIR/src/hooks/prompts/scripts"
mkdir -p "$ARCHIVE_DIR/src/hooks/tests"
mkdir -p "$ARCHIVE_DIR/src/client/prompts/scripts"
mkdir -p "$ARCHIVE_DIR/src/api"
mkdir -p "$ARCHIVE_DIR/src/core/prompts/scripts"
mkdir -p "$ARCHIVE_DIR/src/examples"
mkdir -p "$ARCHIVE_DIR/src/tasks/executor/archive"
mkdir -p "$ARCHIVE_DIR/docs/deprecated"
mkdir -p "$ARCHIVE_DIR/scripts"
mkdir -p "$ARCHIVE_DIR/tests/stress"

# Function to move file if it exists
move_if_exists() {
    local src=$1
    local dest=$2
    if [ -f "$src" ]; then
        echo "Moving: $src"
        mv "$src" "$dest"
    elif [ -d "$src" ]; then
        echo "Moving directory: $src"
        mv "$src" "$dest"
    else
        echo "⏭️  Not found: $src"
    fi
}

echo
echo "=== Moving Unreferenced Python Files ==="

# Prompts commands
move_if_exists "src/cc_executor/prompts/commands/transcript_helper.py" "$ARCHIVE_DIR/src/prompts/commands/"
move_if_exists "src/cc_executor/prompts/commands/verify_marker.py" "$ARCHIVE_DIR/src/prompts/commands/"
move_if_exists "src/cc_executor/prompts/commands/check_file_rules.py" "$ARCHIVE_DIR/src/prompts/commands/"

# Prompts utilities
move_if_exists "src/cc_executor/prompts/cc_execute_utils.py" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/utilities/claude_transcript_stream.py" "$ARCHIVE_DIR/src/prompts/utilities/"

# CLI files
move_if_exists "src/cc_executor/cli/prompts/scripts/assess_all_cli_usage_v2.py" "$ARCHIVE_DIR/src/cli/prompts/scripts/"
move_if_exists "src/cc_executor/cli/prompts/scripts/assess_all_cli_usage.py" "$ARCHIVE_DIR/src/cli/prompts/scripts/"
move_if_exists "src/cc_executor/cli/demo_main_usage.py" "$ARCHIVE_DIR/src/cli/"

# Servers
move_if_exists "src/cc_executor/servers/mcp_cc_execute.py" "$ARCHIVE_DIR/src/servers/"
move_if_exists "src/cc_executor/servers/mcp_server_fastmcp.py" "$ARCHIVE_DIR/src/servers/"

# Utils
move_if_exists "src/cc_executor/utils/file_utils.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/smart_timeout_defaults.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/concurrent_executor.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/initialize_litellm_cache.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/process_executor.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/multimodal_utils.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/log_monitor.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/reflection_parser.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/task_loader.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/timeout_recovery_manager.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/log_utils.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/redis_similarity_search.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/verification.py" "$ARCHIVE_DIR/src/utils/"
move_if_exists "src/cc_executor/utils/enhanced_timeout_calculator.py" "$ARCHIVE_DIR/src/utils/"

# Hooks
move_if_exists "src/cc_executor/hooks/prompts/scripts/assess_all_hooks_usage.py" "$ARCHIVE_DIR/src/hooks/prompts/scripts/"
move_if_exists "src/cc_executor/hooks/prompts/scripts/ASSESS_ALL_HOOKS_USAGE_extracted.py" "$ARCHIVE_DIR/src/hooks/prompts/scripts/"
move_if_exists "src/cc_executor/hooks/claude_structured_response.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/task_list_preflight_check.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/arxiv_mcp_debug_template.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/hook_enforcement.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/task_list_completion_report.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/check_cli_entry_points.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/prove_hooks_broken.py" "$ARCHIVE_DIR/src/hooks/"
move_if_exists "src/cc_executor/hooks/review_code_changes.py" "$ARCHIVE_DIR/src/hooks/"

# Hook test files
move_if_exists "src/cc_executor/hooks/debug_hooks.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/debug_hooks_thoroughly.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_all_three_hooks.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_claude_hooks_debug.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_claude_no_api_key.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_claude_tools_directly.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_hook_demo.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_hooks_correct.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_hooks_really_work.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_hooks_simple.py" "$ARCHIVE_DIR/src/hooks/tests/"
move_if_exists "src/cc_executor/hooks/test_pre_post_hooks.py" "$ARCHIVE_DIR/src/hooks/tests/"

# Client
move_if_exists "src/cc_executor/client/prompts/scripts/assess_all_client_usage.py" "$ARCHIVE_DIR/src/client/prompts/scripts/"

# API
move_if_exists "src/cc_executor/api/mcp_manifest.py" "$ARCHIVE_DIR/src/api/"

# Core
move_if_exists "src/cc_executor/core/prompts/scripts/assess_with_claude_analysis.py" "$ARCHIVE_DIR/src/core/prompts/scripts/"

# Examples
move_if_exists "src/cc_executor/examples/simple_example.py" "$ARCHIVE_DIR/src/examples/"
move_if_exists "src/cc_executor/examples/factorial.py" "$ARCHIVE_DIR/src/examples/"

# Tasks
move_if_exists "src/cc_executor/tasks/executor/archive/002_websocket_reliability_implementation.py" "$ARCHIVE_DIR/src/tasks/executor/archive/"
move_if_exists "src/cc_executor/tasks/executor/archive/003_websocket_reliability_implementation.py" "$ARCHIVE_DIR/src/tasks/executor/archive/"
move_if_exists "src/cc_executor/tasks/executor/archive/001_websocket_reliability_implementation.py" "$ARCHIVE_DIR/src/tasks/executor/archive/"

echo
echo "=== Moving Deprecated Documentation ==="

# Docs
move_if_exists "src/cc_executor/docs/assessments" "$ARCHIVE_DIR/docs/deprecated/"
move_if_exists "src/cc_executor/docs/conversations" "$ARCHIVE_DIR/docs/deprecated/"
move_if_exists "src/cc_executor/docs/planning" "$ARCHIVE_DIR/docs/deprecated/"
move_if_exists "src/cc_executor/docs/tasks" "$ARCHIVE_DIR/docs/deprecated/"

# Prompts docs
move_if_exists "src/cc_executor/prompts/SETUP_TEMPLATE_README.md" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/answer.txt" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/cc_execute_correct.md" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/cc_execute_simple.md" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/docker_compose_config.py" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/docker_deployment.py" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/setup_template.py" "$ARCHIVE_DIR/src/prompts/"
move_if_exists "src/cc_executor/prompts/websocket_orchestrator.py" "$ARCHIVE_DIR/src/prompts/"

# Test debug files
move_if_exists "tests/stress/debug_websocket.py" "$ARCHIVE_DIR/tests/stress/"
move_if_exists "tests/stress/utils/debug_handler.py" "$ARCHIVE_DIR/tests/stress/"

# Scripts
move_if_exists "scripts/debug_server.py" "$ARCHIVE_DIR/scripts/"
move_if_exists "scripts/websocket_test_summary.txt" "$ARCHIVE_DIR/scripts/"

echo
echo "=== Creating Archive Summary ==="

# Create archive summary
cat > "$ARCHIVE_DIR/ARCHIVE_SUMMARY.md" << 'EOF'
# Deprecated Files Archive

Date: $(date)

## Purpose
This archive contains files that were identified as:
- Not imported or referenced anywhere in the codebase
- Deprecated or superseded by newer implementations
- Old test files that have been replaced
- Documentation for obsolete features

## Categories

### Unreferenced Python Modules
- Files in src/ that were not imported by any other module
- Utility scripts that are no longer used
- Old implementations that have been replaced

### Deprecated Hooks
- Test files for hook functionality that have been consolidated
- Old hook implementations that are no longer used

### Old Documentation
- Conversation logs from development
- Planning documents that are no longer relevant
- Task lists from completed work

### Duplicate Implementations
Note: Some files may have been duplicates. The following files exist in multiple locations:
- cc_execute.py (exists in prompts/commands/, prompts/, and client/)

## Restoration
If any of these files are needed, they can be restored from this archive or from git history.

## Cleanup Stats
Total files archived: $(find "$ARCHIVE_DIR" -type f | wc -l)
Total size: $(du -sh "$ARCHIVE_DIR" | cut -f1)
EOF

echo
echo "=== Cleanup Complete ==="
echo "Archived files location: $ARCHIVE_DIR"
echo "Total files archived: $(find "$ARCHIVE_DIR" -type f | wc -l)"
echo "Total size: $(du -sh "$ARCHIVE_DIR" | cut -f1)"

echo
echo "=== Important Notes ==="
echo "1. Some files marked for deletion in git status were not found (already deleted)"
echo "2. Empty __init__.py files were not moved (they may be needed for Python packages)"
echo "3. Duplicate cc_execute.py files need manual review to determine which is canonical"

echo
echo "Next steps:"
echo "1. Review the archive to ensure no critical files were moved"
echo "2. Test that the project still works correctly"
echo "3. Commit the changes: git add -A && git commit -m 'Archive deprecated and unreferenced files'"
echo "4. Consider removing empty directories left behind"