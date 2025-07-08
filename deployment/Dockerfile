FROM python:3.11-slim

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl git \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (uv installs to .local/bin, not .cargo/bin)
ENV PATH="/root/.local/bin:$PATH"

RUN useradd -m -s /bin/bash appuser
WORKDIR /app

# Copy the entire application
COPY . .

# Install dependencies and the package using uv
RUN uv pip install --system -e .

RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Set environment variable to disable venv wrapping in Docker
ENV DISABLE_VENV_WRAPPING=1

USER appuser

# Expose both ports
EXPOSE 8000 8003

# Run the startup script directly
CMD ["python", "deployment/start_services.py"]