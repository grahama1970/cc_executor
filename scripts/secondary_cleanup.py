#!/usr/bin/env python3
"""
Secondary cleanup script to handle remaining files
"""
import os
import shutil
from pathlib import Path

def cleanup_remaining_files(project_root: Path, dry_run: bool = True):
    """Clean up remaining files in root directory."""
    
    # Files to move/delete
    actions = [
        # Test files -> archive/old_tests
        ("test_edge_cases_actual.py", "archive/old_tests"),
        ("test_edge_cases_direct.py", "archive/old_tests"),
        ("test_integration_direct.py", "archive/old_tests"),
        
        # Scripts -> appropriate location
        ("add_checkboxes_to_scenarios.py", "scripts/fixes"),
        ("execute_mcp_arango_tests.py", "scripts/debug"),
        ("final_fix.py", "scripts/fixes"),
        ("scenarios_9_10_summary.py", "archive/scenarios"),
        
        # Logs -> logs directory or delete
        ("async_arango_test.log", "logs"),
        ("sequence_optimizer.log", "logs"),
        ("tool_journey.log", "logs"),
        
        # Documentation -> docs
        ("ARANGO_FAISS_READINESS_REPORT.md", "docs/reports"),
        ("GPU_DETECTION_IMPLEMENTATION.md", "docs/reports"),
        ("INTEGRATION_SCENARIOS_EXECUTION_REPORT.md", "docs/reports"),
        ("KILOCODE_INTEGRATION_SUMMARY.md", "docs/reports"),
        ("Q_LEARNING_REWARD_SYSTEM_GUIDE.md", "docs/guides"),
        ("QUICK_START_GUIDE.md", "docs"),
        ("PROJECT_STRUCTURE.md", "docs"),
        ("GEMINI.md", "docs"),
        ("CLEANUP_SUMMARY_20250714.md", "archive/docs"),
    ]
    
    # Delete old error logs
    delete_patterns = [
        "gemini_error_*.log",
    ]
    
    print(f"Secondary cleanup (dry_run={dry_run})")
    print("=" * 60)
    
    # Process moves
    for filename, dest_dir in actions:
        file_path = project_root / filename
        if file_path.exists():
            dest_path = project_root / dest_dir / filename
            print(f"MOVE: {filename} -> {dest_dir}/")
            if not dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_path))
    
    # Process deletions
    for pattern in delete_patterns:
        for file_path in project_root.glob(pattern):
            print(f"DELETE: {file_path.name}")
            if not dry_run:
                file_path.unlink()
    
    print("\nSecondary cleanup complete!")

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    cleanup_remaining_files(Path.cwd(), dry_run=dry_run)