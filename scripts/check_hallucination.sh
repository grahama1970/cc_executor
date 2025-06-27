#!/bin/bash
# check_hallucination.sh - Detect if Claude hallucinated about execution results

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <pattern> [transcript_dir]"
    echo "Example: $0 'BIDIRECTIONAL.*PASSED'"
    echo "Example: $0 'MARKER_20250625' ~/.claude/projects/-home-user-project"
    exit 1
fi

PATTERN="$1"
TRANSCRIPT_DIR="${2:-$HOME/.claude/projects/$(pwd | sed 's/\//-/g')}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Checking for: $PATTERN"
echo "Transcript: $TRANSCRIPT_DIR"
echo "---"

# Count mentions
all_mentions=$(rg "$PATTERN" "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | wc -l || echo 0)
claims=$(rg "$PATTERN" "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | grep -c '"role":"assistant"' || echo 0)
reality=$(rg "$PATTERN" "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | grep -c 'toolUseResult' || echo 0)

echo "Total mentions: $all_mentions"
echo "Claude claims: $claims"
echo "Actual results: $reality"

# Show actual outputs
if [ "$reality" -gt 0 ]; then
    echo -e "\n=== ACTUAL OUTPUTS ==="
    # Process each matching line
    grep "$PATTERN" "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | while IFS= read -r line; do
        # Extract JSON part (after filename:)
        json_part=$(echo "$line" | cut -d: -f2-)
        
        # Try to extract stdout
        stdout=$(echo "$json_part" | jq -r '.toolUseResult.stdout // empty' 2>/dev/null)
        stderr=$(echo "$json_part" | jq -r '.toolUseResult.stderr // empty' 2>/dev/null)
        
        if [ -n "$stdout" ] && [ "$stdout" != "empty" ]; then
            echo -e "${GREEN}STDOUT:${NC}"
            echo "$stdout" | grep -C2 "$PATTERN" || echo "$stdout" | head -10
            echo "---"
        fi
        
        if [ -n "$stderr" ] && [ "$stderr" != "empty" ]; then
            echo -e "${RED}STDERR:${NC}"
            echo "$stderr" | head -10
            echo "---"
        fi
    done
fi

# Verdict
echo -e "\n=== VERDICT ==="
if [ "$reality" -eq 0 ] && [ "$claims" -gt 0 ]; then
    echo -e "${RED}❌ HALLUCINATION DETECTED${NC}"
    echo "Claude claimed success but no actual results found in transcript"
    exit 1
elif [ "$reality" -gt 0 ]; then
    echo -e "${GREEN}✅ VERIFIED${NC}"
    echo "Pattern found in actual tool results"
    exit 0
else
    echo -e "${YELLOW}⚠️ NOT FOUND${NC}"
    echo "Pattern not mentioned anywhere in transcript"
    exit 2
fi