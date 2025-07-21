#!/usr/bin/env python3
"""
Standalone code review tool that KiloCode can execute via execute_command.

This tool performs the actual code review using LLMs directly, since KiloCode's
slash commands cannot be triggered programmatically.

Usage:
    python kilocode_review_standalone.py <files...> [options]

Example:
    python kilocode_review_standalone.py src/example.py --focus security --severity medium
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from cc_executor.client.client import LiteLLMClient


class KiloCodeReviewExecutor:
    """Executes code reviews that KiloCode can trigger via execute_command."""
    
    def __init__(self):
        self.client = LiteLLMClient()
        logger.remove()  # Remove default handler
        logger.add(sys.stderr, level="INFO", format="{message}")
    
    async def perform_review(
        self,
        files: List[str],
        context: Optional[str] = None,
        focus: Optional[str] = None,
        severity: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        """Perform the actual code review using LLMs."""
        
        logger.info(f"🔍 Starting code review for {len(files)} file(s)")
        
        # Read file contents
        file_contents = {}
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    file_contents[file_path] = f.read()
                logger.info(f"✓ Read {file_path}")
            except Exception as e:
                logger.error(f"✗ Failed to read {file_path}: {e}")
                file_contents[file_path] = f"Error reading file: {e}"
        
        # Build review prompt
        prompt = self._build_review_prompt(file_contents, context, focus, severity)
        
        # Phase 1: O3/GPT-4 Review
        logger.info("📝 Phase 1: Running initial code review...")
        phase1_result = await self._run_phase1_review(prompt)
        
        # Phase 2: Gemini Meta-Review
        logger.info("🔍 Phase 2: Running meta-review validation...")
        phase2_result = await self._run_phase2_review(phase1_result, file_contents, context)
        
        # Combine results
        final_result = {
            "timestamp": datetime.now().isoformat(),
            "files_reviewed": list(file_contents.keys()),
            "configuration": {
                "focus": focus,
                "severity": severity,
                "context_provided": bool(context)
            },
            "phase1_review": phase1_result,
            "phase2_validation": phase2_result,
            "summary": self._generate_summary(phase1_result, phase2_result)
        }
        
        return final_result
    
    def _build_review_prompt(
        self,
        file_contents: Dict[str, str],
        context: Optional[str],
        focus: Optional[str],
        severity: str
    ) -> str:
        """Build the review prompt for Phase 1."""
        
        prompt_parts = ["# Code Review Request\n"]
        
        if context:
            prompt_parts.append(f"## Project Context\n{context}\n")
        
        prompt_parts.append("## Review Configuration")
        prompt_parts.append(f"- Focus: {focus or 'comprehensive'}")
        prompt_parts.append(f"- Minimum Severity: {severity}")
        prompt_parts.append("")
        
        prompt_parts.append("## Files to Review\n")
        for file_path, content in file_contents.items():
            prompt_parts.append(f"### {file_path}")
            prompt_parts.append("```python")
            prompt_parts.append(content)
            prompt_parts.append("```\n")
        
        prompt_parts.append("## Instructions")
        prompt_parts.append("Perform a comprehensive code review focusing on:")
        prompt_parts.append("1. Security vulnerabilities")
        prompt_parts.append("2. Performance issues")
        prompt_parts.append("3. Code quality and maintainability")
        prompt_parts.append("4. Best practices violations")
        prompt_parts.append("")
        prompt_parts.append(f"Report only issues of severity {severity} or higher.")
        prompt_parts.append("For each issue, indicate if fixing it would violate the project context.")
        prompt_parts.append("")
        prompt_parts.append("Format your response as JSON with this structure:")
        prompt_parts.append("""```json
{
    "issues": [
        {
            "file": "path/to/file.py",
            "line": 42,
            "severity": "high",
            "category": "security",
            "description": "Issue description",
            "recommendation": "How to fix",
            "context_compatible": true
        }
    ],
    "summary": {
        "total_issues": 0,
        "by_severity": {"critical": 0, "high": 0, "medium": 0},
        "by_category": {"security": 0, "performance": 0, "quality": 0}
    }
}
```""")
        
        return "\n".join(prompt_parts)
    
    async def _run_phase1_review(self, prompt: str) -> Dict[str, Any]:
        """Run Phase 1 review with O3/GPT-4."""
        try:
            response = await self.client.create_completion(
                model="gpt-4o",  # Or "o3-mini" when available
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer. Provide detailed, actionable feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            # Parse JSON response
            result_text = response.choices[0].message.content
            # Extract JSON from markdown if needed
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end]
            
            return json.loads(result_text)
        except Exception as e:
            logger.error(f"Phase 1 review failed: {e}")
            return {
                "error": str(e),
                "issues": [],
                "summary": {"total_issues": 0}
            }
    
    async def _run_phase2_review(
        self,
        phase1_result: Dict[str, Any],
        file_contents: Dict[str, str],
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Run Phase 2 meta-review with Gemini."""
        
        meta_prompt = f"""# Meta-Review Validation

## Original Review
{json.dumps(phase1_result, indent=2)}

## Project Context
{context or "No specific context provided"}

## Task
Validate the code review above:
1. Check if recommendations respect the project context
2. Identify any false positives
3. Highlight the most critical issues
4. Suggest implementation priority

Provide a JSON response with:
```json
{{
    "validated_issues": [/* issues that are truly important */],
    "false_positives": [/* issues to ignore */],
    "priority_order": [/* issue indices in order of importance */],
    "implementation_notes": "General guidance"
}}
```"""
        
        try:
            # In real implementation, this would use Gemini
            # For now, we'll use GPT-4 as a placeholder
            response = await self.client.create_completion(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a meta-reviewer validating code review results."},
                    {"role": "user", "content": meta_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end]
            
            return json.loads(result_text)
        except Exception as e:
            logger.error(f"Phase 2 review failed: {e}")
            return {
                "error": str(e),
                "validated_issues": phase1_result.get("issues", []),
                "implementation_notes": "Meta-review unavailable"
            }
    
    def _generate_summary(self, phase1: Dict[str, Any], phase2: Dict[str, Any]) -> str:
        """Generate a human-readable summary."""
        total_issues = len(phase1.get("issues", []))
        validated_issues = len(phase2.get("validated_issues", []))
        
        summary_parts = [
            f"Found {total_issues} total issues",
            f"{validated_issues} validated as important",
            f"{total_issues - validated_issues} identified as false positives or low priority"
        ]
        
        if phase2.get("implementation_notes"):
            summary_parts.append(f"\nNotes: {phase2['implementation_notes']}")
        
        return " | ".join(summary_parts[:3]) + (summary_parts[3] if len(summary_parts) > 3 else "")
    
    async def save_results(self, results: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Save results to a file."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/kilocode_review_{timestamp}.json"
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"💾 Results saved to: {output_path}")
        return output_path


async def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(description="KiloCode standalone code review")
    parser.add_argument("files", nargs="+", help="Files to review")
    parser.add_argument("--context", help="Project context (inline)")
    parser.add_argument("--context-file", help="Path to context file")
    parser.add_argument("--focus", choices=["security", "performance", "maintainability", "architecture"],
                       help="Review focus area")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"],
                       default="medium", help="Minimum severity level")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--format", choices=["json", "markdown"], default="json",
                       help="Output format")
    
    args = parser.parse_args()
    
    # Load context
    context = args.context
    if args.context_file and os.path.exists(args.context_file):
        with open(args.context_file, 'r') as f:
            context = f.read()
    
    # Run review
    executor = KiloCodeReviewExecutor()
    results = await executor.perform_review(
        files=args.files,
        context=context,
        focus=args.focus,
        severity=args.severity
    )
    
    # Save results
    output_path = await executor.save_results(results, args.output)
    
    # Display summary
    print("\n" + "="*60)
    print("CODE REVIEW COMPLETE")
    print("="*60)
    print(f"Files reviewed: {len(results['files_reviewed'])}")
    print(f"Issues found: {len(results['phase1_review'].get('issues', []))}")
    print(f"Validated issues: {len(results['phase2_validation'].get('validated_issues', []))}")
    print(f"\nSummary: {results['summary']}")
    print(f"\nFull results: {output_path}")
    print("="*60)
    
    # Exit with appropriate code
    validated_count = len(results['phase2_validation'].get('validated_issues', []))
    sys.exit(1 if validated_count > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())