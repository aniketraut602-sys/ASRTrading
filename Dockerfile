# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (e.g. for TA-Lib if we were building it, or gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir to keep image small
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image.
COPY . ./

# Expose port for Web Dashboard
EXPOSE 8000

# Default command (Production Gunicorn)
CMD gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 0 --log-level debug --error-logfile - --access-logfile - asr_trading.web.server:app -k uvicorn.workers.UvicornWorker
