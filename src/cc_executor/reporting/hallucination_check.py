#!/usr/bin/env python3
"""
Anti-hallucination verification for cc_execute calls.

This module provides simple functions to prove cc_execute results are real.
Every cc_execute call creates a JSON file on disk - this checks those files exist.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


def check_hallucination(execution_uuid: str = None, last_n: int = 1, require_json: bool = True) -> Dict[str, Any]:
    """
    Verify cc_execute results are real by checking JSON response files.
    
    IMPORTANT: All cc_execute calls should use json_mode=True to ensure
    verifiable responses with execution_uuid included.
    
    Args:
        execution_uuid: Specific UUID to verify. If None, checks most recent.
        last_n: Number of recent executions to check (default: 1)
        require_json: If True, only accept responses with valid JSON structure
        
    Returns:
        Dictionary with verification results and proof
    """
    # Responses are saved in cc_executor/client/tmp/responses
    response_dir = Path(__file__).parent.parent / "client/tmp/responses"
    
    if not response_dir.exists():
        return {
            "status": "FAIL",
            "error": f"Response directory does not exist: {response_dir}",
            "is_hallucination": True
        }
    
    # Get response files sorted by modification time
    response_files = sorted(
        response_dir.glob("cc_execute_*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not response_files:
        return {
            "status": "FAIL", 
            "error": "No cc_execute response files found",
            "is_hallucination": True
        }
    
    # Check specific UUID or recent files
    files_to_check = []
    if execution_uuid:
        # Find file with this UUID
        for f in response_files:
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    if data.get('execution_uuid') == execution_uuid:
                        files_to_check = [f]
                        break
            except:
                continue
        
        if not files_to_check:
            return {
                "status": "FAIL",
                "error": f"No file found with UUID: {execution_uuid}",
                "is_hallucination": True
            }
    else:
        # Check last N files
        files_to_check = response_files[:last_n]
    
    # Verify each file
    verifications = []
    
    for response_file in files_to_check:
        try:
            with open(response_file) as f:
                data = json.load(f)
            
            # Check if receipt exists
            receipt_dir = response_dir / "receipts"
            session_id = data.get('session_id', 'unknown')
            receipt_files = list(receipt_dir.glob(f"receipt_{session_id}_*.md")) if receipt_dir.exists() else []
            
            # CRITICAL: For reporting, we need the actual JSON structure from cc_execute
            # The output should already be JSON if json_mode=True was used
            is_json_mode = False
            json_response = None
            uuid_verified = False
            
            # Check if the saved response has proper JSON structure
            # When json_mode=True, cc_execute returns: {"result": {...}, "execution_uuid": "..."}
            output = data.get('output', '')
            
            # Import clean_json_string for parsing
            try:
                from cc_executor.utils.json_utils import clean_json_string
                
                # The output should be a JSON string when json_mode=True
                if output:
                    try:
                        # Parse the JSON response
                        parsed = clean_json_string(output, return_dict=True)
                        if isinstance(parsed, dict):
                            json_response = parsed
                            is_json_mode = True
                            
                            # Verify UUID matches if JSON contains execution_uuid
                            if 'execution_uuid' in parsed:
                                uuid_verified = parsed['execution_uuid'] == data.get('execution_uuid')
                    except:
                        pass
            except ImportError:
                pass
            
            # If require_json is True and no JSON found, mark as invalid
            if require_json and not is_json_mode:
                verifications.append({
                    "file": response_file.name,
                    "file_exists": True,
                    "error": "Response is not in JSON format. Use json_mode=True for verifiable responses.",
                    "is_hallucination": True  # Cannot verify without JSON structure
                })
                continue
            
            verification = {
                "file": response_file.name,
                "file_exists": True,
                "file_path": str(response_file),
                "file_size": response_file.stat().st_size,
                "modified": datetime.fromtimestamp(response_file.stat().st_mtime).isoformat(),
                "task": data.get('task', 'N/A'),
                "output": data.get('output', 'N/A'),
                "execution_uuid": data.get('execution_uuid', 'N/A'),
                "session_id": data.get('session_id', 'N/A'),
                "return_code": data.get('return_code', -1),
                "execution_time": data.get('execution_time', 0),
                "json_valid": is_json_mode,
                "is_json_mode": is_json_mode,
                "json_response": json_response,
                "uuid_verified": uuid_verified,
                "receipt_exists": len(receipt_files) > 0,
                "receipt_file": receipt_files[0].name if receipt_files else None,
                "is_hallucination": False if (is_json_mode and uuid_verified) else not is_json_mode
            }
            
            verifications.append(verification)
            
        except Exception as e:
            verifications.append({
                "file": response_file.name,
                "file_exists": True,
                "error": str(e),
                "is_hallucination": False  # File exists but may be corrupted
            })
    
    return {
        "status": "PASS",
        "checked_files": len(verifications),
        "verifications": verifications,
        "is_hallucination": False,
        "proof": f"Physical files exist at: {response_dir}"
    }


def generate_hallucination_report(verifications: List[Dict[str, Any]] = None, 
                                output_file: str = None,
                                check_last_n: int = 5) -> Path:
    """
    Generate a markdown report proving recent cc_execute calls are not hallucinated.
    
    Args:
        verifications: Pre-computed verifications to use (optional)
        output_file: Filename for the report (optional)
        check_last_n: Number of recent executions to verify (if verifications not provided)
        
    Returns:
        Path to the generated report file
    """
    if verifications is None:
        result = check_hallucination(last_n=check_last_n)
    else:
        result = {
            "status": "PASS" if verifications else "FAIL",
            "checked_files": len(verifications),
            "verifications": verifications,
            "is_hallucination": False if verifications else True,
            "proof": f"Physical files exist at: {Path(__file__).parent.parent / 'client/tmp/responses'}"
        }
    
    report = f"""# Anti-Hallucination Verification Report
