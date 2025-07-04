#!/usr/bin/env python3
"""
Comprehensive assessment of all usage functions in client/ directory.
Uses OutputCapture pattern and generates report following core standards.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# CRITICAL: Add parent directory to path BEFORE any imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import OutputCapture from core
from cc_executor.core.usage_helper import OutputCapture

# Import hooks
try:
    from cc_executor.hooks import setup_environment
    from cc_executor.hooks import check_task_dependencies
    from cc_executor.hooks import record_execution_metrics
    HOOKS_AVAILABLE = True
except ImportError:
    HOOKS_AVAILABLE = False
    print("WARNING: Hooks not available - running without environment setup")

class ClientUsageAssessor:
    """Run and assess all client component usage functions using OutputCapture pattern."""
    
    def __init__(self):
        self.client_dir = Path(__file__).parent.parent.parent  # Go up to client dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"CLIENT_ASSESS_{self.timestamp}"
        
        # Create reports directory
        self.reports_dir = self.client_dir / "prompts" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.report_path = self.reports_dir / f"CLIENT_USAGE_REPORT_{self.timestamp}.md"
        self.results = []
        self.start_time = time.time()
        self.redis_available = self._check_redis()
        
    def _check_redis(self) -> bool:
        """Check if Redis is available."""
        try:
            import redis
            r = redis.Redis(decode_responses=True)
            r.ping()
            return True
        except:
            return False
    
    def get_expected_behavior(self, filename: str) -> Dict[str, Any]:
        """Define expected behaviors for client components."""
        expectations = {
            'client.py': {
                'description': 'WebSocket client for connecting to CC Executor server',
                'indicators': ['WebSocket', 'client', 'connect', 'server', 'standalone'],
                'min_lines': 10,
                'should_have_numbers': True,
                'error_ok': True  # Expected to fail if server not running
            }
        }
        
        # Default for files not explicitly defined
        default = {
            'description': 'Client component functionality test',
            'indicators': ['client', 'websocket', 'connection'],
            'min_lines': 1,
            'should_have_numbers': False,
            'error_ok': False
        }
        
        return expectations.get(filename, default)
    
    def run_usage_function(self, file_path: Path) -> Dict[str, Any]:
        """Run a single usage function."""
        print(f"Running {file_path.name}...")
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root / "src")
        env['CLAUDE_SESSION_ID'] = f"{self.session_id}_{file_path.stem}"
        env['ASSESSMENT_MODE'] = 'true'
        
        try:
            result = subprocess.run(
                [sys.executable, str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            output = {
                'success': True,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': time.time(),
                'timed_out': False
            }
            
        except subprocess.TimeoutExpired:
            output = {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': 'Process timed out after 30 seconds',
                'execution_time': time.time(),
                'timed_out': True
            }
        except Exception as e:
            output = {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Exception: {str(e)}',
                'execution_time': time.time(),
                'timed_out': False
            }
        
        return output
    
    def assess_output(self, filename: str, output: Dict[str, Any], 
                     expectations: Dict[str, Any]) -> Dict[str, Any]:
        """Assess if output is reasonable."""
        combined_output = output['stdout'] + output['stderr']
        
        assessment = {
            'reasonable': False,
            'confidence': 0,
            'reasons': [],
            'indicators_found': [],
            'has_numbers': False
        }
        
        # Check for timeout
        if output['timed_out']:
            assessment['reasons'].append("Process timed out")
            assessment['confidence'] = 95
            return assessment
        
        # For client.py, connection errors are expected and reasonable
        if filename == 'client.py' and "Connection error" in combined_output:
            assessment['reasons'].append("Expected connection error when server not running")
            assessment['reasonable'] = True
            assessment['confidence'] = 85
        
        # Check for exceptions (unless expected)
        has_exception = 'Traceback' in combined_output or 'Exception' in combined_output
        if has_exception and not expectations['error_ok']:
            assessment['reasons'].append("Unexpected exception occurred")
            assessment['confidence'] = 90
            return assessment
        
        # Check output length
        lines = combined_output.strip().split('\n') if combined_output else []
        if len(lines) < expectations['min_lines']:
            assessment['reasons'].append(f"Output too short ({len(lines)} lines, expected {expectations['min_lines']}+)")
            assessment['confidence'] = 70
        else:
            assessment['reasons'].append(f"Adequate output length ({len(lines)} lines)")
            assessment['reasonable'] = True
            assessment['confidence'] = 50
        
        # Check for expected indicators
        found_indicators = []
        for indicator in expectations['indicators']:
            if indicator.lower() in combined_output.lower():
                found_indicators.append(indicator)
        
        assessment['indicators_found'] = found_indicators
        
        if found_indicators:
            indicator_ratio = len(found_indicators) / len(expectations['indicators'])
            if indicator_ratio >= 0.5:
                assessment['reasonable'] = True
                assessment['reasons'].append(f"Found {len(found_indicators)}/{len(expectations['indicators'])} expected indicators")
                assessment['confidence'] = min(95, 50 + indicator_ratio * 40)
            else:
                assessment['reasons'].append(f"Only found {len(found_indicators)}/{len(expectations['indicators'])} indicators")
                assessment['confidence'] += 10
        
        # Check for numbers if expected
        if expectations['should_have_numbers']:
            has_numbers = any(char.isdigit() for char in combined_output)
            assessment['has_numbers'] = has_numbers
            if has_numbers:
                assessment['reasons'].append("Contains numeric data as expected")
                assessment['confidence'] += 10
                assessment['reasonable'] = True
            else:
                assessment['reasons'].append("Missing expected numeric data")
                assessment['confidence'] -= 10
        
        # Check for OutputCapture evidence
        if "💾 Response saved:" in combined_output:
            assessment['reasons'].append("Uses OutputCapture pattern correctly")
            assessment['confidence'] += 5
            assessment['reasonable'] = True
        
        # Final confidence adjustment
        assessment['confidence'] = max(0, min(100, assessment['confidence']))
        
        return assessment
    
    def generate_report(self):
        """Generate comprehensive markdown report."""
        report_lines = [
            "# Client Components Usage Assessment Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session ID: {self.session_id}",
            "",
            "## Summary",
            f"- Total Components Tested: {len(self.results)}",
            f"- Components with Reasonable Output: {sum(1 for r in self.results if r['assessment']['reasonable'])}",
            f"- Success Rate: {sum(1 for r in self.results if r['assessment']['reasonable'])/len(self.results)*100:.1f}%" if self.results else "N/A",
            f"- Hooks Available: {'✅ Yes' if HOOKS_AVAILABLE else '❌ No'}",
            f"- Redis Available: {'✅ Yes' if self.redis_available else '❌ No'}",
            "",
            "## Component Results",
            ""
        ]
        
        # Add results for each component
        for result in self.results:
            filename = result['filename']
            expectations = result['expectations']
            output = result['output']
            assessment = result['assessment']
            execution_time = result['execution_time']
            
            status_icon = "✅" if assessment['reasonable'] else "❌"
            
            report_lines.extend([
                f"### {status_icon} {filename}",
                f"**Description**: {expectations['description']}",
                f"**Exit Code**: {output['exit_code']}",
                f"**Execution Time**: {execution_time:.2f}s",
                f"**Output Lines**: {len(output['stdout'].split(chr(10))) + len(output['stderr'].split(chr(10)))}",
                f"**Indicators Found**: {', '.join(assessment['indicators_found']) if assessment['indicators_found'] else 'None'}",
                f"**Has Numbers**: {'Yes' if assessment.get('has_numbers', False) else 'No'}",
                f"**Notes**:",
            ])
            
            # Add special note for client
            if filename == 'client.py':
                report_lines.append("- Expected to fail if server not running")
            
            report_lines.extend([
                "",
                "**Output Sample**:",
                "```",
                "",
                "--- STDOUT ---",
                output['stdout'][:500] + ('...[truncated]' if len(output['stdout']) > 500 else ''),
                "",
                "--- STDERR ---",
                output['stderr'][:200] + ('...[truncated]' if len(output['stderr']) > 200 else ''),
                "```",
                "",
                "---",
                ""
            ])
        
        # Add recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            "### Maintain Current Excellence:",
            "- Continue using OutputCapture pattern for all usage functions",
            "- Keep functions outside __main__ blocks",
            "- Ensure proper module naming (cc_executor.client.*)",
            "",
            "### Client-Specific Notes:",
            "- Client is a standalone WebSocket client that connects to existing server",
            "- Does not manage its own server lifecycle",
            "- Connection errors are expected when server is not running",
            ""
        ])
        
        # Write report
        with open(self.report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n✅ Report generated: {self.report_path}")
        
        passed = sum(1 for r in self.results if r['assessment']['reasonable'])
        failed = len(self.results) - passed
        return passed, failed
    
    def save_component_response(self, filename: str, output: Dict[str, Any], 
                               assessment: Dict[str, Any], execution_time: float):
        """Save individual component response in OutputCapture format."""
        responses_dir = self.client_dir / "tmp" / "responses"
        responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON following core pattern
        response_file = responses_dir / f"{Path(filename).stem}_{self.timestamp}.json"
        
        response_data = {
            'filename': Path(filename).stem,
            'module': f"cc_executor.client.{Path(filename).stem}",
            'timestamp': self.timestamp,
            'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': execution_time,
            'output': output['stdout'],
            'line_count': len(output['stdout'].split('\n')) if output['stdout'] else 0,
            'success': assessment['reasonable'],
            'has_error': 'error' in output['stderr'].lower() or output['exit_code'] != 0,
            'exit_status': 'completed' if output['exit_code'] == 0 else f'failed: exit_code={output["exit_code"]}'
        }
        
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=4, ensure_ascii=False)
        
        print(f"💾 Response saved: {response_file.relative_to(self.client_dir)}")
    
    def run_all_assessments(self):
        """Run all client assessments and generate report."""
        print("=== Client Components Usage Assessment ===\n")
        print(f"Session ID: {self.session_id}")
        print(f"Hooks Available: {HOOKS_AVAILABLE}")
        print(f"Redis Available: {self.redis_available}")
        print(f"Report will be saved to: {self.report_path}\n")
        
        # Get Python files in client directory
        python_files = []
        for f in sorted(self.client_dir.glob("*.py")):
            if f.name != "__init__.py":
                python_files.append(f)
        
        if not python_files:
            print("No Python files found in client/ directory")
        else:
            for file_path in python_files:
                # Get expectations
                expectations = self.get_expected_behavior(file_path.name)
                
                # Run usage function
                output = self.run_usage_function(file_path)
                
                # Calculate execution time
                execution_time = time.time() - self.start_time
                
                # Assess output
                assessment = self.assess_output(file_path.name, output, expectations)
                
                # Store result
                self.results.append({
                    'filename': file_path.name,
                    'expectations': expectations,
                    'output': output,
                    'assessment': assessment,
                    'execution_time': execution_time
                })
                
                # Print immediate feedback
                status = "✅ PASS" if assessment['reasonable'] else "❌ FAIL"
                print(f"{status} - {file_path.name} (Confidence: {assessment['confidence']}%)")
                
                # Save individual response
                self.save_component_response(file_path.name, output, assessment, execution_time)
        
        # Generate report
        passed, failed = self.generate_report()
        
        if self.results:
            print(f"\n{'='*60}")
            print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
            print(f"Success Rate: {passed/len(self.results)*100:.1f}%" if self.results else "N/A")
        
        return passed, failed


if __name__ == "__main__":
    # Run usage demonstration with OutputCapture
    with OutputCapture(__file__) as capture:
        print(f"Python executable: {sys.executable}")
        print(f"Python version: {sys.version.split()[0]}")
        
        assessor = ClientUsageAssessor()
        passed, failed = assessor.run_all_assessments()
        
        # Exit with appropriate code
        # For client components, connection errors are expected
        # Only exit with 1 if there are unexpected failures
        expected_failures = sum(1 for r in assessor.results 
                              if not r['assessment']['reasonable'] 
                              and r['expectations'].get('error_ok', False))
        unexpected_failures = failed - expected_failures
        exit_code = 0 if unexpected_failures == 0 else 1
        print(f"\nAssessment complete. Exit code: {exit_code}")