#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///

# @tool
# tool_name: ExtractGeminiCode
# description: Extracts code from a Gemini markdown response file into tmp/ directory for analysis. Returns extraction summary without loading full file content.
# input_schema:
#   type: object
#   properties:
#     markdown_file:
#       type: string
#       description: Path to the Gemini markdown response file containing code
#     output_dir:
#       type: string
#       description: Optional output directory (defaults to tmp/gemini_extracted_TIMESTAMP)
#   required: [markdown_file]

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime


def main():
    # Get input from Claude Code
    if len(sys.argv) > 1:
        input_data = json.loads(sys.argv[1])
    else:
        print(json.dumps({
            "error": "No input provided",
            "usage": "Provide markdown_file path"
        }))
        sys.exit(1)
    
    markdown_file = input_data.get("markdown_file")
    if not markdown_file:
        print(json.dumps({
            "error": "markdown_file is required"
        }))
        sys.exit(1)
    
    # Verify file exists
    markdown_path = Path(markdown_file)
    if not markdown_path.exists():
        print(json.dumps({
            "error": f"File not found: {markdown_file}"
        }))
        sys.exit(1)
    
    # Determine output directory
    output_dir = input_data.get("output_dir")
    if not output_dir:
        # Find project root by looking for .env or pyproject.toml
        current = Path.cwd()
        project_root = current
        while current != current.parent:
            if (current / ".env").exists() or (current / "pyproject.toml").exists():
                project_root = current
                break
            current = current.parent
        
        # Create timestamped directory in project's tmp/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = project_root / "tmp" / f"gemini_extracted_{timestamp}"
    
    output_path = Path(output_dir)
    
    # Find the extraction script
    # First try relative to this tool
    tool_dir = Path(__file__).parent.parent.parent
    extract_script = tool_dir / "scripts" / "extract_code_from_markdown.py"
    
    if not extract_script.exists():
        # Try to find it in the project
        possible_locations = [
            Path.cwd() / "scripts" / "extract_code_from_markdown.py",
            Path.cwd() / "extract_code_from_markdown.py",
        ]
        for loc in possible_locations:
            if loc.exists():
                extract_script = loc
                break
        else:
            print(json.dumps({
                "error": "Could not find extract_code_from_markdown.py script"
            }))
            sys.exit(1)
    
    # Run the extraction script
    try:
        result = subprocess.run(
            [sys.executable, str(extract_script), str(markdown_path), str(output_path), "--validate"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(json.dumps({
                "error": "Extraction failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }))
            sys.exit(1)
        
        # Parse the output to get summary
        extraction_summary = {
            "success": True,
            "markdown_file": str(markdown_path),
            "output_directory": str(output_path),
            "extraction_output": result.stdout,
            "files": []
        }
        
        # List extracted files
        if output_path.exists():
            for root, dirs, files in os.walk(output_path):
                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(output_path)
                    extraction_summary["files"].append({
                        "path": str(relative_path),
                        "full_path": str(file_path),
                        "size": file_path.stat().st_size,
                        "lines": len(file_path.read_text().splitlines()) if file_path.suffix in ['.py', '.js', '.ts', '.md', '.txt'] else None
                    })
        
        # Create context file
        context_file = output_path / "EXTRACTION_CONTEXT.md"
        context_content = [
            f"# Gemini Code Extraction Context",
            f"",
            f"**Source**: `{markdown_path.name}`",
            f"**Extracted**: {datetime.now().isoformat()}",
            f"**Output**: `{output_path}`",
            f"",
            f"## Files Extracted",
            f""
        ]
        
        for file_info in extraction_summary["files"]:
            if file_info["lines"]:
                context_content.append(f"- `{file_info['path']}` ({file_info['lines']} lines)")
            else:
                context_content.append(f"- `{file_info['path']}` ({file_info['size']} bytes)")
        
        context_content.extend([
            f"",
            f"## Next Steps",
            f"1. Review extracted files in `{output_path}`",
            f"2. Compare with existing code using diff",
            f"3. Apply changes selectively",
            f"",
            f"## Commands",
            f"```bash",
            f"# List extracted files",
            f"ls -la {output_path}",
            f"",
            f"# Compare with existing",
            f"diff -u src/existing_file.py {output_path}/src/existing_file.py",
            f"```"
        ])
        
        context_file.write_text('\n'.join(context_content))
        extraction_summary["context_file"] = str(context_file)
        
        # Return summary
        print(json.dumps(extraction_summary, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "error": f"Extraction error: {str(e)}",
            "type": type(e).__name__
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()