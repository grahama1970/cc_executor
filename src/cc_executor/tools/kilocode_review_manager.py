#!/usr/bin/env python3
"""
KiloCode Review Manager - Optimized Human-in-the-Loop Workflow

Directory Structure:
kilocode_reviews/
├── 01_ready_for_human/          # What humans need to act on NOW
│   └── 2025-07-19_1430_auth_security/
│       ├── COPY_THIS_PROMPT.md   # Clear action required
│       ├── metadata.json         # Request details
│       └── INSTRUCTIONS.txt      # Step-by-step for human
│
├── 02_awaiting_results/         # In KiloCode, waiting for results
│   └── 2025-07-19_1430_auth_security/
│       └── PASTE_RESULTS_HERE.txt # Where to put KiloCode output
│
├── 03_results_received/         # Results back, needs processing
│   └── 2025-07-19_1430_auth_security/
│       ├── kilocode_output.txt   # Raw KiloCode output
│       └── parsed_issues.json    # Extracted actionable items
│
├── 04_fixes_in_progress/        # Claude Code is implementing
│   └── 2025-07-19_1430_auth_security/
│       ├── FIX_001_HIGH_sql_injection.json
│       └── FIX_002_MEDIUM_xss_issue.json
│
├── 05_completed/                # Done, archived
│   └── 2025-07-19_1430_auth_security/
│       └── COMPLETION_REPORT.json
│
└── DASHBOARD.json               # Current status of all reviews
"""

import json
import os
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from loguru import logger


class ReviewStage(Enum):
    """Workflow stages with clear numbering."""
    READY_FOR_HUMAN = "01_ready_for_human"
    AWAITING_RESULTS = "02_awaiting_results"
    RESULTS_RECEIVED = "03_results_received"
    FIXES_IN_PROGRESS = "04_fixes_in_progress"
    COMPLETED = "05_completed"


class KiloCodeReviewManager:
    """Manages human-in-the-loop code review workflow with KiloCode."""
    
    def __init__(self, base_dir: str = "/tmp/kilocode_reviews"):
        self.base_dir = Path(base_dir)
        self._setup_directories()
        self._update_dashboard()
    
    def _setup_directories(self):
        """Create workflow directory structure."""
        for stage in ReviewStage:
            (self.base_dir / stage.value).mkdir(parents=True, exist_ok=True)
    
    def _generate_review_name(self, description: str) -> str:
        """Generate descriptive folder name: YYYY-MM-DD_HHMM_description."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        # Clean description for filesystem
        clean_desc = re.sub(r'[^a-zA-Z0-9_-]', '_', description.lower())
        clean_desc = clean_desc[:40]  # Limit length
        return f"{timestamp}_{clean_desc}"
    
    def create_review_request(
        self,
        files: List[str],
        description: str,
        context: Optional[str] = None,
        focus: Optional[str] = None,
        severity: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        """
        Create a new review request in 01_ready_for_human.
        
        Args:
            files: List of file paths to review
            description: Human-readable description (used in folder name)
            context: Project context/constraints
            focus: Review focus (security, performance, etc.)
            severity: Minimum severity to report
        
        Returns:
            Dict with review_name and instructions for human
        """
        review_name = self._generate_review_name(description)
        review_dir = self.base_dir / ReviewStage.READY_FOR_HUMAN.value / review_name
        review_dir.mkdir(parents=True, exist_ok=True)
        
        # Read file contents
        file_contents = {}
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    file_contents[file_path] = f.read()
                logger.info(f"Read {file_path}")
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                file_contents[file_path] = f"[ERROR READING FILE: {e}]"
        
        # Save metadata
        metadata = {
            "review_name": review_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "stage": ReviewStage.READY_FOR_HUMAN.value,
            "files": files,
            "context": context,
            "focus": focus,
            "severity": severity
        }
        
        with open(review_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Generate KiloCode prompt
        prompt = self._generate_kilocode_prompt(metadata, file_contents)
        with open(review_dir / "COPY_THIS_PROMPT.md", 'w') as f:
            f.write(prompt)
        
        # Create human instructions
        instructions = f"""KILOCODE REVIEW REQUEST: {description}

STEP-BY-STEP INSTRUCTIONS:

1. COPY the entire contents of COPY_THIS_PROMPT.md

2. OPEN VS Code with KiloCode

3. TYPE: /review-contextual

4. PASTE the prompt

5. WAIT for KiloCode to complete the review

6. COPY KiloCode's ENTIRE response

7. MOVE this folder to 02_awaiting_results/

8. PASTE the response into PASTE_RESULTS_HERE.txt

