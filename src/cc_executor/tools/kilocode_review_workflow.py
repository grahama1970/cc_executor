#!/usr/bin/env python3
"""
KiloCode Review Workflow Manager

This tool manages a human-in-the-loop workflow for code reviews:
1. Claude Code creates review requests
2. Human manually triggers KiloCode's /review-contextual
3. Human saves results back
4. Claude Code implements approved fixes

The workflow directory structure:
/tmp/kilocode_workflow/
├── requests/
│   ├── pending/
│   │   └── review_12345.json
│   └── completed/
│       └── review_12345.json
├── prompts/
│   └── review_12345.md  (ready for copy/paste)
├── results/
│   └── review_12345_results.json
└── fixes/
    ├── pending/
    │   └── fix_12345.json
    └── completed/
        └── fix_12345.json
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

from loguru import logger


class ReviewStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    FIXES_PENDING = "fixes_pending"
    COMPLETED = "completed"


class KiloCodeWorkflow:
    """Manages the human-in-the-loop code review workflow."""
    
    def __init__(self, base_dir: str = "/tmp/kilocode_workflow"):
        self.base_dir = Path(base_dir)
        self._setup_directories()
    
    def _setup_directories(self):
        """Create the workflow directory structure."""
        dirs = [
            "requests/pending",
            "requests/completed",
            "prompts",
            "results",
            "fixes/pending",
            "fixes/completed"
        ]
        for dir_path in dirs:
            (self.base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    def create_review_request(
        self,
        files: List[str],
        context: Optional[str] = None,
        focus: Optional[str] = None,
        severity: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        """
        Create a new review request and generate copy-paste prompt.
        
        Returns:
            Dict with request_id, prompt_file, and instructions
        """
        # Generate request ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_id = f"review_{timestamp}"
        
        # Read file contents
        file_contents = {}
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    file_contents[file_path] = f.read()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                file_contents[file_path] = f"Error reading file: {e}"
        
        # Create request data
        request_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "status": ReviewStatus.PENDING.value,
            "files": files,
            "file_contents": file_contents,
            "context": context,
            "focus": focus,
            "severity": severity
        }
        
        # Save request
        request_file = self.base_dir / "requests" / "pending" / f"{request_id}.json"
        with open(request_file, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        # Generate KiloCode prompt
        prompt = self._generate_kilocode_prompt(request_data)
        prompt_file = self.base_dir / "prompts" / f"{request_id}.md"
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        # Generate instructions
        instructions = f"""
=== CODE REVIEW REQUEST CREATED ===

Request ID: {request_id}
Files: {len(files)}
Status: PENDING

HUMAN ACTION REQUIRED:
1. Copy the prompt from: {prompt_file}
2. Open KiloCode in VS Code
3. Run: /review-contextual
4. Paste the prompt
5. Save results to: {self.base_dir}/results/{request_id}_results.json

