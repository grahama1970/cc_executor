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
# tool_name: SendToGemini
# description: Sends a complete issue report with code context to Gemini for resolution. Handles large markdown files without loading them into Claude's context.
# input_schema:
#   type: object
#   properties:
#     issue_file:
#       type: string
#       description: Path to the markdown file containing the issue report
#     output_file:
#       type: string
#       description: Path where Gemini's response should be saved (defaults to tmp/gemini_response_TIMESTAMP.md)
#     temperature:
#       type: number
#       description: Temperature for response generation (0.0-1.0, default 0.1 for consistency)
#     max_tokens:
#       type: integer
#       description: Maximum tokens for response (default 16000)
#   required: [issue_file]

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import litellm
from loguru import logger


# System prompt for Gemini
GEMINI_SYSTEM_PROMPT = """You are an expert Python developer helping fix issues in an ArangoDB-based logging system.

CRITICAL REQUIREMENTS:
1. Always provide COMPLETE files - never use ellipsis (...) or "rest unchanged"
2. Use EXACT format: <!-- CODE_FILE_START: path --> and <!-- CODE_FILE_END: path -->
3. All database code MUST use test database isolation pattern
4. Include ALL imports, no placeholders
5. Code must be immediately executable
6. Follow the exact template format provided in the issue report

When providing solutions:
- Analyze the root cause first
- Provide complete working code
- Include test commands
- Follow the exact template format provided

IMPORTANT: Your entire response should be in markdown format suitable for code extraction."""


def _estimate_cost(response) -> float:
    """Estimate cost based on token usage if completion_cost is unavailable."""
    if hasattr(response, 'usage'):
        # Gemini 1.5 Flash pricing per million tokens
        input_cost_per_million = 0.15
        output_cost_per_million = 0.60
        
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million
        
        return input_cost + output_cost
    return 0.0


def send_to_gemini(issue_file: str, output_file: str = None, temperature: float = 0.1, max_tokens: int = 16000) -> dict:
    """Send issue report to Gemini and save response."""
    
    # Load environment variables
    load_dotenv()
    
    # Verify issue file exists
    issue_path = Path(issue_file)
    if not issue_path.exists():
        return {
            "error": f"Issue file not found: {issue_file}",
            "success": False
        }
    
    # Read issue content
    try:
        issue_content = issue_path.read_text()
    except Exception as e:
        return {
            "error": f"Failed to read issue file: {e}",
            "success": False
        }
    
    # Determine output file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tmp/gemini_response_{timestamp}.md"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare the complete prompt
    full_prompt = f"{GEMINI_SYSTEM_PROMPT}\n\n{issue_content}"
    
    # Log what we're doing (without the full content)
    logger.info(f"Sending issue to Gemini: {issue_path.name} ({len(issue_content)} chars)")
    logger.info(f"Output will be saved to: {output_path}")
    
    try:
        # Call Gemini Flash via LiteLLM
        response = litellm.completion(
            model="vertex_ai/gemini-1.5-flash",  # Using Gemini Flash as specified
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Extract response content
        gemini_response = response.choices[0].message.content.strip()
        
        # Calculate cost
        cost_calculated = False
        actual_cost = 0.0
        
        # Try LiteLLM's cost tracking first
        try:
            from litellm import completion_cost
            actual_cost = completion_cost(completion_response=response)
            cost_calculated = True
            logger.info(f"API call cost: ${actual_cost:.4f}")
        except Exception as e:
            logger.warning(f"Could not calculate cost with completion_cost: {e}")
            # Fall back to estimation
            actual_cost = _estimate_cost(response)
        
        # Add cost summary to the response
        cost_summary = f"\n\n<!-- GEMINI_API_COST_START -->\n"
        cost_summary += f"## API Call Cost Summary\n\n"
        cost_summary += f"- **Model**: vertex_ai/gemini-1.5-flash\n"
        cost_summary += f"- **Temperature**: {temperature}\n"
        cost_summary += f"- **Max Tokens**: {max_tokens}\n"
        if hasattr(response, 'usage'):
            cost_summary += f"- **Input Tokens**: {response.usage.prompt_tokens:,}\n"
            cost_summary += f"- **Output Tokens**: {response.usage.completion_tokens:,}\n"
            cost_summary += f"- **Total Tokens**: {response.usage.total_tokens:,}\n"
        
        # Add cost info
        if cost_calculated:
            cost_summary += f"- **Total Cost**: ${actual_cost:.4f} USD\n"
        else:
            cost_summary += f"- **Estimated Cost**: ${actual_cost:.4f} USD\n"
        
        cost_summary += f"- **Timestamp**: {datetime.now().isoformat()}\n"
        cost_summary += f"<!-- GEMINI_API_COST_END -->\n"
        
        # Save response with cost summary
        full_response = gemini_response + cost_summary
        output_path.write_text(full_response)
        
        # Create summary without full content
        summary = {
            "success": True,
            "issue_file": str(issue_path),
            "output_file": str(output_path),
            "response_length": len(gemini_response),
            "model": "vertex_ai/gemini-1.5-flash",
            "temperature": temperature,
            "max_tokens": max_tokens,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else None,
                "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else None,
            },
            "cost": {
                "total_cost": actual_cost,
                "currency": "USD",
                "method": "litellm_completion_cost" if cost_calculated else "estimated",
                "cost_per_million_tokens": {
                    "input": 0.15,  # Gemini 1.5 Flash pricing
                    "output": 0.60   # Gemini 1.5 Flash pricing
                }
            }
        }
        
        # Check if response contains expected markers
        has_code_markers = "<!-- CODE_FILE_START:" in gemini_response
        summary["has_code_markers"] = has_code_markers
        
        if not has_code_markers:
            summary["warning"] = "Response does not contain expected CODE_FILE_START markers"
        
        # Count code files in response
            import re
        code_files = re.findall(r'<!-- CODE_FILE_START: (.*?) -->', gemini_response)
        summary["code_files_count"] = len(code_files)
        summary["code_files"] = code_files
        
        logger.info(f"Gemini response saved: {len(gemini_response)} chars, {len(code_files)} code files")
        
        return summary
        
    except Exception as e:
        error_msg = f"Error calling Gemini: {str(e)}"
        logger.error(error_msg)
        
        # Save error information
        error_path = output_path.with_suffix('.error.json')
        error_data = {
            "error": error_msg,
            "type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "issue_file": str(issue_path),
            "attempted_output": str(output_path)
        }
        error_path.write_text(json.dumps(error_data, indent=2))
        
        return {
            "success": False,
            "error": error_msg,
            "error_file": str(error_path)
        }


def main():
    """Command line interface."""
    if len(sys.argv) > 1:
        input_data = json.loads(sys.argv[1])
    else:
        print(json.dumps({
            "error": "No input provided",
            "usage": "Provide issue_file path"
        }))
        sys.exit(1)
    
    # Extract parameters
    issue_file = input_data.get("issue_file")
    if not issue_file:
        print(json.dumps({
            "error": "issue_file is required"
        }))
        sys.exit(1)
    
    output_file = input_data.get("output_file")
    temperature = input_data.get("temperature", 0.1)
    max_tokens = input_data.get("max_tokens", 16000)
    
    # Send to Gemini
    result = send_to_gemini(issue_file, output_file, temperature, max_tokens)
    
    # Output result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()