#!/usr/bin/env python3
"""
Create raw report showing exactly what was captured - no interpretation.
"""

import json
from datetime import datetime
from pathlib import Path

def create_raw_report():
    """Generate a raw report showing exact captured responses."""
    report_lines = []
    report_lines.append("# CC_EXECUTOR RAW RESPONSE REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\nSHOWING EXACT RAW RESPONSES - NO INTERPRETATION\n")
    
    # Find all response files from today
    response_dir = Path("tmp/responses")
    today = datetime.now().strftime('%Y%m%d')
    response_files = sorted(response_dir.glob(f"cc_execute_*_{today}_*.json"))
    
    for response_file in response_files:
        report_lines.append("=" * 80)
        report_lines.append(f"FILE: {response_file}")
        report_lines.append("\nRAW FILE CONTENTS:")
        report_lines.append("```")
        
        # Read and show exact file contents
        with open(response_file, 'r') as f:
            raw_content = f.read()
        report_lines.append(raw_content)
        report_lines.append("```")
        
        # Parse and show output field specifically
        try:
            data = json.loads(raw_content)
            if 'output' in data:
                report_lines.append("\nOUTPUT FIELD ONLY:")
                report_lines.append("```")
                report_lines.append(data['output'])
                report_lines.append("```")
                
                # Check if output looks like JSON
                output = data['output'].strip()
                if output.startswith('{') or output.startswith('['):
                    report_lines.append("\nOUTPUT APPEARS TO BE JSON - ATTEMPTING PARSE:")
                    try:
                        parsed = json.loads(output)
                        report_lines.append("```json")
                        report_lines.append(json.dumps(parsed, indent=2))
                        report_lines.append("```")
                    except Exception as e:
                        report_lines.append(f"PARSE FAILED: {e}")
                else:
                    report_lines.append("\nOUTPUT IS NOT JSON")
        except Exception as e:
            report_lines.append(f"\nERROR READING FILE: {e}")
        
        report_lines.append("\n")
    
    # Write the report
    report_path = f"RAW_RESPONSES_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"Raw report created: {report_path}")
    print(f"Total response files: {len(response_files)}")
    
    return report_path

if __name__ == "__main__":
    create_raw_report()