Files to review: {len(files)}
Focus: {focus or 'general'}
Severity: {severity}

Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        with open(review_dir / "INSTRUCTIONS.txt", 'w') as f:
            f.write(instructions)
        
        self._update_dashboard()
        
        logger.info(f"Created review request: {review_name}")
        
        return {
            "success": True,
            "review_name": review_name,
            "location": str(review_dir),
            "action_required": "Copy COPY_THIS_PROMPT.md and follow INSTRUCTIONS.txt"
        }
    
    def _generate_kilocode_prompt(self, metadata: Dict[str, Any], file_contents: Dict[str, str]) -> str:
        """Generate prompt optimized for KiloCode's /review-contextual."""
        parts = []
        
        # Context section (if provided)
        if metadata.get("context"):
            parts.append(f"# Project Context\n\n{metadata['context']}\n")
        
        # Files section
        parts.append("# Files to Review\n")
        for i, (file_path, content) in enumerate(file_contents.items(), 1):
            parts.append(f"\n## File {i}: {file_path}\n")
            parts.append("```python")
            parts.append(content)
            parts.append("```")
        
        # Review instructions
        parts.append("\n# Review Instructions\n")
        parts.append(f"Description: {metadata['description']}\n")
        
        if metadata.get("focus"):
            parts.append(f"Primary Focus: {metadata['focus']}")
        
        parts.append(f"Minimum Severity: {metadata.get('severity', 'medium')}")
        parts.append("\nFor each issue found:")
        parts.append("1. Specify the exact file and line number")
        parts.append("2. Categorize by type (security, performance, quality, etc.)")
        parts.append("3. Provide severity (critical, high, medium, low)")
        parts.append("4. Give a clear description of the issue")
        parts.append("5. Provide specific, actionable fix with code example")
        parts.append("6. Note if the fix might conflict with the project context")
        
        return "\n".join(parts)
    
    def save_results(self, review_name: str, results_text: str) -> Dict[str, Any]:
        """
        Save KiloCode results and extract actionable fixes.
        
        Args:
            review_name: The review folder name
            results_text: Raw text output from KiloCode
        
        Returns:
            Dict with parsed fixes and next steps
        """
        # Find the review in awaiting_results
        awaiting_dir = self.base_dir / ReviewStage.AWAITING_RESULTS.value / review_name
        if not awaiting_dir.exists():
            # Check if still in ready_for_human
            ready_dir = self.base_dir / ReviewStage.READY_FOR_HUMAN.value / review_name
            if ready_dir.exists():
                # Move to awaiting first
                shutil.move(str(ready_dir), str(awaiting_dir))
            else:
                return {"success": False, "error": f"Review {review_name} not found"}
        
        # Move to results_received
        results_dir = self.base_dir / ReviewStage.RESULTS_RECEIVED.value / review_name
        shutil.move(str(awaiting_dir), str(results_dir))
        
        # Save raw output
        with open(results_dir / "kilocode_output.txt", 'w') as f:
            f.write(results_text)
        
        # Parse results to extract fixes
        parsed_issues = self._parse_kilocode_output(results_text)
        
        with open(results_dir / "parsed_issues.json", 'w') as f:
            json.dump(parsed_issues, f, indent=2)
        
        # Create individual fix files
        fixes_created = []
        for i, issue in enumerate(parsed_issues, 1):
            severity = issue.get("severity", "medium").upper()
            category = issue.get("category", "general")
            fix_name = f"FIX_{i:03d}_{severity}_{category}"
            
            fix_data = {
                "fix_id": fix_name,
                "review_name": review_name,
                "issue": issue,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            
            fix_file = results_dir / f"{fix_name}.json"
            with open(fix_file, 'w') as f:
                json.dump(fix_data, f, indent=2)
            
            fixes_created.append(fix_name)
        
        # Update metadata
        metadata_file = results_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        metadata["stage"] = ReviewStage.RESULTS_RECEIVED.value
        metadata["results_saved_at"] = datetime.now().isoformat()
        metadata["fixes_count"] = len(fixes_created)
        metadata["fixes"] = fixes_created
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self._update_dashboard()
        
        logger.info(f"Saved results for {review_name}, extracted {len(fixes_created)} fixes")
        
        return {
            "success": True,
            "review_name": review_name,
            "fixes_extracted": len(fixes_created),
            "fixes": fixes_created,
            "next_step": "Run get_pending_fixes() to see fixes ready for implementation"
        }
    
    def _parse_kilocode_output(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse KiloCode output to extract actionable issues.
        
        This handles various formats KiloCode might use.
        """
        issues = []
        
        # Try to parse as JSON first
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "issues" in data:
                return data["issues"]
        except:
            pass
        
        # Parse text format with better handling of sections
        current_issue = {}
        in_code_block = False
        code_block_content = []
        current_section = None
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for code blocks
            if line.startswith("```"):
                if in_code_block:
                    # End of code block
                    if current_issue and code_block_content:
                        current_issue["code_fix"] = "\n".join(code_block_content)
                    code_block_content = []
                else:
                    # Skip the language identifier line
                    i += 1
                    if i < len(lines) and lines[i].strip().startswith("#"):
                        # This might be a comment about what to replace
                        comment = lines[i].strip()
                        if "replace" in comment.lower():
                            current_issue["fix_instruction"] = comment
                in_code_block = not in_code_block
                i += 1
                continue
            
            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue
            
            # Look for issue headers (e.g., "### Issue 1: SQL Injection")
            if line.startswith("###") and "issue" in line.lower():
                # Save previous issue if exists
                if current_issue and ("file" in current_issue or "description" in current_issue):
                    # Ensure all fields have defaults
                    current_issue.setdefault("file", "unknown")
                    current_issue.setdefault("line", 0)
                    current_issue.setdefault("severity", "medium")
                    current_issue.setdefault("category", "general")
                    current_issue.setdefault("description", line.replace("###", "").strip())
                    issues.append(current_issue)
                
                # Start new issue
                current_issue = {}
                # Extract description from header
                desc = line.replace("###", "").strip()
                if ":" in desc:
                    desc = desc.split(":", 1)[1].strip()
                current_issue["description"] = desc
            
            # Look for file headers (e.g., "## File: /path/to/file.py")
            elif line.startswith("##") and "file:" in line.lower():
                file_path = self._extract_value(line)
                if current_issue is not None:
                    current_issue["file"] = file_path
                else:
                    current_issue = {"file": file_path}
            
            # Parse bullet points with metadata
            elif line.startswith("-") and "**" in line:
                # Parse lines like: "- **Line**: 42"
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.replace("-", "").replace("**", "").strip().lower()
                    value = value.strip()
                    
                    if key == "line":
                        try:
                            current_issue["line"] = int(value)
                        except:
                            current_issue["line"] = 0
                    elif key in ["severity", "level", "priority"]:
                        current_issue["severity"] = value.lower()
                    elif key in ["category", "type"]:
                        current_issue["category"] = value.lower()
                    elif key == "description":
                        current_issue["description"] = value
                    elif key in ["fix", "recommendation"]:
                        current_issue["recommendation"] = value
            
            i += 1
        
        # Add last issue
        if current_issue and ("file" in current_issue or "description" in current_issue):
            # Ensure all fields have defaults
            current_issue.setdefault("file", "unknown")
            current_issue.setdefault("line", 0)
            current_issue.setdefault("severity", "medium")
            current_issue.setdefault("category", "general")
            current_issue.setdefault("description", "Issue found")
            issues.append(current_issue)
        
        # If no structured issues found but we have content, parse more loosely
        if not issues and len(text.strip()) > 50:
            # Try to at least extract file references and issues
            file_match = None
            for line in lines:
                if "file:" in line.lower() or ".py" in line:
                    file_match = line
                    break
            
            issues.append({
                "file": file_match or "general",
                "line": 0,
                "severity": "medium",
                "category": "review",
                "description": "See full review output",
                "recommendation": "Review the complete output for detailed recommendations"
            })
        
        return issues
    
    def _extract_value(self, line: str) -> str:
        """Extract value after colon in a line."""
        if ':' in line:
            return line.split(':', 1)[1].strip()
        return line
    
    def get_pending_fixes(self) -> List[Dict[str, Any]]:
        """Get all fixes ready for implementation."""
        fixes = []
        
        # Look in results_received stage
        results_dir = self.base_dir / ReviewStage.RESULTS_RECEIVED.value
        for review_dir in results_dir.iterdir():
            if review_dir.is_dir():
                for fix_file in review_dir.glob("FIX_*.json"):
                    with open(fix_file, 'r') as f:
                        fix_data = json.load(f)
                        fix_data["review_path"] = str(review_dir)
                        fixes.append(fix_data)
        
        # Sort by severity (critical > high > medium > low)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        fixes.sort(key=lambda x: (
            severity_order.get(x.get("issue", {}).get("severity", "medium"), 2),
            x.get("created_at", "")
        ))
        
        return fixes
    
    def start_fix(self, review_name: str, fix_id: str) -> Dict[str, Any]:
        """Move a fix to in_progress stage."""
        # Find the review
        results_dir = self.base_dir / ReviewStage.RESULTS_RECEIVED.value / review_name
        if not results_dir.exists():
            return {"success": False, "error": f"Review {review_name} not found"}
        
        # Check if we need to move the entire review
        in_progress_dir = self.base_dir / ReviewStage.FIXES_IN_PROGRESS.value / review_name
        if not in_progress_dir.exists():
            # First fix for this review - move it
            shutil.move(str(results_dir), str(in_progress_dir))
        
        self._update_dashboard()
        
        return {
            "success": True,
            "review_name": review_name,
            "fix_id": fix_id,
            "status": "in_progress"
        }
    
    def complete_fix(self, review_name: str, fix_id: str, notes: str = "") -> Dict[str, Any]:
        """Mark a fix as completed."""
        in_progress_dir = self.base_dir / ReviewStage.FIXES_IN_PROGRESS.value / review_name
        fix_file = in_progress_dir / f"{fix_id}.json"
        
        if not fix_file.exists():
            return {"success": False, "error": f"Fix {fix_id} not found"}
        
        # Update fix data
        with open(fix_file, 'r') as f:
            fix_data = json.load(f)
        
        fix_data["status"] = "completed"
        fix_data["completed_at"] = datetime.now().isoformat()
        fix_data["implementation_notes"] = notes
        
        with open(fix_file, 'w') as f:
            json.dump(fix_data, f, indent=2)
        
        # Check if all fixes are done
        remaining_fixes = 0
        for f in in_progress_dir.glob("FIX_*.json"):
            with open(f, 'r') as file:
                data = json.load(file)
                if data.get("status") != "completed":
                    remaining_fixes += 1
        
        if remaining_fixes == 0:
            # All fixes done - move to completed
            completed_dir = self.base_dir / ReviewStage.COMPLETED.value / review_name
            shutil.move(str(in_progress_dir), str(completed_dir))
            
            # Create completion report
            self._create_completion_report(completed_dir)
        
        self._update_dashboard()
        
        return {
            "success": True,
            "fix_id": fix_id,
            "remaining_fixes": remaining_fixes,
            "review_completed": remaining_fixes == 0
        }
    
    def _create_completion_report(self, completed_dir: Path):
        """Create a summary report for completed review."""
        metadata_file = completed_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Collect all fix data
        fixes_summary = []
        for fix_file in completed_dir.glob("FIX_*.json"):
            with open(fix_file, 'r') as f:
                fix_data = json.load(f)
                fixes_summary.append({
                    "fix_id": fix_data["fix_id"],
                    "severity": fix_data.get("issue", {}).get("severity", "unknown"),
                    "status": fix_data.get("status", "unknown"),
                    "completed_at": fix_data.get("completed_at", "")
                })
        
        report = {
            "review_name": metadata["review_name"],
            "description": metadata["description"],
            "created_at": metadata["created_at"],
            "completed_at": datetime.now().isoformat(),
            "files_reviewed": metadata["files"],
            "total_fixes": len(fixes_summary),
            "fixes_summary": fixes_summary,
            "stage": ReviewStage.COMPLETED.value
        }
        
        with open(completed_dir / "COMPLETION_REPORT.json", 'w') as f:
            json.dump(report, f, indent=2)
    
    def _update_dashboard(self):
        """Update the dashboard with current status."""
        dashboard = {
            "updated_at": datetime.now().isoformat(),
            "stages": {}
        }
        
        for stage in ReviewStage:
            stage_dir = self.base_dir / stage.value
            reviews = []
            
            for review_dir in stage_dir.iterdir():
                if review_dir.is_dir():
                    metadata_file = review_dir / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            reviews.append({
                                "name": review_dir.name,
                                "description": metadata.get("description", ""),
                                "created_at": metadata.get("created_at", ""),
                                "files_count": len(metadata.get("files", []))
                            })
            
            dashboard["stages"][stage.value] = {
                "count": len(reviews),
                "reviews": reviews
            }
        
        with open(self.base_dir / "DASHBOARD.json", 'w') as f:
            json.dump(dashboard, f, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        dashboard_file = self.base_dir / "DASHBOARD.json"
        if dashboard_file.exists():
            with open(dashboard_file, 'r') as f:
                return json.load(f)
        return {"error": "Dashboard not found"}


# Usage example
if __name__ == "__main__":
    manager = KiloCodeReviewManager()
    
    print("KiloCode Review Manager - Demo")
    print("=" * 50)
    
    # Create a review
    result = manager.create_review_request(
        files=["test.py"],
        description="auth_security_review",
        context="Web application with strict security requirements",
        focus="security",
        severity="high"
    )
    
    print(f"\nCreated review: {result['review_name']}")
    print(f"Location: {result['location']}")
    print(f"Action: {result['action_required']}")
    
    # Show status
    status = manager.get_status()
    print(f"\nCurrent Status:")
    for stage, data in status.get("stages", {}).items():
        print(f"  {stage}: {data['count']} reviews")