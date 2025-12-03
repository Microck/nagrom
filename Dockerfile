FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create volume mount points
VOLUME ["/app/data", "/app/config"]

CMD ["python", "-m", "src"]