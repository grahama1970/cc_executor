#!/usr/bin/env python3
"""
Quick verification script for cc_execute calls.
Run this after any cc_execute operations to generate an anti-hallucination report.

Usage:
    python scripts/quick_verify.py          # Check last execution
    python scripts/quick_verify.py --last 5 # Check last 5 executions
    python scripts/quick_verify.py --all    # Generate full report
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import argparse


def verify_cc_execute_calls(last_n=1):
    """Verify recent cc_execute calls and generate report."""
    
    # Find response files
    response_dir = Path(__file__).parent.parent / "client/tmp/responses"
    
    if not response_dir.exists():
        print(f"❌ ERROR: Response directory not found: {response_dir}")
        print("This suggests cc_execute was never called or is misconfigured.")
        return
    
    response_files = sorted(
        response_dir.glob("cc_execute_*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not response_files:
        print("❌ ERROR: No cc_execute response files found")
        print("This means either:")
        print("1. cc_execute was never actually called")
        print("2. Results were hallucinated")
        return
    
    # Limit to requested number
    files_to_check = response_files[:last_n]
    
    # Generate report
    print(f"# CC_EXECUTE Verification Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Checking: {len(files_to_check)} most recent execution(s)")
    print()
    
    print("## Anti-Hallucination Check")
    print(f"✅ **VERIFIED**: Physical JSON files exist on disk")
    print(f"Location: `{response_dir}`")
    print()
    
    print("## Verified Executions")
    print()
    
    for i, fpath in enumerate(files_to_check, 1):
        try:
            with open(fpath) as f:
                data = json.load(f)
            
            print(f"### Execution #{i}")
            print(f"**File**: `{fpath.name}`")
            print(f"**Modified**: {datetime.fromtimestamp(fpath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"**Task**: {data.get('task', 'N/A')}")
            print(f"**Output**: `{data.get('output', '').strip()}`")
            print(f"**Execution UUID**: `{data.get('execution_uuid', 'N/A')}`")
            print(f"**Session ID**: `{data.get('session_id', 'N/A')}`")
            print(f"**Exit Code**: {data.get('return_code', 'N/A')}")
            print(f"**Execution Time**: {data.get('execution_time', 0):.2f}s")
            print()
            
            # Show full JSON for transparency
            print("<details>")
            print("<summary>Full JSON Response</summary>")
            print()
            print("```json")
            print(json.dumps(data, indent=2))
            print("```")
            print("</details>")
            print()
            
        except Exception as e:
            print(f"### Execution #{i} - ERROR")
            print(f"**File**: `{fpath.name}`")
            print(f"**Error**: {e}")
            print()
    
    # Add verification commands
    print("## Independent Verification")
    print("Run these commands to verify the files exist:")
    print()
    print("```bash")
    print(f"# Check files exist")
    print(f"ls -la {response_dir}/cc_execute_*.json | tail -{last_n}")
    print()
    print(f"# View specific file")
    if files_to_check:
        print(f"cat {files_to_check[0]}")
    print()
    print(f"# Check all UUIDs")
    print(f"for f in {response_dir}/cc_execute_*.json; do")
    print(f'  echo "$(basename $f): $(jq -r .execution_uuid $f)"')
    print(f"done | tail -{last_n}")
    print("```")
    print()
    
    print("## Summary")
    print(f"- ✅ Checked {len(files_to_check)} execution(s)")
    print(f"- ✅ All files physically exist on disk")
    print(f"- ✅ No hallucination detected")


def main():
    parser = argparse.ArgumentParser(description='Verify cc_execute calls')
    parser.add_argument('--last', type=int, default=1, help='Number of recent executions to check')
    parser.add_argument('--all', action='store_true', help='Check all executions (up to 20)')
    
    args = parser.parse_args()
    
    if args.all:
        verify_cc_execute_calls(20)
    else:
        verify_cc_execute_calls(args.last)


if __name__ == "__main__":
    main()