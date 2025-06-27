#!/bin/bash
# Hallucination checker for stress test summaries
# Reads JSON from stdin and checks for patterns in transcript

set -euo pipefail

# Read JSON from stdin
JSON_DATA=$(cat)

# Extract markers from JSON
MARKERS=$(echo "$JSON_DATA" | jq -r '.categories | to_entries[] | .value.tasks[] | select(.success == true) | .id' 2>/dev/null || echo "")

if [ -z "$MARKERS" ]; then
    echo "No successful tasks found in JSON"
    exit 1
fi

echo "Checking markers in transcript..."
echo "================================"

FAILED=0
for marker in $MARKERS; do
    echo -n "Checking $marker: "
    
    # Use the check_hallucination.sh script
    if bash src/cc_executor/prompts/commands/check_hallucination.sh "MARKER_.*_$marker" >/dev/null 2>&1; then
        echo "✅ VERIFIED"
    else
        echo "❌ NOT FOUND"
        FAILED=$((FAILED + 1))
    fi
done

echo "================================"
if [ "$FAILED" -eq 0 ]; then
    echo "✅ All markers verified"
    exit 0
else
    echo "❌ $FAILED markers not found in transcript"
    exit 1
fi