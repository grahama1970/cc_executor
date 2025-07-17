#!/bin/bash

# integrate_cc_executor.sh - Integrate CC Executor with Logger Agent Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER_AGENT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CC_EXECUTOR_ROOT="/home/graham/workspace/experiments/cc_executor"

echo "🔗 Integrating CC Executor with Logger Agent Dashboard..."

# Check if CC Executor directory exists
if [ ! -d "$CC_EXECUTOR_ROOT" ]; then
    echo "❌ CC Executor not found at: $CC_EXECUTOR_ROOT"
    exit 1
fi

# Check if Logger Agent dashboard is set up
if [ ! -f "$LOGGER_AGENT_ROOT/.claude/hooks/send_event.py" ]; then
    echo "❌ Logger Agent dashboard not set up. Run setup_dashboard.sh first."
    exit 1
fi

# Create .claude directory in CC Executor if it doesn't exist
mkdir -p "$CC_EXECUTOR_ROOT/.claude"

# The hooks configuration is already in place at .claude/settings.json
echo "✅ CC Executor hooks configuration is set up at .claude/settings.json"

# Create a symlink to the hooks directory (alternative to copying)
# This ensures CC Executor always uses the latest hook scripts
if [ ! -L "$CC_EXECUTOR_ROOT/.claude/hooks" ]; then
    echo "🔗 Creating symlink to Logger Agent hooks..."
    ln -s "$LOGGER_AGENT_ROOT/.claude/hooks" "$CC_EXECUTOR_ROOT/.claude/hooks"
fi

# Create environment file for CC Executor to know about Logger Agent
cat > "$CC_EXECUTOR_ROOT/.claude/.env" << EOF
# Logger Agent Dashboard Configuration
LOGGER_AGENT_API_URL=http://localhost:8000
LOGGER_AGENT_PROJECT_ROOT=$LOGGER_AGENT_ROOT
EOF

# Update CC Executor's hook handling if needed
if [ -d "$CC_EXECUTOR_ROOT/src/cc_executor/hooks" ]; then
    echo "📝 Creating Logger Agent hook wrapper..."
    cat > "$CC_EXECUTOR_ROOT/src/cc_executor/hooks/logger_agent_hook.py" << 'EOF'
#!/usr/bin/env python3
"""
logger_agent_hook.py - Wrapper to send CC Executor events to Logger Agent Dashboard
"""

import subprocess
import json
import sys
import os

def send_to_logger_agent(event_type: str, data: dict):
    """Send event to Logger Agent Dashboard."""
    logger_agent_root = os.environ.get("LOGGER_AGENT_PROJECT_ROOT", 
                                       "/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent")
    
    send_event_script = os.path.join(logger_agent_root, ".claude/hooks/send_event.py")
    
    if os.path.exists(send_event_script):
        cmd = [
            "uv", "run", send_event_script,
            "--source-app", "cc-executor",
            "--event-type", event_type
        ]
        
        # Add chat flag for Stop events
        if event_type == "Stop":
            cmd.append("--add-chat")
        
        try:
            # Send data via stdin
            result = subprocess.run(
                cmd,
                input=json.dumps(data),
                text=True,
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                print(f"Warning: Failed to send event to Logger Agent: {result.stderr}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error sending to Logger Agent: {e}", file=sys.stderr)

if __name__ == "__main__":
    # Read event data from stdin
    try:
        data = json.load(sys.stdin)
        event_type = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
        send_to_logger_agent(event_type, data)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
EOF
fi

echo ""
echo "✅ Integration complete!"
echo ""
echo "To use Logger Agent Dashboard with CC Executor:"
echo ""
echo "1. Start the Logger Agent Dashboard:"
echo "   cd $LOGGER_AGENT_ROOT"
echo "   ./scripts/start_dashboard_background.sh"
echo ""
echo "2. Run Claude Code in CC Executor directory:"
echo "   cd $CC_EXECUTOR_ROOT"
echo "   claude <your command>"
echo ""
echo "3. View events in real-time at:"
echo "   http://localhost:5173"
echo ""
echo "Note: The dashboard must be running to capture events!"