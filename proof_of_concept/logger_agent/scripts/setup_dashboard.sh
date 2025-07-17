#!/bin/bash

# setup_dashboard.sh - Set up the Logger Agent Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OBSERVABILITY_REPO="/home/graham/workspace/experiments/cc_executor/repos/claude-code-hooks-multi-agent-observability"

echo "🔧 Setting up Logger Agent Dashboard..."

# Check if observability repo exists
if [ ! -d "$OBSERVABILITY_REPO" ]; then
    echo "❌ Observability repo not found at: $OBSERVABILITY_REPO"
    echo "Please clone it first."
    exit 1
fi

# Copy Vue dashboard
echo "📋 Copying Vue dashboard..."
if [ ! -d "$PROJECT_ROOT/dashboard" ]; then
    cp -r "$OBSERVABILITY_REPO/apps/client" "$PROJECT_ROOT/dashboard"
    echo "✅ Dashboard copied"
else
    echo "⚠️  Dashboard directory already exists, skipping copy"
fi

# Copy and adapt hook scripts
echo "📋 Setting up Claude hooks..."
mkdir -p "$PROJECT_ROOT/.claude/hooks"

# Copy send_event.py
cp "$OBSERVABILITY_REPO/.claude/hooks/send_event.py" "$PROJECT_ROOT/.claude/hooks/"

# Create utils directory for summarizer
mkdir -p "$PROJECT_ROOT/.claude/hooks/utils"

# Create a simple summarizer (without AI dependencies for now)
cat > "$PROJECT_ROOT/.claude/hooks/utils/summarizer.py" << 'EOF'
def generate_event_summary(event_data):
    """Generate a simple summary of the event."""
    event_type = event_data.get('hook_event_type', 'Unknown')
    payload = event_data.get('payload', {})
    
    if event_type == 'PreToolUse':
        tool = payload.get('tool_name', 'Unknown')
        return f"Starting {tool} execution"
    elif event_type == 'PostToolUse':
        tool = payload.get('tool_name', 'Unknown')
        return f"Completed {tool} execution"
    elif event_type == 'Stop':
        return "Agent response completed"
    elif event_type == 'Notification':
        return "User notification"
    else:
        return f"{event_type} event"
EOF

# Create __init__.py
touch "$PROJECT_ROOT/.claude/hooks/utils/__init__.py"

# Update send_event.py to use logger_agent endpoint
sed -i "s|http://localhost:4000/events|http://localhost:8000/events|g" "$PROJECT_ROOT/.claude/hooks/send_event.py"

# Create settings.json for logger_agent
cat > "$PROJECT_ROOT/.claude/settings.json" << 'EOF'
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type PreToolUse"
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type PostToolUse"
      }]
    }],
    "Notification": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type Notification"
      }]
    }],
    "Stop": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type Stop --add-chat"
      }]
    }],
    "SubagentStop": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app logger-agent --event-type SubagentStop"
      }]
    }]
  }
}
EOF

# Update dashboard configuration
echo "⚙️  Updating dashboard configuration..."
cd "$PROJECT_ROOT/dashboard"

# Create .env file for dashboard
cat > .env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/stream
VITE_MAX_EVENTS_TO_DISPLAY=200
EOF

# Update API endpoints in the Vue app
if [ -f "src/composables/useWebSocket.ts" ]; then
    # Update WebSocket URL
    sed -i "s|ws://localhost:4000/stream|ws://localhost:8000/stream|g" src/composables/useWebSocket.ts
fi

# Update any hardcoded API URLs
find src -type f -name "*.ts" -o -name "*.vue" | xargs sed -i "s|http://localhost:4000|http://localhost:8000|g" 2>/dev/null || true

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$PROJECT_ROOT"
source .venv/bin/activate
uv add fastapi uvicorn websockets python-multipart

echo ""
echo "✅ Dashboard setup complete!"
echo ""
echo "To start the dashboard, run:"
echo "  ./scripts/start_dashboard.sh"
echo ""
echo "To use Claude hooks with this project:"
echo "  1. Make sure the dashboard is running"
echo "  2. Run Claude Code commands in this directory"
echo "  3. Watch events appear in real-time at http://localhost:5173"