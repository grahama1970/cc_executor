#!/usr/bin/env python3
"""
gemini_code_processor.py - Extract and process code from Gemini markdown responses

This script:
1. Extracts code from Gemini's markdown response
2. Places files in tmp/ directory for analysis
3. Compares with existing code
4. Provides update recommendations
"""

import re
import os
import json
import argparse
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import shutil
import subprocess
import sys


class GeminiCodeProcessor:
    """Process code from Gemini markdown responses."""
    
    def __init__(self, markdown_file: Path, project_root: Path, tmp_dir: Optional[Path] = None):
        self.markdown_file = markdown_file
        self.project_root = project_root
        self.tmp_dir = tmp_dir or project_root / "tmp" / f"gemini_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.extracted_files: List[Dict[str, any]] = []
        self.comparison_results: List[Dict[str, any]] = []
        
    def extract_all_code(self) -> Dict[str, any]:
        """Extract all code files from Gemini's markdown."""
        print(f"📂 Extracting code from: {self.markdown_file}")
        print(f"📁 Output directory: {self.tmp_dir}")
        
        # Create tmp directory
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Read markdown content
        content = self.markdown_file.read_text()
        
        # Pattern to match code blocks with file markers
        pattern = r'<!-- CODE_FILE_START: (.*?) -->\n```(?:.*?)\n(.*?)\n```\n<!-- CODE_FILE_END: \1 -->'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            file_path = match.group(1)
            code_content = match.group(2)
            
            # Create full path in tmp directory
            full_path = self.tmp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(code_content)
            
            # Check if file exists in project
            original_path = self.project_root / file_path
            exists_in_project = original_path.exists()
            
            self.extracted_files.append({
                'path': file_path,
                'tmp_path': str(full_path),
                'original_path': str(original_path) if exists_in_project else None,
                'exists_in_project': exists_in_project,
                'size': len(code_content),
                'lines': code_content.count('\n') + 1
            })
            
            print(f"✓ Extracted: {file_path} ({len(code_content)} bytes)")
        
        # Save extraction metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.markdown_file),
            'tmp_dir': str(self.tmp_dir),
            'project_root': str(self.project_root),
            'files_extracted': len(self.extracted_files),
            'files': self.extracted_files
        }
        
        metadata_path = self.tmp_dir / "EXTRACTION_METADATA.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        print(f"\n✅ Extracted {len(self.extracted_files)} files to {self.tmp_dir}")
        return metadata
    
    def validate_extracted_code(self) -> List[Dict[str, any]]:
        """Validate Python syntax and imports in extracted files."""
        validation_results = []
        
        print("\n🔍 Validating extracted code...")
        
        for file_info in self.extracted_files:
            if file_info['path'].endswith('.py'):
                tmp_path = Path(file_info['tmp_path'])
                issues = []
                
                # Check Python syntax
                try:
                    compile(tmp_path.read_text(), tmp_path, 'exec')
                    print(f"✓ Syntax OK: {file_info['path']}")
                except SyntaxError as e:
                    issues.append(f"Syntax error: {e}")
                    print(f"✗ Syntax error in {file_info['path']}: {e}")
                
                # Check imports
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(tmp_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    issues.append(f"Import error: {result.stderr}")
                
                validation_results.append({
                    'file': file_info['path'],
                    'valid': len(issues) == 0,
                    'issues': issues
                })
        
        return validation_results
    
    def compare_with_existing(self) -> List[Dict[str, any]]:
        """Compare extracted files with existing project files."""
        print("\n📊 Comparing with existing files...")
        
        for file_info in self.extracted_files:
            if file_info['exists_in_project']:
                tmp_path = Path(file_info['tmp_path'])
                original_path = Path(file_info['original_path'])
                
                # Read both files
                tmp_content = tmp_path.read_text().splitlines()
                original_content = original_path.read_text().splitlines()
                
                # Generate diff
                diff = list(difflib.unified_diff(
                    original_content,
                    tmp_content,
                    fromfile=f"original/{file_info['path']}",
                    tofile=f"gemini/{file_info['path']}",
                    lineterm=''
                ))
                
                # Count changes
                additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
                
                self.comparison_results.append({
                    'file': file_info['path'],
                    'additions': additions,
                    'deletions': deletions,
                    'total_changes': additions + deletions,
                    'diff_preview': '\n'.join(diff[:50]) if diff else "No changes"
                })
                
                if additions + deletions > 0:
                    print(f"📝 {file_info['path']}: +{additions} -{deletions} lines")
                else:
                    print(f"✓ {file_info['path']}: No changes")
            else:
                print(f"🆕 {file_info['path']}: New file")
                self.comparison_results.append({
                    'file': file_info['path'],
                    'status': 'new_file',
                    'additions': file_info['lines'],
                    'deletions': 0
                })
        
        return self.comparison_results
    
    def generate_update_script(self) -> Path:
        """Generate a script to apply the changes."""
        script_path = self.tmp_dir / "apply_updates.sh"
        
        script_content = [
            "#!/bin/bash",
            "# Auto-generated script to apply Gemini's code updates",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Source: {self.markdown_file.name}",
            "",
            "set -e  # Exit on error",
            "",
            "echo '🚀 Applying Gemini code updates...'",
            ""
        ]
        
        # Add backup commands
        script_content.append("# Create backups")
        for file_info in self.extracted_files:
            if file_info['exists_in_project']:
                script_content.append(f"cp '{file_info['original_path']}' '{file_info['original_path']}.backup'")
        
        script_content.append("")
        script_content.append("# Apply updates")
        
        # Add copy commands
        for file_info in self.extracted_files:
            script_content.append(f"cp '{file_info['tmp_path']}' '{file_info['original_path']}'")
            script_content.append(f"echo '✓ Updated: {file_info['path']}'")
        
        script_content.append("")
        script_content.append("echo '✅ All updates applied successfully!'")
        
        # Write script
        script_path.write_text('\n'.join(script_content))
        script_path.chmod(0o755)
        
        print(f"\n📄 Generated update script: {script_path}")
        return script_path
    
    def generate_report(self) -> Dict[str, any]:
        """Generate a comprehensive report of the extraction and analysis."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.markdown_file),
            'tmp_directory': str(self.tmp_dir),
            'extraction': {
                'total_files': len(self.extracted_files),
                'new_files': sum(1 for f in self.extracted_files if not f['exists_in_project']),
                'modified_files': sum(1 for f in self.extracted_files if f['exists_in_project']),
                'total_lines': sum(f['lines'] for f in self.extracted_files)
            },
            'validation': self.validate_extracted_code(),
            'comparison': self.comparison_results,
            'files': self.extracted_files,
            'update_script': str(self.tmp_dir / "apply_updates.sh")
        }
        
        # Save report
        report_path = self.tmp_dir / "ANALYSIS_REPORT.json"
        report_path.write_text(json.dumps(report, indent=2))
        
        # Generate markdown summary
        summary = [
            f"# Gemini Code Analysis Report",
            f"",
            f"**Generated**: {report['timestamp']}",
            f"**Source**: `{Path(report['source']).name}`",
            f"**Output**: `{report['tmp_directory']}`",
            f"",
            f"## Summary",
            f"- Total files extracted: {report['extraction']['total_files']}",
            f"- New files: {report['extraction']['new_files']}",
            f"- Modified files: {report['extraction']['modified_files']}",
            f"- Total lines of code: {report['extraction']['total_lines']}",
            f"",
            f"## File Changes",
            f""
        ]
        
        for comp in self.comparison_results:
            if comp.get('status') == 'new_file':
                summary.append(f"- 🆕 `{comp['file']}` (new file, {comp['additions']} lines)")
            elif comp['total_changes'] > 0:
                summary.append(f"- 📝 `{comp['file']}` (+{comp['additions']} -{comp['deletions']})")
            else:
                summary.append(f"- ✓ `{comp['file']}` (no changes)")
        
        summary.extend([
            f"",
            f"## Next Steps",
            f"1. Review extracted files in: `{report['tmp_directory']}`",
            f"2. Check validation results for any syntax errors",
            f"3. Review diffs for each modified file",
            f"4. Run: `bash {report['update_script']}` to apply changes",
            f"",
            f"## Commands",
            f"```bash",
            f"# Review extracted files",
            f"ls -la {report['tmp_directory']}",
            f"",
            f"# Check specific file diff",
            f"diff original_file {report['tmp_directory']}/path/to/file",
            f"",
            f"# Apply all updates",
            f"bash {report['update_script']}",
            f"```"
        ])
        
        summary_path = self.tmp_dir / "SUMMARY.md"
        summary_path.write_text('\n'.join(summary))
        
        print(f"\n📊 Report saved to: {report_path}")
        print(f"📄 Summary saved to: {summary_path}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description='Extract and process code from Gemini markdown responses'
    )
    parser.add_argument('markdown_file', help='Gemini markdown response file')
    parser.add_argument('--project-root', default='.', help='Project root directory (default: current dir)')
    parser.add_argument('--tmp-dir', help='Custom tmp directory (default: auto-generated)')
    parser.add_argument('--apply', action='store_true', help='Automatically apply updates')
    parser.add_argument('--no-validation', action='store_true', help='Skip code validation')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = GeminiCodeProcessor(
        markdown_file=Path(args.markdown_file),
        project_root=Path(args.project_root).resolve(),
        tmp_dir=Path(args.tmp_dir) if args.tmp_dir else None
    )
    
    # Extract code
    metadata = processor.extract_all_code()
    
    # Validate unless skipped
    if not args.no_validation:
        validation_results = processor.validate_extracted_code()
        invalid_files = [v for v in validation_results if not v['valid']]
        if invalid_files:
            print(f"\n⚠️  Found {len(invalid_files)} files with validation errors")
            for invalid in invalid_files:
                print(f"  - {invalid['file']}: {invalid['issues']}")
    
    # Compare with existing
    processor.compare_with_existing()
    
    # Generate update script
    update_script = processor.generate_update_script()
    
    # Generate report
    report = processor.generate_report()
    
    print(f"\n✅ Processing complete!")
    print(f"📂 Files extracted to: {processor.tmp_dir}")
    print(f"📊 Review the analysis: {processor.tmp_dir}/SUMMARY.md")
    
    # Apply updates if requested
    if args.apply:
        print(f"\n🚀 Applying updates...")
        result = subprocess.run(['bash', str(update_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Updates applied successfully!")
        else:
            print(f"❌ Error applying updates: {result.stderr}")
            sys.exit(1)


if __name__ == "__main__":
    main()