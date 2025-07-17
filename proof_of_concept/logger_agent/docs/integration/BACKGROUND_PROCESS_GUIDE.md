# Dashboard Background Process Management

## Overview

The Logger Agent Dashboard can now be run as background processes, allowing you to continue using your terminal while the services run.

## Scripts

### 1. `start_dashboard_background.sh`
Starts both the API server and Vue dashboard as background processes.

**Features:**
- Creates PID files for process tracking
- Logs output to separate log files
- Checks if services are already running
- Automatically creates required directories

**Usage:**
```bash
./scripts/start_dashboard_background.sh
```

### 2. `stop_dashboard.sh`
Stops all dashboard services gracefully.

**Features:**
- Reads PID files to find processes
- Attempts graceful shutdown first
- Force kills if necessary
- Cleans up stale PID files

**Usage:**
```bash
./scripts/stop_dashboard.sh
```

### 3. `status_dashboard.sh`
Shows the current status of all services.

**Features:**
- Checks if processes are running
- Verifies ports are listening
- Shows recent log entries
- Displays resource usage (CPU, memory)
- Performs API health check

**Usage:**
```bash
./scripts/status_dashboard.sh
```

### 4. `restart_dashboard.sh`
Convenience script to restart all services.

**Usage:**
```bash
./scripts/restart_dashboard.sh
```

## File Locations

### PID Files
- API Server: `.pids/api_server.pid`
- Dashboard: `.pids/dashboard.pid`

### Log Files
- API Server: `logs/dashboard/api_server.log`
- Dashboard: `logs/dashboard/dashboard.log`

## Monitoring

### View Logs in Real-time
```bash
# Both logs
tail -f logs/dashboard/*.log

# API logs only
tail -f logs/dashboard/api_server.log

# Dashboard logs only
tail -f logs/dashboard/dashboard.log
```

### Check Process Status
```bash
# Full status report
./scripts/status_dashboard.sh

# Quick process check
ps aux | grep -E "(uvicorn|vite)"
```

### Check Port Usage
```bash
# Check if services are listening
lsof -i:8000  # API server
lsof -i:5173  # Vue dashboard
```

## Troubleshooting

### Service Won't Start
1. Check if port is already in use: `lsof -i:8000` or `lsof -i:5173`
2. Check for stale PID files: `ls .pids/`
3. View logs for errors: `tail -50 logs/dashboard/*.log`

### Service Crashes
1. Check logs for error messages
2. Ensure ArangoDB is running: `docker-compose ps`
3. Verify Python dependencies: `uv pip list`

### Can't Stop Service
1. Use status script to find PID: `./scripts/status_dashboard.sh`
2. Manually kill process: `kill -9 <PID>`
3. Remove PID file: `rm .pids/*.pid`

## Best Practices

1. **Always use the scripts** instead of manually starting processes
2. **Check status** before starting to avoid duplicate processes
3. **Monitor logs** for errors or warnings
4. **Graceful shutdown** using stop script when possible
5. **Regular restarts** if memory usage grows over time

## Integration with systemd (Optional)

For production deployments, you can create systemd services:

```ini
# /etc/systemd/system/logger-agent-api.service
[Unit]
Description=Logger Agent API Server
After=network.target arangodb.service

[Service]
Type=simple
User=graham
WorkingDirectory=/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent
Environment="PATH=/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/.venv/bin/python -m uvicorn src.api.dashboard_server:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl enable logger-agent-api
sudo systemctl start logger-agent-api
```