#!/usr/bin/env python3
"""
transcript_helper.py - Helper functions for transcript verification

This module provides utilities to find and verify execution in Claude transcripts,
handling the directory name transformation correctly.
"""

import os
import subprocess
import json
import glob
from datetime import datetime
from pathlib import Path


def get_transcript_dir(project_path=None):
    """
    Get the correct transcript directory for a project.
    
    Claude transforms paths like:
    /home/graham/workspace/experiments/cc_executor 
    -> -home-graham-workspace-experiments-cc-executor
    
    Note: underscores stay as hyphens in the transcript name!
    """
    if project_path is None:
        project_path = os.getcwd()
    
    # Transform the path - note underscores become hyphens
    transcript_name = project_path.replace('_', '-').replace('/', '-')
    base_dir = Path.home() / '.claude' / 'projects'
    
    # Try exact match first
    exact_path = base_dir / transcript_name
    if exact_path.exists():
        return str(exact_path)
    
    # Try without leading dash
    if transcript_name.startswith('-'):
        alt_path = base_dir / transcript_name[1:]
        if alt_path.exists():
            return str(alt_path)
    
    # Search for similar
    pattern = f"*{os.path.basename(project_path).replace('_', '-')}*"
    matches = list(base_dir.glob(pattern))
    if matches:
        # Return most recently modified
        return str(max(matches, key=lambda p: p.stat().st_mtime))
    
    # Default to expected path
    return str(exact_path)


def verify_marker(marker, expected_output=None, verbose=False):
    """
    Verify a marker exists in the transcript with optional output checking.
    
    Returns: (verified: bool, details: dict)
    """
    transcript_dir = get_transcript_dir()
    
    if verbose:
        print(f"Checking transcript: {transcript_dir}")
    
    # Find all jsonl files
    jsonl_files = glob.glob(f"{transcript_dir}/*.jsonl")
    if not jsonl_files:
        return False, {"error": "No transcript files found", "transcript_dir": transcript_dir}
    
    # Search for marker
    cmd = ['rg', marker] + jsonl_files
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return False, {"error": "Marker not found", "marker": marker}
    
    # Parse results
    verified = False
    tool_results = []
    claims = []
    
    for line in result.stdout.strip().split('\n'):
        try:
            # Extract JSON part after filename
            json_str = line.split(':', 1)[1]
            data = json.loads(json_str)
            
            # Check for actual execution
            if 'toolUseResult' in data:
                stdout = data['toolUseResult'].get('stdout', '')
                stderr = data['toolUseResult'].get('stderr', '')
                
                if marker in stdout or marker in stderr:
                    verified = True
                    tool_results.append({
                        'stdout': stdout[:200] if stdout else None,
                        'stderr': stderr[:200] if stderr else None,
                        'exitCode': data['toolUseResult'].get('exitCode')
                    })
                    
                    # Check expected output if provided
                    if expected_output and expected_output in stdout:
                        tool_results[-1]['expected_found'] = True
            
            # Track claims
            elif data.get('role') == 'assistant' and marker in str(data.get('content', '')):
                claims.append(True)
                
        except (json.JSONDecodeError, IndexError):
            continue
    
    # Build result
    details = {
        'verified': verified,
        'transcript_dir': transcript_dir,
        'tool_results': tool_results,
        'claims_without_execution': len(claims) > 0 and not verified,
        'marker': marker
    }
    
    if expected_output:
        details['expected_output_found'] = any(
            r.get('expected_found', False) for r in tool_results
        )
    
    return verified, details


def check_hallucination(pattern, verbose=True):
    """
    Check if a pattern represents a hallucination (claimed but not executed).
    
    Returns: 'VERIFIED' | 'HALLUCINATED' | 'NOT_FOUND'
    """
    transcript_dir = get_transcript_dir()
    
    # Count claims vs reality
    claims_cmd = f'rg "{pattern}" {transcript_dir}/*.jsonl 2>/dev/null | grep -c \'"role":"assistant"\' || echo 0'
    reality_cmd = f'rg "{pattern}" {transcript_dir}/*.jsonl 2>/dev/null | grep -c \'toolUseResult\' || echo 0'
    
    claims_output = subprocess.getoutput(claims_cmd).strip()
    reality_output = subprocess.getoutput(reality_cmd).strip()
    
    # Handle multiline output from wc -l
    claims = int(claims_output.split('\n')[-1].split()[0] if claims_output else 0)
    reality = int(reality_output.split('\n')[-1].split()[0] if reality_output else 0)
    
    if verbose:
        print(f"Pattern: {pattern}")
        print(f"Claims: {claims}, Reality: {reality}")
        print(f"Transcript: {transcript_dir}")
    
    if reality > 0:
        return "VERIFIED"
    elif claims > 0:
        return "HALLUCINATED"
    else:
        return "NOT_FOUND"


def get_recent_executions(minutes=10, limit=20):
    """Get recent tool executions from transcript."""
    transcript_dir = get_transcript_dir()
    
    # Get recent files
    import time
    cutoff_time = time.time() - (minutes * 60)
    
    executions = []
    for jsonl_file in sorted(glob.glob(f"{transcript_dir}/*.jsonl"), 
                           key=os.path.getmtime, reverse=True):
        if os.path.getmtime(jsonl_file) < cutoff_time:
            break
            
        with open(jsonl_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if 'toolUseResult' in data:
                        executions.append({
                            'tool': data.get('message', {}).get('content', [{}])[0].get('name', 'unknown'),
                            'stdout': data['toolUseResult'].get('stdout', '')[:100],
                            'stderr': data['toolUseResult'].get('stderr', '')[:100],
                            'exitCode': data['toolUseResult'].get('exitCode'),
                            'timestamp': data.get('timestamp')
                        })
                        if len(executions) >= limit:
                            return executions
                except:
                    continue
    
    return executions


# Quick verification functions
def quick_verify(marker=None):
    """Quick marker verification with auto-generation."""
    if marker is None:
        marker = f"VERIFY_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        print(marker)
        return marker
    
    verified, details = verify_marker(marker)
    
    if verified:
        print(f"✅ VERIFIED: {marker}")
        if details.get('tool_results'):
            print(f"   Found in {len(details['tool_results'])} executions")
    else:
        print(f"❌ NOT VERIFIED: {marker}")
        if details.get('claims_without_execution'):
            print("   ⚠️  HALLUCINATION WARNING: Claimed but not executed!")
        print(f"   Transcript: {details.get('transcript_dir')}")
    
    return verified


if __name__ == "__main__":
    import sys
    
    # Command line interface
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            # Check hallucination
            pattern = sys.argv[2] if len(sys.argv) > 2 else "MARKER"
            result = check_hallucination(pattern)
            print(f"Result: {result}")
            sys.exit(0 if result == "VERIFIED" else 1)
            
        elif sys.argv[1] == "recent":
            # Show recent executions
            execs = get_recent_executions(minutes=30)
            for e in execs[:10]:
                print(f"{e['timestamp']} {e['tool']:20} exit={e['exitCode']} {e['stdout'][:50]}...")
                
        else:
            # Verify marker
            verified = quick_verify(sys.argv[1])
            sys.exit(0 if verified else 1)
    else:
        # Interactive mode
        print("Transcript Helper - Interactive Mode")
        print(f"Project: {os.getcwd()}")
        print(f"Transcript: {get_transcript_dir()}")
        print("\nUsage:")
        print("  python transcript_helper.py <marker>           # Verify marker")
        print("  python transcript_helper.py check <pattern>    # Check hallucination")
        print("  python transcript_helper.py recent             # Show recent executions")
        print("\nGenerating test marker...")
        quick_verify()