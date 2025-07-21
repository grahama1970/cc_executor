#!/usr/bin/env python3
"""
Verification script to prove MCP tool execution is not hallucinated.

This shows how to check:
1. MCP logs for tool execution
2. Posthook reports for detailed info
3. Claude transcripts for proof
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

def verify_mcp_execution(test_run_id):
    """Verify that MCP tools were actually executed."""
    
    print(f"=== VERIFYING MCP EXECUTION ===")
    print(f"Test Run ID: {test_run_id}")
    print("=" * 50)
    
    # 1. Check MCP logs
    print("\n1. CHECKING MCP LOGS:")
    mcp_log_dir = Path.home() / ".claude" / "mcp_logs"
    if mcp_log_dir.exists():
        for log_file in mcp_log_dir.glob("arango-tools_*.log"):
            print(f"\nChecking {log_file.name}:")
            try:
                result = subprocess.run(
                    ["grep", "-n", test_run_id, str(log_file)],
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print("✓ FOUND in MCP logs:")
                    print(result.stdout[:500])  # First 500 chars
                else:
                    print("✗ Not found in this log")
            except Exception as e:
                print(f"Error checking log: {e}")
    
    # 2. Check posthook reports
    print("\n2. CHECKING POSTHOOK REPORTS:")
    posthook_dir = Path.home() / ".claude" / "mcp_debug_reports"
    if posthook_dir.exists():
        latest_reports = sorted(posthook_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for report in latest_reports:
            print(f"\nChecking {report.name}:")
            try:
                with open(report) as f:
                    data = json.load(f)
                    content = json.dumps(data)
                    if test_run_id in content:
                        print("✓ FOUND in posthook report:")
                        # Show relevant section
                        for key in ["tool_name", "tool_input", "tool_output", "errors"]:
                            if key in data:
                                print(f"  {key}: {str(data[key])[:100]}...")
                        break
            except Exception as e:
                print(f"Error reading report: {e}")
    
    # 3. Check Claude transcript
    print("\n3. CHECKING CLAUDE TRANSCRIPT:")
    transcript_dir = Path.home() / ".claude" / "projects"
    project_dir = transcript_dir / "-home-graham-workspace-experiments-cc-executor"
    
    if project_dir.exists():
        # Get the most recent transcript
        transcripts = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if transcripts:
            latest = transcripts[0]
            print(f"Checking {latest.name}:")
            
            cmd = f"grep '{test_run_id}' {latest} | tail -5"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                print("✓ FOUND in transcript:")
                # Parse and show relevant parts
                for line in result.stdout.strip().split('\n'):
                    try:
                        entry = json.loads(line)
                        if 'toolUseResult' in entry:
                            print(f"  Tool Result: {str(entry['toolUseResult'])[:200]}...")
                        elif 'toolName' in entry:
                            print(f"  Tool Used: {entry['toolName']}")
                    except:
                        pass
            else:
                print("✗ Not found in transcript")
    
    # 4. Summary
    print("\n=== VERIFICATION SUMMARY ===")
    print("If the test ID appears in all three locations, execution is verified.")
    print("If not found, the execution may have been hallucinated.")
    
    # Show quick verification command
    print(f"\nQuick verification command:")
    print(f"rg '{test_run_id}' ~/.claude/mcp_logs/ ~/.claude/mcp_debug_reports/ ~/.claude/projects/-*/*.jsonl")

if __name__ == "__main__":
    # You would pass the actual test run ID here
    test_id = "MCP_ARANGO_TEST_20250718_073103_1752838263128"
    verify_mcp_execution(test_id)