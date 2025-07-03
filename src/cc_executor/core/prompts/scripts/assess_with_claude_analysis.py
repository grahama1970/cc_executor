#!/usr/bin/env python3
"""
Enhanced assessment script that includes Claude's reasonableness analysis.
This addresses the v8 failure by ensuring Claude adds assessments to the report.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent.parent.parent))

# Import the base assessor
from assess_all_core_usage import CoreUsageAssessor

class ClaudeEnhancedAssessor(CoreUsageAssessor):
    """Enhanced assessor that includes Claude's manual analysis."""
    
    def __init__(self):
        super().__init__()
        self.template_path = Path("/home/graham/workspace/experiments/cc_executor/docs/templates/CORE_ASSESSMENT_REPORT_TEMPLATE.md")
        
    def get_claude_assessment(self, filename: str, output: Dict[str, str], 
                            expectations: Dict[str, Any], auto_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Claude's reasonableness assessment for a component.
        This is where Claude's analysis happens - not automated!
        """
        # This is a placeholder that shows the structure
        # In practice, Claude would fill this in based on actual analysis
        claude_assessment = {
            'verdict': 'REASONABLE',  # or 'UNREASONABLE' or 'SUSPICIOUS'
            'expected': f"Component should demonstrate {expectations['description']}",
            'observed': "What Claude actually sees in the output",
            'evidence': [
                "Specific evidence point 1",
                "Specific evidence point 2"
            ],
            'numerical_validation': [
                "Analysis of numbers in output"
            ],
            'conclusion': "Why this output proves (or doesn't prove) the component works"
        }
        
        # For now, return a structure that Claude would fill in
        return {
            'needs_claude_analysis': True,
            'structure': claude_assessment
        }
    
    def generate_report(self):
        """Generate report following the new template with Claude's assessments."""
        report_lines = []
        
        # Header with template reference
        report_lines.extend([
            f"# Core Components Usage Assessment Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session ID: {self.session_id}",
            f"Assessed by: Claude (Script: assess_all_core_usage.py + Manual Analysis)",
            f"Template: docs/templates/CORE_ASSESSMENT_REPORT_TEMPLATE.md v1.0",
            "",
            "## Summary",
            f"- Total Components Tested: {len(self.results)}",
            f"- Automated Pass Rate: {sum(1 for r in self.results if r['assessment']['reasonable']) / len(self.results) * 100:.1f}%",
            f"- Claude's Verified Pass Rate: [REQUIRES CLAUDE'S ANALYSIS]",
            f"- Critical Component (websocket_handler.py): {'✅ PASSED' if any(r['filename'] == 'websocket_handler.py' and r['assessment']['reasonable'] for r in self.results) else '❌ FAILED'}",
            f"- System Health: [REQUIRES CLAUDE'S OVERALL ASSESSMENT]",
            "",
        ])
        
        # Component results with Claude's assessment placeholder
        report_lines.extend([
            "## Component Results",
            ""
        ])
        
        for result in self.results:
            status = '✅' if result['assessment']['reasonable'] else '❌'
            
            # Automated results
            report_lines.extend([
                f"### {status} {result['filename']}",
                "",
                "#### Automated Test Results",
                f"- **Exit Code**: {result['output']['exit_code']}",
                f"- **Execution Time**: {result['output']['execution_time']:.2f}s",
                f"- **Output Lines**: {result['assessment']['line_count']}",
                f"- **Expected Indicators Found**: {', '.join(result['assessment']['indicators_found']) or 'None'}",
                f"- **Contains Numbers**: {'Yes' if result['assessment']['has_numbers'] else 'No'}",
                ""
            ])
            
            # Claude's assessment section
            report_lines.extend([
                "#### 🧠 Claude's Reasonableness Assessment",
                "**Verdict**: [CLAUDE MUST FILL THIS IN]",
                "",
                "**Expected vs Actual**:",
                f"- **Expected**: {result['expectations']['description']}",
                "- **Observed**: [CLAUDE: Describe what you see in the output]",
                "",
                "**Evidence Analysis**:",
                "✓ [CLAUDE: Add specific evidence that proves functionality]",
                "✓ [CLAUDE: Add more evidence points]",
                "✗ [CLAUDE: Note anything missing or concerning]",
                "",
                "**Numerical Validation**:",
                "- [CLAUDE: Analyze any numbers - are they sensible?]",
                "",
                "**Conclusion**: [CLAUDE: 1-2 sentences on whether this proves the component works]",
                ""
            ])
            
            # Output sample
            report_lines.extend([
                "#### Output Sample",
                "```",
                "--- STDOUT ---",
                result['output']['stdout'][:1000] + ('...[truncated]' if len(result['output']['stdout']) > 1000 else ''),
                "\n--- STDERR ---",
                result['output']['stderr'][:500] + ('...[truncated]' if len(result['output']['stderr']) > 500 else ''),
                "```",
                "\n---\n"
            ])
        
        # Claude's overall assessment section
        report_lines.extend([
            "## 🎯 Claude's Overall System Assessment",
            "",
            "### System Health Analysis",
            "Based on the outputs, I assess the cc_executor core system as: [CLAUDE: HEALTHY/DEGRADED/FAILING]",
            "",
            "**Key Observations**:",
            "1. [CLAUDE: Major finding from outputs]",
            "2. [CLAUDE: Pattern noticed across components]", 
            "3. [CLAUDE: Any concerning indicators]",
            "",
            "### Confidence in Results",
            "**Confidence Level**: [CLAUDE: HIGH/MEDIUM/LOW]",
            "",
            "**Reasoning**: [CLAUDE: Why you have this confidence level]",
            "",
            "### Risk Assessment",
            "- **Immediate Risks**: [CLAUDE: Any critical issues found]",
            "- **Potential Issues**: [CLAUDE: Things that might become problems]",
            "- **Unknown Factors**: [CLAUDE: What couldn't be verified]",
            ""
        ])
        
        # Recommendations
        report_lines.extend([
            "## 📋 Recommendations",
            "",
            "### Immediate Actions",
            "1. [CLAUDE: Critical fixes needed based on assessment]",
            "",
            "### Improvements", 
            "1. [CLAUDE: Suggested enhancements based on output analysis]",
            "",
            "### Future Monitoring",
            "1. [CLAUDE: What to watch for in future assessments]",
            ""
        ])
        
        # Note for Claude
        report_lines.extend([
            "---",
            "**NOTE FOR CLAUDE**: This report has placeholders marked with [CLAUDE: ...]. ",
            "You must fill in each of these with your actual analysis of the outputs!",
            "This is not optional - the v8 report failed because it lacked your assessments."
        ])
        
        # Write report
        with open(self.report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n{'='*60}")
        print(f"Assessment Complete!")
        print(f"{'='*60}")
        print(f"Report saved to: {self.report_path}")
        print(f"\n⚠️  IMPORTANT: Claude must now fill in the analysis sections!")
        print(f"The report has placeholders marked [CLAUDE: ...] that need real analysis.")


if __name__ == "__main__":
    # Use same environment setup as base script
    os.environ['SKIP_HOOK_EXECUTION'] = 'true'
    os.environ['SKIP_WEBSOCKET_HANDLER'] = 'true'
    
    assessor = ClaudeEnhancedAssessor()
    assessor.run_tests()
    
    print("\n" + "="*60)
    print("NEXT STEP: Claude must read the report and fill in all [CLAUDE: ...] sections")
    print("with actual reasonableness assessments based on the output samples.")
    print("="*60)