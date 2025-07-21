#!/usr/bin/env python3
"""
Final cleanup script for test directories and remaining files
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def final_cleanup(project_root: Path, dry_run: bool = True):
    """Final cleanup of test directories and files."""
    
    print(f"Final cleanup (dry_run={dry_run})")
    print("=" * 60)
    
    # 1. Move old stress test results
    stress_results = project_root / "tests/stress_test_results"
    if stress_results.exists():
        dest = project_root / "archive/stress_test_results"
        print(f"MOVE: tests/stress_test_results/ -> archive/stress_test_results/")
        if not dry_run:
            shutil.move(str(stress_results), str(dest))
    
    # 2. Archive test_results directory (old results)
    test_results = project_root / "tests/test_results"
    if test_results.exists():
        # Check if it has anything valuable
        valuable_files = list(test_results.glob("**/*.md")) + list(test_results.glob("**/*.json"))
        if valuable_files:
            dest = project_root / "archive/old_test_results"
            print(f"MOVE: tests/test_results/ -> archive/old_test_results/")
            if not dry_run:
                shutil.move(str(test_results), str(dest))
    
    # 3. Clean up test project directories (they're fixtures)
    # Leave them - they're test fixtures for integration tests
    print("KEEP: tests/test_project/ and tests/test_project_alt/ (test fixtures)")
    
    # 4. Move reorganization summary to archive
    reorg_summary = project_root / "reorganization_summary_20250721_070805.json"
    if reorg_summary.exists():
        dest = project_root / "archive/reorganization_summary_20250721_070805.json"
        print(f"MOVE: reorganization_summary_20250721_070805.json -> archive/")
        if not dry_run:
            shutil.move(str(reorg_summary), str(dest))
    
    # 5. Move cleanup summaries to docs
    cleanup_files = [
        "CLEANUP_SUMMARY_20250121.md",
        "CLEANUP_COMPLETE_20250121.md"
    ]
    for filename in cleanup_files:
        file_path = project_root / filename
        if file_path.exists():
            dest = project_root / "docs/cleanup" / filename
            print(f"MOVE: {filename} -> docs/cleanup/")
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest))
    
    # 6. Important test files to keep in tests/
    important_tests = [
        "stress_test_all_versions.py",
        "test_all_mcp_servers.py", 
        "test_mcp_tools_comprehensive.py",
        "test_mcp_tools_directly.py"
    ]
    print("\nKEEPING these important test files in tests/:")
    for test in important_tests:
        print(f"  ✓ tests/{test}")
    
    # 7. Keep these essential files in root
    essential_root = [
        "CHANGELOG.md",
        "README.md",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "MANIFEST.in",
        "vertex_ai_service_account.json"
    ]
    print("\nKEEPING these essential files in root:")
    for file in essential_root:
        print(f"  ✓ {file}")
    
    print("\n" + "=" * 60)
    print("Final cleanup complete!")
    
    if dry_run:
        print("\nThis was a DRY RUN. Run with --execute to perform cleanup.")

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    final_cleanup(Path.cwd(), dry_run=dry_run)