#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "litellm",
#     "python-dotenv",
#     "loguru",
#     "google-auth",
#     "google-cloud-aiplatform",
# ]
# ///

# @tool
# tool_name: SendToGeminiBatch
# description: Sends multiple files to Gemini for fixing, one at a time, with full context for each. Handles the 8K output token limit by making separate calls per file while maintaining complete context.
# input_schema:
#   type: object
#   properties:
#     issue_report_file:
#       type: string
#       description: Path to markdown file containing the complete issue report with all context
#     files_to_fix:
#       type: array
#       items:
#         type: string
#       description: List of file paths that need fixing (will be processed one at a time)
#     output_dir:
#       type: string
#       description: Directory where all Gemini responses will be saved
#     temperature:
#       type: number
#       description: Temperature for response generation (0.0-1.0, default 0.1)
#     max_tokens:
#       type: integer
#       description: Maximum tokens per response (default 7500, max 8192)
#   required: [issue_report_file, files_to_fix]

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import litellm
from loguru import logger
import re


def extract_context_sections(issue_report: str) -> dict:
    """Extract different sections from the issue report.
=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python send_to_gemini_batch.py          # Runs working_usage() - stable, known to work
  python send_to_gemini_batch.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""
    sections = {
        'header': '',
        'context_files': {},
        'requirements': '',
        'footer': ''
    }
    
    # Extract header (everything before first CODE_CONTEXT_START)
    header_match = re.search(r'^(.*?)<!-- CODE_CONTEXT_START:', issue_report, re.DOTALL)
    if header_match:
        sections['header'] = header_match.group(1).strip()
    
    # Extract all context files
    context_pattern = r'<!-- CODE_CONTEXT_START: (.*?) -->\n```.*?\n(.*?)\n```\n<!-- CODE_CONTEXT_END: .*? -->'
    for match in re.finditer(context_pattern, issue_report, re.DOTALL):
        file_path = match.group(1)
        file_content = match.group(2)
        sections['context_files'][file_path] = file_content
    
    # Extract requirements section (after context files)
    req_match = re.search(r'<!-- CODE_CONTEXT_END: .*? -->\n\n(.*?)$', issue_report, re.DOTALL)
    if req_match:
        sections['requirements'] = req_match.group(1).strip()
    
    return sections


def create_single_file_request(sections: dict, file_to_fix: str) -> str:
    """Create a focused request for a single file with all context."""
    
    # Build the request with all context but focused on one file
    request = f"""{sections['header']}

## Current Focus: Fix {file_to_fix}

**IMPORTANT**: Fix ONLY {file_to_fix} in this response. Include the complete fixed file.

## All Context Files (For Reference)

"""
    
    # Include all context files
    for file_path, content in sections['context_files'].items():
        if file_path == file_to_fix:
            request += f"<!-- CODE_CONTEXT_START: {file_path} --> **[THIS IS THE FILE TO FIX]**\n"
        else:
            request += f"<!-- CODE_CONTEXT_START: {file_path} -->\n"
        request += f"```python\n{content}\n```\n"
        request += f"<!-- CODE_CONTEXT_END: {file_path} -->\n\n"
    
    # Add requirements with emphasis on single file
    request += f"""
## Required Solution Format

**FIX ONLY {file_to_fix}**

Please provide the complete fixed file using this exact format:

<!-- CODE_FILE_START: {file_to_fix} -->
```python
# Complete file content - no ellipsis or placeholders
```
<!-- CODE_FILE_END: {file_to_fix} -->

{sections['requirements']}

## Reminder

