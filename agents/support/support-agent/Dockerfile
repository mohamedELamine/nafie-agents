FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 support && \
    chown -R support:support /app
USER support

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]