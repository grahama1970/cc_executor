#!/usr/bin/env python3
"""
Two-Level Code Review System.

Implements a sophisticated code review process:
1. Level 1: o3 model performs initial comprehensive code review
2. Level 2: Gemini reviews o3's output and provides meta-analysis

This creates a more thorough review by having two different AI perspectives.
"""

import os
import sys
import json
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TwoLevelCodeReview:
    """Orchestrates the 2-level code review process."""
    
    def __init__(self):
        self.output_dir = Path("/tmp/code_reviews")
        self.output_dir.mkdir(exist_ok=True)
        
    async def _call_mcp_tool(self, server: str, tool: str, args: Dict) -> Dict:
        """Call an MCP tool and return the result."""
        try:
            # Import MCP client utilities
            from cc_executor.utils.mcp_client import call_mcp_tool
            
            result = await call_mcp_tool(server, tool, args)
            return result
            
        except ImportError:
            # Fallback to direct subprocess call
            logger.warning("MCP client not available, using subprocess")
            return await self._call_mcp_subprocess(server, tool, args)
            
    async def _call_mcp_subprocess(self, server: str, tool: str, args: Dict) -> Dict:
        """Fallback method to call MCP tools via subprocess."""
        try:
            import subprocess
            import json
            
            # Construct MCP call
            mcp_request = {
                "jsonrpc": "2.0",
                "method": f"tools/{tool}",
                "params": args,
                "id": 1
            }
            
            # Find the MCP server script
            server_path = Path(__file__).parent.parent / "servers" / f"mcp_{server}.py"
            if not server_path.exists():
                return {"success": False, "error": f"MCP server not found: {server}"}
                
            # Run the MCP server with the request
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(server_path),
                "--request",
                json.dumps(mcp_request),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            
            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()}
                
            # Parse response
            response = json.loads(stdout.decode())
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"Subprocess MCP call failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def run_o3_review(self, files: List[str], context: Dict) -> Dict:
        """Run first-level review using o3 model."""
        logger.info(f"Starting o3 review for {len(files)} files")
        
        # Prepare the review prompt
        prompt = self._prepare_o3_prompt(files, context)
        
        try:
            # Use litellm for o3 model
            result = await self._call_mcp_tool(
                server="litellm_request",
                tool="process_single_request",
                args={
                    "model": "o3-mini",  # or "gpt-4" as fallback
                    "messages": json.dumps([
                        {
                            "role": "system",
                            "content": "You are an expert code reviewer. Provide thorough, constructive feedback focusing on code quality, security, performance, and best practices."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]),
                    "temperature": 0.3,
                    "max_tokens": 4000
                }
            )
            
            if isinstance(result, str):
                result = json.loads(result)
                
            if result.get("status") == "success":
                response = result.get("response", {})
                return {
                    "success": True,
                    "review": response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "model": "o3-mini",
                    "timestamp": time.time()
                }
            else:
                # Fallback to GPT-4
                logger.warning("o3 not available, falling back to GPT-4")
                return await self._fallback_gpt4_review(files, context, prompt)
                
        except Exception as e:
            logger.error(f"o3 review failed: {e}")
            return await self._fallback_gpt4_review(files, context, prompt)
            
    async def _fallback_gpt4_review(self, files: List[str], context: Dict, prompt: str) -> Dict:
        """Fallback to GPT-4 if o3 is not available."""
        try:
            result = await self._call_mcp_tool(
                server="litellm_request",
                tool="process_single_request",
                args={
                    "model": "gpt-4",
                    "messages": json.dumps([
                        {
                            "role": "system",
                            "content": "You are an expert code reviewer. Provide thorough, constructive feedback."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]),
                    "temperature": 0.3,
                    "max_tokens": 4000
                }
            )
            
            if isinstance(result, str):
                result = json.loads(result)
                
            if result.get("status") == "success":
                response = result.get("response", {})
                return {
                    "success": True,
                    "review": response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "model": "gpt-4",
                    "timestamp": time.time()
                }
                
        except Exception as e:
            logger.error(f"GPT-4 fallback also failed: {e}")
            
        return {
            "success": False,
            "error": "Both o3 and GPT-4 reviews failed"
        }
        
    async def run_gemini_meta_review(self, o3_review: str, files: List[str], context: Dict) -> Dict:
        """Run second-level meta-review using Gemini."""
        logger.info("Starting Gemini meta-review")
        
        # Prepare meta-review prompt
        prompt = self._prepare_gemini_prompt(o3_review, files, context)
        
        try:
            # Use llm_instance for Gemini
            result = await self._call_mcp_tool(
                server="llm_instance",
                tool="execute_llm",
                args={
                    "model": "gemini",
                    "prompt": prompt,
                    "timeout": 120,
                    "json_mode": False
                }
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "meta_review": result.get("output", ""),
                    "model": "gemini",
                    "timestamp": time.time()
                }
            else:
                # Fallback to using gemini CLI directly
                return await self._fallback_gemini_cli(prompt)
                
        except Exception as e:
            logger.error(f"Gemini meta-review failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _fallback_gemini_cli(self, prompt: str) -> Dict:
        """Direct Gemini CLI fallback."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gemini", "-p", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode == 0:
                return {
                    "success": True,
                    "meta_review": stdout.decode(),
                    "model": "gemini-cli",
                    "timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini CLI failed: {e}"
            }
            
    def _prepare_o3_prompt(self, files: List[str], context: Dict) -> str:
        """Prepare the prompt for o3 review."""
        # Read file contents
        file_contents = []
        for file_path in files[:10]:  # Limit to 10 files to avoid token limits
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    file_contents.append(f"\n### File: {file_path}\n```python\n{content}\n```")
            except Exception as e:
                logger.error(f"Could not read {file_path}: {e}")
                
        files_text = "\n".join(file_contents)
        
        # Build prompt
        prompt = f"""# Code Review Request

## Context
- Session: {context.get('session_id', 'unknown')}
- Task Summary: {json.dumps(context.get('task_summary', {}), indent=2)}
- Files Modified: {len(files)}

## Files to Review
{files_text}

## Review Instructions
Please provide a comprehensive code review covering:

1. **Code Quality**
   - Readability and maintainability
   - Adherence to Python/language best practices
   - Code organization and structure

2. **Security**
   - Potential vulnerabilities
   - Input validation
   - Error handling

3. **Performance**
   - Algorithmic efficiency
   - Resource usage
   - Potential bottlenecks

4. **Architecture**
   - Design patterns
   - Modularity
   - Extensibility

5. **Testing**
   - Test coverage recommendations
   - Edge cases to consider

Please categorize issues as:
- 🔴 Critical: Must fix before production
- 🟡 Important: Should fix soon
- 🟢 Suggestion: Nice to have improvements

Provide specific line numbers and code examples where applicable."""
        
        return prompt
        
    def _prepare_gemini_prompt(self, o3_review: str, files: List[str], context: Dict) -> str:
        """Prepare the prompt for Gemini meta-review."""
        prompt = f"""# Meta Code Review Analysis

You are reviewing another AI's code review to provide a second perspective and catch any missed issues.

## Original Review Context
- Files Reviewed: {len(files)}
- Review Model: {context.get('o3_model', 'o3-mini')}
- Session: {context.get('session_id', 'unknown')}

## Original Review
{o3_review}

## Your Task
Please provide a meta-analysis of the code review above:

1. **Review Quality Assessment**
   - Is the review thorough and comprehensive?
   - Are there any obvious issues missed?
   - Is the feedback constructive and actionable?

2. **Additional Insights**
   - What additional concerns should be addressed?
   - Are there architectural patterns or anti-patterns not mentioned?
   - What about long-term maintainability?

3. **Priority Adjustment**
   - Do you agree with the severity ratings?
   - Should any issues be escalated or downgraded?

4. **Missing Perspectives**
   - Security considerations not covered?
   - Performance implications overlooked?
   - Testing strategies not mentioned?

5. **Actionable Summary**
   - Top 3 most critical issues across both reviews
   - Recommended immediate actions
   - Long-term improvement suggestions

Please be specific and reference the original review where you agree or disagree."""
        
        return prompt
        
    def _format_final_review(self, o3_result: Dict, gemini_result: Dict, files: List[str], context: Dict) -> str:
        """Format the final review output."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        review = f"""# 🔍 Two-Level Code Review Report

**Generated**: {timestamp}  
**Session**: {context.get('session_id', 'unknown')}  
**Files Reviewed**: {len(files)}

---

## 📊 Review Summary

**Task Completion**: {context.get('task_summary', {}).get('completed_tasks', 0)}/{context.get('task_summary', {}).get('total_tasks', 0)} tasks completed  
**Success Rate**: {context.get('task_summary', {}).get('completion_rate', 0):.1f}%

---

## 🤖 Level 1: Initial Code Review
**Model**: {o3_result.get('model', 'unknown')}  
**Status**: {'✅ Success' if o3_result.get('success') else '❌ Failed'}

{o3_result.get('review', 'No review available')}

---

## 🧠 Level 2: Meta Review Analysis
**Model**: {gemini_result.get('model', 'unknown')}  
**Status**: {'✅ Success' if gemini_result.get('success') else '❌ Failed'}

{gemini_result.get('meta_review', 'No meta-review available')}

---

## 📝 Files Reviewed

"""
        
        for file_path in files:
            review += f"- `{file_path}`\n"
            
        review += """
---

## 🎯 Action Items

Based on both reviews, here are the consolidated action items:

### 🔴 Critical Issues
_[Extracted from reviews above]_

### 🟡 Important Improvements
_[Extracted from reviews above]_

### 🟢 Suggestions
_[Extracted from reviews above]_

---

_This review was generated automatically after task list completion._
"""
        
        return review
        
    def _extract_summary(self, review_text: str) -> Dict:
        """Extract summary statistics from review text."""
        summary = {
            "critical_issues": 0,
            "important_issues": 0,
            "suggestions": 0,
            "total_suggestions": 0
        }
        
        # Count issue types
        summary["critical_issues"] = review_text.count("🔴")
        summary["important_issues"] = review_text.count("🟡")
        summary["suggestions"] = review_text.count("🟢")
        summary["total_suggestions"] = sum([
            summary["critical_issues"],
            summary["important_issues"],
            summary["suggestions"]
        ])
        
        return summary
        
    async def run_two_level_review(self, files: List[str], context: Dict) -> Dict:
        """Run the complete 2-level review process."""
        logger.info(f"Starting 2-level code review for {len(files)} files")
        
        # Level 1: o3 review
        o3_result = await self.run_o3_review(files, context)
        
        if not o3_result.get("success"):
            logger.error("Level 1 review failed")
            return {
                "success": False,
                "error": "Level 1 (o3) review failed",
                "details": o3_result
            }
            
        # Add o3 model to context for Gemini
        context["o3_model"] = o3_result.get("model", "unknown")
        
        # Level 2: Gemini meta-review
        gemini_result = await self.run_gemini_meta_review(
            o3_result["review"],
            files,
            context
        )
        
        # Format final review
        final_review = self._format_final_review(o3_result, gemini_result, files, context)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"review_{context.get('session_id', 'unknown')}_{timestamp}.md"
        
        try:
            with open(output_file, 'w') as f:
                f.write(final_review)
            logger.info(f"Review saved to: {output_file}")
        except Exception as e:
            logger.error(f"Could not save review: {e}")
            output_file = None
            
        # Extract summary
        summary = self._extract_summary(final_review)
        
        return {
            "success": True,
            "level1": o3_result,
            "level2": gemini_result,
            "final_review": final_review,
            "output_file": str(output_file) if output_file else None,
            "summary": summary
        }


# Test functionality
if __name__ == "__main__":
    async def test():
        print("\n=== Two-Level Code Review Test ===\n")
        
        reviewer = TwoLevelCodeReview()
        
        # Test files (use actual files from the project)
        test_files = [
            "/home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/hook_integration.py",
            "/home/graham/workspace/experiments/cc_executor/src/cc_executor/hooks/update_task_status.py"
        ]
        
        # Filter to existing files
        test_files = [f for f in test_files if os.path.exists(f)]
        
        if not test_files:
            print("No test files found")
            return
            
        print(f"Testing with {len(test_files)} files")
        
        context = {
            "session_id": "test_session",
            "task_summary": {
                "total_tasks": 5,
                "completed_tasks": 5,
                "completion_rate": 100.0
            }
        }
        
        # Test prompt generation
        print("\n1. Testing o3 prompt generation:")
        prompt = reviewer._prepare_o3_prompt(test_files, context)
        print(f"   Prompt length: {len(prompt)} chars")
        print(f"   First 200 chars: {prompt[:200]}...")
        
        print("\n2. Testing Gemini prompt generation:")
        mock_o3_review = "This is a mock o3 review with some 🔴 critical and 🟡 important issues."
        gemini_prompt = reviewer._prepare_gemini_prompt(mock_o3_review, test_files, context)
        print(f"   Prompt length: {len(gemini_prompt)} chars")
        
        print("\n3. Testing review formatting:")
        mock_results = {
            "o3": {"success": True, "review": mock_o3_review, "model": "o3-mini"},
            "gemini": {"success": True, "meta_review": "This is a mock Gemini meta-review.", "model": "gemini"}
        }
        
        final = reviewer._format_final_review(
            mock_results["o3"],
            mock_results["gemini"],
            test_files,
            context
        )
        print(f"   Final review length: {len(final)} chars")
        
        print("\n4. Testing summary extraction:")
        summary = reviewer._extract_summary(final)
        print(f"   Summary: {summary}")
        
        print("\n=== Test Complete ===")
        
    # Run test
    asyncio.run(test())