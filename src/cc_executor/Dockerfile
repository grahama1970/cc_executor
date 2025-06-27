FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core MCP implementation
COPY core/ ./core/

# Expose the WebSocket port
EXPOSE 8003

# Run the MCP WebSocket service
CMD ["python", "-m", "core.main", "--port", "8003"]