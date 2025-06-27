#!/usr/bin/env python3
"""Claude Transcript Stream - Flexible transcript viewer for Claude Code"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
from typing import Optional, List, Tuple

class TranscriptStreamer:
    """Stream Claude transcripts with multiple viewing modes"""
    
    def __init__(self, mode: str = "filtered", src_dir: Optional[str] = None):
        self.mode = mode
        self.src_dir = src_dir or os.getcwd()
        self.src_dir = self.src_dir.rstrip('/')
        
    def find_transcript_dir(self) -> str:
        """Find the correct transcript directory"""
        # For cc_executor, use the known path
        if 'cc_executor' in self.src_dir:
            return f"{os.environ['HOME']}/.claude/projects/-home-graham-workspace-experiments-cc-executor"
        
        # Otherwise, remove prefix, then replace / and _ with -
        rel_path = self.src_dir.replace('/home/graham/', '')
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-{rel_path}"
        transcript_dir = transcript_dir.replace('/', '-').replace('_', '-')
        return transcript_dir
    
    def find_latest_transcript(self, transcript_dir: str) -> Optional[str]:
        """Find the most recent transcript by checking timestamps inside files"""
        print(f"Looking in: {transcript_dir}")
        
        if not os.path.exists(transcript_dir):
            return None
            
        # Get all .jsonl files with their last timestamp
        files_with_time: List[Tuple[str, str]] = []
        for file in Path(transcript_dir).glob("*.jsonl"):
            try:
                # Read last line to get timestamp
                result = subprocess.run(
                    f"tail -1 '{file}' | jq -r '.timestamp // \"1970-01-01\"'",
                    shell=True, capture_output=True, text=True
                )
                timestamp = result.stdout.strip()
                if timestamp and timestamp != "1970-01-01":
                    files_with_time.append((timestamp, str(file)))
            except Exception:
                continue
        
        if not files_with_time:
            return None
            
        # Sort by timestamp and get the most recent
        files_with_time.sort(reverse=True)
        return files_with_time[0][1]
    
    def stream_full(self, file_path: str):
        """Stream full prettified JSON"""
        cmd = f"tail -f '{file_path}' | jq '.'"
        subprocess.run(cmd, shell=True)
    
    def stream_filtered(self, file_path: str):
        """Stream filtered JSON with essential fields only"""
        jq_filter = '''{
            timestamp: .timestamp[11:19],
            type: .type,
            message: (
                if .type == "user" then
                    .message.content[0].text // .message.content[0].type
                elif .type == "assistant" then
                    if .message.content[0].tool_use then
                        {tool: .message.content[0].tool_use.name, input: .message.content[0].tool_use.input}
                    else
                        .message.content[0].text
                    end
                else null
                end
            ),
            toolResult: (
                if .toolUseResult then
                    {
                        stdout: (.toolUseResult.stdout | if length > 500 then .[0:500] + "...[truncated]" else . end),
                        stderr: .toolUseResult.stderr,
                        exitCode: .toolUseResult.exitCode
                    }
                else null
                end
            )
        } | del(..|nulls)'''
        
        cmd = f"tail -f '{file_path}' | jq '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def stream_human(self, file_path: str):
        """Stream human-readable format"""
        jq_filter = r'''
            if .type == "user" and .message.content and .message.content[0].text then
                "\n[" + (.timestamp[11:19] // "no-time") + "] USER:\n" + .message.content[0].text
            elif .toolUseResult and .toolUseResult.stdout then
                "\n[" + (.timestamp[11:19] // "no-time") + "] RESULT:\n" + (.toolUseResult.stdout | if length > 500 then .[0:500] + "..." else . end)
            elif .type == "assistant" and .message.content and .message.content[0].text then
                "\n[" + (.timestamp[11:19] // "no-time") + "] ASSISTANT:\n" + .message.content[0].text
            else empty end
        '''
        
        cmd = f"tail -f '{file_path}' | jq -r '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def stream_tools(self, file_path: str):
        """Stream tool usage and results only"""
        jq_filter = r'''
            if .type == "assistant" and .message.content[0].tool_use then
                "\n[" + (.timestamp[11:19] // "no-time") + "] TOOL: " + .message.content[0].tool_use.name
            elif .toolUseResult then
                "[" + (.timestamp[11:19] // "no-time") + "] RESULT: " + 
                if .toolUseResult.exitCode then
                    "exit=" + (.toolUseResult.exitCode | tostring) + " " + 
                    (.toolUseResult.stdout | split("\n")[0] | if length > 80 then .[0:80] + "..." else . end)
                else
                    (.toolUseResult.stdout | split("\n")[0] | if length > 80 then .[0:80] + "..." else . end)
                end
            else empty end
        '''
        
        cmd = f"tail -f '{file_path}' | jq -r '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def stream_errors(self, file_path: str):
        """Stream errors and failures only"""
        jq_filter = r'''
            if .toolUseResult and (.toolUseResult.exitCode != 0 or .toolUseResult.stderr) then
                "\n[" + (.timestamp[11:19] // "no-time") + "] ERROR:\n" + 
                "Exit: " + (.toolUseResult.exitCode | tostring) + "\n" +
                if .toolUseResult.stderr then "STDERR: " + .toolUseResult.stderr else "" end +
                if .toolUseResult.stdout and (.toolUseResult.stdout | contains("Error") or contains("Failed")) then
                    "\nSTDOUT: " + .toolUseResult.stdout
                else "" end
            else empty end
        '''
        
        cmd = f"tail -f '{file_path}' | jq -r '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def stream_markers(self, file_path: str):
        """Stream verification markers only"""
        jq_filter = r'''
            if .toolUseResult.stdout then
                .toolUseResult.stdout | 
                split("\n") | 
                map(select(test("MARKER|VERIFY|CHECK|✓|✗|SUCCESS|FAILURE"))) | 
                if length > 0 then 
                    "[" + (.timestamp[11:19] // "no-time") + "] " + join("\n")
                else empty end
            else empty end
        '''
        
        cmd = f"tail -f '{file_path}' | jq -r '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def stream_conversation(self, file_path: str):
        """Stream clean conversation view"""
        jq_filter = r'''
            if .type == "user" and .message.content[0].text then
                "\n👤 USER: " + (.message.content[0].text | split("\n")[0])
            elif .type == "assistant" and .message.content[0].text then
                "🤖 CLAUDE: " + (.message.content[0].text | split("\n")[0] | if length > 100 then .[0:100] + "..." else . end)
            else empty end
        '''
        
        cmd = f"tail -f '{file_path}' | jq -r '{jq_filter}'"
        subprocess.run(cmd, shell=True)
    
    def run(self):
        """Run the transcript streamer"""
        transcript_dir = self.find_transcript_dir()
        latest_file = self.find_latest_transcript(transcript_dir)
        
        if not latest_file:
            print(f"No transcript file found in {transcript_dir}")
            return 1
        
        print(f"Mode: {self.mode}")
        print(f"Streaming from: {latest_file}")
        print("Press Ctrl+C to stop")
        print("---")
        
        try:
            if self.mode in ["full", "all"]:
                self.stream_full(latest_file)
            elif self.mode in ["filtered", "filter"]:
                self.stream_filtered(latest_file)
            elif self.mode in ["human", "readable"]:
                self.stream_human(latest_file)
            elif self.mode in ["tools", "tool"]:
                self.stream_tools(latest_file)
            elif self.mode in ["errors", "error"]:
                self.stream_errors(latest_file)
            elif self.mode in ["markers", "marker"]:
                self.stream_markers(latest_file)
            elif self.mode in ["conversation", "conv"]:
                self.stream_conversation(latest_file)
            else:
                print(f"Unknown mode: {self.mode}")
                print("Available modes:")
                print("  full        - Complete JSON output")
                print("  filtered    - Essential fields only (default)")
                print("  human       - Human-readable format")
                print("  tools       - Tool usage and results")
                print("  errors      - Errors and failures only")
                print("  markers     - Verification markers only")
                print("  conversation - Clean conversation view")
                return 1
        except KeyboardInterrupt:
            print("\nStopped.")
        
        return 0


def verify_marker(marker: str = "MARKER", src_dir: Optional[str] = None):
    """Quick verification of a marker in transcripts"""
    src_dir = src_dir or os.getcwd()
    src_dir = src_dir.rstrip('/')
    
    # Find transcript directory
    if 'cc_executor' in src_dir:
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-workspace-experiments-cc-executor"
    else:
        rel_path = src_dir.replace('/home/graham/', '')
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-{rel_path}"
        transcript_dir = transcript_dir.replace('/', '-').replace('_', '-')
    
    print(f"Searching for '{marker}' in {transcript_dir}...")
    cmd = f"rg '{marker}' '{transcript_dir}'/*.jsonl | tail -5"
    subprocess.run(cmd, shell=True)


def recent_activity(lines: int = 20, src_dir: Optional[str] = None):
    """Show recent transcript activity"""
    src_dir = src_dir or os.getcwd()
    src_dir = src_dir.rstrip('/')
    
    # Find transcript directory
    if 'cc_executor' in src_dir:
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-workspace-experiments-cc-executor"
    else:
        rel_path = src_dir.replace('/home/graham/', '')
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-{rel_path}"
        transcript_dir = transcript_dir.replace('/', '-').replace('_', '-')
    
    # Find latest file
    try:
        files = list(Path(transcript_dir).glob("*.jsonl"))
        if not files:
            print("No transcript found")
            return
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        print(f"Recent activity from: {latest_file}")
        
        jq_filter = r'''
            if .type == "user" then
                "[" + .timestamp[11:19] + "] USER: " + (.message.content[0].text // .message.content[0].type | tostring | split("\n")[0])
            elif .type == "assistant" and .message.content[0].tool_use then
                "[" + .timestamp[11:19] + "] TOOL: " + .message.content[0].tool_use.name
            elif .toolUseResult then
                "[" + .timestamp[11:19] + "] RESULT: exit=" + (.toolUseResult.exitCode | tostring)
            else empty end
        '''
        
        cmd = f"tail -{lines} '{latest_file}' | jq -r '{jq_filter}' | grep -v '^$'"
        subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Claude Transcript Stream - Flexible viewer")
    parser.add_argument('mode', nargs='?', default='filtered',
                       choices=['full', 'filtered', 'human', 'tools', 'errors', 'markers', 'conversation'],
                       help='Viewing mode (default: filtered)')
    parser.add_argument('-d', '--dir', help='Source directory (default: current)')
    parser.add_argument('-v', '--verify', metavar='MARKER', help='Verify a marker and exit')
    parser.add_argument('-r', '--recent', type=int, metavar='N', help='Show recent N activities and exit')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_marker(args.verify, args.dir)
        return 0
    
    if args.recent:
        recent_activity(args.recent, args.dir)
        return 0
    
    streamer = TranscriptStreamer(args.mode, args.dir)
    return streamer.run()


if __name__ == "__main__":
    # Self-test
    print("Testing transcript stream...")
    marker = f"CTS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Test marker: {marker}")
    
    # Wait for transcript
    time.sleep(1)
    
    # Verify
    verify_marker(marker)
    
    print("\n✅ If you see the marker above, transcript stream is working!")
    print("\nUsage: python claude_transcript_stream.py [mode]")
    print("Modes: full, filtered, human, tools, errors, markers, conversation")
    
    # Run main if not in test mode
    if len(sys.argv) > 1:
        sys.exit(main())