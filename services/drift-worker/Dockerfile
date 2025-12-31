FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libproj-dev \
    libgeos-dev \
    libnetcdf-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the worker
CMD ["python", "worker.py"]
