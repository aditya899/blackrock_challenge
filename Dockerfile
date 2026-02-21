# docker build -t blk-hacking-ind-aditya-raj .
# Using Alpine Linux for minimal image size and enhanced security
FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies required for Python packages
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create non-root user for security
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser

# Expose the application port
EXPOSE 5477

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5477/blackrock/challenge/v1/performance || exit 1

# Run the application
CMD ["python", "app.py"]
