# Markdown Format Requirements for Automated Code Extraction

**STATUS: OPEN** - Requires implementation by Gemini

## Description

The current markdown format used by Gemini for providing code implementations is not optimized for automated extraction. We need a standardized format with clear machine-readable markers that will work perfectly with the extraction script created in `/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/scripts/extract_code_from_markdown.py`.

## Current Behavior

Gemini currently uses this format:
```markdown
---
File: path/to/file.py
---
```python
# code here
```
```

This format has several issues:
- Ambiguous delimiters (triple dashes used in many contexts)
- No clear end marker for file boundaries
- Difficult to parse reliably with regex
- No metadata about the file (permissions, type, etc.)

## Expected Behavior

Gemini should use the standardized format with HTML comments as markers:
```markdown
<!-- CODE_FILE_START: src/utils/log_utils.py -->
```python
#!/usr/bin/env python3
# file content here
```
<!-- CODE_FILE_END: src/utils/log_utils.py -->
```

## Extraction Script Requirements

The extraction script expects the following format:

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

## Required Markdown Template for Gemini

Gemini should follow this exact template when providing code:

```markdown
# Code Implementation for [Project Name]

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
#!/usr/bin/env python3
"""
Module description here.
"""

# Complete file content here
```
<!-- CODE_FILE_END: src/module1.py -->

<!-- CODE_FILE_START: src/module2.py -->
```python
#!/usr/bin/env python3
"""
Another module.
"""

# Complete file content here
```
<!-- CODE_FILE_END: src/module2.py -->

<!-- CODE_FILE_START: requirements.txt -->
```text
aioarango>=1.0.0
loguru>=0.7.0
uvloop>=0.19.0
python-dotenv>=1.0.0
```
<!-- CODE_FILE_END: requirements.txt -->

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

## Benefits of This Format

1. **Machine-Readable**: Clear HTML comment markers that won't conflict with markdown content
2. **Validation**: End markers include the filename for validation
3. **Metadata Support**: Structured metadata section for additional information
4. **Language Hints**: Code blocks can include language hints for syntax highlighting
5. **Nested Paths**: Full path support for complex directory structures
6. **Error Detection**: Mismatched start/end tags are easily detected

## Usage Example

After Gemini provides code in the correct format:

```bash
# Extract all files
python scripts/extract_code_from_markdown.py \
    docs/conversations/gemini_logger_app.md \
    src/ \
    --validate \
    --report extraction_report.json

# Test all extracted files
python scripts/test_extracted_code.py \
    src/ \
    --report test_report.json
```

## Testing the Format

To verify Gemini is using the correct format, we can validate:

1. All CODE_FILE_START tags have matching CODE_FILE_END tags
2. File paths in start/end tags match exactly
3. No code blocks exist outside of CODE_FILE markers
4. Metadata section is valid JSON
5. All files extract without errors

## Priority

**High** - This standardization is critical for:
- Automated CI/CD pipelines
- Reliable code extraction
- Reduced manual intervention
- Better collaboration between human and AI developers

## Implementation Checklist

- [ ] Update Gemini's prompt to use the new format
- [ ] Provide examples of correct formatting
- [ ] Test extraction with sample markdown
- [ ] Validate all existing code can be extracted
- [ ] Document any edge cases or special handling

---

**Note**: Once implemented, this format will save hours of manual extraction work and eliminate human errors in the code transfer process.