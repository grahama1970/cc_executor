#!/usr/bin/env python3
"""
verify_marker.py - Verify execution markers in Claude transcripts

Usage:
    python verify_marker.py [MARKER] [EXPECTED_OUTPUT]
    
Examples:
    python verify_marker.py
    python verify_marker.py MARKER_20250625_123456
    python verify_marker.py MARKER_20250625_123456 "Test PASSED"
"""

import os
import sys
import subprocess
import json
import glob
from datetime import datetime
from pathlib import Path

class TranscriptVerifier:
    def __init__(self):
        self.pwd = os.getcwd()
        self.transcript_dir = self._get_transcript_dir()
        
    def _get_transcript_dir(self):
        """Get the transcript directory for current project"""
        # Convert pwd to transcript format
        transcript_name = self.pwd.replace('/', '-')
        base_path = Path.home() / '.claude' / 'projects'
        
        # Try exact match first
        exact_path = base_path / transcript_name
        if exact_path.exists():
            return str(exact_path)
            
        # Try to find similar directories
        pattern = str(base_path / f"*{transcript_name}*")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
            
        # Fallback to most recent
        all_dirs = list(base_path.glob("*"))
        if all_dirs:
            return str(max(all_dirs, key=lambda p: p.stat().st_mtime))
            
        return str(base_path / transcript_name)
    
    def verify_marker(self, marker=None, expected_output=None):
        """Verify that a marker exists in transcript"""
        
        # Generate marker if not provided
        if not marker:
            marker = f"MARKER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
            print(f"Generated marker: {marker}")
        
        print(f"Verifying: {marker}")
        print(f"Transcript: {self.transcript_dir}")
        
        # Search for marker
        jsonl_files = glob.glob(f"{self.transcript_dir}/*.jsonl")
        if not jsonl_files:
            print(f"❌ No transcript files found in {self.transcript_dir}")
            return False
            
        found = False
        found_outputs = []
        
        for jsonl_file in jsonl_files:
            try:
                # Use grep for faster searching
                result = subprocess.run(
                    ['grep', marker, jsonl_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Parse matching lines
                    for line in result.stdout.strip().split('\n'):
                        try:
                            data = json.loads(line)
                            
                            # Check for tool results
                            if 'toolUseResult' in data:
                                stdout = data['toolUseResult'].get('stdout', '')
                                stderr = data['toolUseResult'].get('stderr', '')
                                
                                if marker in stdout:
                                    found = True
                                    found_outputs.append(('stdout', stdout))
                                    
                                if marker in stderr:
                                    found = True
                                    found_outputs.append(('stderr', stderr))
                                    
                            # Check assistant messages
                            elif data.get('role') == 'assistant':
                                content = str(data.get('content', ''))
                                if marker in content:
                                    found_outputs.append(('claim', content))
                                    
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                print(f"Error reading {jsonl_file}: {e}")
                
        # Report results
        if found:
            print(f"✅ VERIFIED: {marker} found in transcript")
            
            # Show actual outputs
            for output_type, content in found_outputs[:3]:  # Show first 3
                if output_type in ['stdout', 'stderr']:
                    print(f"\n=== Actual {output_type} ===")
                    # Extract relevant lines around marker
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if marker in line:
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            print('\n'.join(lines[start:end]))
                            break
                            
            # Check expected output
            if expected_output:
                expected_found = any(
                    expected_output in content 
                    for output_type, content in found_outputs 
                    if output_type in ['stdout', 'stderr']
                )
                
                if expected_found:
                    print(f"✅ Expected output found: {expected_output[:50]}...")
                else:
                    print(f"⚠️ Expected output NOT found: {expected_output}")
                    return False
                    
            return True
            
        else:
            print(f"❌ NOT VERIFIED: {marker} not found in transcript")
            
            # Check if we have claims without execution
            claims_only = any(
                output_type == 'claim' 
                for output_type, _ in found_outputs
            )
            
            if claims_only:
                print("⚠️ HALLUCINATION WARNING: Claude claimed it but didn't execute!")
                
            # Debug info
            print(f"\nDebug info:")
            print(f"- Checked {len(jsonl_files)} transcript files")
            print(f"- Most recent: {max(jsonl_files, key=os.path.getmtime) if jsonl_files else 'None'}")
            
            return False

def main():
    """Command line interface"""
    verifier = TranscriptVerifier()
    
    # Get arguments
    marker = sys.argv[1] if len(sys.argv) > 1 else None
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    
    # If no marker provided, just print one and exit
    if not marker:
        marker = f"MARKER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        print(marker)
        print(f"# Use this marker in your code, then verify with:")
        print(f"# python {sys.argv[0]} {marker}")
        return
    
    # Verify
    success = verifier.verify_marker(marker, expected)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()