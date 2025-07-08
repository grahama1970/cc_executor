#!/usr/bin/env python3
"""
Create comprehensive stress test report with all raw responses.
"""

import json
import os
from datetime import datetime
from pathlib import Path

def create_comprehensive_report():
    """Generate a comprehensive report of all cc_execute tests."""
    report_lines = []
    report_lines.append("# CC_EXECUTOR Comprehensive Stress Test Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\n## Executive Summary")
    
    # Find all response files from today
    response_dir = Path("tmp/responses")
    today = datetime.now().strftime('%Y%m%d')
    response_files = sorted(response_dir.glob(f"cc_execute_*_{today}_*.json"))
    
    report_lines.append(f"\nTotal executions today: {len(response_files)}")
    report_lines.append("\n## Detailed Results with Raw Responses")
    
    # Process each response file
    for i, response_file in enumerate(response_files, 1):
        report_lines.append(f"\n### Test {i}: {response_file.name}")
        
        try:
            with open(response_file) as f:
                data = json.load(f)
            
            # Basic info
            report_lines.append(f"\n**Session ID**: {data.get('session_id', 'N/A')}")
            report_lines.append(f"**Timestamp**: {data.get('timestamp', 'N/A')}")
            report_lines.append(f"**Execution UUID**: {data.get('execution_uuid', 'N/A')}")
            report_lines.append(f"**Exit Code**: {data.get('return_code', 'N/A')}")
            report_lines.append(f"**Execution Time**: {data.get('execution_time', 0):.2f}s")
            
            # Full task (no truncation)
            report_lines.append("\n**Complete Task**:")
            report_lines.append("```")
            report_lines.append(data.get('task', 'No task found'))
            report_lines.append("```")
            
            # Raw output
            report_lines.append("\n**Raw Output**:")
            output = data.get('output', '')
            if output:
                report_lines.append("```")
                report_lines.append(output)
                report_lines.append("```")
            else:
                report_lines.append("*No output captured*")
            
            # Parsed JSON if available
            if output and output.strip().startswith('{'):
                try:
                    parsed = json.loads(output)
                    report_lines.append("\n**Prettified JSON Output**:")
                    report_lines.append("```json")
                    report_lines.append(json.dumps(parsed, indent=2))
                    report_lines.append("```")
                except:
                    pass
            
            # Error output if any
            if data.get('error'):
                report_lines.append("\n**Error Output**:")
                report_lines.append("```")
                report_lines.append(str(data['error']))
                report_lines.append("```")
            
            # Verification
            report_lines.append("\n**Verification Commands**:")
            report_lines.append("```bash")
            report_lines.append(f"# Verify this execution UUID in transcripts")
            report_lines.append(f'rg "{data.get("execution_uuid", "")}" ~/.claude/projects/-*/*.jsonl | wc -l')
            report_lines.append(f"\n# View the raw response file")
            report_lines.append(f"cat {response_file.absolute()}")
            report_lines.append("```")
            
        except Exception as e:
            report_lines.append(f"\n**Error reading file**: {e}")
        
        report_lines.append("\n" + "="*80)
    
    # Find the game engine results file
    game_results_file = Path("game_engine_algorithm_competition_results.json")
    if game_results_file.exists():
        report_lines.append("\n## Game Engine Algorithm Competition Results")
        try:
            with open(game_results_file) as f:
                game_data = json.load(f)
            report_lines.append("\n**Full Competition Results**:")
            report_lines.append("```json")
            report_lines.append(json.dumps(game_data, indent=2))
            report_lines.append("```")
        except Exception as e:
            report_lines.append(f"\nError reading game results: {e}")
    
    # Assessment reports
    report_lines.append("\n## Assessment Reports Generated")
    assessment_files = sorted(response_dir.glob(f"CC_EXECUTE_ASSESSMENT_REPORT_{today}_*.md"))
    for assessment_file in assessment_files:
        report_lines.append(f"\n- {assessment_file.name}")
        with open(assessment_file) as f:
            content = f.read()
        report_lines.append("```markdown")
        report_lines.append(content)
        report_lines.append("```")
    
    # Write the report
    report_path = f"CC_EXECUTOR_COMPREHENSIVE_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ Comprehensive report created: {report_path}")
    print(f"   Total tests documented: {len(response_files)}")
    print(f"   Report size: {os.path.getsize(report_path):,} bytes")
    
    return report_path

if __name__ == "__main__":
    create_comprehensive_report()
