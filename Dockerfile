# Use Python 3.11 slim image
# Force rebuild: 2025-12-19-v3
FROM python:3.11-slim

# Install Node.js 18
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY simulador/requirements.txt simulador/
COPY simulador/frontend/package*.json simulador/frontend/

# Install dependencies (these layers will be cached if package files don't change)
RUN cd simulador/frontend && npm install
RUN pip install --no-cache-dir -r simulador/requirements.txt

# Copy source code (this layer changes frequently, so it's last)
COPY . .

# Build frontend from source (this will use the updated api.ts)
RUN cd simulador/frontend && npm run build && cd ../..

# Change to simulador directory
WORKDIR /app/simulador

# Expose port
EXPOSE 8080

# Start command - use Gunicorn with eventlet for WebSocket support (compatible with Flask-Sock)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--worker-class", "eventlet", "--workers", "1", "--timeout", "300", "colab_server:app"]
