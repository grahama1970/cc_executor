# ArXiv MCP Extraction Methods Recommendation

## Current State
The ArXiv MCP server currently supports:
- `pymupdf` - Basic text extraction
- `pdfplumber` - Alternative extraction
- `auto` - Tries multiple methods

## Recommended Additions

### 1. Add pymupdf4llm (Fast extraction: 30-120 seconds)
```python
elif method == "pymupdf4llm":
    code = '''
import json
import pymupdf4llm

try:
    # Fast extraction optimized for LLMs
    md_text = pymupdf4llm.to_markdown("{pdf_path}")
    
    # Parse sections from markdown
    sections = parse_markdown_sections(md_text)
    
    extracted = {
        "success": True,
        "method": "pymupdf4llm",
        "extraction_time": "fast",
        "content": sections,
        "raw_markdown": md_text
    }
    
    print(json.dumps(extracted))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
```

### 2. Add marker-pdf (Comprehensive extraction: 5-10 minutes)
```python
elif method == "marker":
    code = '''
import json
import subprocess
import os

try:
    # Run marker-pdf CLI for comprehensive extraction
    output_dir = "/tmp/marker_output"
    os.makedirs(output_dir, exist_ok=True)
    
    result = subprocess.run([
        "marker_single",
        "{pdf_path}",
        output_dir,
        "--parallel_factor", "2"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        # Read the generated markdown
        md_file = os.path.join(output_dir, os.path.basename("{pdf_path}").replace('.pdf', '.md'))
        with open(md_file, 'r') as f:
            content = f.read()
        
        extracted = {
            "success": True,
            "method": "marker",
            "extraction_time": "comprehensive",
            "content": parse_marker_output(content),
            "raw_markdown": content
        }
    else:
        extracted = {
            "success": False,
            "error": result.stderr
        }
    
    print(json.dumps(extracted))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
```

## Extraction Method Selection Logic

Update the tool to accept a `method` parameter:
- `fast` or `pymupdf4llm` - For quick research (30-120s)
- `comprehensive` or `marker` - For detailed analysis (5-10m)
- `auto` - Decides based on paper length/complexity

## Usage Examples

```python
# Fast extraction for quick research
mcp__arxiv-cc__arxiv_extract_content({
    "paper_id": "2401.12345",
    "method": "fast",
    "sections": ["abstract", "conclusion"]
})

# Comprehensive extraction for deep analysis
mcp__arxiv-cc__arxiv_extract_content({
    "paper_id": "2401.12345", 
    "method": "comprehensive",
    "extract_equations": true,
    "extract_figures": true,
    "extract_code": true
})
```