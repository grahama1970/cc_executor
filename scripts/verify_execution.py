#!/usr/bin/env python3
"""
Wrapper script to verify cc_execute calls.
This calls the reporting module to check for hallucinations.

Usage:
    python scripts/verify_execution.py       # Check last execution
    python scripts/verify_execution.py --last 5  # Check last 5
    python scripts/verify_execution.py --report  # Generate full report
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cc_executor.reporting import verify_cc_execute_calls, generate_hallucination_report

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify cc_execute executions')
    parser.add_argument('--last', type=int, default=1, help='Number of recent executions')
    parser.add_argument('--report', action='store_true', help='Generate full markdown report')
    
    args = parser.parse_args()
    
    if args.report:
        report = generate_hallucination_report(check_last_n=args.last)
        print(report)
    else:
        verify_cc_execute_calls(args.last)