FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed by shapely / pillow)
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache — only reruns on requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Create storage directory
RUN mkdir -p /storage/plans

# Expose port
EXPOSE 8000

# Start server with hot reload in dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]