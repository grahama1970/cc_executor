#!/usr/bin/env python3
"""
append_full_scripts_to_report.py - Append full script contents to issues report

This script reads the FINAL_ISSUES_REPORT_FOR_GEMINI.md and appends the full
contents of all referenced Python scripts at the end.
"""

import re
from pathlib import Path
from typing import List, Tuple

def find_script_references(report_content: str) -> List[str]:
    """Find all script paths mentioned in the report."""
    # Pattern to match script paths like src/xxx/yyy.py
    pattern = r'`(src/[^`]+\.py)`'
    matches = re.findall(pattern, report_content)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_scripts = []
    for script in matches:
        if script not in seen:
            seen.add(script)
            unique_scripts.append(script)
    
    return unique_scripts

def read_script(base_dir: Path, script_path: str) -> Tuple[str, str]:
    """Read a script file and return its path and content."""
    full_path = base_dir / script_path
    try:
        content = full_path.read_text()
        return script_path, content
    except Exception as e:
        return script_path, f"ERROR: Could not read file - {e}"

def create_full_scripts_section(base_dir: Path, script_paths: List[str]) -> str:
    """Create the markdown section with all script contents."""
    sections = ["\n\n## Appendix: Full Script Contents\n\n"]
    sections.append("Below are the complete contents of all scripts referenced in this report:\n")
    
    for i, script_path in enumerate(script_paths, 1):
        path, content = read_script(base_dir, script_path)
        
        # Determine status based on report content
        if "log_utils.py" in path:
            status = "✅ WORKING"
        elif "arango_init.py" in path:
            status = "⚠️ PARTIALLY FIXED"
        elif any(x in path for x in ["hybrid_search", "relationship_extraction", "memory_agent"]):
            status = "✅ REAL IMPLEMENTATION"
        else:
            status = "❌ NEEDS FIXES"
        
        sections.append(f"\n### {i}. `{path}` - {status}\n\n")
        sections.append("```python\n")
        sections.append(content)
        sections.append("\n```\n")
    
    return "".join(sections)

def main():
    """Main function to append scripts to report."""
    # Paths
    base_dir = Path("/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent")
    report_path = base_dir / "docs/issues/FINAL_ISSUES_REPORT_FOR_GEMINI.md"
    
    # Read the current report
    print(f"Reading report from: {report_path}")
    report_content = report_path.read_text()
    
    # Check if we already added the scripts
    if "## Appendix: Full Script Contents" in report_content:
        print("Scripts section already exists in report. Removing old version...")
        # Remove everything after the appendix marker
        report_content = report_content.split("## Appendix: Full Script Contents")[0].rstrip()
    
    # Find all script references
    script_paths = find_script_references(report_content)
    print(f"\nFound {len(script_paths)} unique script references:")
    for path in script_paths:
        print(f"  - {path}")
    
    # Create the full scripts section
    print("\nReading script contents...")
    scripts_section = create_full_scripts_section(base_dir, script_paths)
    
    # Append to report
    updated_report = report_content + scripts_section
    
    # Write back
    report_path.write_text(updated_report)
    print(f"\n✅ Successfully appended {len(script_paths)} scripts to the report")
    print(f"Updated report saved to: {report_path}")
    
    # Show summary
    total_lines = updated_report.count('\n')
    print(f"\nReport now contains {total_lines} lines")

if __name__ == "__main__":
    main()