The prompt has been formatted for KiloCode's /review-contextual command.
"""
        
        logger.info(f"Created review request: {request_id}")
        
        return {
            "request_id": request_id,
            "prompt_file": str(prompt_file),
            "instructions": instructions,
            "status": "success"
        }
    
    def _generate_kilocode_prompt(self, request_data: Dict[str, Any]) -> str:
        """Generate a prompt formatted for KiloCode's /review-contextual."""
        parts = []
        
        # Add context if provided
        if request_data.get("context"):
            parts.append(f"# Context\n\n{request_data['context']}\n")
        
        # Add files
        parts.append("# Files to Review\n")
        for file_path, content in request_data["file_contents"].items():
            parts.append(f"\n## {file_path}\n")
            parts.append("```python")
            parts.append(content)
            parts.append("```\n")
        
        # Add review instructions
        parts.append("\n# Review Instructions\n")
        if request_data.get("focus"):
            parts.append(f"Focus on: {request_data['focus']}\n")
        parts.append(f"Minimum severity: {request_data.get('severity', 'medium')}\n")
        parts.append("\nProvide actionable fixes with code examples where applicable.")
        parts.append("\nFor each issue, indicate if the fix would violate the project context.")
        
        return "\n".join(parts)
    
    def save_review_results(self, request_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save KiloCode review results and extract fixes.
        
        Args:
            request_id: The review request ID
            results: The review results from KiloCode
        
        Returns:
            Dict with extracted fixes and status
        """
        # Load original request
        request_file = self.base_dir / "requests" / "pending" / f"{request_id}.json"
        if not request_file.exists():
            return {"status": "error", "message": f"Request {request_id} not found"}
        
        with open(request_file, 'r') as f:
            request_data = json.load(f)
        
        # Save results
        results_file = self.base_dir / "results" / f"{request_id}_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Extract fixes
        fixes = self._extract_fixes(request_data, results)
        
        # Create fix requests
        fix_ids = []
        for fix in fixes:
            fix_id = self._create_fix_request(request_id, fix)
            fix_ids.append(fix_id)
        
        # Update request status
        request_data["status"] = ReviewStatus.FIXES_PENDING.value
        request_data["results_file"] = str(results_file)
        request_data["fix_ids"] = fix_ids
        
        # Move to completed
        completed_file = self.base_dir / "requests" / "completed" / f"{request_id}.json"
        with open(completed_file, 'w') as f:
            json.dump(request_data, f, indent=2)
        request_file.unlink()
        
        logger.info(f"Saved results for {request_id}, extracted {len(fixes)} fixes")
        
        return {
            "status": "success",
            "request_id": request_id,
            "fixes_extracted": len(fixes),
            "fix_ids": fix_ids
        }
    
    def _extract_fixes(self, request_data: Dict[str, Any], results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract actionable fixes from review results."""
        fixes = []
        
        # Handle different result formats
        if isinstance(results, dict):
            # Look for common patterns in KiloCode results
            issues = results.get("issues", [])
            if not issues and "actionable_fixes" in results:
                issues = results["actionable_fixes"]
            elif not issues and "recommendations" in results:
                issues = results["recommendations"]
            
            for issue in issues:
                if isinstance(issue, dict):
                    fix = {
                        "file": issue.get("file", ""),
                        "line": issue.get("line", 0),
                        "description": issue.get("description", ""),
                        "recommendation": issue.get("recommendation", ""),
                        "code_fix": issue.get("code_fix", ""),
                        "severity": issue.get("severity", "medium"),
                        "category": issue.get("category", "general")
                    }
                    fixes.append(fix)
        
        return fixes
    
    def _create_fix_request(self, review_id: str, fix: Dict[str, Any]) -> str:
        """Create a fix request for tracking."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        fix_id = f"fix_{timestamp}"
        
        fix_data = {
            "fix_id": fix_id,
            "review_id": review_id,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "fix": fix,
            "implemented": False,
            "implementation_notes": ""
        }
        
        fix_file = self.base_dir / "fixes" / "pending" / f"{fix_id}.json"
        with open(fix_file, 'w') as f:
            json.dump(fix_data, f, indent=2)
        
        return fix_id
    
    def get_pending_fixes(self) -> List[Dict[str, Any]]:
        """Get all pending fixes to implement."""
        pending_dir = self.base_dir / "fixes" / "pending"
        fixes = []
        
        for fix_file in pending_dir.glob("*.json"):
            with open(fix_file, 'r') as f:
                fixes.append(json.load(f))
        
        return sorted(fixes, key=lambda x: x["timestamp"])
    
    def implement_fix(self, fix_id: str, notes: str = "") -> Dict[str, Any]:
        """Mark a fix as implemented."""
        fix_file = self.base_dir / "fixes" / "pending" / f"{fix_id}.json"
        if not fix_file.exists():
            return {"status": "error", "message": f"Fix {fix_id} not found"}
        
        with open(fix_file, 'r') as f:
            fix_data = json.load(f)
        
        # Update fix data
        fix_data["status"] = "completed"
        fix_data["implemented"] = True
        fix_data["implementation_notes"] = notes
        fix_data["completed_at"] = datetime.now().isoformat()
        
        # Move to completed
        completed_file = self.base_dir / "fixes" / "completed" / f"{fix_id}.json"
        with open(completed_file, 'w') as f:
            json.dump(fix_data, f, indent=2)
        fix_file.unlink()
        
        logger.info(f"Marked fix {fix_id} as implemented")
        
        return {"status": "success", "fix_id": fix_id}
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get overall workflow status."""
        status = {
            "pending_requests": len(list((self.base_dir / "requests" / "pending").glob("*.json"))),
            "completed_requests": len(list((self.base_dir / "requests" / "completed").glob("*.json"))),
            "pending_fixes": len(list((self.base_dir / "fixes" / "pending").glob("*.json"))),
            "completed_fixes": len(list((self.base_dir / "fixes" / "completed").glob("*.json"))),
            "results_available": len(list((self.base_dir / "results").glob("*.json")))
        }
        return status


# Usage functions for testing
async def demo_workflow():
    """Demonstrate the complete workflow."""
    workflow = KiloCodeWorkflow()
    
    # 1. Create a review request
    print("1. Creating review request...")
    result = workflow.create_review_request(
        files=["test_file.py"],
        context="This is a test project with security requirements",
        focus="security",
        severity="high"
    )
    print(result["instructions"])
    
    # 2. Simulate human saving results
    print("\n2. Simulating review results...")
    mock_results = {
        "issues": [
            {
                "file": "test_file.py",
                "line": 42,
                "severity": "high",
                "category": "security",
                "description": "SQL injection vulnerability",
                "recommendation": "Use parameterized queries",
                "code_fix": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
            }
        ]
    }
    
    save_result = workflow.save_review_results(result["request_id"], mock_results)
    print(f"Saved results: {save_result}")
    
    # 3. Get pending fixes
    print("\n3. Getting pending fixes...")
    fixes = workflow.get_pending_fixes()
    for fix in fixes:
        print(f"Fix {fix['fix_id']}: {fix['fix']['description']}")
    
    # 4. Implement a fix
    if fixes:
        print("\n4. Implementing first fix...")
        impl_result = workflow.implement_fix(fixes[0]["fix_id"], "Fixed using parameterized queries")
        print(f"Implementation result: {impl_result}")
    
    # 5. Check status
    print("\n5. Workflow status:")
    status = workflow.get_workflow_status()
    for key, value in status.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_workflow())