# Dockerfile for Render Deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Render sets PORT env var)
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
