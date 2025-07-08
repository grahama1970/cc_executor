# Docker Deployment Template

## Purpose
Generate Docker configurations for projects. Docker is well-established with billions of examples - use standard patterns unless the project has unique requirements.

## Template Instructions

### 1. Quick Analysis
Look at the project structure and use standard Docker patterns:
- Python + requirements.txt → python:3.x-slim base image
- Node + package.json → node:lts-alpine base image
- Multiple services → docker-compose.yml
- Database dependencies → add standard database containers

### 2. Only Ask When Truly Ambiguous

Most Docker decisions have standard answers. Only ask when you encounter genuine ambiguity:
- Multiple services that could be combined or separated
- Non-standard port configurations
- Special authentication requirements

### 3. Use Perplexity for Docker Best Practices

If confused about Docker patterns, use the perplexity-ask tool:
```python
mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": "Docker best practice for running FastAPI and WebSocket server - same container or separate?"
    }]
})
```

### 4. Generate Standard Configuration

Create standard Docker files based on well-established patterns:

**Dockerfile:**
- Use official base images (python:3.11-slim, node:lts-alpine)
- Multi-stage builds for smaller images
- Non-root user for security
- COPY requirements/package files first for layer caching

**docker-compose.yml:**
- Version 3.8+ for modern features
- Health checks on all services
- Named volumes for data persistence
- Explicit networks for service isolation

### 5. Test and Fix

Build and run. If it works, you're done. If not:
1. Check error message against common Docker issues
2. Use perplexity-ask for specific error resolution
3. Only ask the human if it's a project-specific decision

## Example: CC Executor Dockerization

```python
# Instead of asking "should FastAPI and WebSocket be in same container?"
# Use perplexity-ask to check best practice:

mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user", 
        "content": "Best practice: FastAPI on port 8000 and WebSocket server on port 8003 - same container or separate? Project is a code execution service."
    }]
})

# Then implement based on the answer
```

## Standard Patterns to Apply

1. **Python Web Apps**: 
   - python:3.11-slim base
   - **IMPORTANT**: Use the project's existing package manager:
     - If project uses `uv` and `pyproject.toml`: Install uv in Docker and use `uv pip install --system -e .`
     - If project has `requirements.txt`: Use standard `pip install -r requirements.txt`
     - DO NOT create a separate requirements.txt if the project uses pyproject.toml!
   - Run with uvicorn/gunicorn

2. **Multi-Process Containers**:
   - Use supervisord or a simple Python multiprocess script
   - Health checks for each internal service

3. **Development vs Production**:
   - Dev: Mount source code, enable hot reload
   - Prod: Copy code, run with optimizations

4. **Virtual Environments in Docker**:
   - **NEVER mount host venv into container** - symlinks will be broken
   - Use `--system` flag with pip/uv to install globally in container
   - If mounting source code, exclude venv: `- /app/.venv` in volumes
   - Set `DISABLE_VENV_WRAPPING=1` if code tries to wrap commands with venv activation

## Critical Docker Debugging Tips

1. **ALWAYS force rebuild when debugging**:
   ```bash
   docker compose build --no-cache service_name
   docker compose up -d --force-recreate service_name
   ```

2. **Container keeps restarting?**
   - Check logs: `docker logs container_name --tail 50`
   - Verify CMD/ENTRYPOINT paths are correct
   - Use `docker run --rm image_name ls -la /path` to check files

3. **Code changes not reflected?**
   - Docker caches layers - use `--no-cache` when building
   - Use `docker compose down` before rebuilding
   - Check if volumes are overwriting your changes

## Remember

Docker has been solved. Use existing patterns. Only deviate when the project has genuinely unique requirements. ALWAYS use the project's existing package management system (uv, poetry, pip) rather than creating duplicate dependency files.