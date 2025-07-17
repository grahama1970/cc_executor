#!/usr/bin/env python3
"""
extract_code_from_markdown.py - Extract code files from markdown documentation

Extracts all code blocks marked with CODE_FILE_START/END markers and creates
the corresponding files in the correct directory structure.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python extract_code_from_markdown.py          # Runs working_usage() - stable, known to work
  python extract_code_from_markdown.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import json
from datetime import datetime
import sys


class CodeExtractor:
    """Extract code files from markdown with validation."""
    
    def __init__(self, markdown_file: Path, output_dir: Path):
        self.markdown_file = markdown_file
        self.output_dir = output_dir
        self.extracted_files: List[Dict[str, any]] = []
        self.errors: List[str] = []
        
    def extract(self) -> Dict[str, any]:
        """Extract all code files from markdown."""
        try:
            content = self.markdown_file.read_text()
        except Exception as e:
            self.errors.append(f"Failed to read markdown file: {e}")
            return self.generate_report()
        
        # Pattern to match code blocks with CODE_FILE markers
        pattern = r'<!-- CODE_FILE_START: (.*?) -->\n```(?:.*?)\n(.*?)\n```\n<!-- CODE_FILE_END: (.*?) -->'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            start_path = match.group(1).strip()
            code_content = match.group(2)
            end_path = match.group(3).strip()
            
            # Validate matching paths
            if start_path != end_path:
                self.errors.append(
                    f"Mismatched file paths: START={start_path}, END={end_path}"
                )
                continue
            
            # Create full path
            full_path = self.output_dir / start_path
            
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(code_content)
                
                self.extracted_files.append({
                    'path': start_path,
                    'size': len(code_content),
                    'lines': code_content.count('\n') + 1,
                    'language': self._detect_language(start_path)
                })
            except Exception as e:
                self.errors.append(f"Failed to write {start_path}: {e}")
        
        # Also extract metadata if present
        self._extract_metadata(content)
        
        return self.generate_report()
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'bash',
            '.env': 'env'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')
    
    def _extract_metadata(self, content: str) -> None:
        """Extract metadata section if present."""
        metadata_pattern = r'<!-- EXTRACTION_METADATA_START -->\n```json\n(.*?)\n```\n<!-- EXTRACTION_METADATA_END -->'
        
        match = re.search(metadata_pattern, content, re.DOTALL)
        if match:
            try:
                metadata = json.loads(match.group(1))
                self.metadata = metadata
            except json.JSONDecodeError as e:
                self.errors.append(f"Invalid JSON in metadata section: {e}")
    
    def generate_report(self) -> Dict[str, any]:
        """Generate extraction report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.markdown_file),
            'output_dir': str(self.output_dir),
            'files_extracted': len(self.extracted_files),
            'files': self.extracted_files,
            'errors': self.errors,
            'success': len(self.errors) == 0
        }
        
        if hasattr(self, 'metadata'):
            report['metadata'] = self.metadata
        
        return report
    
    def validate_extraction(self) -> List[str]:
        """Validate that all expected files were extracted."""
        issues = []
        
        # Check for Python syntax errors
        for file_info in self.extracted_files:
            if file_info['language'] == 'python':
                file_path = self.output_dir / file_info['path']
                try:
                    with open(file_path, 'r') as f:
                        compile(f.read(), file_path, 'exec')
                except SyntaxError as e:
                    issues.append(f"Syntax error in {file_info['path']}: {e}")
                except Exception as e:
                    issues.append(f"Error validating {file_info['path']}: {e}")
        
        # Check if metadata matches extracted files
        if hasattr(self, 'metadata') and 'total_files' in self.metadata:
            if self.metadata['total_files'] != len(self.extracted_files):
                issues.append(
                    f"Metadata mismatch: expected {self.metadata['total_files']} files, "
                    f"but extracted {len(self.extracted_files)}"
                )
        
        return issues


def extract_from_markdown(
    markdown_file: str,
    output_dir: str,
    validate: bool = False,
    report_file: Optional[str] = None
) -> Dict[str, any]:
    """Main extraction function."""
    extractor = CodeExtractor(
        Path(markdown_file),
        Path(output_dir)
    )
    
    report = extractor.extract()
    
    # Print summary
    print(f"\nExtraction Summary:")
    print(f"  Source: {markdown_file}")
    print(f"  Output: {output_dir}")
    print(f"  Files extracted: {report['files_extracted']}")
    
    if report['files']:
        print("\nExtracted files:")
        for file_info in report['files']:
            print(f"  - {file_info['path']} ({file_info['lines']} lines, {file_info['language']})")
    
    if report['errors']:
        print("\nErrors encountered:")
        for error in report['errors']:
            print(f"  - {error}")
    
    if validate:
        print("\nValidating extracted files...")
        issues = extractor.validate_extraction()
        if issues:
            print("Validation issues found:")
            for issue in issues:
                print(f"  - {issue}")
            report['validation_issues'] = issues
        else:
            print("All files validated successfully!")
    
    if report_file:
        Path(report_file).write_text(json.dumps(report, indent=2))
        print(f"\nDetailed report saved to: {report_file}")
    
    return report


