# Live Odds Service - Dockerfile for Render.com
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create logs directory (though we'll use stdout on Render)
RUN mkdir -p logs

# Make Python scripts executable
RUN chmod +x *.py

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default PORT (Render will override with $PORT)
ENV PORT=8080

# Run the live odds cron service
CMD ["python3", "cron_live.py"]
