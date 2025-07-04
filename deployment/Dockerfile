# CC Executor Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CC_EXECUTOR_SHELL=bash \
    REDIS_URL=redis://redis:6379 \
    DEFAULT_PORT=8003

# Split package installation for better caching and debugging
# Install essential build tools first
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Redis tools separately
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm last (often the slowest)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Create necessary directories with proper ownership
RUN mkdir -p /app/logs /app/data /home/appuser/.claude && \
    chown -R appuser:appuser /app /home/appuser

# Copy project files as root
COPY pyproject.toml setup.py MANIFEST.in README.md ./
COPY src/ ./src/
COPY .claude-hooks.json ./

# Change ownership of copied files
RUN chown -R appuser:appuser /app

# Install CC Executor as root (for system packages)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Ensure logs directory is writable by appuser
RUN chown -R appuser:appuser /app/logs /app/data

# Switch to non-root user
USER appuser

# Expose WebSocket port
EXPOSE 8003

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Start CC Executor WebSocket server
CMD ["python", "-m", "cc_executor.core.websocket_handler"]