# Code Extraction Workflow Improvements

**Date**: 2025-01-14  
**Author**: Claude Code Assistant  
**Purpose**: Document lessons learned and propose improvements for extracting code from markdown documentation

## Current Process Issues

### 1. Manual Extraction is Error-Prone
- Manually reading through large markdown files is inefficient
- Easy to miss files or make copy/paste errors
- No validation that all files were extracted correctly
- Time-consuming and repetitive

### 2. Lack of Clear Markers
The current markdown format uses:
```markdown
---
File: path/to/file.py
---
```python
# code here
```
```

This works but could be more machine-readable.

### 3. No Verification System
- No automatic check that extracted files match source
- No count of expected vs actual files
- No diff capability to see what changed

## Proposed Improvements

### 1. Standardized Markdown Format with Clear Markers

```markdown
<!-- CODE_FILE_START: src/utils/log_utils.py -->
```python
#!/usr/bin/env python3
# file content here
```
<!-- CODE_FILE_END: src/utils/log_utils.py -->

<!-- CONFIG_FILE_START: .env -->
```bash
# config content here
```
<!-- CONFIG_FILE_END: .env -->
```

Benefits:
- Machine-readable markers
- File path included in both start and end tags
- Language hint for syntax highlighting
- Easy to validate matching start/end tags

### 2. Automated Extraction Script

```python
#!/usr/bin/env python3
"""
extract_code_from_markdown.py - Extract code files from markdown documentation

Extracts all code blocks marked with CODE_FILE_START/END markers and creates
the corresponding files in the correct directory structure.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import json
from datetime import datetime

class CodeExtractor:
    """Extract code files from markdown with validation."""
    
    def __init__(self, markdown_file: Path, output_dir: Path):
        self.markdown_file = markdown_file
        self.output_dir = output_dir
        self.extracted_files: List[Dict[str, any]] = []
        
    def extract(self) -> Dict[str, any]:
        """Extract all code files from markdown."""
        content = self.markdown_file.read_text()
        
        # Pattern to match code blocks
        pattern = r'<!-- CODE_FILE_START: (.*?) -->\n```(?:.*?)\n(.*?)\n```\n<!-- CODE_FILE_END: \1 -->'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            file_path = match.group(1)
            code_content = match.group(2)
            
            # Create full path
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(code_content)
            
            self.extracted_files.append({
                'path': file_path,
                'size': len(code_content),
                'lines': code_content.count('\n') + 1
            })
            
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, any]:
        """Generate extraction report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.markdown_file),
            'output_dir': str(self.output_dir),
            'files_extracted': len(self.extracted_files),
            'files': self.extracted_files
        }
    
    def validate_extraction(self) -> List[str]:
        """Validate that all expected files were extracted."""
        issues = []
        
        # Check for Python syntax errors
        for file_info in self.extracted_files:
            if file_info['path'].endswith('.py'):
                file_path = self.output_dir / file_info['path']
                try:
                    compile(file_path.read_text(), file_path, 'exec')
                except SyntaxError as e:
                    issues.append(f"Syntax error in {file_info['path']}: {e}")
        
        return issues


def main():
    parser = argparse.ArgumentParser(description='Extract code from markdown')
    parser.add_argument('markdown_file', help='Input markdown file')
    parser.add_argument('output_dir', help='Output directory for extracted files')
    parser.add_argument('--validate', action='store_true', help='Validate extracted code')
    parser.add_argument('--report', help='Save extraction report to JSON file')
    
    args = parser.parse_args()
    
    extractor = CodeExtractor(
        Path(args.markdown_file),
        Path(args.output_dir)
    )
    
    report = extractor.extract()
    
    print(f"Extracted {report['files_extracted']} files:")
    for file_info in report['files']:
        print(f"  - {file_info['path']} ({file_info['lines']} lines)")
    
    if args.validate:
        issues = extractor.validate_extraction()
        if issues:
            print("\nValidation issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nAll files validated successfully!")
    
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2))
        print(f"\nReport saved to: {args.report}")


if __name__ == "__main__":
    main()
```

### 3. Gemini-Specific Template

Create a template for Gemini to follow:

```markdown
# Code Export Template for Gemini

When providing code implementations, please use the following format:

## File Structure Overview
```
project/
├── src/
│   ├── module1.py
│   └── module2.py
├── tests/
│   └── test_module1.py
├── requirements.txt
└── README.md
```

## Code Files

<!-- CODE_FILE_START: src/module1.py -->
```python
# Complete file content here
```
<!-- CODE_FILE_END: src/module1.py -->

## Extraction Metadata

<!-- EXTRACTION_METADATA_START -->
```json
{
  "total_files": 5,
  "languages": ["python", "yaml", "markdown"],
  "dependencies": ["aioarango", "loguru", "uvloop"],
  "test_command": "python src/main.py",
  "notes": "Requires ArangoDB 3.12+ with experimental features enabled"
}
```
<!-- EXTRACTION_METADATA_END -->
```

### 4. Test Runner Script

