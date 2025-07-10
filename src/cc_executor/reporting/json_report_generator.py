#!/usr/bin/env python3
"""
JSON-based report generator for CC Executor.

This module generates reports ONLY from JSON responses to ensure verification
and prevent hallucination. All cc_execute calls must use json_mode=True.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from cc_executor.utils.json_utils import clean_json_string


class JSONReportGenerator:
    """Generate reports from verified JSON responses only."""
    
    def __init__(self):
        self.response_dir = Path(__file__).parent.parent / "client/tmp/responses"
        
    def load_json_response(self, response_file: Path) -> Optional[Dict[str, Any]]:
        """
        Load and validate a JSON response file.
        
        Returns None if file doesn't contain valid JSON response.
        """
        try:
            with open(response_file) as f:
                data = json.load(f)
            
            # Response must have these fields from cc_execute
            required_fields = ['output', 'execution_uuid', 'task']
            if not all(field in data for field in required_fields):
                return None
            
            # Parse the output as JSON
            output = data.get('output', '')
            if not output:
                return None
                
            # Use clean_json_string to extract JSON
            parsed = clean_json_string(output, return_dict=True)
            if not isinstance(parsed, dict):
                return None
            
            # Verify execution_uuid matches
            if 'execution_uuid' in parsed:
                if parsed['execution_uuid'] != data['execution_uuid']:
                    return None  # UUID mismatch - potential hallucination
            
            # Return enriched data
            return {
                'file_path': str(response_file),
                'file_name': response_file.name,
                'task': data['task'],
                'execution_uuid': data['execution_uuid'],
                'session_id': data.get('session_id', ''),
                'execution_time': data.get('execution_time', 0),
                'return_code': data.get('return_code', -1),
                'timestamp': data.get('timestamp', ''),
                'json_response': parsed,
                'raw_output': output
            }
            
        except Exception as e:
            return None
    
    def generate_execution_report(self, executions: List[Dict[str, Any]]) -> str:
        """
        Generate a markdown report from JSON executions.
        
        Args:
            executions: List of validated JSON execution data
            
        Returns:
            Markdown report string
        """
        report_lines = []
        
        # Header
        report_lines.append("# CC Executor JSON Execution Report")
        report_lines.append("")
        report_lines.append(f"**Generated**: {datetime.now().isoformat()}")
        report_lines.append(f"**Total Executions**: {len(executions)}")
        report_lines.append("")
        
        # Verification summary
        report_lines.append("## Verification Summary")
        report_lines.append("")
        report_lines.append("All executions in this report:")
        report_lines.append("- ✅ Have valid JSON responses")
        report_lines.append("- ✅ Include execution UUID for verification")
        report_lines.append("- ✅ Are saved as physical files on disk")
        report_lines.append("- ✅ Can be independently verified")
        report_lines.append("")
        
        # Execution details
        report_lines.append("## Execution Details")
        report_lines.append("")
        
        for i, exec_data in enumerate(executions, 1):
            report_lines.append(f"### Execution {i}")
            report_lines.append("")
            
            # Basic info
            report_lines.append("**Metadata**:")
            report_lines.append(f"- File: `{exec_data['file_name']}`")
            report_lines.append(f"- UUID: `{exec_data['execution_uuid']}`")
            report_lines.append(f"- Session: `{exec_data['session_id']}`")
            report_lines.append(f"- Duration: {exec_data['execution_time']:.1f}s")
            report_lines.append(f"- Exit Code: {exec_data['return_code']}")
            report_lines.append("")
            
            # Task
            report_lines.append("**Task**:")
            report_lines.append("```")
            report_lines.append(exec_data['task'])
            report_lines.append("```")
            report_lines.append("")
            
            # JSON Response
            json_resp = exec_data['json_response']
            report_lines.append("**JSON Response**:")
            report_lines.append("```json")
            report_lines.append(json.dumps(json_resp, indent=2))
            report_lines.append("```")
            report_lines.append("")
            
            # Extract specific fields if they exist
            if 'result' in json_resp:
                report_lines.append("**Result**:")
                if isinstance(json_resp['result'], str):
                    # If result is a JSON string, parse it
                    try:
                        result_parsed = clean_json_string(json_resp['result'], return_dict=True)
                        if isinstance(result_parsed, dict):
                            report_lines.append("```json")
                            report_lines.append(json.dumps(result_parsed, indent=2))
                            report_lines.append("```")
                        else:
                            report_lines.append(f"> {json_resp['result']}")
                    except:
                        report_lines.append(f"> {json_resp['result']}")
                else:
                    report_lines.append("```json")
                    report_lines.append(json.dumps(json_resp['result'], indent=2))
                    report_lines.append("```")
                report_lines.append("")
            
            if 'summary' in json_resp:
                report_lines.append(f"**Summary**: {json_resp['summary']}")
                report_lines.append("")
            
            # Verification
            report_lines.append("**Verification**:")
            report_lines.append(f"- Response File Exists: ✅")
            report_lines.append(f"- JSON Valid: ✅")
            report_lines.append(f"- UUID Match: {'✅' if json_resp.get('execution_uuid') == exec_data['execution_uuid'] else '❌'}")
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")
        
        # Footer
        report_lines.append("## Verification Instructions")
        report_lines.append("")
        report_lines.append("To independently verify these results:")
        report_lines.append("")
        report_lines.append("```bash")
        report_lines.append("# Check the response files exist")
        report_lines.append("ls -la src/cc_executor/client/tmp/responses/")
        report_lines.append("")
        report_lines.append("# Verify a specific execution")
        report_lines.append("cat src/cc_executor/client/tmp/responses/<filename> | jq .")
        report_lines.append("```")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("*This report was generated from actual JSON responses only.*")
        
        return '\n'.join(report_lines)
    
    def generate_report_from_files(self, response_files: List[Path], 
                                  output_path: Optional[Path] = None) -> Path:
        """
        Generate a report from response files.
        
        Args:
            response_files: List of response file paths
            output_path: Where to save the report
            
        Returns:
            Path to the generated report
        """
        # Load and validate all responses
        executions = []
        for file_path in response_files:
            exec_data = self.load_json_response(file_path)
            if exec_data:
                executions.append(exec_data)
        
        if not executions:
            raise ValueError("No valid JSON responses found. Ensure cc_execute uses json_mode=True")
        
        # Generate report
        report = self.generate_execution_report(executions)
        
        # Save report
        if output_path is None:
            output_path = Path(__file__).parent / f"JSON_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        return output_path
    
    def generate_latest_report(self, last_n: int = 5) -> Path:
        """Generate report from the latest N executions."""
        if not self.response_dir.exists():
            raise ValueError(f"Response directory does not exist: {self.response_dir}")
        
        # Get latest response files
        response_files = sorted(
            self.response_dir.glob("cc_execute_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:last_n]
        
        if not response_files:
            raise ValueError("No response files found")
        
        return self.generate_report_from_files(response_files)


def generate_json_report(last_n: int = 5) -> Path:
    """Quick function to generate a report from recent executions."""
    generator = JSONReportGenerator()
    return generator.generate_latest_report(last_n)


if __name__ == "__main__":
    # Generate report from last 5 executions
    report_path = generate_json_report(5)
    print(f"✅ Generated JSON-based report: {report_path}")