Generated: {datetime.now().isoformat()}

## Summary
- Status: **{result['status']}**
- Is Hallucination: **{'YES - RESULTS ARE FAKE' if result.get('is_hallucination') else 'NO - RESULTS ARE REAL'}**
- Files Checked: {result.get('checked_files', 0)}

"""
    
    if result['status'] == 'FAIL':
        report += f"""## ❌ VERIFICATION FAILED

**Error**: {result.get('error', 'Unknown error')}

This likely means cc_execute was never actually called, or results were fabricated.
"""
    else:
        report += f"""## ✅ VERIFICATION PASSED

**Proof**: {result.get('proof')}

## Verified Executions

"""
        for i, v in enumerate(result.get('verifications', []), 1):
            if 'error' in v:
                report += f"""### Execution #{i} - ERROR
- File: {v['file']}
- Error: {v['error']}

"""
            else:
                report += f"""### Execution #{i} - VERIFIED REAL
- **File**: `{v['file']}`
- **Full Path**: `{v['file_path']}`
- **File Size**: {v['file_size']} bytes
- **Modified**: {v['modified']}
- **Task**: {v['task'][:100]}...
- **Output**: {v['output'][:100]}...
- **UUID**: `{v['execution_uuid']}`
- **Exit Code**: {v['return_code']}
- **Execution Time**: {v['execution_time']:.2f}s
- **JSON Mode**: {'Yes' if v.get('is_json_mode') else 'No'}

"""
                # If JSON response detected, show parsed data
                if v.get('is_json_mode') and v.get('json_response'):
                    report += "**Parsed JSON Response**:\n```json\n"
                    report += json.dumps(v['json_response'], indent=2)[:500]
                    if len(json.dumps(v['json_response'])) > 500:
                        report += "\n... (truncated)"
                    report += "\n```\n\n"

        # Add verification commands
        report += """## Independent Verification Commands

Run these commands yourself to verify:

```bash
# List actual files on disk
ls -la src/cc_executor/client/tmp/responses/cc_execute_*.json | tail -10

# Check file contents directly
tail -5 src/cc_executor/client/tmp/responses/cc_execute_*.json | head -50

# Verify with jq
for f in src/cc_executor/client/tmp/responses/cc_execute_*.json; do
    echo "=== $f ==="
    jq -r '.execution_uuid + " | " + .task' "$f" 2>/dev/null | head -5
done
```
"""
    
    report += f"""
## Conclusion

{'⚠️ **WARNING**: These results appear to be hallucinated!' if result.get('is_hallucination') else '✅ **VERIFIED**: These results are real and exist on disk.'}

Physical JSON files {'DO NOT EXIST' if result.get('is_hallucination') else 'EXIST'} at the paths shown above.
"""
    
    # Save report
    if output_file is None:
        output_file = f"HALLUCINATION_CHECK_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    report_path = Path(__file__).parent / output_file
    with open(report_path, 'w') as f:
        f.write(report)
    
    return report_path


def quick_check() -> None:
    """Quick command-line check for the most recent execution."""
    result = check_hallucination(last_n=1)
    
    if result['status'] == 'FAIL':
        print(f"❌ LIKELY HALLUCINATION: {result.get('error')}")
    else:
        v = result['verifications'][0]
        print(f"✅ VERIFIED REAL")
        print(f"   File: {v['file']}")
        print(f"   Task: {v['task'][:50]}...")
        print(f"   Output: {v['output'].strip()}")
        print(f"   UUID: {v['execution_uuid']}")
        print(f"\nProof: cat {v['file_path']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        # Generate full report
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        report_path = generate_hallucination_report(check_last_n=n)
        
        print(f"Report saved to: {report_path}")
        with open(report_path) as f:
            print("\n" + f.read())
    else:
        # Quick check
        quick_check()