```python
#!/usr/bin/env python3
"""
test_extracted_code.py - Test all extracted Python scripts

Runs the working_usage() function of each extracted Python script
and generates a test report.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List
import sys
import os

class ExtractedCodeTester:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.results = []
        
    def find_python_scripts(self) -> List[Path]:
        """Find all Python scripts with if __name__ == "__main__" blocks."""
        scripts = []
        for py_file in self.project_dir.rglob("*.py"):
            if self.has_main_block(py_file):
                scripts.append(py_file)
        return scripts
    
    def has_main_block(self, script: Path) -> bool:
        """Check if script has a main block."""
        content = script.read_text()
        return 'if __name__ == "__main__"' in content
    
    def test_script(self, script: Path, max_attempts: int = 2) -> Dict:
        """Test a single script."""
        result = {
            'script': str(script.relative_to(self.project_dir)),
            'attempts': [],
            'success': False
        }
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_dir / 'src')
        
        for attempt in range(max_attempts):
            try:
                proc = subprocess.run(
                    [sys.executable, str(script)],
                    cwd=self.project_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                attempt_result = {
                    'attempt': attempt + 1,
                    'returncode': proc.returncode,
                    'stdout': proc.stdout[-1000:],  # Last 1000 chars
                    'stderr': proc.stderr[-1000:]
                }
                
                result['attempts'].append(attempt_result)
                
                if proc.returncode == 0:
                    result['success'] = True
                    break
                    
            except subprocess.TimeoutExpired:
                attempt_result = {
                    'attempt': attempt + 1,
                    'error': 'Timeout after 30 seconds'
                }
                result['attempts'].append(attempt_result)
            except Exception as e:
                attempt_result = {
                    'attempt': attempt + 1,
                    'error': str(e)
                }
                result['attempts'].append(attempt_result)
        
        return result
    
    def run_all_tests(self) -> Dict:
        """Run tests on all scripts."""
        scripts = self.find_python_scripts()
        
        print(f"Found {len(scripts)} Python scripts to test")
        
        for script in scripts:
            print(f"Testing {script.name}...", end=' ')
            result = self.test_script(script)
            self.results.append(result)
            
            if result['success']:
                print("✅ PASSED")
            else:
                print("❌ FAILED")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate test report."""
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        return {
            'total_scripts': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.results) * 100 if self.results else 0,
            'results': self.results
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test extracted code')
    parser.add_argument('project_dir', help='Project directory with extracted code')
    parser.add_argument('--report', help='Save test report to JSON file')
    
    args = parser.parse_args()
    
    tester = ExtractedCodeTester(Path(args.project_dir))
    report = tester.run_all_tests()
    
    print(f"\n{'='*60}")
    print(f"Test Summary:")
    print(f"  Total Scripts: {report['total_scripts']}")
    print(f"  Successful: {report['successful']}")
    print(f"  Failed: {report['failed']}")
    print(f"  Success Rate: {report['success_rate']:.1f}%")
    print(f"{'='*60}\n")
    
    if report['failed'] > 0:
        print("Failed Scripts:")
        for result in report['results']:
            if not result['success']:
                print(f"\n  {result['script']}:")
                last_attempt = result['attempts'][-1]
                if 'error' in last_attempt:
                    print(f"    Error: {last_attempt['error']}")
                elif last_attempt['stderr']:
                    print(f"    Error: {last_attempt['stderr'][:200]}...")
    
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2))
        print(f"\nDetailed report saved to: {args.report}")
    
    return 0 if report['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 5. CI/CD Integration

```yaml
# .github/workflows/extract-and-test.yml
name: Extract and Test Code

on:
  push:
    paths:
      - 'docs/conversations/*.md'

jobs:
  extract-and-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Extract code from markdown
      run: |
        python scripts/extract_code_from_markdown.py \
          docs/conversations/gemini_logger_app.md \
          extracted_code/ \
          --validate \
          --report extraction_report.json
    
    - name: Install dependencies
      run: |
        cd extracted_code
        pip install -r requirements.txt
    
    - name: Test extracted code
      run: |
        python scripts/test_extracted_code.py \
          extracted_code/ \
          --report test_report.json
    
    - name: Upload reports
      uses: actions/upload-artifact@v3
      with:
        name: extraction-reports
        path: |
          extraction_report.json
          test_report.json
```

## Benefits of This Approach

1. **Automation**: No manual copying required
2. **Validation**: Automatic syntax checking and testing
3. **Reproducibility**: Same process every time
4. **Version Control**: Track changes in extracted code
5. **CI/CD Ready**: Can be integrated into pipelines
6. **Error Detection**: Catches issues early
7. **Documentation**: Automatic reports generated

## Implementation Steps

1. Create the extraction script
2. Define markdown format standards
3. Create test runner script
4. Document the process
5. Train Gemini on the format
6. Integrate into workflow

## Conclusion

By implementing an automated extraction workflow, we can:
- Save significant time
- Reduce errors
- Improve consistency
- Enable better collaboration
- Create a more professional development process

The investment in creating these tools would pay off quickly, especially when working with AI-generated code that needs to be extracted, tested, and integrated into projects.