#!/usr/bin/env python3
"""
Project Reorganization Script for CC Executor
This script implements the cleanup plan from PROJECT_REORGANIZATION_PLAN_2025.md
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json
import sys

# Add to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ProjectReorganizer:
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.moves = []
        self.deletes = []
        self.creates = []
        
    def log_action(self, action: str, source: str, dest: str = None):
        """Log an action to be taken."""
        if action == "move":
            self.moves.append((source, dest))
            print(f"MOVE: {source} -> {dest}")
        elif action == "delete":
            self.deletes.append(source)
            print(f"DELETE: {source}")
        elif action == "create":
            self.creates.append(source)
            print(f"CREATE: {source}")
            
    def create_directories(self):
        """Create new directory structure."""
        dirs_to_create = [
            "archive/old_tests",
            "archive/scenarios",
            "archive/outputs",
            "scripts/fixes",
            "scripts/debug",
            "scripts/setup",
            "scripts/analysis",
            "scripts/mcp",
            "config",
            "docs/mcp_servers/individual_server_docs",
            "tests/mcp_servers/scenarios",
            "tests/fixtures",
            "tests/archive"
        ]
        
        for dir_path in dirs_to_create:
            full_path = self.project_root / dir_path
            self.log_action("create", str(full_path))
            if not self.dry_run:
                full_path.mkdir(parents=True, exist_ok=True)
                
    def cleanup_root_directory(self):
        """Move test files and scripts from root to appropriate locations."""
        
        # Test files to move
        test_patterns = [
            ("test_arango_*.py", "archive/old_tests"),
            ("test_gemini_*.py", "archive/old_tests"),
            ("test_gpu_*.py", "archive/old_tests"),
            ("test_hello_universal_llm.py", "archive/old_tests"),
            ("test_infrastructure_readiness.py", "archive/old_tests"),
            ("test_kilocode_*.py", "archive/old_tests"),
            ("test_llm_*.py", "archive/old_tests"),
            ("test_mcp_*.py", "archive/old_tests"),
            ("test_posthook.py", "archive/old_tests"),
            ("test_qlearning_integration.py", "archive/old_tests"),
            ("test_review_non_interactive.py", "archive/old_tests"),
            ("test_scenario_16_pattern_discovery.py", "archive/old_tests"),
            ("test_single_file_review.py", "archive/old_tests"),
            ("test_two_level_review.py", "archive/old_tests"),
            ("test_universal_llm.py", "archive/old_tests"),
        ]
        
        # Fix scripts to move
        fix_patterns = [
            ("fix_*.py", "scripts/fixes"),
            ("update_*.py", "scripts/fixes"),
            ("verify_*.py", "scripts/fixes"),
        ]
        
        # Scenario files
        scenario_patterns = [
            ("scenario_*.py", "archive/scenarios"),
            ("create_test_data_scenarios_9_10.py", "archive/scenarios"),
            ("execute_scenario_16.py", "archive/scenarios"),
        ]
        
        # Debug scripts
        debug_patterns = [
            ("debug_*.py", "scripts/debug"),
            ("diagnose_mcp_issues.py", "scripts/debug"),
        ]
        
        # Setup scripts
        setup_patterns = [
            ("install_universal_llm_mcp.py", "scripts/setup"),
            ("create_mcp_logger_package.py", "scripts/setup"),
        ]
        
        # Process all patterns
        all_patterns = test_patterns + fix_patterns + scenario_patterns + debug_patterns + setup_patterns
        
        for pattern, dest_dir in all_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    dest_path = self.project_root / dest_dir / file_path.name
                    self.log_action("move", str(file_path), str(dest_path))
                    if not self.dry_run:
                        shutil.move(str(file_path), str(dest_path))
                        
    def cleanup_outputs(self):
        """Remove or archive old output files."""
        
        # Files to delete
        delete_patterns = [
            "gemini_output_*.json",
            "raw_output.txt",
            "test_results_*.json",
        ]
        
        for pattern in delete_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    self.log_action("delete", str(file_path))
                    if not self.dry_run:
                        file_path.unlink()
                        
    def move_config_files(self):
        """Move configuration files to config directory."""
        
        config_files = [
            "add_arango_mcp_config.json",
            "add_universal_llm_executor_config.json",
            "stress_test_launch_plan.json",
        ]
        
        # Note: vertex_ai_service_account.json stays in root (gitignored)
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                dest_path = self.project_root / "config" / file_path.name
                self.log_action("move", str(file_path), str(dest_path))
                if not self.dry_run:
                    shutil.move(str(file_path), str(dest_path))
                    
    def reorganize_mcp_docs(self):
        """Move MCP documentation to centralized location."""
        
        source_dir = self.project_root / "src/cc_executor/servers/docs"
        dest_dir = self.project_root / "docs/mcp_servers"
        
        if source_dir.exists():
            # Move specific important files
            important_files = [
                "MCP_CHECKLIST.md",
                "ARANGO_TOOLS_README.md",
                "MCP_ARCHITECTURE_README.md",
                "QUICK_GUIDE.md"
            ]
            
            for file_name in important_files:
                file_path = source_dir / file_name
                if file_path.exists():
                    dest_path = dest_dir / file_name
                    self.log_action("move", str(file_path), str(dest_path))
                    if not self.dry_run:
                        shutil.move(str(file_path), str(dest_path))
                        
    def generate_summary(self):
        """Generate a summary of actions taken."""
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "directories_created": len(self.creates),
            "files_moved": len(self.moves),
            "files_deleted": len(self.deletes),
            "actions": {
                "creates": self.creates,
                "moves": [(str(s), str(d)) for s, d in self.moves],
                "deletes": self.deletes
            }
        }
        
        summary_path = self.project_root / f"reorganization_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not self.dry_run:
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
                
        return summary
        
    def run(self):
        """Execute the reorganization."""
        
        print(f"Starting project reorganization (dry_run={self.dry_run})")
        print("=" * 60)
        
        # Create new directories
        print("\n1. Creating directory structure...")
        self.create_directories()
        
        # Clean up root directory
        print("\n2. Cleaning up root directory...")
        self.cleanup_root_directory()
        
        # Clean up outputs
        print("\n3. Removing old output files...")
        self.cleanup_outputs()
        
        # Move config files
        print("\n4. Moving configuration files...")
        self.move_config_files()
        
        # Reorganize MCP docs
        print("\n5. Reorganizing MCP documentation...")
        self.reorganize_mcp_docs()
        
        # Generate summary
        print("\n6. Generating summary...")
        summary = self.generate_summary()
        
        print("\n" + "=" * 60)
        print(f"Reorganization complete!")
        print(f"Directories created: {len(self.creates)}")
        print(f"Files moved: {len(self.moves)}")
        print(f"Files deleted: {len(self.deletes)}")
        
        if self.dry_run:
            print("\nThis was a DRY RUN. No actual changes were made.")
            print("Run with --execute to perform the reorganization.")
            
        return summary


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reorganize CC Executor project structure")
    parser.add_argument("--execute", action="store_true", help="Actually perform the reorganization (default is dry run)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root directory")
    
    args = parser.parse_args()
    
    reorganizer = ProjectReorganizer(args.project_root, dry_run=not args.execute)
    reorganizer.run()
    

if __name__ == "__main__":
    main()