async def working_usage():
    """Demonstrate extraction from a sample markdown file."""
    print("=== Testing Code Extraction from Markdown ===")
    
    # Create a sample markdown file
    sample_md = Path("/tmp/sample_code.md")
    sample_md.write_text("""# Sample Code Documentation

## Overview
This is a sample markdown file with embedded code.

## Code Files

<!-- CODE_FILE_START: src/hello.py -->
```python
#!/usr/bin/env python3
\"\"\"
hello.py - Simple greeting module
\"\"\"

def greet(name: str) -> str:
    \"\"\"Return a greeting message.\"\"\"
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))
```
<!-- CODE_FILE_END: src/hello.py -->

<!-- CODE_FILE_START: src/utils/helpers.py -->
```python
#!/usr/bin/env python3
\"\"\"
helpers.py - Utility functions
\"\"\"

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

def multiply(a: int, b: int) -> int:
    \"\"\"Multiply two numbers.\"\"\"
    return a * b
```
<!-- CODE_FILE_END: src/utils/helpers.py -->

<!-- CODE_FILE_START: requirements.txt -->
```text
requests>=2.31.0
pytest>=7.4.0
```
<!-- CODE_FILE_END: requirements.txt -->

## Extraction Metadata

<!-- EXTRACTION_METADATA_START -->
```json
{
  "total_files": 3,
  "languages": ["python", "text"],
  "test_command": "python src/hello.py",
  "notes": "Simple example project"
}
```
<!-- EXTRACTION_METADATA_END -->
""")
    
    # Extract to temporary directory
    output_dir = Path("/tmp/extracted_code")
    output_dir.mkdir(exist_ok=True)
    
    # Run extraction
    report = extract_from_markdown(
        str(sample_md),
        str(output_dir),
        validate=True,
        report_file="/tmp/extraction_report.json"
    )
    
    # Test that files were created
    hello_py = output_dir / "src" / "hello.py"
    helpers_py = output_dir / "src" / "utils" / "helpers.py"
    requirements = output_dir / "requirements.txt"
    
    print("\nVerifying extracted files:")
    for file_path in [hello_py, helpers_py, requirements]:
        if file_path.exists():
            print(f"  ✓ {file_path.relative_to(output_dir)} exists")
        else:
            print(f"  ✗ {file_path.relative_to(output_dir)} missing")
    
    # Test running the extracted code
    if hello_py.exists():
        print("\nTesting extracted code:")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(hello_py)],
            capture_output=True,
            text=True
        )
        print(f"  Output: {result.stdout.strip()}")
        print(f"  Success: {result.returncode == 0}")
    
    return report['success']


async def debug_function():
    """Test edge cases and error handling."""
    print("=== Debug Mode: Testing Edge Cases ===")
    
    # Test 1: Mismatched file markers
    print("\nTest 1: Mismatched file markers")
    bad_md = Path("/tmp/bad_format.md")
    bad_md.write_text("""# Bad Format Example

<!-- CODE_FILE_START: src/file1.py -->
```python
print("This won't extract")
```
<!-- CODE_FILE_END: src/different_file.py -->
""")
    
    output_dir = Path("/tmp/bad_extraction")
    output_dir.mkdir(exist_ok=True)
    
    report = extract_from_markdown(
        str(bad_md),
        str(output_dir),
        validate=True
    )
    
    print(f"  Errors detected: {len(report['errors'])}")
    
    # Test 2: Invalid Python syntax
    print("\nTest 2: Invalid Python syntax")
    syntax_md = Path("/tmp/syntax_error.md")
    syntax_md.write_text("""# Syntax Error Example

<!-- CODE_FILE_START: bad_syntax.py -->
```python
def broken_function(
    print("Missing closing parenthesis"
```
<!-- CODE_FILE_END: bad_syntax.py -->
""")
    
    output_dir2 = Path("/tmp/syntax_extraction")
    output_dir2.mkdir(exist_ok=True)
    
    report2 = extract_from_markdown(
        str(syntax_md),
        str(output_dir2),
        validate=True
    )
    
    print(f"  Files extracted: {report2['files_extracted']}")
    print(f"  Validation issues: {len(report2.get('validation_issues', []))}")
    
    # Test 3: Large file extraction
    print("\nTest 3: Large file extraction")
    large_md = Path("/tmp/large_file.md")
    large_content = """# Large File Test

<!-- CODE_FILE_START: large_data.py -->
```python
# Large file with many lines
data = [
"""
    # Add 1000 lines
    for i in range(1000):
        large_content += f"    {i},  # Line {i}\n"
    
    large_content += """
]
```
<!-- CODE_FILE_END: large_data.py -->
"""
    large_md.write_text(large_content)
    
    output_dir3 = Path("/tmp/large_extraction")
    output_dir3.mkdir(exist_ok=True)
    
    report3 = extract_from_markdown(
        str(large_md),
        str(output_dir3)
    )
    
    if report3['files']:
        print(f"  Extracted {report3['files'][0]['lines']} lines")
    
    return True


if __name__ == "__main__":
    import asyncio
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if len(sys.argv) > 2:
        # CLI mode
        parser = argparse.ArgumentParser(description='Extract code from markdown')
        parser.add_argument('markdown_file', help='Input markdown file')
        parser.add_argument('output_dir', help='Output directory for extracted files')
        parser.add_argument('--validate', action='store_true', help='Validate extracted code')
        parser.add_argument('--report', help='Save extraction report to JSON file')
        
        args = parser.parse_args()
        
        report = extract_from_markdown(
            args.markdown_file,
            args.output_dir,
            validate=args.validate,
            report_file=args.report
        )
        
        sys.exit(0 if report['success'] else 1)
    else:
        # Test mode
        async def main():
            if mode == "debug":
                print("Running in DEBUG mode...")
                success = await debug_function()
            else:
                print("Running in WORKING mode...")
                success = await working_usage()
            return success
        
        success = asyncio.run(main())
        sys.exit(0 if success else 1)