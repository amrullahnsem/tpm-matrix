# =============================================================================
# EFLOW TPM Competency Matrix - Production Dockerfile
# Multi-stage / lightweight Python 3.12-slim container
# =============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=false \
    WORKERS=2 \
    MIGRATE_ON_STARTUP=true

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY seed/ ./seed/
COPY sql/ ./sql/
COPY run.py entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Persistent directory for SQLite database and PDF/Excel reports
RUN mkdir -p /app/data /app/data/reports

EXPOSE 8000

# Health check using the /healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "run.py", "--no-reload"]
