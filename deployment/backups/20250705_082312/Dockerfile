FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

# Copy the unified startup script
COPY deployment/start_services.py /app/start_services.py
RUN chmod +x /app/start_services.py

RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

USER appuser

# Expose both ports
EXPOSE 8000 8003

# Run the unified startup script
CMD ["python", "/app/start_services.py"]