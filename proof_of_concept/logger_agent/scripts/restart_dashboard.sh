#!/bin/bash

# restart_dashboard.sh - Restart the Logger Agent Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Restarting Logger Agent Dashboard..."
echo ""

# Stop existing services
"$SCRIPT_DIR/stop_dashboard.sh"

echo ""
sleep 2

# Start services again
"$SCRIPT_DIR/start_dashboard_background.sh"