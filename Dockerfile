# Use Python 3.11 slim image
FROM python:3.11-slim

# Install Node.js 18
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Install frontend dependencies and build
RUN cd simulador/frontend && npm install && npm run build && cd ../..

# Install Python dependencies
RUN pip install --no-cache-dir -r simulador/requirements.txt

# Change to simulador directory
WORKDIR /app/simulador

# Expose port
EXPOSE 8080

# Start command
CMD ["python3", "colab_server.py"]
