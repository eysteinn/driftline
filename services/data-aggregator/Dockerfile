FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create temp directory for data
RUN mkdir -p /tmp/gfs_wind_data /tmp/copernicus_ocean_data

# Set Python path
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "-m", "app.main"]
