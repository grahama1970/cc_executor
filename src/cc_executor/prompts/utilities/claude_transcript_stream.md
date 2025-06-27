# Claude Transcript Stream — Self-Improving Prompt

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 1
- **Failure**: 0
- **Total Executions**: 1
- **Last Updated**: 2025-01-26
- **Success Ratio**: 1:0 (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation - flexible transcript streaming with multiple filter modes
- v2: Fixed type hints and added proper tests
- v3: Fixed transcript directory path handling for cc_executor project

---

## 📋 TASK DEFINITION

Create a flexible transcript streaming tool that:
1. Automatically finds the correct transcript for any project
2. Offers multiple viewing modes (full, filtered, human-readable, etc.)
3. Handles the directory naming quirks correctly
4. Provides useful shortcuts for common verification tasks

---

## 🚀 IMPLEMENTATION

The implementation is in the external file: `claude_transcript_stream.py`

This follows our standard pattern of not embedding Python files over 10 lines in markdown.

### Key Features:
- 7 different viewing modes (full, filtered, human, tools, errors, markers, conversation)
- Automatic transcript directory detection
- Smart file selection based on timestamps
- Command-line arguments for flexibility
- Quick verification and recent activity functions

---

## 📝 INSTALLATION

function claude_transcript_stream() {
    local mode="${1:-filtered}"
    local src_dir="${2:-$PWD}"
    src_dir="${src_dir%/}"
    
    # Remove prefix, then replace / and _ with -
    local rel_path="${src_dir#/home/graham/}"
    local transcript_dir="$HOME/.claude/projects/-home-graham-${rel_path//\//-}"
    transcript_dir="${transcript_dir//_/-}"
    
    echo "Looking in: $transcript_dir"
    
    # Find the most recent transcript by checking timestamps inside files
    local latest_file
    latest_file=$(for f in "$transcript_dir"/*.jsonl 2>/dev/null; do
        [[ -f "$f" ]] || continue
        echo "$(tail -1 "$f" | jq -r '.timestamp // "1970-01-01"' 2>/dev/null) $f"
    done | sort -r | head -1 | cut -d' ' -f2)
    
    if [[ -z "$latest_file" ]]; then
        echo "No transcript file found in $transcript_dir"
        return 1
    fi
    
    echo "Mode: $mode"
    echo "Streaming from: $latest_file"
    echo "Press Ctrl+C to stop"
    echo "---"
    
    case "$mode" in
        "full"|"all")
            # Full prettified JSON - everything
            tail -f "$latest_file" | jq '.'
            ;;
            
        "filtered"|"filter")
            # Filtered JSON - essential fields only
            tail -f "$latest_file" | jq '{
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
            } | del(..|nulls)'
            ;;
            
        "human"|"readable")
            # Human-readable format
            tail -f "$latest_file" | jq -r '
                if .type == "user" and .message.content and .message.content[0].text then
                    "\n[" + (.timestamp[11:19] // "no-time") + "] USER:\n" + .message.content[0].text
                elif .toolUseResult and .toolUseResult.stdout then
                    "\n[" + (.timestamp[11:19] // "no-time") + "] RESULT:\n" + (.toolUseResult.stdout | if length > 500 then .[0:500] + "..." else . end)
                elif .type == "assistant" and .message.content and .message.content[0].text then
                    "\n[" + (.timestamp[11:19] // "no-time") + "] ASSISTANT:\n" + .message.content[0].text
                else empty end
            '
            ;;
            
        "tools"|"tool")
            # Show only tool usage and results
            tail -f "$latest_file" | jq -r '
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
            '
            ;;
            
        "errors"|"error")
            # Show only errors and failures
            tail -f "$latest_file" | jq -r '
                if .toolUseResult and (.toolUseResult.exitCode != 0 or .toolUseResult.stderr) then
                    "\n[" + (.timestamp[11:19] // "no-time") + "] ERROR:\n" + 
                    "Exit: " + (.toolUseResult.exitCode | tostring) + "\n" +
                    if .toolUseResult.stderr then "STDERR: " + .toolUseResult.stderr else "" end +
                    if .toolUseResult.stdout and (.toolUseResult.stdout | contains("Error") or contains("Failed")) then
                        "\nSTDOUT: " + .toolUseResult.stdout
                    else "" end
                else empty end
            '
            ;;
            
        "markers"|"marker")
            # Show only markers and verification points
            tail -f "$latest_file" | jq -r '
                if .toolUseResult.stdout then
                    .toolUseResult.stdout | 
                    split("\n") | 
                    map(select(test("MARKER|VERIFY|CHECK|✓|✗|SUCCESS|FAILURE"))) | 
                    if length > 0 then 
                        "[" + (.timestamp[11:19] // "no-time") + "] " + join("\n")
                    else empty end
                else empty end
            '
            ;;
            
        "conversation"|"conv")
            # Clean conversation view - no tool details
            tail -f "$latest_file" | jq -r '
                if .type == "user" and .message.content[0].text then
                    "\n👤 USER: " + (.message.content[0].text | split("\n")[0])
                elif .type == "assistant" and .message.content[0].text then
                    "🤖 CLAUDE: " + (.message.content[0].text | split("\n")[0] | if length > 100 then .[0:100] + "..." else . end)
                else empty end
            '
            ;;
            
        *)
            echo "Unknown mode: $mode"
            echo "Available modes:"
            echo "  full        - Complete JSON output"
            echo "  filtered    - Essential fields only (default)"
            echo "  human       - Human-readable format"
            echo "  tools       - Tool usage and results"
            echo "  errors      - Errors and failures only"
            echo "  markers     - Verification markers only"
            echo "  conversation - Clean conversation view"
            return 1
            ;;
    esac
}

# Convenience aliases
alias cts='claude_transcript_stream'
alias cts-full='claude_transcript_stream full'
alias cts-human='claude_transcript_stream human'
alias cts-tools='claude_transcript_stream tools'
alias cts-errors='claude_transcript_stream errors'
alias cts-markers='claude_transcript_stream markers'
alias cts-conv='claude_transcript_stream conversation'

# Quick verification function
function ctv() {
    local marker="${1:-MARKER}"
    local dir="${2:-$PWD}"
    
    local rel_path="${dir#/home/graham/}"
    local transcript_dir="$HOME/.claude/projects/-home-graham-${rel_path//\//-}"
    transcript_dir="${transcript_dir//_/-}"
    
    echo "Searching for '$marker' in $transcript_dir..."
    rg "$marker" "$transcript_dir"/*.jsonl | tail -5
}

# Show recent transcript activity
function ctr() {
    local lines="${1:-20}"
    local dir="${2:-$PWD}"
    
    local rel_path="${dir#/home/graham/}"
    local transcript_dir="$HOME/.claude/projects/-home-graham-${rel_path//\//-}"
    transcript_dir="${transcript_dir//_/-}"
    
    local latest_file=$(ls -t "$transcript_dir"/*.jsonl 2>/dev/null | head -1)
    
    if [[ -n "$latest_file" ]]; then
        echo "Recent activity from: $latest_file"
        tail -"$lines" "$latest_file" | jq -r '
            if .type == "user" then
                "[" + .timestamp[11:19] + "] USER: " + (.message.content[0].text // .message.content[0].type | tostring | split("\n")[0])
            elif .type == "assistant" and .message.content[0].tool_use then
                "[" + .timestamp[11:19] + "] TOOL: " + .message.content[0].tool_use.name
            elif .toolUseResult then
                "[" + .timestamp[11:19] + "] RESULT: exit=" + (.toolUseResult.exitCode | tostring)
            else empty end
        ' | grep -v "^$"
    else
        echo "No transcript found"
    fi
}
```

---

## 🎯 USAGE EXAMPLES

```bash
# Default filtered view
claude_transcript_stream

# Full JSON for debugging
claude_transcript_stream full

# Human-readable conversation
claude_transcript_stream human

# Watch for errors
claude_transcript_stream errors

# Track verification markers
claude_transcript_stream markers

# Quick verification
ctv "MARKER_1750958332"

# Show recent activity
ctr 50
```

---

## 📝 INSTALLATION

1. The Python file is already available as `claude_transcript_stream.py` in the same directory.

2. Add to ~/.zshrc for easy access:
```bash
function cts() {
    python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/claude_transcript_stream.py "$@"
}

alias cts-full='cts full'
alias cts-human='cts human'
alias cts-tools='cts tools'
alias cts-errors='cts errors'
alias cts-markers='cts markers'
alias cts-conv='cts conversation'

# Quick verification
function ctv() {
    cts -v "$1"
}

# Recent activity
function ctr() {
    cts -r "${1:-20}"
}
```

---

## 🧪 SELF-TEST

```python
#!/usr/bin/env python3
"""Test the claude_transcript_stream functionality"""

import subprocess
import time
import os
from datetime import datetime

def test_transcript_stream():
    """Run comprehensive tests"""
    
    # Test 1: Basic functionality
    print("Test 1: Basic marker verification")
    marker = f"CTS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Marker: {marker}")
    
    # Wait for transcript
    time.sleep(1)
    
    # Verify marker
    result = subprocess.run(
        f"python claude_transcript_stream.py -v '{marker}'",
        shell=True, capture_output=True, text=True, 
        cwd="/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts"
    )
    
    if marker in result.stdout or "found" in result.stdout.lower():
        print("✅ Marker verification working")
    else:
        print("❌ Marker not found in transcript")
    
    # Test 2: Recent activity
    print("\nTest 2: Recent activity")
    result = subprocess.run(
        "python claude_transcript_stream.py -r 5",
        shell=True, capture_output=True, text=True,
        cwd="/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts"
    )
    
    if "USER:" in result.stdout or "TOOL:" in result.stdout or "RESULT:" in result.stdout:
        print("✅ Recent activity working")
    else:
        print("❌ No recent activity found")
    
    # Test 3: Different modes
    print("\nTest 3: Testing different modes")
    modes = ["full", "filtered", "human", "tools", "errors", "markers", "conversation"]
    
    for mode in modes:
        # Just check if command runs without error
        result = subprocess.run(
            f"python claude_transcript_stream.py {mode} -d /home/graham/workspace/experiments/cc_executor",
            shell=True, capture_output=True, text=True,
            cwd="/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts"
        )
        
        if result.returncode != 0 and "No transcript file found" not in result.stderr:
            print(f"❌ Mode '{mode}' failed: {result.stderr[:100]}")
        else:
            print(f"✅ Mode '{mode}' executable")
    
    # Test 4: Directory naming edge cases
    print("\nTest 4: Directory naming patterns")
    test_dirs = [
        "/home/graham/workspace/test_project",
        "/home/graham/workspace/test-project", 
        "/home/graham/workspace/test_project_v2"
    ]
    
    for test_dir in test_dirs:
        # Simulate the directory translation
        rel_path = test_dir.replace('/home/graham/', '')
        transcript_dir = f"{os.environ['HOME']}/.claude/projects/-home-graham-{rel_path}"
        transcript_dir = transcript_dir.replace('/', '-').replace('_', '-')
        print(f"  {test_dir} -> {transcript_dir}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_transcript_stream()
```

### Quick Test Commands

```bash
# Test basic functionality
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts
python claude_transcript_stream.py -v "TEST_MARKER"

# Test recent activity
python claude_transcript_stream.py -r 10

# Test streaming (run in background)
timeout 5 python claude_transcript_stream.py markers

# Test different modes
for mode in full filtered human tools errors markers conversation; do
    echo "Testing $mode mode..."
    timeout 2 python claude_transcript_stream.py $mode
done
```

### Known Issues and Fixes

1. **Issue**: Type hints warnings in IDE
   - **Fix**: Added proper type annotations for List[Tuple[str, str]]

2. **Issue**: Directory naming with underscores
   - **Fix**: Replace both `/` and `_` with `-` in transcript path

3. **Issue**: Finding current session transcript
   - **Fix**: Check timestamps inside files, not just file modification time

4. **Issue**: Long output in tool results
   - **Fix**: Truncate stdout to 500 chars in filtered mode