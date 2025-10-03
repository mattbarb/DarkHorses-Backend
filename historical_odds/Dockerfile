FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make scripts executable
RUN chmod +x cron_historical.py backfill_historical.py run_historical.py

# Expose monitoring port
EXPOSE 5001

# Run the scheduler (which includes the monitor server)
CMD ["python3", "cron_historical.py"]