- Fix ONLY {file_to_fix}
- Include ALL imports and code
- Maintain the same functionality
- Apply all necessary fixes for this file
- You have access to all context files above for reference
"""
    
    return request


def _estimate_cost(response) -> float:
    """Estimate cost based on token usage."""
    if hasattr(response, 'usage'):
        input_cost_per_million = 0.15
        output_cost_per_million = 0.60
        
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million
        
        return input_cost + output_cost
    return 0.0


async def send_single_file_to_gemini(
    request_content: str, 
    output_file: str,
    temperature: float = 0.1,
    max_tokens: int = 7500
) -> dict:
    """Send a single file fix request to Gemini."""
    
    try:
        # Call Gemini Flash via LiteLLM
        response = litellm.completion(
            model="vertex_ai/gemini-1.5-flash",
            messages=[{"role": "user", "content": request_content}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Extract response
        gemini_response = response.choices[0].message.content.strip()
        
        # Calculate cost
        cost = 0.0
        try:
            from litellm import completion_cost
            cost = completion_cost(completion_response=response)
        except:
            cost = _estimate_cost(response)
        
        # Add cost summary
        cost_summary = f"\n\n<!-- GEMINI_API_COST_START -->\n"
        cost_summary += f"## API Call Cost Summary\n\n"
        cost_summary += f"- **Model**: vertex_ai/gemini-1.5-flash\n"
        cost_summary += f"- **Temperature**: {temperature}\n"
        cost_summary += f"- **Max Tokens**: {max_tokens}\n"
        if hasattr(response, 'usage'):
            cost_summary += f"- **Input Tokens**: {response.usage.prompt_tokens:,}\n"
            cost_summary += f"- **Output Tokens**: {response.usage.completion_tokens:,}\n"
            cost_summary += f"- **Total Tokens**: {response.usage.total_tokens:,}\n"
        cost_summary += f"- **Total Cost**: ${cost:.4f} USD\n"
        cost_summary += f"- **Timestamp**: {datetime.now().isoformat()}\n"
        cost_summary += f"<!-- GEMINI_API_COST_END -->\n"
        
        # Save response
        Path(output_file).write_text(gemini_response + cost_summary)
        
        # Check for code markers
        code_files = re.findall(r'<!-- CODE_FILE_START: (.*?) -->', gemini_response)
        
        return {
            "success": True,
            "output_file": output_file,
            "cost": cost,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else None,
                "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else None
            },
            "code_files": code_files,
            "has_code_markers": len(code_files) > 0
        }
        
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return {
            "success": False,
            "error": str(e),
            "output_file": output_file
        }


def send_to_gemini_batch(
    issue_report_file: str,
    files_to_fix: list,
    output_dir: str = None,
    temperature: float = 0.1,
    max_tokens: int = 7500
) -> dict:
    """Process multiple files through Gemini, one at a time."""
    
    # Load environment
    load_dotenv()
    
    # Read issue report
    issue_path = Path(issue_report_file)
    if not issue_path.exists():
        return {
            "error": f"Issue report not found: {issue_report_file}",
            "success": False
        }
    
    issue_content = issue_path.read_text()
    
    # Extract sections
    sections = extract_context_sections(issue_content)
    
    # Determine output directory
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"tmp/gemini_batch_{timestamp}"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process each file
    results = []
    total_cost = 0.0
    
    logger.info(f"Processing {len(files_to_fix)} files through Gemini...")
    
    for i, file_to_fix in enumerate(files_to_fix, 1):
        logger.info(f"[{i}/{len(files_to_fix)}] Processing {file_to_fix}")
        
        # Create focused request
        request_content = create_single_file_request(sections, file_to_fix)
        
        # Save request for debugging
        request_file = output_path / f"request_{i}_{Path(file_to_fix).stem}.md"
        request_file.write_text(request_content)
        
        # Determine output file
        response_file = output_path / f"response_{i}_{Path(file_to_fix).stem}.md"
        
        # Send to Gemini
        import asyncio
        result = asyncio.run(send_single_file_to_gemini(
            request_content,
            str(response_file),
            temperature,
            max_tokens
        ))
        
        result['file_to_fix'] = file_to_fix
        result['request_file'] = str(request_file)
        results.append(result)
        
        if result['success']:
            total_cost += result.get('cost', 0)
            logger.info(f"  ✓ Success - Cost: ${result.get('cost', 0):.4f}")
        else:
            logger.error(f"  ✗ Failed - {result.get('error', 'Unknown error')}")
    
    # Create summary
    summary = {
        "success": all(r['success'] for r in results),
        "issue_report": str(issue_path),
        "output_directory": str(output_path),
        "files_processed": len(files_to_fix),
        "files_succeeded": sum(1 for r in results if r['success']),
        "total_cost": total_cost,
        "average_cost_per_file": total_cost / len(files_to_fix) if files_to_fix else 0,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    # Save summary
    summary_file = output_path / "BATCH_SUMMARY.json"
    summary_file.write_text(json.dumps(summary, indent=2))
    
    logger.info(f"\nBatch processing complete:")
    logger.info(f"  Files: {summary['files_succeeded']}/{summary['files_processed']} succeeded")
    logger.info(f"  Total cost: ${summary['total_cost']:.4f}")
    logger.info(f"  Output: {output_path}")
    
    return summary


def main():
    """Command line interface."""
    if len(sys.argv) > 1:
        input_data = json.loads(sys.argv[1])
    else:
        print(json.dumps({
            "error": "No input provided",
            "usage": "Provide issue_report_file and files_to_fix"
        }))
        sys.exit(1)
    
    # Extract parameters
    issue_report_file = input_data.get("issue_report_file")
    files_to_fix = input_data.get("files_to_fix", [])
    
    if not issue_report_file or not files_to_fix:
        print(json.dumps({
            "error": "issue_report_file and files_to_fix are required"
        }))
        sys.exit(1)
    
    output_dir = input_data.get("output_dir")
    temperature = input_data.get("temperature", 0.1)
    max_tokens = input_data.get("max_tokens", 7500)
    
    # Process batch
    result = send_to_gemini_batch(
        issue_report_file,
        files_to_fix,
        output_dir,
        temperature,
        max_tokens
    )
    
    # Output result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    main()