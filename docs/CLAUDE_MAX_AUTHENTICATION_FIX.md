# Claude Max Plan Authentication in Docker

## The Problem

When using Claude Max Plan (Claude Code environment), authentication is stored in `~/.claude/.credentials.json` with restrictive permissions (600). Docker containers running as `appuser` cannot read this file.

## The Solution

### Option 1: Copy credentials into container (Recommended for local dev)

```bash
# Create a temporary credentials file with proper permissions
cp ~/.claude/.credentials.json /tmp/claude_credentials.json
chmod 644 /tmp/claude_credentials.json

# Update docker-compose.yml to mount this file
# Add to volumes section:
# - /tmp/claude_credentials.json:/home/appuser/.claude/.credentials.json:ro
```

### Option 2: Run container as your user

```bash
# Add to docker-compose.yml environment section:
# user: "${UID}:${GID}"

# Then run:
export UID=$(id -u)
export GID=$(id -g)
docker compose up -d
```

### Option 3: Use host network mode (simplest for local dev)

```bash
# Add to cc_execute service in docker-compose.yml:
# network_mode: host

# This allows the container to use host's authentication directly
```

## Quick Fix for Testing

```bash
# Make credentials readable (temporarily)
chmod 644 ~/.claude/.credentials.json

# Start Docker
cd deployment
docker compose up -d

# Restore permissions after testing
chmod 600 ~/.claude/.credentials.json
```

## Verification

Test if Claude CLI works in container:

```bash
docker exec -it cc_execute claude -p "Say hello"
```

If it hangs, authentication is not working. If it responds, you're good to go!