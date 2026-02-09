# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any (e.g. for some pip packages)
# RUN apt-get update && apt-get install -y ...

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flask gunicorn

# Copy application code
COPY . .

# Expose port (Cloud Run defaults to 8080)
ENV PORT 8080
EXPOSE 8080

# Run with Gunicorn (Production Server)
# Workers: 1 is enough for this synchronous workload, maybe 2 for concurrency
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
